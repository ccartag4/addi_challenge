"""
One observable, replayable door to the Anthropic Messages API for structured calls.

Why a wrapper instead of SDK calls scattered through the pipeline:
* every live call is recorded in `evidence/llm_calls.jsonl` (usage, cache activity, latency,
  model that actually answered, stop reason, outcome) — never the customer text, never the key;
* every valid response is stored under `cache/` keyed by the exact request (model, effort,
  system prompt, user content, schema), so the pipeline replays offline, byte-identical,
  without a key (reviewers) and without paying twice (us); a prompt change changes the key;
* the failure modes the API documents are handled in one place: safety refusal, `max_tokens`
  truncation, output that does not validate, rate limits and server errors.

API facts this module relies on (Anthropic Python SDK 1.8.0, checked in the installed package,
not from memory — see HOW_I_WORKED 3.3 for why that matters):
* `client.beta.messages.create(..., output_config={"format": {"type": "json_schema", ...}})`
  makes the first text block valid JSON for the schema (structured outputs).
  `anthropic.transform_schema` removes the JSON-schema keywords the API rejects (maxLength,
  minimum, maxItems...) and moves them into descriptions; pydantic re-validates them here.
* `fallbacks="default"` with beta `server-side-fallback-2026-07-01`: when Claude Opus 5's safety
  classifiers decline a request, the API re-runs it on Anthropic's recommended substitute
  model inside the same call instead of returning `stop_reason == "refusal"`.
* Prompt caching is a prefix match: the system block carries `cache_control` and contains
  nothing volatile; `usage.cache_read_input_tokens` is the proof that it works (512-token
  minimum on Claude Opus 5, 4096 on Claude Haiku 4.5).
* Claude Opus 5 thinks by default (adaptive); `output_config.effort` is the cost lever;
  `temperature`/`top_p` are rejected on this model, so determinism comes from the cache.
* The SDK retries 429 / 5xx / connection errors with exponential backoff (`max_retries`).
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

import anthropic
from anthropic import transform_schema
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parents[1]           # deliverables/
DEFAULT_CACHE_DIR = ROOT / "cache"
DEFAULT_TRACE_PATH = ROOT / "evidence" / "llm_calls.jsonl"

STRUCTURED_OUTPUTS_BETA = "structured-outputs-2025-12-15"   # what messages.parse() sends
FALLBACKS_BETA = "server-side-fallback-2026-07-01"           # gates fallbacks="default"

MODES = ("auto", "live", "offline")
EFFORTS = ("low", "medium", "high", "xhigh", "max")

# Prices in USD per million tokens (Anthropic pricing page, September 2026). Cache writes cost
# 1.25x input, cache reads 0.1x input. Used only to report cost; nothing decides on it.
MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "claude-opus-5":    {"effort": True,  "fallbacks": True,  "input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write": 6.25},
    "claude-sonnet-5":  {"effort": True,  "fallbacks": False, "input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 2.50},
    "claude-haiku-4-5": {"effort": False, "fallbacks": False, "input": 1.0, "output": 5.0,  "cache_read": 0.10, "cache_write": 1.25},
}
UNKNOWN_PROFILE = {"effort": True, "fallbacks": False, "input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0}

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base class; the pipeline turns any of these into a routed-to-human record."""


class LLMUnavailable(LLMError):
    """No key, offline cache miss, authentication failure or an API error after retries."""


class OfflineCacheMiss(LLMUnavailable):
    pass


class LLMRefusal(LLMError):
    """The model (and any fallback) declined the request: stop_reason == 'refusal'."""


class LLMOutputInvalid(LLMError):
    """Two attempts produced output that was truncated or did not validate."""


@dataclass(frozen=True)
class LLMConfig:
    model: str = "claude-opus-5"
    effort: Optional[str] = "medium"        # None = do not send output_config.effort
    max_tokens: int = 4096                  # thinking + JSON; doubled once on truncation
    mode: str = "auto"                      # auto: replay cache, call live if a key exists
    cache_dir: Path = DEFAULT_CACHE_DIR
    trace_path: Optional[Path] = DEFAULT_TRACE_PATH
    max_retries: int = 4                    # SDK retries for 429 / 5xx / connection errors
    timeout_s: float = 120.0
    use_fallbacks: bool = True

    @staticmethod
    def from_env(**overrides: Any) -> "LLMConfig":
        """`.env` next to the package (git-ignored) then environment variables, then explicit
        overrides. Environment: LUMO_TRIAGE_MODEL, LUMO_TRIAGE_EFFORT, LUMO_TRIAGE_MODE."""
        load_dotenv(ROOT / ".env", override=False)
        kwargs: dict[str, Any] = {}
        for key, var in (("model", "LUMO_TRIAGE_MODEL"), ("effort", "LUMO_TRIAGE_EFFORT"), ("mode", "LUMO_TRIAGE_MODE")):
            value = os.environ.get(var, "").strip()
            if value:
                kwargs[key] = value
        kwargs.update({k: v for k, v in overrides.items() if v is not None})
        cfg = LLMConfig(**kwargs)
        if cfg.effort is not None and cfg.effort.lower() in ("none", "off", ""):
            cfg = replace(cfg, effort=None)
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {self.mode!r}")
        if self.effort is not None and self.effort not in EFFORTS:
            raise ValueError(f"effort must be one of {EFFORTS} or None, got {self.effort!r}")

    @property
    def profile(self) -> dict[str, Any]:
        return MODEL_PROFILES.get(self.model, UNKNOWN_PROFILE)


@dataclass
class LLMResult:
    text: str                       # first text block: the JSON document
    stop_reason: Optional[str]
    served_by: Optional[str]        # model that answered (differs after a fallback)
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    latency_ms: int
    from_cache: bool                # replayed from disk, no API call
    fallback_used: bool
    request_id: Optional[str]
    cost_usd: float                 # cost of the call when it was made
    refusal: Optional[str] = None   # category / explanation when stop_reason == refusal


def json_schema_for(output_type: Type[BaseModel]) -> dict[str, Any]:
    """The schema actually sent: pydantic's, after the SDK's transformation."""
    return transform_schema(output_type.model_json_schema())


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LLMClient:
    """Structured calls with caching, tracing and failure handling. Thread-safe."""

    def __init__(self, cfg: LLMConfig, client: Any = None):
        cfg.validate()
        self.cfg = cfg
        self._client = client                # injectable for tests (anything with .beta.messages.create)
        self._lock = threading.Lock()
        self.calls = 0                       # live API calls made by this client
        self.replays = 0                     # responses served from the on-disk cache
        self.spent_usd = 0.0                 # cost incurred by this process
        self.touched: set[Path] = set()      # cache files read or written by this client (for pruning)

    # ------------------------------------------------------------------ mode and SDK
    @property
    def has_key(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

    def live_allowed(self) -> bool:
        if self.cfg.mode == "offline":
            return False
        if self.cfg.mode == "live":
            return True
        return self.has_key or self._client is not None

    def _sdk(self) -> Any:
        if self._client is None:
            if not self.has_key:
                raise LLMUnavailable(
                    "ANTHROPIC_API_KEY is not set. Put it in deliverables/.env (see .env.example) "
                    "or run with LUMO_TRIAGE_MODE=offline to replay the committed cache."
                )
            self._client = anthropic.Anthropic(max_retries=self.cfg.max_retries, timeout=self.cfg.timeout_s)
        return self._client

    # ------------------------------------------------------------------ request shape
    def build_request(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Everything except max_tokens. The system block is the cached prefix; the user turn
        is the varying suffix, so it carries no cache marker."""
        profile = self.cfg.profile
        output_config: dict[str, Any] = {"format": {"type": "json_schema", "schema": schema}}
        if self.cfg.effort and profile["effort"]:
            output_config["effort"] = self.cfg.effort
        request: dict[str, Any] = {
            "model": self.cfg.model,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": user}],
            "output_config": output_config,
            "betas": [STRUCTURED_OUTPUTS_BETA],
        }
        if self.cfg.use_fallbacks and profile["fallbacks"]:
            request["fallbacks"] = "default"
            request["betas"] = [STRUCTURED_OUTPUTS_BETA, FALLBACKS_BETA]
        return request

    def _cache_path(self, label: str, item_id: str, key: str) -> Path:
        return self.cfg.cache_dir / _safe(self.cfg.model) / _safe(label) / f"{_safe(item_id)}__{key}.json"

    # ------------------------------------------------------------------ main entry point
    def structured_call(self, *, label: str, item_id: str, system: str, user: str, output_type: Type[T]) -> tuple[T, LLMResult]:
        schema = json_schema_for(output_type)
        request = self.build_request(system, user, schema)
        key = _fingerprint({"model": request["model"], "effort": request["output_config"].get("effort"),
                            "system": system, "user": user, "schema": schema})
        path = self._cache_path(label, item_id, key)

        if self.cfg.mode != "live":
            cached = self._read_cache(path, key)
            if cached is not None:
                result = self._result_from_body(cached["response"], from_cache=True,
                                                latency_ms=int(cached.get("latency_ms", 0)),
                                                request_id=cached.get("request_id"),
                                                cost_usd=float(cached.get("cost_usd", 0.0)))
                parsed = output_type.model_validate_json(result.text)   # was valid when stored
                with self._lock:
                    self.replays += 1
                    self.touched.add(path)
                return parsed, result

        if not self.live_allowed():
            raise OfflineCacheMiss(
                f"{item_id}: no cached response for this exact request and live calls are not "
                f"allowed (mode={self.cfg.mode}, key={'present' if self.has_key else 'absent'})."
            )

        max_tokens = self.cfg.max_tokens
        last_error = "unknown"
        for attempt in (1, 2):
            result = self._call(request, max_tokens, label, item_id, attempt)
            if result.stop_reason == "refusal":
                raise LLMRefusal(f"{item_id}: the model declined the request ({result.refusal or 'no details'}).")
            if result.stop_reason == "max_tokens":
                last_error = f"truncated at max_tokens={max_tokens}"
                max_tokens *= 2
                continue
            try:
                parsed = output_type.model_validate_json(result.text)
            except ValidationError as e:
                first = e.errors()[0] if e.errors() else {}
                last_error = f"output did not validate: {first.get('loc')} {first.get('msg')}"
                continue
            self._write_cache(path, key, label, item_id, result, request)
            with self._lock:
                self.touched.add(path)
            return parsed, result
        raise LLMOutputInvalid(f"{item_id}: {last_error} (2 attempts).")

    def prune_untouched(self) -> list[Path]:
        """Delete cache files of this model that this client neither read nor wrote: responses
        to prompts that no longer exist (an earlier prompt version). Returns what was removed."""
        model_dir = self.cfg.cache_dir / _safe(self.cfg.model)
        removed: list[Path] = []
        if not model_dir.exists():
            return removed
        for path in sorted(model_dir.rglob("*.json")):
            if path not in self.touched:
                path.unlink()
                removed.append(path)
        return removed

    # ------------------------------------------------------------------ live call
    def _call(self, request: dict[str, Any], max_tokens: int, label: str, item_id: str, attempt: int) -> LLMResult:
        client = self._sdk()
        kwargs = dict(request)
        kwargs["max_tokens"] = max_tokens
        t0 = time.perf_counter()
        try:
            response = client.beta.messages.create(**kwargs)
        except anthropic.APIError as e:                     # status errors and connection errors
            latency_ms = int((time.perf_counter() - t0) * 1000)
            self._trace({"ts": _utc_now(), "label": label, "item_id": item_id, "attempt": attempt,
                         "model_requested": self.cfg.model, "effort": request["output_config"].get("effort"),
                         "outcome": type(e).__name__, "error": str(e)[:300], "latency_ms": latency_ms})
            if isinstance(e, anthropic.AuthenticationError):
                raise LLMUnavailable("The API rejected the key (401). Check ANTHROPIC_API_KEY in deliverables/.env.") from e
            raise LLMUnavailable(f"{item_id}: API call failed after retries: {type(e).__name__}: {e}") from e
        latency_ms = int((time.perf_counter() - t0) * 1000)
        body = response.to_dict()
        result = self._result_from_body(body, from_cache=False, latency_ms=latency_ms,
                                        request_id=getattr(response, "_request_id", None))
        with self._lock:
            self.calls += 1
            self.spent_usd += result.cost_usd
        outcome = "ok"
        if result.stop_reason == "refusal":
            outcome = "refusal"
        elif result.stop_reason == "max_tokens":
            outcome = "max_tokens"
        self._trace({"ts": _utc_now(), "label": label, "item_id": item_id, "attempt": attempt,
                     "model_requested": self.cfg.model, "served_by": result.served_by,
                     "effort": request["output_config"].get("effort"), "outcome": outcome,
                     "stop_reason": result.stop_reason, "fallback_used": result.fallback_used,
                     "input_tokens": result.input_tokens, "cache_read_tokens": result.cache_read_tokens,
                     "cache_write_tokens": result.cache_write_tokens, "output_tokens": result.output_tokens,
                     "latency_ms": latency_ms, "cost_usd": round(result.cost_usd, 6), "request_id": result.request_id})
        return result

    # ------------------------------------------------------------------ helpers
    def _result_from_body(self, body: dict[str, Any], *, from_cache: bool, latency_ms: int,
                          request_id: Optional[str] = None, cost_usd: Optional[float] = None) -> LLMResult:
        content = body.get("content") or []
        text = next((b.get("text", "") for b in content if b.get("type") == "text"), "")
        usage = body.get("usage") or {}
        in_t = int(usage.get("input_tokens") or 0)
        out_t = int(usage.get("output_tokens") or 0)
        read_t = int(usage.get("cache_read_input_tokens") or 0)
        write_t = int(usage.get("cache_creation_input_tokens") or 0)
        served = body.get("model")
        fallback_used = any(b.get("type") == "fallback" for b in content) or (
            served is not None and not str(served).startswith(self.cfg.model)
        )
        refusal = None
        details = body.get("stop_details") or {}
        if body.get("stop_reason") == "refusal":
            refusal = f"{details.get('category')}: {details.get('explanation')}" if details else "refusal"
        if cost_usd is None:
            p = self.cfg.profile
            cost_usd = (in_t * p["input"] + read_t * p["cache_read"] + write_t * p["cache_write"] + out_t * p["output"]) / 1e6
        return LLMResult(text=text, stop_reason=body.get("stop_reason"), served_by=served,
                         input_tokens=in_t, output_tokens=out_t, cache_read_tokens=read_t,
                         cache_write_tokens=write_t, latency_ms=latency_ms, from_cache=from_cache,
                         fallback_used=fallback_used, request_id=request_id, cost_usd=cost_usd, refusal=refusal)

    def _read_cache(self, path: Path, key: str) -> Optional[dict[str, Any]]:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if data.get("fingerprint") == key else None

    def _write_cache(self, path: Path, key: str, label: str, item_id: str, result: LLMResult, request: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "fingerprint": key,
            "label": label,
            "item_id": item_id,
            "model_requested": self.cfg.model,
            "effort": request["output_config"].get("effort"),
            "recorded_at": _utc_now(),
            "latency_ms": result.latency_ms,
            "cost_usd": round(result.cost_usd, 6),
            "request_id": result.request_id,
            "response": self._last_body_for(result),
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(body, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)

    @staticmethod
    def _last_body_for(result: LLMResult) -> dict[str, Any]:
        """A minimal, stable response body: enough to replay (text, model, stop reason, usage)."""
        return {
            "model": result.served_by,
            "stop_reason": result.stop_reason,
            "content": [{"type": "text", "text": result.text}] + ([{"type": "fallback"}] if result.fallback_used else []),
            "usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_read_input_tokens": result.cache_read_tokens,
                "cache_creation_input_tokens": result.cache_write_tokens,
            },
        }

    def _trace(self, record: dict[str, Any]) -> None:
        if not self.cfg.trace_path:
            return
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with self._lock:
            self.cfg.trace_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cfg.trace_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

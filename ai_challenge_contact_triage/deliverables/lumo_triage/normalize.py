"""
Step 1 of the pipeline: load, normalise and deduplicate the incoming messages.

* Timestamps: 40 of the 340 sample messages carry no UTC offset while the rest carry -05:00.
  A naive timestamp is interpreted as Bogotá local time (the customers are Colombian and the
  channel closes in America/Bogota); every message gets `received_at_utc` in ISO-8601 Zulu.
* Text: Unicode NFC, whitespace collapsed, trimmed. Nothing else is changed: the model and the
  entity verifier both work on this `text`, so "verbatim" means verbatim to this string.
* Exact duplicates: a content hash over an aggressively normalised form (lower-case, accents
  and punctuation removed). The first message with a hash is the original; later ones point to
  it via `duplicate_of`.
* Near duplicates: token Jaccard >= 0.6 (the same threshold as evidence/message_profiling.md)
  over pairs, grouped with union-find. O(n^2) set operations: instant for a few hundred
  messages and a few seconds for a 10,000-message day; beyond that, MinHash/LSH (e.g. the
  `datasketch` library) gives the same grouping in linear time. Groups are informational for
  the CX lead; they do not change the decision.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

BOGOTA = timezone(timedelta(hours=-5))
NEAR_DUPLICATE_THRESHOLD = 0.6


@dataclass
class Message:
    id: str
    channel: str
    received_at_raw: str
    received_at_utc: str
    sender: str
    text: str
    content_hash: str
    duplicate_of: Optional[str] = None
    near_duplicate_group: Optional[int] = None
    tokens: list[str] = field(default_factory=list, repr=False)


def normalize_timestamp(value: str) -> str:
    """ISO-8601 in, ISO-8601 UTC ('...Z') out. Naive values are Bogotá local time."""
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BOGOTA)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_tokens(text: str) -> list[str]:
    """Lower-case, accent-free, alphanumeric tokens: the basis of hashing and similarity."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", t)


def content_hash(text: str) -> str:
    return hashlib.sha1(" ".join(canonical_tokens(text)).encode("utf-8")).hexdigest()[:16]


def load_messages(path: str | Path) -> list[Message]:
    messages: list[Message] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        text = normalize_text(raw["text"])
        messages.append(Message(
            id=raw["id"],
            channel=raw["channel"],
            received_at_raw=raw["received_at"],
            received_at_utc=normalize_timestamp(raw["received_at"]),
            sender=raw["from"],
            text=text,
            content_hash=content_hash(text),
            tokens=canonical_tokens(text),
        ))
    return messages


def mark_exact_duplicates(messages: Iterable[Message]) -> int:
    """Point later copies to the first message with the same content hash. Returns the count."""
    first_by_hash: dict[str, str] = {}
    n = 0
    for m in sorted(messages, key=lambda x: (x.received_at_utc, x.id)):
        if not m.tokens:
            continue  # punctuation-only messages ('...', '?????') have no content to duplicate
        if m.content_hash in first_by_hash:
            m.duplicate_of = first_by_hash[m.content_hash]
            n += 1
        else:
            first_by_hash[m.content_hash] = m.id
    return n


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def mark_near_duplicates(messages: list[Message], threshold: float = NEAR_DUPLICATE_THRESHOLD) -> int:
    """Group messages whose token Jaccard similarity >= threshold. Returns messages in groups."""
    token_sets = [set(m.tokens) for m in messages]
    parent = list(range(len(messages)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(messages)):
        if not token_sets[i]:
            continue
        for j in range(i + 1, len(messages)):
            if token_sets[j] and jaccard(token_sets[i], token_sets[j]) >= threshold:
                parent[find(i)] = find(j)

    groups: dict[int, list[int]] = {}
    for i in range(len(messages)):
        groups.setdefault(find(i), []).append(i)
    group_id = 0
    involved = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        group_id += 1
        for i in members:
            messages[i].near_duplicate_group = group_id
        involved += len(members)
    return involved


def prepare(path: str | Path) -> list[Message]:
    messages = load_messages(path)
    mark_exact_duplicates(messages)
    mark_near_duplicates(messages)
    return messages

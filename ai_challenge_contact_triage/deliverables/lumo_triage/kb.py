"""
Knowledge-base loader: the four policy files split into sections with the stable ids declared
in `policy/taxonomy.yaml` (`kb_sections`: file + "## heading").

The drafting prompt receives only the sections allowed for the message's reasons, and the
verifier checks citations and numbers against exactly this text, so "grounded" always means
"in one of these sections" and a citation can be followed to the file and heading by hand.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from .schema import TAXONOMY

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT.parent / "knowledge_base"

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def digits_in(text: str) -> set[str]:
    """Digit strings of every number in a text ('$95.000' -> '95000', '24 horas' -> '24')."""
    return {re.sub(r"\D", "", n) for n in NUMBER.findall(text)}


@dataclass(frozen=True)
class Section:
    id: str
    file: str
    heading: str
    text: str

    @property
    def digits(self) -> set[str]:
        return digits_in(self.text)


def split_sections(markdown: str) -> dict[str, str]:
    """'## heading' -> body text (bullets kept as written) for one policy file."""
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in markdown.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current, buf = m.group(1), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


class KnowledgeBase:
    def __init__(self, kb_dir: Path = KB_DIR, taxonomy: dict = TAXONOMY):
        self.sections: dict[str, Section] = {}
        files: dict[str, dict[str, str]] = {}
        for sid, meta in taxonomy["kb_sections"].items():
            if meta["file"] not in files:
                files[meta["file"]] = split_sections((kb_dir / meta["file"]).read_text(encoding="utf-8"))
            text = files[meta["file"]].get(meta["heading"])
            if not text:
                raise KeyError(f"{sid}: heading {meta['heading']!r} not found or empty in {meta['file']}")
            self.sections[sid] = Section(sid, meta["file"], meta["heading"], text)
        self._by_reason = {r["id"]: list(r["kb_sections"]) for r in taxonomy["reasons"]}

    def section_ids_for(self, reasons: Iterable[str]) -> list[str]:
        """Union of the sections bound to the given reasons, in order, without repeats."""
        out: list[str] = []
        for reason in reasons:
            for sid in self._by_reason.get(reason, []):
                if sid not in out:
                    out.append(sid)
        return out

    def get(self, ids: Iterable[str]) -> list[Section]:
        return [self.sections[i] for i in ids if i in self.sections]

    @staticmethod
    def render(sections: Iterable[Section]) -> str:
        return "\n".join(
            f'<kb_section id="{s.id}" file="{s.file}" heading="{s.heading}">\n{s.text}\n</kb_section>'
            for s in sections
        )


@lru_cache(maxsize=1)
def load_kb() -> KnowledgeBase:
    return KnowledgeBase()

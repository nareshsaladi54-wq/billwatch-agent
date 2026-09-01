"""A memory you can read. Long-term notes are appended to a Markdown file, one
line per fact, namespaced by actor. In an AgentCore deployment this same
interface is backed by AgentCore Memory; locally it is a file you can `cat`."""
from __future__ import annotations

import datetime
import pathlib

from .config import DATA_DIR

MEM_FILE = pathlib.Path(DATA_DIR) / "memory.md"


def remember(actor_id: str, note: str) -> str:
    MEM_FILE.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    with open(MEM_FILE, "a") as fh:
        fh.write(f"- [{stamp}] ({actor_id}) {note.strip()}\n")
    return "noted"


def recall(actor_id: str, query: str = "") -> list[str]:
    if not MEM_FILE.exists():
        return []
    lines = [ln.strip() for ln in MEM_FILE.read_text().splitlines() if ln.strip()]
    hits = [ln for ln in lines if f"({actor_id})" in ln]
    if query:
        terms = [t for t in query.lower().split() if len(t) > 2]
        hits = [ln for ln in hits if any(t in ln.lower() for t in terms)] or hits
    return hits[-12:]

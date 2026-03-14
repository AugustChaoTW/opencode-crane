# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

"""
BibTeX read/write utilities for CRANE.
"""

from pathlib import Path
from typing import cast

import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter


def append_entry(bib_path: str, entry: str) -> None:
    """Append a BibTeX entry to a .bib file."""
    path = Path(bib_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + entry.strip() + "\n")


def remove_entry(bib_path: str, key: str) -> bool:
    """Remove a BibTeX entry by key from a .bib file. Returns True if found."""
    path = Path(bib_path)
    if not path.exists() or path.stat().st_size == 0:
        return False

    with open(path, encoding="utf-8") as f:
        db = cast(BibDatabase, bibtexparser.load(f))

    original_count = len(db.entries)
    db.entries = [entry for entry in db.entries if entry.get("ID") != key]
    if len(db.entries) == original_count:
        return False

    writer = BibTexWriter()
    with open(path, "w", encoding="utf-8") as f:
        f.write(writer.write(db))
    return True


def read_entries(bib_path: str) -> list[dict[str, str]]:
    """Parse all entries from a .bib file."""
    path = Path(bib_path)
    if not path.exists() or path.stat().st_size == 0:
        return []

    with open(path, encoding="utf-8") as f:
        db = cast(BibDatabase, bibtexparser.load(f))

    entries: list[dict[str, str]] = []
    for entry in db.entries:
        parsed_entry: dict[str, str] = {"key": str(entry.get("ID", ""))}
        for field, value in entry.items():
            if field == "ID":
                continue
            parsed_entry[str(field)] = str(value)
        entries.append(parsed_entry)
    return entries

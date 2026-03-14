"""
BibTeX read/write utilities for CRANE.
"""

from pathlib import Path


def append_entry(bib_path: str, entry: str) -> None:
    """Append a BibTeX entry to a .bib file."""
    path = Path(bib_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + entry.strip() + "\n")


def remove_entry(bib_path: str, key: str) -> bool:
    """Remove a BibTeX entry by key from a .bib file. Returns True if found."""
    raise NotImplementedError


def read_entries(bib_path: str) -> list[dict]:
    """Parse all entries from a .bib file."""
    raise NotImplementedError

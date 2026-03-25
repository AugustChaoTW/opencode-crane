"""
YAML read/write utilities for CRANE paper metadata.
"""

from pathlib import Path

import yaml


def write_paper_yaml(papers_dir: str, key: str, data: dict) -> str:
    """Write a paper YAML file. Returns the file path."""
    path = Path(papers_dir) / f"{key}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return str(path)


def read_paper_yaml(papers_dir: str, key: str) -> dict | None:
    """Read a paper YAML file. Returns None if not found."""
    path = Path(papers_dir) / f"{key}.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_paper_keys(papers_dir: str) -> list[str]:
    """List all paper keys (filenames without .yaml extension)."""
    path = Path(papers_dir)
    if not path.exists():
        return []
    return sorted(p.stem for p in path.glob("*.yaml"))


def delete_paper_yaml(papers_dir: str, key: str) -> bool:
    """Delete a paper YAML file. Returns True if file existed."""
    path = Path(papers_dir) / f"{key}.yaml"
    if path.exists():
        path.unlink()
        return True
    return False

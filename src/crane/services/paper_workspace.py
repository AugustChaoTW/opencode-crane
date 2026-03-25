"""Per-paper workspace management for verification pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PaperWorkspace:
    """Workspace for a single paper verification job."""

    journal_abbr: str
    project_root: str
    paper_path: Path
    protected_zones_path: Path
    audit_report_path: Path
    detection_report_path: Path
    change_log_path: Path
    health_report_path: Path
    references_path: Path
    figures_dir: Path
    supplementary_dir: Path

    @property
    def main_tex(self) -> Path:
        return self.paper_path

    @property
    def abbr(self) -> str:
        return self.journal_abbr


def create_workspace(
    journal_abbr: str,
    project_root: str | Path = ".",
    template_path: Path | None = None,
) -> PaperWorkspace:
    """Create a new paper workspace for verification.

    Args:
        journal_abbr: 5-character journal abbreviation (e.g., "NIPS", "ICML")
        project_root: Project root directory
        template_path: Optional LaTeX template to copy

    Returns:
        PaperWorkspace with all paths set up
    """
    if len(journal_abbr) > 5:
        raise ValueError("Journal abbreviation must be 5 characters or less")

    root = Path(project_root)
    papers_dir = root / "papers"
    paper_dir = papers_dir / journal_abbr.upper()

    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / "figures").mkdir(exist_ok=True)
    (paper_dir / "supplementary").mkdir(exist_ok=True)

    main_tex = paper_dir / f"{journal_abbr.upper()}-MAIN.tex"
    if not main_tex.exists():
        if template_path and template_path.exists():
            main_tex.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            main_tex.write_text(_default_template(journal_abbr), encoding="utf-8")

    protected_zones = paper_dir / f"{journal_abbr.upper()}-protected-zones.yaml"
    if not protected_zones.exists():
        protected_zones.write_text(
            _default_protected_zones(journal_abbr, main_tex), encoding="utf-8"
        )

    audit_report = paper_dir / f"{journal_abbr.upper()}-audit-report.yaml"
    detection_report = paper_dir / f"{journal_abbr.upper()}-detection-report.yaml"
    change_log = paper_dir / f"{journal_abbr.upper()}-change-log.yaml"
    health_report = paper_dir / f"{journal_abbr.upper()}-health-report.md"
    references = paper_dir / "references.bib"

    for path in [audit_report, detection_report, change_log, references]:
        if not path.exists():
            path.touch()

    if not health_report.exists():
        health_report.write_text(
            (
                f"# {journal_abbr.upper()} Paper Health Report\n\n"
                f"Generated: {datetime.now().isoformat()}\n"
            ),
            encoding="utf-8",
        )

    return PaperWorkspace(
        journal_abbr=journal_abbr.upper(),
        project_root=str(root),
        paper_path=main_tex,
        protected_zones_path=protected_zones,
        audit_report_path=audit_report,
        detection_report_path=detection_report,
        change_log_path=change_log,
        health_report_path=health_report,
        references_path=references,
        figures_dir=paper_dir / "figures",
        supplementary_dir=paper_dir / "supplementary",
    )


def get_workspace(
    journal_abbr: str,
    project_root: str | Path = ".",
) -> PaperWorkspace | None:
    """Get existing workspace for a paper.

    Args:
        journal_abbr: 5-character journal abbreviation
        project_root: Project root directory

    Returns:
        PaperWorkspace if exists, None otherwise
    """
    root = Path(project_root)
    paper_dir = root / "papers" / journal_abbr.upper()

    if not paper_dir.exists():
        return None

    main_tex = paper_dir / f"{journal_abbr.upper()}-MAIN.tex"
    if not main_tex.exists():
        return None

    return PaperWorkspace(
        journal_abbr=journal_abbr.upper(),
        project_root=str(root),
        paper_path=main_tex,
        protected_zones_path=paper_dir / f"{journal_abbr.upper()}-protected-zones.yaml",
        audit_report_path=paper_dir / f"{journal_abbr.upper()}-audit-report.yaml",
        detection_report_path=paper_dir / f"{journal_abbr.upper()}-detection-report.yaml",
        change_log_path=paper_dir / f"{journal_abbr.upper()}-change-log.yaml",
        health_report_path=paper_dir / f"{journal_abbr.upper()}-health-report.md",
        references_path=paper_dir / "references.bib",
        figures_dir=paper_dir / "figures",
        supplementary_dir=paper_dir / "supplementary",
    )


def list_workspaces(project_root: str | Path = ".") -> list[str]:
    """List all paper workspaces.

    Args:
        project_root: Project root directory

    Returns:
        List of journal abbreviations with workspaces
    """
    root = Path(project_root)
    papers_dir = root / "papers"

    if not papers_dir.exists():
        return []

    return [
        d.name for d in papers_dir.iterdir() if d.is_dir() and (d / f"{d.name}-MAIN.tex").exists()
    ]


def _default_template(journal_abbr: str) -> str:
    """Generate default LaTeX template."""
    return f"""\\documentclass{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{amsmath,amssymb,amsfonts}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}

\\title{{{journal_abbr.upper()} Paper}}
\\author{{Author Name}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle

\\begin{{abstract}}
Your abstract here.
\\end{{abstract}}

\\section{{Introduction}}
Introduction text here.

\\section{{Related Work}}
Related work here.

\\section{{Methodology}}
Methodology here.

\\section{{Results}}
Results here.

\\section{{Discussion}}
Discussion here.

\\section{{Conclusion}}
Conclusion here.

\\bibliographystyle{{plain}}
\\bibliography{{references}}

\\end{{document}}
"""


def _default_protected_zones(journal_abbr: str, paper_path: Path) -> str:
    """Generate default protected zones YAML."""
    return f"""metadata:
  paper_path: {paper_path}
  generated_at: "{datetime.now().isoformat()}"
  version: 1

protected_zones: []
"""

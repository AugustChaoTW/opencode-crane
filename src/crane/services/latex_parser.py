"""LaTeX section parser for paper review."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SectionLocation:
    name: str
    level: int
    start_line: int
    end_line: int
    content: str
    subsections: list[SectionLocation] = field(default_factory=list)


@dataclass
class PaperStructure:
    title: str
    abstract: str
    sections: list[SectionLocation]
    appendices: list[SectionLocation]
    raw_text: str


SECTION_PATTERN = re.compile(r"\\(section|subsection|subsubsection)\{([^}]+)\}")
ABSTRACT_PATTERN = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.DOTALL)
TITLE_PATTERN = re.compile(r"\\title\{([^}]+)\}")
APPENDIX_PATTERN = re.compile(r"\\appendix")


def parse_latex_sections(tex_path: str | Path) -> PaperStructure:
    """Parse LaTeX file into structured sections."""
    path = Path(tex_path)
    if not path.exists():
        raise FileNotFoundError(f"LaTeX file not found: {tex_path}")

    content = path.read_text(encoding="utf-8")
    _lines = content.split("\n")

    title_match = TITLE_PATTERN.search(content)
    title = title_match.group(1) if title_match else ""

    abstract_match = ABSTRACT_PATTERN.search(content)
    abstract = abstract_match.group(1).strip() if abstract_match else ""

    appendix_match = APPENDIX_PATTERN.search(content)
    appendix_start = appendix_match.start() if appendix_match else len(content)

    section_positions = []
    for match in SECTION_PATTERN.finditer(content):
        level = {"section": 1, "subsection": 2, "subsubsection": 3}[match.group(1)]
        name = match.group(2).strip()
        line_num = content[: match.start()].count("\n") + 1
        section_positions.append((match.start(), match.end(), level, name, line_num))

    sections = []
    appendices = []

    for i, (start_pos, end_pos, level, name, line_num) in enumerate(section_positions):
        next_start = section_positions[i + 1][0] if i + 1 < len(section_positions) else len(content)
        section_content = content[end_pos:next_start].strip()

        next_line = content[:next_start].count("\n") + 1

        section = SectionLocation(
            name=name,
            level=level,
            start_line=line_num,
            end_line=next_line,
            content=section_content,
        )

        if start_pos >= appendix_start:
            appendices.append(section)
        else:
            sections.append(section)

    sections = _build_hierarchy(sections)
    appendices = _build_hierarchy(appendices)

    return PaperStructure(
        title=title,
        abstract=abstract,
        sections=sections,
        appendices=appendices,
        raw_text=content,
    )


def _build_hierarchy(flat_sections: list[SectionLocation]) -> list[SectionLocation]:
    if not flat_sections:
        return []

    root_sections = []
    stack = []

    for section in flat_sections:
        while stack and stack[-1].level >= section.level:
            stack.pop()

        if stack:
            stack[-1].subsections.append(section)
        else:
            root_sections.append(section)

        stack.append(section)

    return root_sections


def get_section_text(structure: PaperStructure, section_name: str) -> str:
    """Get text content of a specific section."""
    for section in structure.sections:
        if section.name.lower() == section_name.lower():
            return section.content
        for subsection in section.subsections:
            if subsection.name.lower() == section_name.lower():
                return subsection.content
    return ""


def get_all_sections_flat(structure: PaperStructure) -> list[SectionLocation]:
    """Get all sections as a flat list."""
    result = []
    for section in structure.sections:
        result.append(section)
        result.extend(section.subsections)
    for appendix in structure.appendices:
        result.append(appendix)
        result.extend(appendix.subsections)
    return result

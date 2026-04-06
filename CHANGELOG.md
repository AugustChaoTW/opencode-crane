# Changelog

All notable changes to **opencode-crane** are documented here.

This file follows [Keep a Changelog](https://keepachangelog.com/) and uses Semantic Versioning.

## [v0.10.1] - 2026-04-06

### Added
- **Journal-Aware Writing Style Toolkit** (Phase A-D): complete pipeline from style analysis to interactive rewrite with preference learning.
- **Phase A — Data Models & Section Parsing**: `StyleMetrics` (8 quantitative metrics), `StyleGuide`, `SectionDiagnosis`, `RewriteSuggestion`, `SectionChunker` with canonical section normalisation.
- **Phase B — WritingStyleService**: core diagnostic engine with per-section deviation scoring, cross-section pattern detection, domain-aware metric weighting, and style guide caching.
- **Phase C — 7 MCP Tools**: `crane_extract_journal_style_guide`, `crane_diagnose_section`, `crane_diagnose_paper`, `crane_get_style_exemplars`, `crane_suggest_rewrites`, `crane_compare_sections`, `crane_export_style_report`.
- **Phase D — Interactive Rewrite**: `InteractiveRewriteService` with accept/reject/modify workflow, session persistence, pause/resume support. 6 new MCP tools: `crane_start_rewrite_session`, `crane_submit_rewrite_choice`, `crane_get_rewrite_session`, `crane_list_rewrite_sessions`, `crane_get_user_preferences`, `crane_reset_user_preferences`.
- **Phase D — Preference Learning**: `PreferenceLearnerService` that learns user writing preferences across sessions, adjusts suggestion confidence, and tracks per-category importance weights.
- **Phase E — Test Coverage**: 87 new tests (49 Phase D unit tests + 38 integration tests) covering all 13 MCP tools, multi-domain support, session persistence, and cross-session preference learning.
- Expanded Q1 journal profiles from 18 to 55, providing broader coverage for submission matching.
- New domain-specific evaluation packages for Cybersecurity, IoT, and MIS, in addition to the existing AI/ML.
- 4 new documentation files: `JOURNAL_INTEGRATION.md`, `WRITING_STYLE_GUIDE.md`, `INTERACTIVE_REWRITE.md`, `PREFERENCE_LEARNING.md`.

### Changed
- Updated the journal matching algorithm to better handle large-scale profile comparisons.
- Refined the 7-dimension scoring weights for the new domain packages.
- Updated README with v0.10.1 features, 13 new tool descriptions, and updated project structure.
- Synced `__init__.py` version to match `pyproject.toml`.

### Fixed
- Improved LaTeX section parsing for non-standard templates.

## [v0.10.0] - 2026-04-06

### Breaking
- breaking: freeze the public MCP tool surface before v1.0.0; legacy aliases will be removed once documentation and prompts are updated.

### Added
- Draft v1.0.0 release prep and cleanup notes for the current 35-tool surface.

### Changed
- Consolidate release notes and operator docs around the publication-ready workflow.

### Fixed
- N/A.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.9.1] - 2026-04-01

### Added
- Added the remaining submission-stage tooling: `run_submission_check` plus the 19-service orchestration path for literature review, experiment collation, framing analysis, and paper health checks.
- Finalized the 35-tool surface covering paper search (arXiv), reference management, citation verification, task tracking, screening, comparison, figures, section review, journal recommendation, and submission prep.

### Changed
- Refined the service layer to support publication-ready workflows and stronger cross-project isolation.
- Updated docs and examples for the 35 MCP tools and 19 services.

### Fixed
- Stabilized tool registration and output formats for the final release track.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.9.0] - 2026-03-26

### Added
- Added the Q1 journal evaluation path and journal-fit helpers: `evaluate_q1_standards`, `analyze_paper_for_journal`, `generate_submission_checklist`, and `find_similar_papers_in_journal`.
- Expanded publication prep around section review, protected zones, and figure generation.

### Changed
- Elevated the reviewer workflow from paper drafting to submission readiness.
- Expanded README guidance around 3-LLM verification, section review, and journal targeting.

### Fixed
- Corrected release plumbing and tool-count sync as the tool surface expanded.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.8.0] - 2026-03-25

### Added
- Added `generate_figure` and `generate_comparison` for publication-quality visuals.
- Added `review_paper_sections` and `parse_paper_structure` for section-level LaTeX review.
- Added screening workflow tools: `screen_reference`, `list_screened_references`, and `compare_papers`.

### Changed
- Extended the research workflow from literature triage into manuscript-quality analysis.
- Backfilled the reviewer stack with protected-zones and 3-LLM-aware editing support.

### Fixed
- Improved retry logic and documentation sync across the workflow stack.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.7.0] - 2026-03-23

### Added
- Added `evaluate_q1_standards` for Q1 journal readiness checks.
- Introduced the 3-LLM verification loop (Auditor / Detector / Editor) as a first-class manuscript workflow.

### Changed
- Shifted focus from paper ingestion toward review-quality manuscript assessment.
- Tightened the writing workflow around protected zones and revision gating.

### Fixed
- Harmonized the review taxonomy with the ESWA feedback pass.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.6.0] - 2026-03-23

### Added
- Added `review_paper_sections` and `parse_paper_structure` to support chapter-by-chapter review.
- Added manuscript-oriented features for protected zones and paper-writing assistance.

### Changed
- Moved CRANE from research-note tooling toward manuscript editing and structural analysis.

### Fixed
- Improved LaTeX parsing and section boundary handling.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.5.0] - 2026-03-23

### Added
- Added `generate_figure` and `generate_comparison` for paper-ready charts.
- Added the first submission-visualization path for results reporting.

### Changed
- Formalized publication-quality outputs as a core CRANE capability.

### Fixed
- Improved output-path handling for project-relative figures.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.4.0] - 2026-03-22

### Added
- Added `screen_reference`, `list_screened_references`, and `compare_papers` to support systematic review decisions.
- Expanded paper selection from search/download into include/exclude tracking.

### Changed
- Broadened the literature-review workflow to include comparison matrices and screening records.

### Fixed
- Improved screening result serialization and reference comparison output.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.3.0] - 2026-03-21

### Added
- Added `report_progress`, `close_task`, `get_milestone_progress`, and `workspace_status`.
- Introduced GitHub Issues progress reporting and stateless workspace reconstruction.

### Changed
- Promoted GitHub Issues from CRUD-only task storage to a real research project tracker.
- Added cross-project isolation via `project_dir`/`cwd` handling.

### Fixed
- Aligned installer and docs with the 19-tool transition.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.2.0] - 2026-03-16

### Added
- Added `run_pipeline` for `literature-review` and `full-setup` automation.
- Added the first orchestration layer for multi-step research workflows.

### Changed
- Enhanced `SKILL.md` and event-hook design to make the MCP server easier for OpenCode agents to use.

### Fixed
- Normalized command execution and path handling in the pipeline path.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

## [v0.1.0] - 2026-03-14

### Added
- Launched CRANE as an OpenCode-native MCP server with the core 18-tool surface.
- Added paper search (arXiv), download, reading, and reference management.
- Added citation verification and GitHub Issues task CRUD for research tracking.
- Added project bootstrap (`init_research`, `get_project_info`) and the initial MCP integration.

### Changed
- Restructured the project around a service-oriented MCP architecture and TDD scaffolding.
- Published the first install guide and README feature highlights.

### Fixed
- Parsed `gh issue create` output reliably instead of assuming JSON.

### Deprecated
- N/A.

### Removed
- N/A.

### Security
- N/A.

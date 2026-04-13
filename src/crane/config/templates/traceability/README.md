# CRANE Paper Traceability Templates (v0.13.0)

This directory contains 10 YAML template files that implement the CRANE paper traceability system. Each file represents a layer of the traceability chain, from the upstream research questions down to the artifact index.

## Purpose

The traceability system ensures that every claim in a paper is anchored to a research question (RQ), supported by experiments (E), visualized in figures/tables (Fig/Tab), and defended against reviewer risks (R). When a number changes, the change log propagates which sections, figures, and claims must be updated.

## Files

| File | Key | Description |
|---|---|---|
| `1_contribution.yaml` | C{n} | Contribution registry: what the paper claims to contribute, per-contribution defensibility analysis, and global overclaiming guard |
| `2_experiment.yaml` | E{n} | Experiment registry: canonical settings, locked numbers, and paper placement (figures/tables/sections) |
| `3_section_outline.yaml` | Sec:{n} | Per-section writing contracts: goals, must-include items, must-not-do items, and citation requirements |
| `4_citation_map.yaml` | ref_key | Citation placement rules: where each reference must/must-not appear and which experiments/figures need it |
| `5_figure_table_map.yaml` | Fig:{n} / Tab:{n} | Figure and table specs: exact locked numbers, visualization parameters, captions, and update triggers |
| `6_research_question.yaml` | RQ{n} | Research question registry: the upstream anchor for all traceability; links to experiments, figures, and contributions |
| `7_change_log_impact.yaml` | CH{n} | Change log: records every change to an artifact with downstream impact analysis and resolution tracking |
| `8_limitation_reviewer_risk.yaml` | R{n} | Reviewer risk register: anticipated objections with severity, response strategy, and fallback claims |
| `9_dataset_baseline_protocol.yaml` | DS{n} / BL{n} | Dataset and baseline protocol: split definitions, implementation sources, and reproducibility rules |
| `10_artifact_index.yaml` | A{n} | Artifact index: all tracked files (scripts, notebooks, checkpoints, figures) with provenance and git tracking status |

## Traceability Chain

```
RQ{n} (6_research_question.yaml)
  └─► C{n} (1_contribution.yaml)
        └─► E{n} (2_experiment.yaml)
              └─► Fig/Tab (5_figure_table_map.yaml)
                    └─► Sec:{n} (3_section_outline.yaml)
                          └─► ref_key (4_citation_map.yaml)

Changes tracked in: 7_change_log_impact.yaml
Risks tracked in:   8_limitation_reviewer_risk.yaml
Data/baselines in:  9_dataset_baseline_protocol.yaml
All assets in:      10_artifact_index.yaml
```

## Usage

Copy the entire directory into a paper project:

```bash
cp -r src/crane/config/templates/traceability/ my_paper/.crane/traceability/
```

Then fill in each file top-to-bottom, starting with `6_research_question.yaml` (the upstream anchor) and working down to `10_artifact_index.yaml`.

CRANE tools in v0.13.0 can auto-populate these files from paper content using the LLM templates in `src/crane/templates/llm/traceability_extract_*.txt`.

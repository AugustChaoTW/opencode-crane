# Pre-Submission Check in 5 Minutes

Time: 5 minutes

Use this for one-command pre-publication verification before you submit a paper.

## Commands

```bash
crane init_research
```

Expected output:
```text
Initializing research workspace...
Created labels and milestones
Created references/ directory
Created issue templates
Status: ready
```

```bash
crane run_submission_check --paper_path papers/main.tex
```

Expected output:
```text
Running pre-submission check
Literature review: complete
Experiment results: complete
Framing analysis: complete
Paper health: complete
```

```bash
ls BEFORE_SUBMISSION_RUN1/reports/
```

Expected output:
```text
EXP_RESULTS.md
FRAMING_ANALYSIS.md
LITERATURE_REVIEW.md
PAPER_HEALTH_REPORT.md
count: 4
```

```bash
crane get_milestone_progress
```

Expected output:
```text
Milestone: Phase 2: Literature Review
Open tasks: 3
Completed tasks: 7
Ready with revisions: yes
Readiness verdict: ready_with_revisions
```

## Troubleshooting

- If you see `module not found`, run: `uv sync`.
- If `papers/main.tex` does not exist, point `--paper_path` to your real main TeX file.
- If `BEFORE_SUBMISSION_RUN1` already exists, the next run becomes `BEFORE_SUBMISSION_RUN2`.

## Next steps

- Open the four report files and fix the listed issues.
- Re-run `crane run_submission_check --paper_path papers/main.tex` after edits.
- Share the reports with coauthors before submission.

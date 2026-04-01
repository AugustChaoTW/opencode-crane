# Multi-Author Workflow with GitHub Issues

Time: 5-10 minutes

Use this to coordinate literature review work across multiple authors.

## Commands

```bash
crane create_task --title "Literature review: LoRa Mesh" --phase literature-review --priority high
```

Expected output:
```text
Creating GitHub issue...
Title: Literature review: LoRa Mesh
Phase: literature-review
Priority: high
Issue number: 42
Status: open
```

```bash
crane list_tasks --state open
```

Expected output:
```text
Open tasks: 1
#42 Literature review: LoRa Mesh
Labels: crane, kind:task, phase:literature-review
Priority: high
Assignee: @me
```

```bash
crane report_progress {issue_num} "Completed 5 papers, summary in issue"
```

Expected output:
```text
Posting progress comment...
Issue: #{issue_num}
Comment saved
Timestamp: now
Status: updated
```

```bash
gh issue view {issue_num}
```

Expected output:
```text
title: Literature review: LoRa Mesh
state: OPEN
comments: 1
labels: crane, kind:task, phase:literature-review
history: progress comment visible
```

```bash
crane get_milestone_progress
```

Expected output:
```text
Milestone: Phase 2: Literature Review
Open issues: 1
Closed issues: 0
Progress: 12%
Tracked by milestone: yes
```

## Troubleshooting

- If you see `module not found`, run: `uv sync`.
- If `gh issue view` fails, run `gh auth status` and log in again.
- If the issue number is wrong, use the number printed by `crane create_task`.

## Next steps

- Add one issue per paper or subtask.
- Use `crane update_task` to assign milestones or labels.
- Use `crane close_task` when the work is finished.

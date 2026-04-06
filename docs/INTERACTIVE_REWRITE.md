# Interactive Rewrite Workflow

The interactive rewrite system lets you review and decide on each writing style suggestion individually, building a curated set of improvements.

## Workflow Overview

```
Start Session → Review Suggestions → Accept/Reject/Modify → Complete → Learn Preferences
```

## Step 1: Start a Session

```python
result = crane_start_rewrite_session(
    paper_path="main.tex",
    journal_name="IEEE TPAMI",
    section_name="Introduction",
    max_suggestions=5,
)
# Returns: session_id, pending suggestions list
```

The system:
1. Parses your paper and extracts the target section
2. Computes current style metrics
3. Compares against journal targets
4. Generates rewrite suggestions ranked by severity

## Step 2: Review Each Suggestion

Each suggestion includes:
- `original_text`: The text span that deviates from journal style
- `suggested_text`: Proposed replacement (may be empty for rule-based suggestions)
- `rationale`: Why this change improves journal fit
- `confidence`: How confident the system is (0-1)

## Step 3: Submit Decisions

For each suggestion, choose one of three actions:

### Accept
```python
crane_submit_rewrite_choice(
    session_id="rw_...",
    suggestion_index=0,
    decision="accept",
)
```

### Reject
```python
crane_submit_rewrite_choice(
    session_id="rw_...",
    suggestion_index=1,
    decision="reject",
    reason="I prefer passive voice in this context",
)
```

### Modify
```python
crane_submit_rewrite_choice(
    session_id="rw_...",
    suggestion_index=2,
    decision="modify",
    modified_text="My preferred alternative phrasing here",
)
```

## Step 4: Session Management

### Pause and Resume
```python
# Pause mid-session
crane_get_rewrite_session(session_id="rw_...")  # Check status

# Resume later — sessions persist to disk
crane_submit_rewrite_choice(session_id="rw_...", ...)
```

### List Sessions
```python
crane_list_rewrite_sessions(status="active")   # Active sessions
crane_list_rewrite_sessions(status="completed") # Completed sessions
crane_list_rewrite_sessions()                   # All sessions
```

## Step 5: Session Summary

After completing all decisions:

```python
result = crane_get_rewrite_session(session_id="rw_...")
# Returns:
# {
#   "accepted": 3,
#   "rejected": 1,
#   "modified": 1,
#   "acceptance_rate": 0.6,
#   "applied_count": 4,  # accepted + modified
# }
```

## Session Persistence

Sessions are saved as YAML files in `data/rewrite_sessions/`. They survive:
- Application restarts
- Multiple editing sessions
- Different terminal sessions

## Integration with Preference Learning

After completing a session, CRANE's PreferenceLearner automatically:
1. Analyses your accept/reject/modify patterns
2. Identifies which style categories you prefer
3. Adjusts future suggestion priorities accordingly

See [PREFERENCE_LEARNING.md](PREFERENCE_LEARNING.md) for details.

## Best Practices

1. **Start with the worst section**: Run `crane_diagnose_paper` first, then start with the section that has the highest deviation score
2. **Provide reasons for rejections**: This helps the preference learner understand your style
3. **Use modify for partial agreement**: When a suggestion is directionally correct but needs refinement
4. **Re-diagnose after applying**: Run `crane_diagnose_section` again to verify improvement
5. **Work section by section**: Complete one section before moving to the next

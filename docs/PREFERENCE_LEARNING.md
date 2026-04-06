# Preference Learning

CRANE learns your writing preferences from interactive rewrite sessions and uses them to personalise future suggestions.

## How It Works

```
Session Choices → Extract Patterns → Update Preferences → Adjust Future Suggestions
```

### Learning Signal

Each decision in an interactive rewrite session provides a learning signal:

| Decision | Signal | Effect |
|----------|--------|--------|
| **accept** | User agrees with this style direction | Increase preference strength (+0.1) |
| **reject** | User disagrees with this style direction | Decrease strength (-0.15) or increase opposite |
| **modify** | User partially agrees | Slight increase (+0.05) |

### What Gets Learned

For each style metric, CRANE tracks:
- **direction**: Whether you prefer higher or lower values
- **strength**: How strongly you feel about this (0-1)
- **evidence_count**: How many decisions support this preference
- **category_weight**: Overall importance of the style category

## Viewing Your Preferences

```python
result = crane_get_user_preferences(user_id="default")
# Returns:
# {
#   "user_id": "default",
#   "total_sessions": 5,
#   "total_choices": 23,
#   "acceptance_rate": 0.65,
#   "preferences": [
#     {"metric": "passive_voice_ratio", "category": "grammar",
#      "direction": "lower", "strength": 0.45, "evidence_count": 8},
#     {"metric": "avg_sentence_length", "category": "readability",
#      "direction": "lower", "strength": 0.30, "evidence_count": 5},
#   ],
#   "category_weights": {"grammar": 1.15, "readability": 0.95}
# }
```

## How Preferences Affect Suggestions

When generating new suggestions, CRANE:

1. Computes a **preference boost** for each suggestion based on alignment with your preferences
2. Adjusts the suggestion's **confidence score** up or down
3. **Re-sorts** suggestions so preferred types appear first

Example: If you consistently accept passive-voice fixes, future passive-voice suggestions get a confidence boost and appear higher in the list.

## Multi-User Support

Each user has isolated preferences:

```python
crane_get_user_preferences(user_id="alice")
crane_get_user_preferences(user_id="bob")
```

Preferences are stored in `data/user_preferences/{user_id}.yaml`.

## Resetting Preferences

```python
crane_reset_user_preferences(user_id="default")
```

This clears all learned preferences and resets to neutral.

## Persistence

Preferences persist across:
- Application restarts
- Different projects (preferences are user-level, not project-level)
- Multiple rewrite sessions

## Category Weights

Beyond individual metric preferences, CRANE tracks category-level weights:

| Category | Default Weight | Range |
|----------|---------------|-------|
| readability | 1.0 | 0.5 - 2.0 |
| vocabulary | 1.0 | 0.5 - 2.0 |
| grammar | 1.0 | 0.5 - 2.0 |

Accepting suggestions in a category increases its weight; rejecting decreases it.

## Privacy

All preference data is stored locally in YAML files. No data is sent to external services. You can inspect, edit, or delete preference files directly.

## Technical Details

The preference learning algorithm uses exponential moving averages:
- Accept: `strength = min(strength + 0.1, 1.0)`
- Reject (same direction): `strength = max(strength - 0.15, 0.0)`
- Reject (opposite direction): `strength = min(strength + 0.05, 1.0)`
- Modify: `strength = min(strength + 0.05, 1.0)`

Category weights follow a similar pattern with smaller increments (±0.05), bounded to [0.5, 2.0].

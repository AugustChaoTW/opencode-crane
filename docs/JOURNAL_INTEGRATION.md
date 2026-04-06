# Adding New Journals to CRANE

This guide explains how to add new Q1 journal profiles to CRANE's writing style analysis system.

## Journal Profile Structure

All journal profiles live in `data/journals/q1_journal_profiles.yaml`. Each entry follows this schema:

```yaml
- name: "IEEE Transactions on Pattern Analysis and Machine Intelligence"
  abbreviation: "IEEE TPAMI"
  publisher: "IEEE"
  quartile: "Q1"
  impact_factor: 23.6
  scope_keywords:
    - "pattern recognition"
    - "computer vision"
    - "machine learning"
  preferred_paper_types:
    - "empirical"
    - "theoretical"
  preferred_method_families:
    - "deep learning"
    - "statistical learning"
  preferred_evidence_patterns:
    - "benchmark_heavy"
    - "ablation_study"
  typical_word_count: [8000, 12000]
  review_timeline_months: [3, 9]
  acceptance_rate: 0.15
  apc_usd: 2800
  open_access: false
  open_access_type: "subscription"
  waiver_available: false
  desk_reject_signals:
    - "insufficient novelty"
    - "missing ablation"
  citation_venues:
    - "CVPR"
    - "ICCV"
    - "NeurIPS"
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Full journal name |
| `abbreviation` | string | Common abbreviation |
| `publisher` | string | Publisher name (IEEE, ACM, Springer, Elsevier, etc.) |
| `quartile` | string | Journal quartile (Q1, Q2, etc.) |
| `impact_factor` | float | Current impact factor |
| `scope_keywords` | list[str] | Keywords defining the journal's scope |
| `typical_word_count` | list[int] | [min, max] word count range |
| `acceptance_rate` | float | Acceptance rate (0-1) |

## Style Class Mapping

CRANE maps publishers to style classes that determine default writing targets:

| Publisher | Style Class | Characteristics |
|-----------|-------------|-----------------|
| IEEE | `ieee_transactions` | Formal, structured contributions, technical precision |
| ACM, JMLR | `acm` | Empirical rigour, RQ-driven, statistical significance |
| Springer, Nature, MDPI | `springer_nature` | Narrative flow, comprehensive methodology |
| Elsevier, Wiley, Taylor & Francis | `elsevier` | Module-based architecture, comparative evaluation |

## Domain Detection

CRANE auto-detects the research domain from `scope_keywords`:

- **ai_ml**: Keywords like "machine learning", "deep learning", "neural network"
- **cybersecurity**: Keywords like "security", "intrusion detection", "cryptography"
- **iot**: Keywords like "internet of things", "sensor", "embedded"
- **mis**: Keywords like "information systems", "management", "IS research"

## Adding a New Journal

1. Open `data/journals/q1_journal_profiles.yaml`
2. Add a new entry following the schema above
3. Verify with:

```python
from crane.services.writing_style_service import WritingStyleService

service = WritingStyleService("Your New Journal")
guide = service.get_style_guide()
print(f"Domain: {guide.domain}")
print(f"Sections: {list(guide.section_targets.keys())}")
```

4. Run tests: `uv run pytest tests/services/test_writing_style_service.py -v`

## Custom Style Guides

For journals with specific style requirements, you can create a cached style guide in `data/style_guides/`:

```yaml
journal_name: "Your Journal"
domain: "ai_ml"
metrics:
  flesch_kincaid_grade: 13.0
  smog_index: 14.5
  avg_sentence_length: 22
  avg_word_length: 5.1
  type_token_ratio: 0.52
  technical_term_density: 0.10
  passive_voice_ratio: 0.18
  nominalization_ratio: 0.07
section_targets:
  Introduction:
    flesch_kincaid_grade: 12.0
    avg_sentence_length: 22
    passive_voice_ratio: 0.15
  Methods:
    flesch_kincaid_grade: 14.0
    avg_sentence_length: 20
    passive_voice_ratio: 0.25
exemplars: []
sample_size: 0
confidence_score: 0.8
```

## Supported Journals (55)

CRANE ships with profiles for 55 Q1 journals across 4 domains. Run `crane_extract_journal_style_guide(journal_name="...")` with any supported journal name or abbreviation.

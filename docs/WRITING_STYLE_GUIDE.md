# Writing Style Analysis Guide

CRANE's Journal-Aware Writing Style Toolkit helps align your manuscript's writing style with target journal expectations.

## Quick Start

```python
# 1. Diagnose your paper against a journal
crane_diagnose_paper(paper_path="main.tex", journal_name="IEEE TPAMI")

# 2. Get detailed section analysis
crane_diagnose_section(paper_path="main.tex", section_name="Introduction", journal_name="IEEE TPAMI")

# 3. Get rewrite suggestions
crane_suggest_rewrites(paper_path="main.tex", section_name="Methods", journal_name="IEEE TPAMI")

# 4. Compare two journals
crane_compare_sections(paper_path="main.tex", section_name="Introduction",
                       journal1="IEEE TPAMI", journal2="ACM TOSEM")

# 5. Export full report
crane_export_style_report(paper_path="main.tex", journal_name="IEEE TPAMI")
```

## 8 Style Metrics

CRANE measures 8 quantitative metrics for each section:

### Readability
| Metric | Description | Typical Range |
|--------|-------------|---------------|
| `flesch_kincaid_grade` | Grade level (higher = harder) | 11-16 |
| `smog_index` | SMOG readability index | 12-16 |
| `avg_sentence_length` | Words per sentence | 18-28 |
| `avg_word_length` | Characters per word | 4.5-5.5 |

### Vocabulary
| Metric | Description | Typical Range |
|--------|-------------|---------------|
| `type_token_ratio` | Lexical diversity (unique/total) | 0.40-0.60 |
| `technical_term_density` | Fraction of technical terms | 0.05-0.15 |

### Grammar
| Metric | Description | Typical Range |
|--------|-------------|---------------|
| `passive_voice_ratio` | Fraction of passive sentences | 0.10-0.30 |
| `nominalization_ratio` | Fraction of nominalised forms | 0.04-0.10 |

## Issue Severity Levels

- **critical** (deviation >= 40%): Must fix before submission
- **major** (deviation >= 20%): Should fix for better journal fit
- **minor** (deviation >= 10%): Nice to fix, low priority

## Domain-Specific Weights

Different domains weight metrics differently:

| Domain | Higher Weight | Lower Weight |
|--------|--------------|--------------|
| AI/ML | technical_term_density (1.3x) | passive_voice_ratio (0.8x) |
| Cybersecurity | technical_term_density (1.4x) | passive_voice_ratio (0.7x) |
| IoT | technical_term_density (1.2x) | — |
| MIS | passive_voice_ratio (1.3x), type_token_ratio (1.2x) | — |

## Section-Level Targets

Each journal has different targets per section:

- **Introduction**: Lower passive voice, moderate technicality
- **Methods**: Higher passive voice (acceptable), high technicality
- **Results**: Short sentences, data-focused vocabulary
- **Discussion**: Longer sentences, higher lexical diversity
- **Conclusion**: Simplest readability, lowest technicality

## Workflow: From Diagnosis to Submission

```
1. Run full diagnosis:     crane_diagnose_paper(...)
2. Review critical issues:  Focus on sections with deviation > 40
3. Get suggestions:         crane_suggest_rewrites(...) for worst sections
4. Start interactive rewrite: crane_start_rewrite_session(...)
5. Accept/reject/modify:    crane_submit_rewrite_choice(...)
6. Re-diagnose:            crane_diagnose_paper(...) to verify improvement
7. Export report:           crane_export_style_report(...)
```

## Cross-Section Pattern Detection

CRANE detects patterns that span multiple sections:
- Consistent passive voice overuse across 2+ sections
- Readability concerns in 3+ sections (paper may be too complex/simple overall)

These cross-section issues appear as additional `major` severity items.

## API Reference

| Tool | Purpose |
|------|---------|
| `crane_extract_journal_style_guide` | Get style targets for any of 55 journals |
| `crane_diagnose_section` | Analyse one section against targets |
| `crane_diagnose_paper` | Full paper diagnosis |
| `crane_get_style_exemplars` | Get exemplar writing patterns |
| `crane_suggest_rewrites` | Generate rewrite suggestions |
| `crane_compare_sections` | Compare two journals' expectations |
| `crane_export_style_report` | Generate Markdown report |
| `crane_start_rewrite_session` | Start interactive rewrite |
| `crane_submit_rewrite_choice` | Submit accept/reject/modify |
| `crane_get_rewrite_session` | Get session status |
| `crane_list_rewrite_sessions` | List all sessions |
| `crane_get_user_preferences` | View learned preferences |
| `crane_reset_user_preferences` | Reset preference history |

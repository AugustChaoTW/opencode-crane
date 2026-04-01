# Literature Review in 10 Minutes
Time: 5-10 minutes
Use this when you want the full CRANE paper workflow: search → add → download → read → annotate.
## Commands
```bash
crane search_papers "transformer attention mechanism" --max=3
```
Expected output:
```text
1. title: Attention Is All You Need
   paper_id: 1706.03762
   pdf_url: https://arxiv.org/pdf/1706.03762.pdf
2. title: Efficient Attention
   paper_id: 2006.16236
   pdf_url: https://arxiv.org/pdf/2006.16236.pdf
3. title: Linformer: Self-Attention with Linear Complexity
   paper_id: 2006.04768
   pdf_url: https://arxiv.org/pdf/2006.04768.pdf
```
```bash
crane add_reference {paper_id}
```
Expected output:
```text
Added reference: {key}
Wrote: references/papers/{key}.yaml
Updated: references/bibliography.bib
Source: arxiv
Status: done
```
```bash
crane download_paper {paper_id}
```
Expected output:
```text
Downloading PDF...
Saved to: references/pdfs/{paper_id}.pdf
Size: 2.4 MB
Checksum: ok
Status: done
```
```bash
crane read_paper {paper_id} | head -100
```
Expected output:
```text
Title: Attention Is All You Need
Abstract: We propose a new simple network architecture...
Introduction: Recurrent models have been dominant...
Method: multi-head self-attention
Conclusion: Transformer outperforms prior seq2seq models
```
```bash
crane annotate_reference {key} --summary "Transformer replaces recurrence with self-attention." --tags foundation
```
Expected output:
```text
Annotated reference: {key}
Summary: saved
Tags: foundation
Related issues: 0
Status: updated
```
## Troubleshooting
- If you see `module not found`, run: `uv sync`.
- If `crane search_papers` returns nothing, try a broader query.
- If `download_paper` fails, rerun with the same `{paper_id}` after a minute.
## Next steps
- Add 2-3 more papers with the same workflow.
- Confirm the tag filter with `crane list_references --filter_tag foundation`.
- Use `crane compare_papers` for a quick comparison matrix.
- Move to `02-submission-check.md` when your draft is ready.

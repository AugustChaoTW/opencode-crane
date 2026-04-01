# Draft: opencode-crane Innovation Directions

## Requirements (confirmed)
- Deliver 5-7 bold but feasible product ideas for opencode-crane.
- For each idea, include: core innovation, technical feasibility, expected UX improvement, competitive differentiation, risks and challenges.
- Response language: English.
- Final plan language: English.
- Plan should be suitable for ultrawork execution.
- Planning style should be TDD-oriented.
- Include a clear atomic commit strategy.

## Technical Decisions
- Focus area is innovation and differentiation, not incremental parity work.
- Output is expected to connect AI-native capabilities with research workflow redesign.

## Research Findings
- Current opencode-crane strengths: multi-source paper search, YAML+BibTeX reference memory, GitHub-native task orchestration, citation verification, section-level paper review, 3-LLM verification, provenance-oriented workflows.
- Current gaps versus traditional research tools: weak visual graph exploration, limited collaborative annotation, no PRISMA/systematic-review workflow depth, no rich PDF annotation loop, no strong full-text/cross-project semantic memory layer.
- Strategic white space: move from reactive paper/tool usage toward a proactive research operating layer that maintains research state, proposes next actions, links literature to experiments/manuscript, and improves submission outcomes.
- Competitive landscape pattern: Elicit/NotebookLM/Semantic Scholar/Scite/Connected Papers each solve narrow slices well, but remain largely reactive, query-driven, and weak at closed-loop project execution.
- Architectural advantage: opencode-crane already has service-layer separation, MCP-native interaction, pipeline orchestration, provenance concepts, and repo/GitHub integration that could support proactive AI-native research workflows.
- Execution constraints to respect: trust is fragile, scope sprawl is dangerous, and short-term roadmap should avoid broad platform fantasies without a narrow indispensable wedge.

## Open Questions
- Should the recommendations optimize primarily for solo researchers, research labs, or enterprise R&D teams?
- Should the ideas emphasize near-term shippable features, frontier bets, or a mix of both?
- Should the differentiation be MCP/OpenCode-native only, or also assume a future standalone product surface?

## Strategic Hypotheses Under Consideration
- The most defensible differentiation is not "better paper chat" but a trusted research operating layer with auditable memory and workflow control.
- The strongest ideas should form closed loops: detect gap -> create task -> gather evidence -> update artifact -> verify result.
- A narrow initial wedge is likely better than broad coverage: e.g. code-backed CS/ML paper authorship, lab-level review workflows, or enterprise R&D insight operations.

## Scope Boundaries
- INCLUDE: AI capability expansion, workflow innovation, new research paradigms, proactive agent behavior.
- EXCLUDE: Detailed implementation work, code changes, marketing copy.

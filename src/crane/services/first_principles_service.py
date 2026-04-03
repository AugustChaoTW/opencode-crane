"""
First principles deconstruction service.
Implements heuristic analysis to challenge conventional wisdom.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.workspace import resolve_workspace


class FirstPrinciplesService:
    """Service for deconstructing conventional wisdom via first principles."""

    _DOMAIN_ALIASES: dict[str, str] = {
        "ai": "ai/ml",
        "ml": "ai/ml",
        "machine learning": "ai/ml",
        "ai/ml": "ai/ml",
        "artificial intelligence": "ai/ml",
        "nlp": "nlp",
        "natural language processing": "nlp",
        "computer vision": "computer vision",
        "cv": "computer vision",
        "general": "general",
    }

    _BELIEF_LIBRARY: dict[str, list[dict[str, Any]]] = {
        "ai/ml": [
            {
                "belief": "More data is always better",
                "evidence_for": [
                    "Scaling curves often show improved performance with larger datasets.",
                    "Large pre-training corpora reduce overfitting in many regimes.",
                ],
                "evidence_against": [
                    "Noisy or biased data can degrade downstream behavior.",
                    "Data quality and coverage can dominate raw data volume.",
                    "Beyond saturation points, additional data yields diminishing returns.",
                ],
            },
            {
                "belief": "Bigger models win",
                "evidence_for": [
                    "Many benchmark leaderboards are dominated by larger parameter counts.",
                    "Large models can represent richer function classes.",
                ],
                "evidence_against": [
                    "Smaller distilled or sparse models can match performance at lower cost.",
                    "Optimization instability and data mismatch can nullify scale advantages.",
                    "Inference efficiency and deployment constraints can outweigh top-line gains.",
                ],
            },
            {
                "belief": "Pre-training solves everything",
                "evidence_for": [
                    "Pre-training transfers broad representations to many tasks.",
                    "Foundation models reduce labeled-data requirements in downstream tasks.",
                ],
                "evidence_against": [
                    "Domain shifts can break pre-trained priors and require adaptation.",
                    "Alignment, calibration, and robustness are not solved by scale alone.",
                    "Some problems require explicit structure, tools, or symbolic constraints.",
                ],
            },
            {
                "belief": "Benchmarks measure real progress",
                "evidence_for": [
                    "Benchmarks provide reproducible targets and common evaluation protocols.",
                    "Standardized metrics help compare approaches quickly.",
                ],
                "evidence_against": [
                    "Benchmark overfitting can inflate progress without real-world transfer.",
                    "Hidden leakage and narrow test distributions distort true capability.",
                    "Real deployment needs reliability, interpretability, and safety metrics.",
                ],
            },
        ],
        "nlp": [
            {
                "belief": "Transformer architecture is optimal for all sequence tasks",
                "evidence_for": [
                    "Transformers achieved state-of-the-art in language modeling and translation.",
                    "Self-attention captures long-range dependencies effectively.",
                ],
                "evidence_against": [
                    "State-space and recurrent alternatives can be more efficient at long context.",
                    "Task-specific inductive biases can outperform generic architectures.",
                    "Latency- or memory-constrained scenarios may favor non-transformer designs.",
                ],
            }
        ],
        "computer vision": [
            {
                "belief": "Convolutional inductive biases are obsolete",
                "evidence_for": [
                    "Vision transformer variants have surpassed CNNs on several benchmarks.",
                    "Large-scale pre-training helps attention-based models generalize.",
                ],
                "evidence_against": [
                    "CNN priors improve sample efficiency and robustness in low-data regimes.",
                    "Hybrid architectures often combine convolution with attention for best trade-offs.",
                    "Locality and translation invariance remain valuable for many visual tasks.",
                ],
            }
        ],
        "general": [
            {
                "belief": "Peer review ensures quality",
                "evidence_for": [
                    "Peer review filters obvious methodological errors.",
                    "Review cycles can improve clarity and rigor before publication.",
                ],
                "evidence_against": [
                    "Reviewer variance and bias can produce inconsistent outcomes.",
                    "Reproducibility crises show publication does not guarantee correctness.",
                    "Novel ideas can be rejected due to conservatism.",
                ],
            },
            {
                "belief": "Impact factor measures paper quality",
                "evidence_for": [
                    "High-impact venues often maintain stricter editorial standards.",
                    "Impact factor loosely tracks journal-level visibility.",
                ],
                "evidence_against": [
                    "Journal-level averages are poor proxies for individual paper value.",
                    "Citation distributions are heavily skewed and gameable.",
                    "Field-specific citation norms make cross-domain comparisons unreliable.",
                ],
            },
        ],
    }

    _FIRST_PRINCIPLES: dict[str, list[str]] = {
        "ai/ml": [
            "Learning systems only generalize to patterns represented in data and objective functions.",
            "Optimization follows the loss surface actually defined, not the intent researchers had.",
            "Compute, data quality, and architecture constraints jointly determine capability.",
            "Evaluation is meaningful only if it matches deployment conditions.",
        ],
        "nlp": [
            "Language understanding requires modeling structure, context, and uncertainty.",
            "Architectures are tools; optimality depends on objective, constraints, and data.",
            "Efficiency constraints are first-class for real-world sequence systems.",
        ],
        "computer vision": [
            "Visual perception requires both local feature extraction and global context reasoning.",
            "Inductive bias trades off flexibility with sample efficiency.",
            "Performance claims must account for data regime and deployment constraints.",
        ],
        "general": [
            "Scientific truth depends on reproducible evidence, not authority.",
            "Metrics are proxies and can be gamed when optimized directly.",
            "Consensus can lag behind evidence when incentives favor orthodoxy.",
        ],
    }

    _REBUILT_CONCLUSIONS: dict[str, list[str]] = {
        "ai/ml": [
            "Data quality and objective alignment often matter more than raw data volume.",
            "Model scale is a lever, not a law; capability per unit cost is often the winning objective.",
            "Pre-training is a starting point, while adaptation, tooling, and constraints determine final utility.",
            "Robustness and transfer should be treated as primary progress signals alongside benchmark score.",
        ],
        "nlp": [
            "No single architecture dominates every sequence regime once latency, memory, and domain shift are considered.",
            "Hybrid and task-adaptive designs can outperform one-size-fits-all transformers.",
        ],
        "computer vision": [
            "Convolutional priors remain useful where data is limited or locality dominates.",
            "Best-performing systems frequently combine inductive priors with attention mechanisms.",
        ],
        "general": [
            "Publication and prestige metrics are weak substitutes for direct replication evidence.",
            "Research quality assessment should emphasize methods, transparency, and reproducibility.",
        ],
    }

    _HISTORICAL_PATTERNS: dict[str, list[str]] = {
        "ai/ml": [
            "Perceptrons and neural networks were declared dead after early limitations, then revived repeatedly with new methods and compute.",
            "Expert systems were once expected to replace many professionals but failed to scale due to brittleness.",
            "Symbolic-vs-connectionist debates repeatedly flipped as tooling and data changed.",
        ],
        "nlp": [
            "Rule-based NLP was considered sufficient in early eras, then statistical and neural methods overtook it.",
            "Bag-of-words approaches were once dominant before context-aware models exposed their limits.",
        ],
        "computer vision": [
            "Hand-crafted feature pipelines (e.g., SIFT/HOG-era assumptions) were displaced by learned representations.",
            "Claims that one architecture family had permanently won repeatedly failed after paradigm shifts.",
        ],
        "general": [
            "Consensus that ulcers were primarily stress-induced shifted after evidence for H. pylori.",
            "The assumption of continental immobility collapsed after plate tectonics evidence accumulated.",
        ],
    }

    _TRADITION_HINTS = (
        "always",
        "optimal",
        "ensures",
        "obsolete",
        "all",
        "measures",
    )

    def __init__(self, project_dir: str | None = None):
        workspace = resolve_workspace(project_dir)
        self.project_root = Path(workspace.project_root)

    def _normalize_domain(self, domain: str) -> str:
        normalized = domain.strip().lower()
        if not normalized:
            return "general"
        return self._DOMAIN_ALIASES.get(normalized, normalized)

    def _resolve_paper_path(self, paper_path: str) -> Path:
        path = Path(paper_path)
        if path.is_absolute():
            return path
        return self.project_root / path

    def _infer_domain_from_text(self, text: str) -> str:
        lowered = text.lower()
        keyword_scores = {
            "ai/ml": ["machine learning", "model", "training", "benchmark", "pre-train"],
            "nlp": ["language", "token", "transformer", "sequence", "llm"],
            "computer vision": ["image", "vision", "convolution", "detection", "segmentation"],
        }
        best_domain = "general"
        best_score = 0
        for candidate, keywords in keyword_scores.items():
            score = sum(lowered.count(keyword) for keyword in keywords)
            if score > best_score:
                best_score = score
                best_domain = candidate
        return best_domain

    def _belief_candidates(self, domain: str) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        candidates.extend(self._BELIEF_LIBRARY.get(domain, []))
        if domain != "general":
            candidates.extend(self._BELIEF_LIBRARY["general"])
        return candidates

    def _is_tradition(
        self, belief: str, evidence_for: list[str], evidence_against: list[str]
    ) -> bool:
        lowered = belief.lower()
        has_dogmatic_word = any(token in lowered for token in self._TRADITION_HINTS)
        supportive_is_short = len(evidence_for) <= 2
        strong_counter = len(evidence_against) >= len(evidence_for)
        return has_dogmatic_word or (supportive_is_short and strong_counter)

    def _filter_beliefs(self, domain: str, specific_belief: str) -> list[dict[str, Any]]:
        candidates = self._belief_candidates(domain)
        if not specific_belief:
            return candidates

        target = specific_belief.strip().lower()
        matched = [entry for entry in candidates if target in str(entry["belief"]).lower()]
        if matched:
            return matched

        return [
            {
                "belief": specific_belief,
                "evidence_for": [
                    "Commonly repeated as practical guidance in the field.",
                    "May be supported in some empirical settings.",
                ],
                "evidence_against": [
                    "May fail under distribution shift, constraints, or alternative objectives.",
                    "Could persist due to authority or fashion rather than durable evidence.",
                ],
            }
        ]

    def _build_gaps(
        self, conventional_wisdom: list[dict[str, Any]], rebuilt: list[str]
    ) -> list[str]:
        gaps: list[str] = []
        rebuilt_text = " ".join(rebuilt).lower()

        for item in conventional_wisdom:
            belief = str(item["belief"])
            b = belief.lower()
            if "always" in b and "depends" not in rebuilt_text:
                gaps.append(
                    f"Conventional claim '{belief}' is absolute, rebuilt view is conditional."
                )
            elif "bigger models" in b and "cost" in rebuilt_text:
                gaps.append(
                    "Conventional focus on parameter count conflicts with rebuilt emphasis on capability per unit cost."
                )
            elif "benchmarks" in b and "transfer" in rebuilt_text:
                gaps.append(
                    "Benchmark-centric consensus diverges from rebuilt requirement for real-world transfer and robustness."
                )
            elif "impact factor" in b:
                gaps.append(
                    "Prestige-metric consensus diverges from rebuilt evidence-first assessment of individual papers."
                )

        if not gaps:
            gaps.append(
                "Rebuilt conclusions indicate context-dependence where conventional wisdom is often applied too broadly."
            )
        return gaps

    def _build_contrarian_opportunities(
        self,
        conventional_wisdom: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        opportunities: list[dict[str, str]] = []
        for item in conventional_wisdom:
            belief = str(item["belief"])
            is_tradition = bool(item["is_tradition"])
            if not is_tradition and len(item["evidence_against"]) < 2:
                continue

            advantage = (
                "Compete on neglected axes (data quality, objective alignment, efficiency, reliability) "
                "while others optimize the dominant narrative."
            )
            risk = (
                "Contrarian positions may face reviewer skepticism and higher burden of proof "
                "before acceptance."
            )

            if "bigger models" in belief.lower():
                advantage = "Achieve better cost-performance and deployability by prioritizing efficient architectures."
            elif "more data" in belief.lower():
                advantage = "Win with curated, representative, and debiased data instead of brute-force collection."
            elif "benchmarks" in belief.lower():
                advantage = "Differentiate through robustness and field performance where leaderboard gains do not transfer."

            opportunities.append(
                {
                    "wrong_belief": belief,
                    "advantage": advantage,
                    "risk": risk,
                }
            )
        return opportunities

    def _assess_expert_consensus(self, conventional_wisdom: list[dict[str, Any]]) -> str:
        evidence_driven = 0
        authority_driven = 0

        for item in conventional_wisdom:
            if item["is_tradition"]:
                authority_driven += 1
            if len(item["evidence_against"]) <= len(item["evidence_for"]):
                evidence_driven += 1

        if evidence_driven > authority_driven:
            return (
                "Consensus appears mostly evidence-driven, but still requires boundary-condition checks "
                "before broad application."
            )
        if authority_driven > 0:
            return (
                "Consensus appears partly echo-chamber driven: several beliefs look tradition-heavy "
                "and should be stress-tested empirically."
            )
        return "Consensus quality is mixed; experts may be directionally right but overconfident in generalization."

    def _build_actionable_implications(
        self,
        rebuilt_conclusions: list[str],
        opportunities: list[dict[str, str]],
    ) -> list[str]:
        implications = [
            "Design experiments that explicitly test where the dominant belief fails.",
            "Report context, constraints, and failure modes instead of single aggregate metrics.",
        ]
        implications.extend(
            f"Pursue contrarian thesis: {o['advantage']}" for o in opportunities[:3]
        )
        implications.extend(rebuilt_conclusions[:2])
        return implications

    def deconstruct(
        self,
        domain: str,
        specific_belief: str = "",
        paper_path: str = "",
    ) -> dict[str, Any]:
        """
        Deconstruct conventional wisdom using First Principles reasoning.

        Returns:
            {
                "domain": str,
                "specific_belief": str,
                "conventional_wisdom": [{...}],
                "first_principles": [str],
                "rebuilt_conclusions": [str],
                "conventional_vs_rebuilt_gap": [str],
                "contrarian_opportunities": [{...}],
                "historical_patterns": [str],
                "expert_consensus_assessment": str,
                "actionable_implications": [str],
            }
        """
        inferred_domain = self._normalize_domain(domain)
        if paper_path:
            resolved = self._resolve_paper_path(paper_path)
            if not resolved.exists():
                raise FileNotFoundError(f"Paper not found: {resolved}")
            paper_text = resolved.read_text(encoding="utf-8", errors="ignore")
            if not domain.strip():
                inferred_domain = self._infer_domain_from_text(paper_text)

        conventional_candidates = self._filter_beliefs(inferred_domain, specific_belief)
        conventional_wisdom: list[dict[str, Any]] = []
        for entry in conventional_candidates:
            belief = str(entry["belief"])
            evidence_for = list(entry["evidence_for"])
            evidence_against = list(entry["evidence_against"])
            conventional_wisdom.append(
                {
                    "belief": belief,
                    "evidence_for": evidence_for,
                    "evidence_against": evidence_against,
                    "is_tradition": self._is_tradition(belief, evidence_for, evidence_against),
                }
            )

        first_principles = self._FIRST_PRINCIPLES.get(
            inferred_domain,
            self._FIRST_PRINCIPLES["general"],
        )
        rebuilt_conclusions = self._REBUILT_CONCLUSIONS.get(
            inferred_domain,
            self._REBUILT_CONCLUSIONS["general"],
        )
        gaps = self._build_gaps(conventional_wisdom, rebuilt_conclusions)
        opportunities = self._build_contrarian_opportunities(conventional_wisdom)
        historical_patterns = self._HISTORICAL_PATTERNS.get(
            inferred_domain,
            self._HISTORICAL_PATTERNS["general"],
        )
        consensus_assessment = self._assess_expert_consensus(conventional_wisdom)
        implications = self._build_actionable_implications(rebuilt_conclusions, opportunities)

        return {
            "domain": inferred_domain,
            "specific_belief": specific_belief,
            "conventional_wisdom": conventional_wisdom,
            "first_principles": first_principles,
            "rebuilt_conclusions": rebuilt_conclusions,
            "conventional_vs_rebuilt_gap": gaps,
            "contrarian_opportunities": opportunities,
            "historical_patterns": historical_patterns,
            "expert_consensus_assessment": consensus_assessment,
            "actionable_implications": implications,
        }

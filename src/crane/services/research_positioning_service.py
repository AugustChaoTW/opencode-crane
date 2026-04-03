from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from crane.services.latex_parser import get_all_sections_flat, parse_latex_sections


class ResearchPositioningService:
    _DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
        "AI/ML": (
            "ai",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "transformer",
            "llm",
            "foundation model",
        ),
        "NLP": (
            "nlp",
            "language model",
            "natural language",
            "summarization",
            "translation",
            "token",
            "prompt",
        ),
        "CV": (
            "computer vision",
            "vision",
            "image",
            "video",
            "detection",
            "segmentation",
        ),
        "Robotics": (
            "robot",
            "robotics",
            "manipulation",
            "navigation",
            "autonomous system",
        ),
        "Systems": (
            "system",
            "distributed",
            "inference",
            "latency",
            "throughput",
            "serving",
            "infrastructure",
        ),
        "Security": (
            "security",
            "privacy",
            "adversarial",
            "attack",
            "defense",
            "encryption",
        ),
    }

    _CIVILIZATIONAL_FORCES: dict[str, tuple[str, ...]] = {
        "AI democratization": ("llm", "open model", "agent", "assistant", "copilot"),
        "Compute inequality": ("gpu", "compute", "training cost", "scaling", "distributed"),
        "Regulatory landscape": (
            "safety",
            "alignment",
            "privacy",
            "compliance",
            "trustworthy",
            "governance",
        ),
        "Labor automation transition": (
            "automation",
            "productivity",
            "workflow",
            "human-ai",
            "decision support",
        ),
        "Climate and energy pressure": (
            "energy",
            "efficient",
            "carbon",
            "sustainable",
            "green",
        ),
        "Geopolitical technology competition": (
            "sovereign",
            "national",
            "geopolitic",
            "strategic autonomy",
            "supply chain",
        ),
    }

    _INDUSTRY_TRENDS: dict[str, list[str]] = {
        "AI/ML": [
            "Shift from standalone models to integrated AI systems",
            "Growing pressure for reproducibility and efficient scaling",
            "Movement from benchmark wins to deployment value",
        ],
        "NLP": [
            "From task-specific models to general-purpose language agents",
            "Increased focus on hallucination control and reliability",
            "Rapid adoption of retrieval-augmented generation",
        ],
        "CV": [
            "Convergence of vision-language and multimodal models",
            "Higher demand for real-time and edge deployment",
            "Data-centric curation replacing pure architecture churn",
        ],
        "Robotics": [
            "Fusion of foundation models with embodied control",
            "Rise of sim-to-real transfer pipelines",
            "Growing safety and policy constraints in real-world operation",
        ],
        "Systems": [
            "Inference optimization is now strategic infrastructure",
            "Cost-aware serving and observability become core metrics",
            "Platform consolidation around MLOps and deployment tooling",
        ],
        "Security": [
            "AI systems introduce new attack surfaces",
            "Regulation-driven security and privacy requirements are increasing",
            "Continuous red-teaming becomes standard practice",
        ],
    }

    _NOVELTY_KEYWORDS = (
        "first",
        "novel",
        "new",
        "introduce",
        "unexplored",
        "frontier",
        "state-of-the-art",
        "sota",
        "breakthrough",
    )
    _MATURE_KEYWORDS = (
        "benchmark",
        "baseline",
        "ablation",
        "standard",
        "widely used",
        "established",
        "production",
    )
    _NICHE_KEYWORDS = (
        "low-resource",
        "specialized",
        "domain-specific",
        "rare",
        "narrow",
        "long-tail",
    )

    def __init__(self, project_dir: str | None = None):
        self.project_root = Path(project_dir).resolve() if project_dir else Path.cwd().resolve()

    def analyze_positioning(
        self,
        paper_path: str | None = None,
        research_topic: str = "",
        domain: str = "",
    ) -> dict[str, Any]:
        resolved_paper_path = self._resolve_paper_path(paper_path)
        paper_signals = self._extract_paper_signals(resolved_paper_path)

        topic = research_topic.strip() or self._infer_topic(paper_signals)
        if not topic:
            topic = "General research program"

        inferred_domain = domain.strip() or self._infer_domain(topic, paper_signals)

        civilizational = self._analyze_civilizational(topic, inferred_domain, paper_signals)
        industry = self._analyze_industry(topic, inferred_domain, paper_signals)
        organizational = self._analyze_organizational(inferred_domain, paper_signals, industry)
        tactical = self._analyze_tactical(paper_signals, topic)
        operational = self._analyze_operational(paper_signals, tactical)

        cross_level_connections = self._build_cross_level_connections(
            topic,
            inferred_domain,
            civilizational,
            industry,
            organizational,
            tactical,
            operational,
        )
        level_mismatch = self._detect_level_mismatch(
            civilizational, industry, organizational, tactical
        )
        zoom_recommendation = self._recommend_zoom_level(
            organizational,
            tactical,
            operational,
            level_mismatch,
        )
        blind_spots = self._detect_blind_spots(
            civilizational,
            industry,
            organizational,
            tactical,
            operational,
        )

        return {
            "topic": topic,
            "domain": inferred_domain,
            "levels": {
                "civilizational": civilizational,
                "industry": industry,
                "organizational": organizational,
                "tactical": tactical,
                "operational": operational,
            },
            "cross_level_connections": cross_level_connections,
            "level_mismatch": level_mismatch,
            "zoom_recommendation": zoom_recommendation,
            "blind_spots": blind_spots,
        }

    def _resolve_paper_path(self, paper_path: str | None) -> Path | None:
        if not paper_path:
            return None
        path = Path(paper_path)
        if not path.is_absolute():
            path = self.project_root / path
        return path

    def _extract_paper_signals(self, paper_path: Path | None) -> dict[str, Any]:
        if paper_path is None:
            return {
                "title": "",
                "abstract": "",
                "keywords": [],
                "sections": set(),
                "has_limitations": False,
            }

        structure = parse_latex_sections(paper_path)
        flat_sections = get_all_sections_flat(structure)
        section_names = {section.name.lower().strip() for section in flat_sections}
        raw_text = structure.raw_text
        keyword_pool = f"{structure.title} {structure.abstract} {raw_text[:4000]}"

        return {
            "title": structure.title.strip(),
            "abstract": structure.abstract.strip(),
            "keywords": self._extract_keywords(keyword_pool),
            "sections": section_names,
            "has_limitations": any("limitation" in name for name in section_names)
            or bool(
                re.search(r"\\b(limitations?|threats to validity)\\b", raw_text, re.IGNORECASE)
            ),
        }

    def _infer_topic(self, paper_signals: dict[str, Any]) -> str:
        title = str(paper_signals.get("title", "")).strip()
        if title:
            return title

        abstract = str(paper_signals.get("abstract", "")).strip()
        if abstract:
            sentence = re.split(r"(?<=[.!?])\s+", abstract)[0].strip()
            if sentence:
                return sentence[:140]

        keywords = paper_signals.get("keywords", [])
        if keywords:
            return f"Research on {', '.join(keywords[:4])}"

        return ""

    def _infer_domain(self, topic: str, paper_signals: dict[str, Any]) -> str:
        text = f"{topic} {' '.join(paper_signals.get('keywords', []))}".lower()
        best_domain = "AI/ML"
        best_hits = 0
        for name, keywords in self._DOMAIN_KEYWORDS.items():
            hits = sum(1 for keyword in keywords if keyword in text)
            if hits > best_hits:
                best_domain = name
                best_hits = hits
        return best_domain

    def _extract_keywords(self, text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-/]{2,}", text.lower())
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "that",
            "this",
            "into",
            "using",
            "based",
            "approach",
            "method",
            "results",
            "paper",
            "model",
            "models",
        }
        filtered = [token for token in tokens if token not in stopwords and len(token) >= 3]
        counts = Counter(filtered)
        return [token for token, _ in counts.most_common(12)]

    def _analyze_civilizational(
        self,
        topic: str,
        domain: str,
        paper_signals: dict[str, Any],
    ) -> dict[str, Any]:
        text = f"{topic} {domain} {' '.join(paper_signals.get('keywords', []))}".lower()
        key_forces: list[str] = []
        force_hits = 0

        for force, force_keywords in self._CIVILIZATIONAL_FORCES.items():
            hit_count = sum(1 for keyword in force_keywords if keyword in text)
            if hit_count > 0:
                key_forces.append(force)
                force_hits += hit_count

        if not key_forces and domain in {"AI/ML", "NLP", "CV", "Robotics"}:
            key_forces = ["AI democratization", "Regulatory landscape"]
            force_hits = 2

        score = min(100.0, 35.0 + float(force_hits * 12)) if key_forces else 28.0
        analysis = (
            f"{topic} sits in {domain} and intersects {len(key_forces)} societal force(s), "
            "indicating meaningful long-horizon relevance."
            if key_forces
            else f"{topic} currently appears weakly coupled to large civilizational shifts."
        )

        return {
            "analysis": analysis,
            "key_forces": key_forces,
            "relevance_score": round(score, 1),
        }

    def _analyze_industry(
        self,
        topic: str,
        domain: str,
        paper_signals: dict[str, Any],
    ) -> dict[str, Any]:
        text = f"{topic} {' '.join(paper_signals.get('keywords', []))}".lower()
        novelty_hits = sum(1 for kw in self._NOVELTY_KEYWORDS if kw in text)
        mature_hits = sum(1 for kw in self._MATURE_KEYWORDS if kw in text)
        niche_hits = sum(1 for kw in self._NICHE_KEYWORDS if kw in text)

        if novelty_hits >= 2 and mature_hits == 0:
            position = "leading edge"
        elif mature_hits >= 2 and novelty_hits <= 1:
            position = "mainstream"
        elif niche_hits >= 2:
            position = "niche"
        else:
            position = "emerging"

        macro_trends = self._INDUSTRY_TRENDS.get(domain, self._INDUSTRY_TRENDS["AI/ML"])
        analysis = (
            f"In {domain}, this topic is positioned as {position}; it should align with "
            "domain adoption velocity and evidence expectations."
        )

        return {
            "analysis": analysis,
            "macro_trends": macro_trends,
            "position": position,
        }

    def _analyze_organizational(
        self,
        domain: str,
        paper_signals: dict[str, Any],
        industry: dict[str, Any],
    ) -> dict[str, Any]:
        sections: set[str] = paper_signals.get("sections", set())
        has_eval = any(
            "experiment" in name or "evaluation" in name or "result" in name for name in sections
        )
        has_method = any("method" in name or "approach" in name for name in sections)
        has_limitations = bool(paper_signals.get("has_limitations", False))
        position = str(industry.get("position", "emerging"))

        fit_score = int(has_eval) + int(has_method) + int(has_limitations)
        if fit_score >= 3:
            strategic_fit = "High fit with research organization goals and review expectations."
        elif fit_score == 2:
            strategic_fit = (
                "Moderate fit; core direction is sound but portfolio framing is incomplete."
            )
        else:
            strategic_fit = (
                "Low fit; project narrative is not yet aligned with organizational strategy."
            )

        if position == "leading edge" and not has_eval:
            resource_alignment = (
                "Constrained: frontier ambition with insufficient evaluation infrastructure."
            )
        elif domain in {"AI/ML", "NLP", "CV"} and not has_limitations:
            resource_alignment = "Partially aligned: technical assets exist, but governance/risk documentation is weak."
        else:
            resource_alignment = (
                "Aligned: current scope is feasible with typical academic/industry resources."
            )

        analysis = (
            "Organizational success depends on matching ambition with evaluation rigor, "
            "cross-functional support, and publication strategy."
        )
        return {
            "analysis": analysis,
            "strategic_fit": strategic_fit,
            "resource_alignment": resource_alignment,
        }

    def _analyze_tactical(self, paper_signals: dict[str, Any], topic: str) -> dict[str, Any]:
        sections: set[str] = paper_signals.get("sections", set())
        gaps = self._derive_section_gaps(
            sections, bool(paper_signals.get("has_limitations", False))
        )

        next_30_90_days: list[str] = []
        milestones: list[str] = []

        if "related_work" in gaps:
            next_30_90_days.append(
                "Expand related-work mapping and position against nearest baselines"
            )
            milestones.append("Related work synthesis completed and citation map updated")
        if "method" in gaps:
            next_30_90_days.append(
                "Stabilize method section with algorithmic details and assumptions"
            )
            milestones.append("Method specification frozen for experiments")
        if "evaluation" in gaps:
            next_30_90_days.append("Design benchmark protocol, baselines, and ablation grid")
            milestones.append("Evaluation protocol executed with reproducible scripts")
        if "conclusion" in gaps:
            next_30_90_days.append("Consolidate findings into conclusion with measurable claims")
            milestones.append("Conclusion and contributions aligned with results")
        if "limitations" in gaps:
            next_30_90_days.append(
                "Document limitations, failure cases, and responsible-use boundaries"
            )
            milestones.append("Limitations/threats section accepted by internal review")

        if not next_30_90_days:
            next_30_90_days = [
                f"Run focused iteration cycle on {topic} with stronger baselines",
                "Prepare submission package (artifact, appendix, reproducibility checklist)",
            ]
            milestones = [
                "Full manuscript polish complete",
                "Internal pre-submission review passed",
            ]

        return {
            "analysis": "Tactical horizon should convert positioning into measurable 30/60/90-day outcomes.",
            "next_30_90_days": next_30_90_days,
            "milestones": milestones,
        }

    def _analyze_operational(
        self,
        paper_signals: dict[str, Any],
        tactical: dict[str, Any],
    ) -> dict[str, Any]:
        sections: set[str] = paper_signals.get("sections", set())
        has_abstract = bool(paper_signals.get("abstract", "").strip())

        immediate_actions: list[str] = []
        if not has_abstract:
            immediate_actions.append("Draft a concise abstract with problem-method-result triad")
        if not any("introduction" in name for name in sections):
            immediate_actions.append("Write an introduction defining gap, stakes, and contribution")
        if not any("evaluation" in name or "experiment" in name for name in sections):
            immediate_actions.append("Create evaluation checklist and schedule first benchmark run")
        if not bool(paper_signals.get("has_limitations", False)):
            immediate_actions.append("Add limitations and failure-case placeholders")

        if not immediate_actions:
            immediate_actions.extend(
                [
                    "Tighten claim-evidence linkage in each section",
                    "Re-run one key experiment for confidence interval reporting",
                    "Prepare camera-ready style consistency pass",
                ]
            )

        this_week = immediate_actions[:3]
        if len(this_week) < 3:
            tactical_items = tactical.get("next_30_90_days", [])
            for item in tactical_items:
                if isinstance(item, str) and item not in this_week:
                    this_week.append(item)
                if len(this_week) >= 3:
                    break

        return {
            "analysis": "Operational execution should remove immediate blockers before strategic expansion.",
            "immediate_actions": immediate_actions,
            "this_week": this_week,
        }

    def _derive_section_gaps(self, sections: set[str], has_limitations: bool) -> list[str]:
        gaps: list[str] = []
        if not any("related" in name and "work" in name for name in sections):
            gaps.append("related_work")
        if not any("method" in name or "approach" in name for name in sections):
            gaps.append("method")
        if not any(
            "evaluation" in name or "experiment" in name or "result" in name for name in sections
        ):
            gaps.append("evaluation")
        if not any("conclusion" in name for name in sections):
            gaps.append("conclusion")
        if not has_limitations:
            gaps.append("limitations")
        return gaps

    def _build_cross_level_connections(
        self,
        topic: str,
        domain: str,
        civilizational: dict[str, Any],
        industry: dict[str, Any],
        organizational: dict[str, Any],
        tactical: dict[str, Any],
        operational: dict[str, Any],
    ) -> list[str]:
        return [
            (
                "Civilizational forces "
                f"({', '.join(civilizational.get('key_forces', [])[:2]) or 'limited signal'}) "
                f"shape industry trajectory in {domain}."
            ),
            (
                f"Industry position ({industry.get('position', 'emerging')}) sets the evidence bar "
                "for organizational prioritization and staffing."
            ),
            (
                "Organizational fit determines whether tactical 30/90-day plans "
                "can convert into publishable outcomes."
            ),
            (
                f"Operational actions this week ({len(operational.get('this_week', []))} items) "
                f"are the execution bridge for the {topic} agenda."
            ),
            (
                f"Tactical milestones ({len(tactical.get('milestones', []))}) should be used "
                "as checkpoints to validate cross-level coherence."
            ),
        ]

    def _detect_level_mismatch(
        self,
        civilizational: dict[str, Any],
        industry: dict[str, Any],
        organizational: dict[str, Any],
        tactical: dict[str, Any],
    ) -> str | None:
        relevance = float(civilizational.get("relevance_score", 0.0))
        position = str(industry.get("position", "emerging"))
        resource_alignment = str(organizational.get("resource_alignment", "")).lower()
        milestones = tactical.get("milestones", [])
        milestone_count = len(milestones) if isinstance(milestones, list) else 0

        if relevance >= 70.0 and position in {"emerging", "niche"} and milestone_count >= 3:
            return "Solving a strategic problem with tactical tools"
        if position == "leading edge" and "constrained" in resource_alignment:
            return "Leading-edge ambition without matching organizational resources"
        if (
            "low fit" in str(organizational.get("strategic_fit", "")).lower()
            and milestone_count > 0
        ):
            return "Executing milestones without strategic alignment"
        return None

    def _recommend_zoom_level(
        self,
        organizational: dict[str, Any],
        tactical: dict[str, Any],
        operational: dict[str, Any],
        level_mismatch: str | None,
    ) -> str:
        if level_mismatch:
            return "organizational"
        immediate_actions = operational.get("immediate_actions", [])
        milestones = tactical.get("milestones", [])
        if isinstance(immediate_actions, list) and len(immediate_actions) >= 4:
            return "operational"
        if isinstance(milestones, list) and len(milestones) >= 4:
            return "tactical"
        if "constrained" in str(organizational.get("resource_alignment", "")).lower():
            return "organizational"
        return "industry"

    def _detect_blind_spots(
        self,
        civilizational: dict[str, Any],
        industry: dict[str, Any],
        organizational: dict[str, Any],
        tactical: dict[str, Any],
        operational: dict[str, Any],
    ) -> list[str]:
        blind_spots: list[str] = []

        if float(civilizational.get("relevance_score", 0.0)) < 40.0:
            blind_spots.append(
                "Civilizational narrative is weak; long-horizon societal relevance is unclear."
            )
        if str(industry.get("position", "")) == "niche":
            blind_spots.append(
                "Industry adoption path is underdeveloped beyond specialized use-cases."
            )
        if "constrained" in str(organizational.get("resource_alignment", "")).lower():
            blind_spots.append("Resource-risk mismatch may block execution at scale.")
        if len(tactical.get("milestones", [])) < 2:
            blind_spots.append("Tactical plan lacks enough milestone granularity.")
        if len(operational.get("this_week", [])) < 2:
            blind_spots.append(
                "Operational cadence is weak; immediate execution loop is underdefined."
            )

        if not blind_spots:
            blind_spots.append(
                "No critical blind spot detected; maintain periodic cross-level audit."
            )
        return blind_spots

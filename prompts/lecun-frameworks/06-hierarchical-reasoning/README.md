# Hierarchical Reasoning Engine
**Attribution:** Based on Yann LeCun's Hierarchical Representation Theory

## Core Concept
The Hierarchical Reasoning Engine implements Yann LeCun's theory that intelligent systems must reason at multiple levels of abstraction simultaneously. Instead of remaining confined to a single perspective, this framework forces an analysis that spans from immediate operational tasks to broad civilizational shifts, identifying connections and misalignments across the entire spectrum.

## Core LeCun Concept: Hierarchical Representation
Yann LeCun argues that human-level AI requires the ability to represent the world at different scales of time and abstraction. In this framework, reasoning isn't linear. It's a vertical stack where high-level goals (abstract principles) inform mid-level strategies (plans), which then dictate low-level actions (concrete details). By analyzing a problem across these layers, you ensure your daily actions align with your long-term strategic reality.

## When to Use
- You feel "stuck in the weeds" of daily operations and need perspective.
- A major strategic decision feels disconnected from your current resources.
- You suspect you're treating a systemic industry shift as a temporary tactical problem.
- You need to align a team's daily tasks with a company's mission.

## The Prompt
```markdown
You are a cognitive scientist who implements Yann LeCun's hierarchical representation theory — his argument that intelligent systems must reason at multiple levels of abstraction simultaneously, from concrete details to abstract principles, instead of staying stuck at one level.

I need you to analyze my problem at every level of abstraction — from the biggest picture to the smallest detail.

Layer:
- Level 5 — Civilizational: how does this relate to the broadest forces shaping society (technology, demographics, climate, geopolitics)
- Level 4 — Industry: what macro trends in my industry are influencing this situation that I might not see from inside
- Level 3 — Organizational: how does this affect and get affected by my company's strategy, culture, and resources
- Level 2 — Tactical: what specific actions, timelines, and resources are needed to address this in the next 30-90 days
- Level 1 — Operational: what do I need to do TODAY and THIS WEEK as the immediate next step
- Cross-level connections: how do decisions at one level create consequences at other levels
- Level mismatch detection: am I trying to solve a Level 4 problem with a Level 1 solution (or vice versa)
- Zoom recommendation: which level of abstraction should I be spending the most time thinking about right now
- Blind spot identification: which level am I naturally ignoring that could contain the most important insight

Format as a LeCun-style hierarchical analysis with insights at each level, cross-level connections, and a recommended focus area.

My problem: [YOUR PROBLEM: Describe your challenge, business decision, or strategic question]
```

## Output Format
The AI will provide a structured report including:
1. **Vertical Analysis:** Insights for each of the five levels (Civilizational down to Operational).
2. **Systemic Connections:** An explanation of how these levels influence each other.
3. **Diagnostic Check:** Identification of any "level mismatches" (e.g., using a short-term fix for a long-term industry shift).
4. **Actionable Focus:** A specific recommendation on which level requires your immediate mental energy and which level you've likely been neglecting.

## Usage Tips
- **Be Specific in Input:** The more detail you provide about your current "Level 1" or "Level 2" situation, the better the engine can connect it to "Level 4" and "Level 5" trends.
- **Watch for Mismatches:** Pay close attention to the "Level Mismatch Detection" section. This is often where the most significant strategic errors are found.
- **Iterative Zooming:** If the "Zoom Recommendation" suggests focusing on Level 4, run the prompt again with a more detailed focus on industry macro trends.

## Example Input Template
**Problem:** Our software company is seeing a 15% drop in renewals for our legacy enterprise product, even though our support team is working harder than ever to resolve tickets.

**Context:** We've been focused on bug fixes and UI polish (Level 1/2), but competitors are launching AI-native alternatives.

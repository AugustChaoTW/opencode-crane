# Energy-Based Decision Analyzer

**Attribution:** Based on the Energy-Based Models (EBM) framework proposed by Yann LeCun.

## Core Concept Summary
This framework treats decision-making as a search for the state with the lowest "energy"—the option most compatible with your constraints, goals, and external reality. Instead of settling for the first plausible solution, it evaluates all possible outcomes simultaneously to find the global optimum.

## Core LeCun Concept: Energy-Based Models (EBMs)
In Yann LeCun's architecture, intelligence involves evaluating a set of possible outcomes and assigning an "energy" score to each. High energy represents incompatibility or violation of constraints, while low energy indicates a high degree of compatibility with the world and your objectives. The system does not just generate an answer; it minimizes an energy function to select the option that best fits the totality of the situation.

## When to Use This Framework
- Complex decisions with multiple competing constraints.
- High-stakes strategic planning where "obvious" answers might be local minima.
- Situations where you feel pressured to act and need to correct for action bias.
- When you need to evaluate the robustness of a choice against different scenarios.

## The Prompt
```markdown
You are a decision scientist who applies Yann LeCun's Energy-Based Model framework to real-world decisions. This theory suggests that intelligent systems should evaluate all possible outcomes simultaneously and select the one with the lowest "energy" (most compatibility with reality) instead of just generating the first plausible answer.

Analyze the decision provided using this energy-based framework:

1. Option Generation: List every possible course of action, including ones not yet considered (minimum 5-7 options).
2. Compatibility Scoring: For each option, rate how compatible it is with the stated goals, constraints, values, and real-world conditions.
3. Constraint Satisfaction: Identify which options violate hard constraints (budget, time, legal, ethical) and must be eliminated.
4. Energy Landscape Mapping: Rank all options from lowest energy (best fit) to highest energy (worst fit) with clear reasoning.
5. Local Minima Warning: Determine if the "obvious best choice" is actually the best, or if it represents a local optimum while a superior option exists elsewhere.
6. Sensitivity Analysis: Identify which decision factors, if changed slightly, would flip the ranking entirely.
7. Robustness Check: Evaluate which option performs reasonably well across all scenarios, not just the best case.
8. Regret Minimization: Predict which choice would result in the least regret in 10 years, regardless of the ultimate outcome.
9. Action Bias Correction: Evaluate if an option is being chosen because it is genuinely best, or because of internal or external pressure to take action.

Format the analysis as a LeCun-style energy-based decision report with options ranked, scored, and a clear recommendation including a confidence level.

[YOUR DECISION: Describe the decision you're facing, your options, your constraints, and what outcome matters most]
```

## Usage Tips and Best Practices
- **Be Explicit with Constraints:** The more detail you provide about your "hard" constraints (e.g., "Must cost under $5k," "Must be completed by June"), the better the AI can calculate the "energy" of each option.
- **Challenge the "Obvious":** Pay close attention to the "Local Minima" section. This is designed to help you see past conventional wisdom or your own biases.
- **Compare Scenarios:** If you are unsure about certain external factors, run the prompt twice with different assumptions to see how the energy landscape shifts.

## Output Format
The AI will provide a structured report including:
- **Comprehensive Option List:** A broad range of 5-7 potential paths.
- **Detailed Scoring:** A breakdown of how each path fits your criteria.
- **Filtered Results:** Immediate removal of non-viable options.
- **Ranked Leaderboard:** A clear hierarchy of choices from most to least compatible.
- **Risk Assessment:** Insights into sensitivity, robustness, and potential regret.
- **Final Recommendation:** A definitive suggested path with a percentage-based confidence level.

## Example Input Template
[YOUR DECISION: We need to decide whether to migrate our entire infrastructure to a new cloud provider or optimize our current setup. Our main constraints are a $50k migration budget and a hard deadline of 3 months. The most important outcome is long-term scalability and reducing monthly recurring costs by at least 20%.]

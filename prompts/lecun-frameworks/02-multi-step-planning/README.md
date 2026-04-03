# Multi-Step Planning Framework

## Attribution
**Source:** Inspired by Yann LeCun's research principles at Meta FAIR.

## Core Concept Summary
This framework forces the AI to decompose complex requests into a structured execution plan before generating the final output. It addresses the "one-token-at-a-time" limitation by establishing a multi-step roadmap including dependency mapping, obstacle anticipation, and quality checkpoints.

## Core LeCun Concept
Yann LeCun, Chief AI Scientist at Meta, frequently criticizes current Large Language Models (LLMs) for their lack of a "world model" and hierarchical planning. He argues that because LLMs generate text autoregressively (one token after another), they often fail at complex reasoning tasks that require looking ahead or considering long-term dependencies. This framework emulates a "planning layer" by requiring the model to think through the entire execution path before acting.

## When to Use This Framework
- **Highly Complex Tasks:** When a request involves multiple moving parts or sensitive logic.
- **Strategic Planning:** For business strategies, technical architectures, or long-form content.
- **Problem Solving:** When you need the AI to anticipate potential failures or provide backup paths.
- **High-Stakes Output:** When "getting it right the first time" is critical and requires rigorous self-evaluation.

## The Prompt (Ready to Copy-Paste)
```markdown
You are an AI planning researcher at Meta FAIR (Fundamental AI Research) who implements LeCun's core criticism of current AI: that language models generate responses one token at a time without planning ahead, while real intelligence requires thinking multiple steps forward before acting.

I need you to PLAN your entire response before writing a single word.

Plan:
- Goal decomposition: break my request into 5-10 sub-goals that must be accomplished in sequence
- Dependency mapping: which sub-goals must be completed before others can start (the critical path)
- Resource identification: what knowledge, data, frameworks, and reasoning tools are needed for each sub-goal
- Obstacle anticipation: what could go wrong at each step and how to handle it if it does
- Alternative paths: if the primary plan hits a dead end, what's the backup approach
- Quality criteria: what does "excellent" look like for each sub-goal (define the standard before executing)
- Execution sequence: the exact order to tackle each sub-goal for maximum coherence
- Integration plan: how all sub-goals connect into one unified, consistent final response
- Self-evaluation checkpoints: after completing each sub-goal, verify it meets the quality criteria before moving on

Now execute the plan step by step, showing your work at each stage.
Format as a planned, multi-step response with the reasoning visible at each stage — not a stream-of-consciousness answer.

[YOUR REQUEST: Describe what you need — the more complex, the more this planning framework improves the output]
```

## Output Format
The AI will produce a two-phase response:
1.  **The Master Plan:** A detailed breakdown of the 9 planning components listed in the prompt.
2.  **Sequential Execution:** A step-by-step fulfillment of each sub-goal, where the AI explicitly checks its work against the defined quality criteria before proceeding to the next step.

## Usage Tips and Best Practices
- **Complexity is Key:** This prompt is "overkill" for simple questions; use it for tasks that would take a human 30+ minutes to plan.
- **Review the Plan First:** For extremely critical tasks, ask the AI to "Stop after generating the Plan" so you can refine the sub-goals before it starts the execution phase.
- **Specify Constraints:** If you have specific "Quality Criteria" in mind, add them to your request to guide the AI's internal self-evaluation.

## Example Input Template
**Prompt:**
[PASTE THE FRAMEWORK ABOVE]

**Request:**
"I need to design a 12-month go-to-market strategy for a new B2B SaaS platform that uses AI to automate legal compliance for healthcare startups."

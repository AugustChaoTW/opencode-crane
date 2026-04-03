# Hallucination Destroyer

This framework forces AI to move beyond statistical word prediction and toward grounded reasoning. It's based on Yann LeCun's critique that large language models lack a true model of the world, leading them to produce confident but unverified claims.

## Core Concept
The Hallucination Destroyer implements a rigorous verification layer by requiring the AI to classify every claim it makes. It forces the model to separate facts from inferences and explicitly flag uncertainties, preventing the typical "confident-sounding nonsense" that plagues standard LLM outputs.

## Core LeCun Concept
Yann LeCun often argues that current LLMs hallucinate because they're simply predicting the next most likely token based on statistical patterns. They don't have a grounded model of reality to check their statements against. This prompt creates a manual "world model" check, forcing the AI to evaluate its own internal knowledge against levels of certainty and logical consistency before presenting it as truth.

## When to Use
Use this framework for any task where accuracy is the top priority.
- Fact-checking complex claims or historical data.
- Technical analysis where logical errors can have high costs.
- Strategic planning that relies on specific market or data assumptions.
- Any situation where "I don't know" is a more valuable answer than a guess.

## The Prompt
Copy and paste the block below to activate the Hallucination Destroyer:

```text
You are an AI reliability researcher implementing Yann LeCun's core critique of large language models: that they hallucinate because they generate text without grounding it in a verified model of reality — producing confident-sounding nonsense that passes for expertise.
I need you to ground every claim in verifiable reasoning and flag anything you're uncertain about.

Grounding Requirements:
- Claim separation: break your response into individual factual claims, each on its own line
- Evidence classification: for each claim, label it as VERIFIED (you're highly confident), PROBABLE (likely but not certain), INFERRED (logical deduction but not established fact), or SPECULATIVE (educated guess)
- Source of knowledge: for each claim, state WHY you believe it (training data pattern, logical deduction, mathematical certainty, or assumption)
- Uncertainty flagging: explicitly mark every statement where you're less than 80% confident with a [VERIFY] tag
- Contradiction scan: check if any of your claims contradict each other
- Fabrication check: are any specific numbers, dates, quotes, or statistics generated from pattern rather than knowledge (if so, say "I'm generating this estimate, not citing a source")
- Alternative explanations: for key conclusions, what's the strongest counter-argument or alternative interpretation
- What I don't know: explicitly list the things relevant to this question that you genuinely don't have enough information to answer
- Confidence calibration: give your overall response a confidence score from 1-10 with reasoning

Format as a grounded response with every claim labeled by confidence level and all uncertainties explicitly flagged.

[YOUR QUESTION: Ask any factual, analytical, or strategic question where accuracy matters more than speed]
```

## Output Format
The AI will provide a structured report instead of a standard paragraph:
1. **Grounded Claims List:** Each sentence is labeled with a status (VERIFIED, PROBABLE, etc.) and a brief explanation of the knowledge source.
2. **Uncertainty Tags:** Low-confidence items are marked with `[VERIFY]`.
3. **Alternative Perspectives:** A summary of counter-arguments or different ways to interpret the data.
4. **Knowledge Gaps:** A specific list of what the AI cannot answer.
5. **Final Calibration:** A 1-10 score reflecting the AI's own assessment of the response's reliability.

## Usage Tips & Best Practices
- **Be Specific:** The more specific your question, the better the AI can ground its claims. Vague questions lead to more speculative labels.
- **Challenge the Labels:** If the AI labels something as VERIFIED but you're skeptical, ask it to provide the specific training data pattern or logic it used.
- **Watch for Patterns:** Use this to identify where the AI is relying on "pattern matching" versus "logical deduction."
- **Iterate on Gaps:** Use the "What I don't know" section as a starting point for your next query or manual research.

## Example Input Template
```text
[INSERT PROMPT ABOVE]

My question: What are the specific, verified long-term environmental impacts of using sodium-ion batteries compared to lithium-ion batteries, and which parts of the supply chain remain speculative?
```

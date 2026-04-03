# World Model Reasoning Engine

Based on Yann LeCun's Research on Autonomous Machine Intelligence

## Core Concept Summary
The World Model Reasoning Engine moves AI beyond text pattern matching by forcing it to build an internal representation of the environment. It simulates cause-and-effect relationships and physical or economic constraints before generating a response. This approach ensures decisions are grounded in a functional understanding of how the world works rather than just linguistic probability.

## Core LeCun Concept
This framework is rooted in Yann LeCun's proposal for "A Path Towards Autonomous Machine Intelligence." The central idea is that true intelligence requires a "World Model" that can predict the consequences of actions and the evolution of the environment. Instead of predicting the next token, the engine predicts the next state of the world, identifying causal links and hidden variables that govern complex systems.

## When to Use This Framework
- Making high-stakes business or personal decisions with many moving parts.
- Analyzing complex systems where the outcome isn't immediately obvious.
- Predicting the long-term impact of a specific strategy or intervention.
- Identifying risks and second-order effects in a changing environment.

## The Prompt
```markdown
You are an AI researcher who has deeply studied Yann LeCun's World Model architecture. This architecture proposes that real intelligence requires an internal model of how the world works, not just pattern matching on text.

I need you to build an internal world model before answering my question, instead of jumping to the first plausible-sounding response.

Reason through these steps:
1. State the observable facts: what do you ACTUALLY know about this situation from the information I provided? Separate facts from assumptions.
2. Build the world model: what are the cause-and-effect relationships, physical constraints, economic forces, and human incentives at play?
3. Identify hidden variables: what factors are NOT mentioned but are almost certainly influencing the situation?
4. Simulate forward: based on your world model, what happens next if nothing changes (the default trajectory)?
5. Simulate interventions: if I take action A, B, or C, how does each ripple through the world model?
6. Predict second-order effects: what consequences of each action are NOT obvious but become inevitable over time?
7. Identify model uncertainty: where is your world model weakest and what information would make it stronger?
8. Contradiction check: does your reasoning contain any internal contradictions or assumptions that conflict?
9. Confidence calibration: rate your confidence in each prediction honestly. Don't pretend certainty you don't have.

Format your response as a LeCun-style world model analysis with a causal diagram described in text, forward simulations, and calibrated confidence levels.

[YOUR SITUATION: Describe the complex decision, business problem, or situation you need deep reasoning on]
```

## Output Format
When you run this prompt, the AI will provide:
- **Causal Diagram (Text-based):** A mapping of the forces and incentives driving the situation.
- **Forward Simulations:** Detailed "what-if" scenarios based on current trajectories and possible actions.
- **Confidence Levels:** Explicit percentage or qualitative ratings for each prediction to highlight where information is missing.
- **Hidden Variable Analysis:** A list of overlooked factors that could change the entire outcome.

## Usage Tips and Best Practices
- **Provide Rich Context:** The world model is only as good as the information it's built on. Include as many specific details as possible about the players, constraints, and environment.
- **Define Your Actions:** If you want the AI to simulate specific interventions, clearly label them as "Action A," "Action B," etc.
- **Interrogate the Uncertainty:** Pay close attention to the "Model Uncertainty" section. This tells you exactly what data you need to find next to make a better decision.
- **Iterate:** If the initial world model feels incomplete, use the AI's "Uncertainty" feedback to provide more context and run the prompt again.

## Example Input Template
**Situation:** Our mid-sized software company is considering switching from a subscription model to a usage-based pricing model.

**Current Facts:**
- 5,000 active monthly users.
- Average revenue per user is $50.
- Customer churn is currently 2% per month.
- Competitors are starting to offer usage-based pricing.

**Goals:**
- Increase long-term revenue.
- Reward high-volume users while staying accessible to small teams.

[YOUR SITUATION: Describe the complex decision, business problem, or situation you need deep reasoning on]

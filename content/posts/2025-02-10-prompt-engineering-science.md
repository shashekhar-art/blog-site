---
title: "Prompt Engineering: From Dark Art to Engineering Discipline"
date: "2025-02-10"
category: "Prompt Engineering"
tags: ["PromptEngineering", "ChainOfThought", "FewShot", "Production"]
summary: "Prompt engineering has evolved from guessing magic phrases to a rigorous engineering discipline. Learn the systematic techniques that actually work in production."
cover_gradient: "gradient-5"
cover_emoji: "🪄"
author: "Shashi Shekhar"
---

## The Dirty Secret About Prompts

Early LLM demos made it look like magic. Type the right incantation and the model would do anything. "Say please" one pundit suggested. People tried "ignore all previous instructions" and then debated it on Twitter.

The truth is more boring and more powerful: **prompt engineering is software engineering**. It has principles, patterns, failure modes, and best practices. And like all good engineering, it's empirical — you test, measure, and iterate.

Let me share what actually works.

## Foundation: How LLMs Actually Read Your Prompts

To engineer prompts well, you need to understand what's happening under the hood.

LLMs predict the next token based on everything before it. The prompt is the initial context. The model's response is a statistical continuation of that context. When you write a prompt, you're not *instructing* an AI — you're *shaping the context* in which it generates.

This mental model explains everything:

- Why examples work (they shift the distribution toward similar outputs)
- Why order matters (earlier tokens influence later ones)
- Why "think step by step" works (it primes step-by-step reasoning tokens)
- Why being specific beats being vague (less ambiguous context = less ambiguous output)

## The Prompt Structure That Works

Here's the template I use for complex prompts:

```
[SYSTEM CONTEXT]
You are a [specific role with relevant expertise].
Your task is to [clear objective].
You must [hard constraints].
You should [soft preferences].

[EXAMPLES] (optional but powerful)
---
Input: [example 1]
Output: [example 1 response]
---
Input: [example 2]
Output: [example 2 response]
---

[CURRENT INPUT]
[The actual user query or data]

[OUTPUT FORMAT]
Respond in [format]. Include [required fields].
```

Let me break down why each part matters.

## Technique 1: Role Prompting

"You are an expert" sounds like flattery, but it works because it shifts the model's statistical context toward expert-level language patterns.

**Weak:**
```
Summarize this contract.
```

**Strong:**
```
You are a senior corporate lawyer specializing in SaaS vendor agreements.
Your task is to review the following contract excerpt and identify:
1. Non-standard clauses that favor the vendor
2. Missing standard protections
3. Any ambiguous language that could create liability

Be direct and specific. Flag actual clause numbers.
```

The difference isn't just style. The strong version produces substantially more useful output because it constrains the model's behavior space.

## Technique 2: Chain-of-Thought (CoT)

Simply adding "think step by step" or "let's work through this" dramatically improves reasoning accuracy. This isn't placebo — it's documented in research.

```python
# Without CoT — often wrong on complex reasoning
prompt_basic = """
Is this refund request valid? Customer bought 45 days ago, policy is 30 days.
Answer yes/no.
"""

# With CoT — much more reliable
prompt_cot = """
Is this refund request valid?

Context:
- Purchase date: 45 days ago
- Refund window: 30 days from purchase

Think through this step by step:
1. Calculate days since purchase
2. Compare to refund window
3. State your conclusion

Then give your final answer.
"""
```

For production systems handling important decisions, always use CoT. The "extra tokens" are worth it.

## Technique 3: Few-Shot Learning

Give examples and the model learns the pattern. This is arguably the most powerful technique for formatting and classification tasks.

```python
classification_prompt = """
Classify customer feedback sentiment and urgency.

Examples:
---
Feedback: "The product is amazing! Exactly what I needed."
Sentiment: positive
Urgency: low
Category: praise
---
Feedback: "This is broken and I have a demo tomorrow! URGENT FIX NEEDED"
Sentiment: negative
Urgency: critical
Category: bug_report
---
Feedback: "How do I export to CSV? Can't find the option."
Sentiment: neutral
Urgency: medium
Category: feature_question
---

Now classify:
Feedback: "{user_feedback}"
Sentiment:
Urgency:
Category:
"""
```

**Key insights on few-shot prompts:**
- 3-5 examples is usually optimal
- Examples should cover edge cases, not just obvious cases
- Order examples from simple to complex
- Ensure examples match your real distribution

## Technique 4: Structured Output

Stop parsing free text. Tell the model exactly what format to return.

```python
import anthropic
import json

client = anthropic.Anthropic()

extract_prompt = """
Extract structured information from the following job posting.

Return ONLY a JSON object with this exact schema:
{
  "title": "string",
  "company": "string",
  "location": "string or null",
  "salary_range": {"min": number or null, "max": number or null, "currency": "string"},
  "required_skills": ["string"],
  "experience_years": {"min": number or null, "max": number or null},
  "remote": boolean
}

Job Posting:
{posting}
"""

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": extract_prompt.format(posting=job_text)}]
)

# Parse the structured output
data = json.loads(response.content[0].text)
```

For even better reliability, use tool use / function calling — it forces schema-compliant output at the API level.

## Technique 5: Constitutional Constraints

Define what the model should NOT do as clearly as what it should do.

```python
customer_service_prompt = """
You are a helpful customer service assistant for TechCorp.

You MUST:
- Be professional and empathetic
- Acknowledge the customer's frustration if present
- Provide actionable next steps

You MUST NOT:
- Make promises about refunds without verifying eligibility
- Mention competitor products
- Discuss internal system issues
- Share specific pricing not in the provided catalog

If unsure, say: "Let me connect you with a specialist who can help with that."
"""
```

Constitutional constraints prevent the most common failure modes before they happen.

## Advanced: Self-Consistency

For critical decisions, run the same prompt multiple times and take the majority vote:

```python
import anthropic
from collections import Counter

def self_consistent_classify(text: str, n: int = 5) -> str:
    client = anthropic.Anthropic()
    prompt = f"""
    Classify the sentiment of this review as exactly one of: 
    positive, negative, neutral, mixed.
    
    Review: "{text}"
    
    Answer with just the classification word.
    """

    results = []
    for _ in range(n):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}]
        )
        results.append(response.content[0].text.strip().lower())

    # Return majority vote
    return Counter(results).most_common(1)[0][0]

# Use a cheap model for multiple samples, expensive model only when inconsistent
classification = self_consistent_classify(review_text)
```

This works especially well for classification tasks where consistency matters.

## The Evaluation Framework

You can't improve what you don't measure. Here's how I evaluate prompts systematically:

```python
class PromptEvaluator:
    def __init__(self, eval_dataset: list[dict]):
        """
        eval_dataset: list of {"input": str, "expected": str, "category": str}
        """
        self.dataset = eval_dataset
        self.client = anthropic.Anthropic()

    def evaluate_prompt(self, prompt_template: str) -> dict:
        results = {"correct": 0, "total": len(self.dataset), "by_category": {}}

        for example in self.dataset:
            prompt = prompt_template.format(**example)
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            output = response.content[0].text

            # Your comparison logic here
            is_correct = self.compare(output, example["expected"])
            if is_correct:
                results["correct"] += 1

            cat = example["category"]
            if cat not in results["by_category"]:
                results["by_category"][cat] = {"correct": 0, "total": 0}
            results["by_category"][cat]["total"] += 1
            if is_correct:
                results["by_category"][cat]["correct"] += 1

        results["accuracy"] = results["correct"] / results["total"]
        return results
```

Run this before and after every prompt change. Track results in a spreadsheet. It feels tedious but it's the only way to make systematic progress.

## Common Prompt Engineering Mistakes

**1. Vague objectives**
> "Help me with this email"

The model will write *an* email. Maybe not the right email.

**2. Over-relying on system prompts**
System prompts are important but they have lower weight than user messages for many models. Put critical instructions in the user message too.

**3. Ignoring temperature**
`temperature=0` for deterministic tasks (extraction, classification).
`temperature=0.7-1.0` for creative tasks.
Most production systems should default to 0.

**4. Not testing edge cases**
Your prompt works on the examples you wrote it for. Test with:
- Empty inputs
- Very long inputs
- Inputs in different languages
- Adversarial inputs ("ignore previous instructions")

**5. Treating prompts as immutable**
Your first prompt is a draft. Maintain a version-controlled prompt library with evaluation scores.

## Putting It Together: A Production Prompt Pipeline

```python
class ProductionPrompt:
    def __init__(self, template: str, version: str, eval_score: float):
        self.template = template
        self.version = version
        self.eval_score = eval_score

    def render(self, **kwargs) -> str:
        return self.template.format(**kwargs)

    def run(self, model: str = "claude-sonnet-4-6", **kwargs) -> str:
        client = anthropic.Anthropic()
        rendered = self.render(**kwargs)

        response = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": rendered}]
        )
        return response.content[0].text

# Version-controlled prompt
contract_classifier = ProductionPrompt(
    template=CLASSIFIER_TEMPLATE,
    version="v2.3",
    eval_score=0.94,
)
```

## Conclusion

Prompt engineering isn't magic and it's not a temporary hack until AGI arrives. It's a genuine engineering discipline with principles, patterns, and best practices. The engineers who treat it as such — who measure, iterate, and document — consistently outperform those who rely on intuition.

Start with clear objectives. Use examples. Measure accuracy. Version control your prompts. Treat them as code, because in a very real sense, they are.

---

*If you found this useful, I write about practical GenAI engineering weekly. Connect on [LinkedIn](https://www.linkedin.com/in/shashi-shekhar-18octo/).*

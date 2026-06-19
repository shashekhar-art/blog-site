---
title: "DeepEval: The Production-Grade Framework for Evaluating LLM Applications"
date: "2026-03-08"
category: "LLMs"
tags: ["DeepEval", "LLMEvaluation", "RAG", "Testing", "Python", "ConfidentAI"]
summary: "DeepEval has become the de-facto standard for evaluating LLM applications in production. This deep dive covers every metric, from faithfulness to G-Eval, with real code and benchmarks."
cover_gradient: "gradient-3"
cover_emoji: "🧪"
author: "Shashi Shekhar"
---

## Why LLM Evaluation Is the Hardest Problem in GenAI

You've built a RAG pipeline. It demos beautifully. Your stakeholders are impressed. You ship it to production.

Three weeks later, a user reports that the system confidently told them the wrong refund window. Another says it ignored the question entirely and went off-script. Your VP of Product is in your inbox.

This isn't a model problem. It's an **evaluation problem**. You didn't have a systematic way to test your system before it reached users.

Enter [DeepEval](https://github.com/confident-ai/deepeval) — the open-source Python framework that makes LLM evaluation as rigorous as unit testing.

## What DeepEval Actually Does

DeepEval provides a suite of metrics specifically designed for LLM application components:

| Component | Metrics Available |
|-----------|------------------|
| RAG Retrieval | Context Precision, Context Recall, Context Relevancy |
| RAG Generation | Faithfulness, Answer Relevancy, Hallucination |
| Chatbots | Conversational G-Eval, Role Adherence |
| Agents | Task Completion, Tool Correctness |
| General | G-Eval (custom), Bias, Toxicity |

Each metric uses an LLM-as-judge approach — it uses a capable model (GPT-4o, Claude Sonnet) to evaluate the outputs of your application model.

## Setting Up DeepEval

```bash
pip install deepeval
deepeval login  # connects to Confident AI dashboard (optional)
```

```python
import deepeval
from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    HallucinationMetric,
)
from deepeval.test_case import LLMTestCase

# A single test case captures the full RAG interaction
test_case = LLMTestCase(
    input="What is Deloitte's refund policy for advisory services?",
    actual_output="Deloitte offers a 30-day satisfaction guarantee on advisory engagements.",
    expected_output="Deloitte's advisory refund policy varies by engagement type and is detailed in the MSA.",
    retrieval_context=[
        "Section 4.2: Refund eligibility depends on engagement type...",
        "For fixed-fee projects, refunds are subject to approval...",
    ],
)
```

## The Core RAG Metrics Explained

### 1. Faithfulness — Is the answer grounded in context?

This is the most critical metric for RAG. It asks: **did the model make up anything that isn't in the retrieved context?**

```python
faithfulness_metric = FaithfulnessMetric(
    threshold=0.8,
    model="gpt-4o",
    include_reason=True,
)

faithfulness_metric.measure(test_case)
print(f"Score: {faithfulness_metric.score}")
print(f"Reason: {faithfulness_metric.reason}")
# Score: 0.67
# Reason: The claim "30-day satisfaction guarantee" is not supported
# by the retrieved context, which discusses variable refund policies.
```

### 2. Answer Relevancy — Does the answer actually address the question?

```python
from deepeval.metrics import AnswerRelevancyMetric

relevancy = AnswerRelevancyMetric(threshold=0.7, model="claude-sonnet-4-6")
relevancy.measure(test_case)
print(f"Relevancy: {relevancy.score}")  # 0.85 — broadly relevant
```

### 3. Contextual Precision — Were the RIGHT documents retrieved first?

Contextual Precision measures whether relevant chunks appear at the top of your retrieved context. A low score means your retriever is burying the good stuff.

```python
from deepeval.metrics import ContextualPrecisionMetric

precision = ContextualPrecisionMetric(threshold=0.75)
precision.measure(test_case)
```

### 4. Contextual Recall — Did retrieval find ALL the relevant information?

```python
from deepeval.metrics import ContextualRecallMetric

recall = ContextualRecallMetric(threshold=0.7)
recall.measure(test_case)
# Low score = your vector store is missing relevant chunks
```

## G-Eval: Building Custom Metrics

The most powerful feature of DeepEval. Define ANY evaluation criterion in natural language:

```python
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

# Custom metric: Is the tone professional and enterprise-appropriate?
professional_tone = GEval(
    name="ProfessionalTone",
    criteria="""
    Evaluate whether the response uses appropriate professional language
    for an enterprise business context. The response should:
    - Avoid slang, casual language, or overly informal phrasing
    - Use industry-standard terminology correctly
    - Maintain a helpful but authoritative tone
    - Not be unnecessarily verbose or jargon-heavy
    """,
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.7,
)

# Custom metric: Does the response include actionable next steps?
actionability = GEval(
    name="Actionability",
    criteria="""
    Determine whether the response gives the user a clear next step or
    actionable guidance. Responses that end with vague suggestions like
    "consult an expert" without specifics score low.
    """,
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
    ],
    threshold=0.6,
)
```

## Writing a Full Evaluation Suite with pytest

DeepEval integrates natively with pytest:

```python
# test_rag_pipeline.py
import pytest
from deepeval import assert_test
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    HallucinationMetric,
)
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset

# Load your RAG pipeline
from my_app.rag import rag_pipeline, retrieve_context


def generate_test_case(question: str, expected: str) -> LLMTestCase:
    context = retrieve_context(question)
    answer = rag_pipeline(question, context)
    return LLMTestCase(
        input=question,
        actual_output=answer,
        expected_output=expected,
        retrieval_context=context,
    )


# Define test cases
TEST_CASES = [
    ("What is our data retention policy?", "Data is retained for 7 years per SOX requirements."),
    ("How do I escalate a P1 incident?", "P1 incidents must be escalated to the on-call manager within 15 minutes."),
    ("What are the approved cloud providers?", "Azure and AWS are approved. GCP requires security review."),
]


@pytest.mark.parametrize("question,expected", TEST_CASES)
def test_rag_faithfulness(question, expected):
    test_case = generate_test_case(question, expected)
    assert_test(test_case, [
        FaithfulnessMetric(threshold=0.8),
    ])


@pytest.mark.parametrize("question,expected", TEST_CASES)
def test_rag_answer_quality(question, expected):
    test_case = generate_test_case(question, expected)
    assert_test(test_case, [
        AnswerRelevancyMetric(threshold=0.75),
        HallucinationMetric(threshold=0.2),  # Lower is better for hallucination
    ])
```

Run it:
```bash
deepeval test run test_rag_pipeline.py
# or with verbose output:
deepeval test run test_rag_pipeline.py -v
```

## Benchmarking Your RAG Pipeline Before and After Changes

The real power comes when you use DeepEval to measure the impact of every change:

```python
from deepeval import evaluate
from deepeval.dataset import EvaluationDataset

dataset = EvaluationDataset()
dataset.add_test_cases_from_csv(
    file_path="eval_dataset.csv",
    input_col_name="question",
    actual_output_col_name="answer",
    expected_output_col_name="ground_truth",
    retrieval_context_col_name="context",
)

results = evaluate(
    test_cases=dataset.test_cases,
    metrics=[
        FaithfulnessMetric(threshold=0.8),
        AnswerRelevancyMetric(threshold=0.75),
        ContextualPrecisionMetric(threshold=0.7),
        ContextualRecallMetric(threshold=0.7),
    ],
)

# Log to Confident AI dashboard for tracking over time
print(f"Overall pass rate: {results.confident_link}")
```

## My Recommended Evaluation Workflow

After running DeepEval on 15+ production RAG systems at clients, here's the workflow that works:

**Phase 1: Baseline (before any optimization)**
- Run 50–100 diverse questions against your pipeline
- Record Faithfulness, Relevancy, Precision, Recall
- This is your benchmark

**Phase 2: Identify the bottleneck**
- Low Contextual Recall → fix chunking/indexing strategy
- Low Contextual Precision → fix retriever ranking/re-ranking
- Low Faithfulness → fix your system prompt or add citations
- Low Answer Relevancy → fix query understanding

**Phase 3: Iterate and measure**
- Make one change at a time
- Re-run the full eval suite
- Only ship if scores improve or stay flat

**Phase 4: Regression testing in CI**
- Add `deepeval test run` to your CI/CD pipeline
- Set minimum thresholds that block merges if violated
- Maintain a curated "golden set" of 20–30 high-value test cases

## The Bottom Line

In 2026, shipping an LLM application without DeepEval is like shipping software without unit tests. The framework has matured significantly, the metrics are well-calibrated, and the pytest integration makes it a natural fit for existing engineering workflows.

If you're building RAG systems, agents, or any LLM-powered feature — start your evaluation framework on day one, not after your first production incident.

---

*Have questions about setting up DeepEval for your stack? Connect with me on [LinkedIn](https://www.linkedin.com/in/shashi-shekhar-18octo/) — I run these evaluations regularly for enterprise AI projects.*

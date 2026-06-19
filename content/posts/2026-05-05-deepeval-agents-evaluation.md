---
title: "Evaluating AI Agents with DeepEval: Beyond RAG Metrics"
date: "2026-05-05"
category: "Agents"
tags: ["DeepEval", "AIAgents", "AgentEvaluation", "LangGraph", "Testing", "2026"]
summary: "Evaluating RAG pipelines is solved. Evaluating AI agents is the new frontier. DeepEval's agent metrics — task completion, tool correctness, trajectory reasoning — are now the gold standard."
cover_gradient: "gradient-1"
cover_emoji: "🕵️"
author: "Shashi Shekhar"
---

## The Evaluation Gap in Agentic AI

By now, most teams have figured out how to evaluate their RAG pipelines. Faithfulness, contextual precision, answer relevancy — these metrics are well-understood, tooling is mature, and CI integration is standard practice.

But agents? That's a different story.

The challenge is fundamental: **agents don't have a single input-output pair to evaluate.** They have a *trajectory* — a sequence of thoughts, tool calls, observations, and decisions — that eventually produces an outcome. Evaluating the outcome alone misses most of what can go wrong.

DeepEval's agent evaluation suite, significantly expanded in early 2026, addresses this directly. Let me walk through how to use it.

## What Makes Agent Evaluation Different

For a RAG system:
```
Input → Retrieve → Generate → Output
         ↑ eval     ↑ eval     ↑ eval
```

For an agent:
```
Input → Think → Tool Call → Observe → Think → Tool Call → ... → Output
        ↑eval    ↑eval       ↑eval     ↑eval   ↑eval      ...   ↑eval
```

Each step in the trajectory can fail in different ways:
- **Planning failure**: The agent chose the wrong next action
- **Tool selection failure**: Called the wrong tool or wrong parameters
- **Observation failure**: Misinterpreted the tool output
- **Loop failure**: Got stuck repeating the same action
- **Premature termination**: Stopped before completing the task
- **Hallucinated tool calls**: Made up tool outputs it never received

DeepEval now has metrics for all of these.

## Setting Up Agent Tracing with DeepEval

```python
from deepeval.integrations.langchain import observe
from deepeval.test_case import ConversationalTestCase, LLMTestCase
from deepeval.metrics import (
    TaskCompletionMetric,
    ToolCorrectnessMetric,
    AgentTrajectoryMetric,
)
import deepeval

# Instrument your agent with the @observe decorator
@observe(type="agent")
def run_research_agent(task: str) -> dict:
    """A LangGraph agent that researches a topic and produces a report."""
    from my_app.agents import ResearchAgent
    
    agent = ResearchAgent()
    result = agent.run(task)
    
    return {
        "output": result["final_report"],
        "tool_calls": result["tool_call_history"],
        "steps": result["steps_taken"],
    }
```

## Task Completion Metric

The most fundamental agent metric: **did the agent actually complete the assigned task?**

```python
from deepeval.metrics import TaskCompletionMetric
from deepeval.test_case import LLMTestCase

# Test: Can the agent find and summarize recent AI papers?
test_case = LLMTestCase(
    input="Find the 3 most cited AI papers from Q1 2026 and summarize their key findings.",
    actual_output=agent_result["output"],
    # Include the full trajectory for analysis
    tools_called=agent_result["tool_calls"],
)

task_completion = TaskCompletionMetric(
    threshold=0.7,
    model="claude-sonnet-4-6",
    verbose_mode=True,
)

task_completion.measure(test_case)
print(f"Task Completion Score: {task_completion.score}")
print(f"Reason: {task_completion.reason}")
# Score: 0.85
# Reason: Agent successfully identified and summarized 3 papers with correct
# citation counts. Minor deduction: summary of paper 2 lacked quantitative results.
```

## Tool Correctness Metric

Did the agent call the right tools in the right order with the right inputs?

```python
from deepeval.metrics import ToolCorrectnessMetric

# Define what the optimal tool usage should look like
optimal_tools = [
    {"tool_name": "search_arxiv", "tool_input": {"query": "AI papers 2026 Q1", "sort_by": "citations"}},
    {"tool_name": "fetch_paper_details", "tool_input": {"paper_id": "..."}},
    {"tool_name": "summarize_document", "tool_input": {"text": "..."}},
]

actual_tools = agent_result["tool_calls"]  # What the agent actually called

tool_correctness = ToolCorrectnessMetric(
    threshold=0.75,
    # Exact match vs semantic match for tool names
    evaluation_mode="exact",
)

test_case = LLMTestCase(
    input="Find the 3 most cited AI papers from Q1 2026 and summarize them.",
    actual_output=agent_result["output"],
    tools_called=actual_tools,
    expected_tools=optimal_tools,
)

tool_correctness.measure(test_case)
print(f"Tool Correctness: {tool_correctness.score}")
```

## Agent Trajectory Metric (The Powerful One)

This is where DeepEval's 2026 agent evaluation really shines. The trajectory metric evaluates the **entire reasoning chain**, not just the final output.

```python
from deepeval.metrics import AgentTrajectoryMetric

# Define the expected trajectory (high-level steps)
expected_trajectory = [
    "Search for recent AI papers with citation data",
    "Filter and rank by citation count",
    "Retrieve full details for top 3 papers",
    "Summarize each paper's key findings",
    "Compile final report",
]

trajectory_metric = AgentTrajectoryMetric(
    threshold=0.7,
    model="gpt-4o",
    # Options: "strict" (must match expected) or "lenient" (any valid path)
    evaluation_mode="lenient",
)

# The test case includes the full step-by-step trace
test_case = LLMTestCase(
    input="Find the 3 most cited AI papers from Q1 2026 and summarize them.",
    actual_output=agent_result["output"],
    tools_called=agent_result["tool_calls"],
    # Include intermediate reasoning steps
    trajectory=[
        {"thought": "I need to search for recent papers", "action": "search_arxiv", "observation": "Found 847 papers"},
        {"thought": "Need to sort by citations", "action": "sort_results", "observation": "Top paper: 1243 citations"},
        # ... full trajectory
    ],
    expected_trajectory=expected_trajectory,
)

trajectory_metric.measure(test_case)
```

## A Complete Agent Test Suite

Here's the full pytest-based agent evaluation setup I use for production agent systems:

```python
# tests/test_agents.py
import pytest
from deepeval import assert_test
from deepeval.metrics import (
    TaskCompletionMetric,
    ToolCorrectnessMetric,
    AgentTrajectoryMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase
from my_app.agents import ResearchAgent, DataAnalysisAgent


# =====================
# Research Agent Tests
# =====================
RESEARCH_TASKS = [
    {
        "input": "Find the latest developments in multimodal LLMs from March 2026",
        "tools_expected": ["search_arxiv", "fetch_paper", "summarize"],
        "min_task_score": 0.75,
    },
    {
        "input": "What are the key differences between DeepSeek v3 and Claude Sonnet 4.6?",
        "tools_expected": ["search_web", "compare_models"],
        "min_task_score": 0.70,
    },
]


@pytest.mark.parametrize("task", RESEARCH_TASKS)
def test_research_agent_completion(task):
    agent = ResearchAgent()
    result = agent.run(task["input"])

    test_case = LLMTestCase(
        input=task["input"],
        actual_output=result["output"],
        tools_called=result["tool_calls"],
    )

    assert_test(test_case, [
        TaskCompletionMetric(threshold=task["min_task_score"]),
        ToolCorrectnessMetric(threshold=0.7),
    ])


# =====================
# Data Analysis Agent
# =====================
def test_data_agent_no_hallucination():
    """Agent must not invent statistics not present in source data."""
    agent = DataAnalysisAgent()
    result = agent.analyze(
        data_path="tests/fixtures/q1_sales.csv",
        query="What was the revenue trend in Q1 2026?",
    )

    test_case = LLMTestCase(
        input="What was the revenue trend in Q1 2026?",
        actual_output=result["analysis"],
        retrieval_context=result["data_excerpts"],
    )

    # Agents analyzing data must be faithful to the source data
    assert_test(test_case, [
        FaithfulnessMetric(threshold=0.9),  # Higher threshold for data analysis
        TaskCompletionMetric(threshold=0.8),
    ])
```

Run with:
```bash
deepeval test run tests/test_agents.py --verbose
```

## Detecting Agent Failure Patterns

Beyond pass/fail, DeepEval helps you identify *why* agents fail. Here are the patterns I see most often:

**Pattern 1: Tool Parameter Hallucination**
The agent calls the right tool but with made-up parameters.
```
Expected: search_database(query="refund policy", table="policies")
Actual:   search_database(query="refund policy", table="customer_records")  ← wrong table
```
Detection: Tool Correctness metric with strict parameter matching.

**Pattern 2: Premature Termination**
The agent stops before completing all sub-tasks.
```
Task: "Analyze sales data AND generate a forecast"
Agent: Analyzes sales data, then stops.  ← misses the forecast
```
Detection: Task Completion metric catches this reliably.

**Pattern 3: Reasoning Loop**
The agent keeps calling the same tool repeatedly without making progress.
```
Step 3: search_web("LLM benchmarks 2026")  ← same call as step 1
Step 4: search_web("LLM benchmarks 2026")  ← still same call
```
Detection: Trajectory metric with loop detection enabled.

## Looking Ahead

The agent evaluation space is moving fast. In the coming months, DeepEval is adding:
- **Multi-agent system evaluation** (coordinating between agents)
- **Long-horizon task evaluation** (tasks spanning multiple sessions)
- **Safety evaluation for agentic actions** (detecting unauthorized operations)

For now, the combination of Task Completion + Tool Correctness + Trajectory covers 90% of what you need to confidently deploy agents.

The teams building robust agent evaluation today will be the ones who can deploy agents reliably in 2026 and beyond.

---

*Building agentic systems in production? I'd love to compare notes. Connect on [LinkedIn](https://www.linkedin.com/in/shashi-shekhar-18octo/).*

---
title: "AI Agents: Building Autonomous Systems That Actually Work"
date: "2025-02-28"
category: "Agents"
tags: ["AIAgents", "LangGraph", "ToolUse", "Automation", "MultiAgent"]
summary: "AI agents are the next frontier — systems that reason, plan, and take actions autonomously. Here's a practical guide to building agents that are reliable enough to deploy."
cover_gradient: "gradient-1"
cover_emoji: "🤖"
author: "Shashi Shekhar"
---

## What Is an AI Agent, Really?

The term "AI agent" gets applied to everything from a simple chatbot to fully autonomous software systems. Let me give you a precise definition.

An AI agent is a system that:
1. **Perceives** its environment (reads inputs, checks state)
2. **Reasons** about what to do (uses an LLM to plan and decide)
3. **Acts** (executes tools, writes code, calls APIs, sends messages)
4. **Observes** the result (reads outputs, updates state)
5. **Repeats** until the goal is achieved

The key difference from a regular chatbot: agents can take **multiple steps** autonomously, **use tools** to interact with the world, and **loop** until a task is complete.

## The ReAct Pattern: The Foundation of Agents

The most proven agentic architecture is **ReAct** (Reasoning + Acting):

```
Thought: I need to find today's NVDA stock price
Action: search_web("NVDA stock price today")
Observation: NVDA is trading at $875.43 as of 2:30 PM EST

Thought: I have the current price. Now I need yesterday's close.
Action: get_historical_price("NVDA", "2025-02-27")
Observation: NVDA closed at $862.10 on Feb 27

Thought: I have both prices. I can calculate the change.
Action: calculate(875.43 - 862.10) / 862.10 * 100
Observation: 1.55% increase

Thought: I have everything I need for the answer.
Final Answer: NVDA is up 1.55% today, currently trading at $875.43.
```

This explicit reasoning trace is powerful because:
- The LLM shows its work (interpretable)
- Each step is verifiable
- Errors surface early in the loop
- You can add validation at each observation

## Building Your First Agent with Claude

```python
import anthropic
import json

client = anthropic.Anthropic()

# Define tools the agent can use
tools = [
    {
        "name": "search_web",
        "description": "Search the web for current information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "execute_python",
        "description": "Execute Python code and return the result",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "read_file",
        "description": "Read a file and return its contents",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"}
            },
            "required": ["path"]
        }
    }
]

def run_tool(name: str, inputs: dict) -> str:
    """Execute a tool and return the result."""
    if name == "search_web":
        # Implement actual web search
        return f"[Search results for: {inputs['query']}]"
    elif name == "execute_python":
        # WARNING: Sandbox this in production!
        try:
            exec_globals = {}
            exec(inputs["code"], exec_globals)
            return str(exec_globals.get("result", "Code executed successfully"))
        except Exception as e:
            return f"Error: {str(e)}"
    elif name == "read_file":
        try:
            with open(inputs["path"]) as f:
                return f.read()
        except Exception as e:
            return f"Error: {str(e)}"
    return "Unknown tool"


def run_agent(task: str, max_steps: int = 10) -> str:
    messages = [{"role": "user", "content": task}]
    
    for step in range(max_steps):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )
        
        # If no tool call, we have the final answer
        if response.stop_reason == "end_turn":
            return response.content[0].text
        
        # Process tool calls
        assistant_message = {"role": "assistant", "content": response.content}
        messages.append(assistant_message)
        
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        
        messages.append({"role": "user", "content": tool_results})
    
    return "Max steps reached without completion."

# Use it
result = run_agent("Analyze the sales data in data/q4_sales.csv and tell me the top 3 products")
```

## Multi-Agent Systems: Orchestrator + Specialists

Single agents have limits. For complex tasks, a **multi-agent architecture** with specialized agents works better:

```
                    ┌─────────────────────┐
                    │  Orchestrator Agent  │
                    │  (Plans & delegates) │
                    └────────┬────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  Research    │ │  Code Writer │ │   Reviewer   │
    │    Agent     │ │    Agent     │ │    Agent     │
    └──────────────┘ └──────────────┘ └──────────────┘
```

```python
import anthropic

client = anthropic.Anthropic()

class ResearchAgent:
    """Specializes in finding and synthesizing information."""

    def run(self, query: str) -> str:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="You are a research specialist. Find relevant information, cite sources, and provide a concise summary.",
            messages=[{"role": "user", "content": f"Research: {query}"}]
        )
        return response.content[0].text


class CodeAgent:
    """Specializes in writing and reviewing code."""

    def run(self, specification: str) -> str:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="You are an expert Python developer. Write clean, tested, production-ready code.",
            messages=[{"role": "user", "content": specification}]
        )
        return response.content[0].text


class OrchestratorAgent:
    """Breaks down tasks and coordinates specialist agents."""

    def __init__(self):
        self.research = ResearchAgent()
        self.coder = CodeAgent()

    def run(self, task: str) -> str:
        # Step 1: Plan
        plan_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system="You orchestrate specialist AI agents. Break down tasks into steps: RESEARCH, CODE, REVIEW.",
            messages=[{"role": "user", "content": f"Plan this task: {task}"}]
        )
        plan = plan_response.content[0].text

        # Step 2: Execute based on plan
        results = {}
        if "RESEARCH" in plan.upper():
            results["research"] = self.research.run(task)
        if "CODE" in plan.upper():
            spec = f"Based on this research: {results.get('research', '')}\nImplement: {task}"
            results["code"] = self.coder.run(spec)

        # Step 3: Synthesize
        synthesis_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"Synthesize these results for task '{task}':\n{json.dumps(results, indent=2)}"
            }]
        )
        return synthesis_response.content[0].text


orchestrator = OrchestratorAgent()
result = orchestrator.run("Build a Python script to monitor our API endpoint and alert on high latency")
```

## The Hardest Part: Reliability

Agents fail in ways chatbots don't. Here are the failure modes I've encountered:

### Tool Errors and Recovery

```python
def run_tool_with_retry(name: str, inputs: dict, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            result = run_tool(name, inputs)
            if "Error" not in result:
                return result
            # Tool returned an error — tell the agent and let it adapt
            return f"Tool returned error (attempt {attempt+1}): {result}"
        except Exception as e:
            if attempt == max_retries - 1:
                return f"Tool failed after {max_retries} attempts: {str(e)}"
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Preventing Infinite Loops

```python
class AgentGuardrails:
    def __init__(self, max_steps=15, max_tokens_total=100000, forbidden_actions=None):
        self.max_steps = max_steps
        self.max_tokens_total = max_tokens_total
        self.forbidden_actions = forbidden_actions or []
        self.tokens_used = 0
        self.steps_taken = 0

    def check(self, tool_name: str = None, tokens_used: int = 0) -> tuple[bool, str]:
        self.steps_taken += 1
        self.tokens_used += tokens_used

        if self.steps_taken > self.max_steps:
            return False, f"Exceeded max steps ({self.max_steps})"
        if self.tokens_used > self.max_tokens_total:
            return False, f"Exceeded token budget ({self.max_tokens_total})"
        if tool_name in self.forbidden_actions:
            return False, f"Action '{tool_name}' is not permitted"
        return True, "ok"
```

### Human-in-the-Loop for High-Stakes Actions

Not everything should be fully autonomous. Build in confirmation for irreversible actions:

```python
HIGH_RISK_TOOLS = {"delete_file", "send_email", "execute_sql", "deploy_to_prod"}

def execute_with_approval(tool_name: str, inputs: dict) -> str:
    if tool_name in HIGH_RISK_TOOLS:
        print(f"\n⚠️  HIGH RISK ACTION REQUESTED")
        print(f"Tool: {tool_name}")
        print(f"Inputs: {json.dumps(inputs, indent=2)}")
        approval = input("Approve? (yes/no): ").strip().lower()
        if approval != "yes":
            return "Action cancelled by user."
    return run_tool(tool_name, inputs)
```

## When to Use Agents vs. Simple LLM Calls

Not every task needs an agent. Use this decision framework:

| Use Case | Simple Call | Agent |
|----------|-------------|-------|
| Summarize a document | ✅ | Overkill |
| Answer a question from a knowledge base | ✅ RAG | Overkill |
| Multi-step research + report | ❌ | ✅ |
| Code review | ✅ | Overkill |
| Automated software debugging | ❌ | ✅ |
| Customer FAQ bot | ✅ | Overkill |
| CI/CD pipeline management | ❌ | ✅ |

The rule of thumb: if the task requires **more than 3-4 steps**, **multiple external tools**, or **dynamic planning based on intermediate results** — use an agent.

## What's Coming: Agentic Futures

The current generation of agents is impressive but brittle. The next wave will feature:

- **Persistent memory**: Agents that remember past interactions and learn from them
- **Better planning**: Tree-of-thought and Monte Carlo planning for complex tasks
- **Multi-modal actions**: Agents that can see screens, click buttons, and interact with GUIs
- **Improved reliability**: Better error handling, verification, and uncertainty quantification

We're at the beginning of the agent era. The teams building the foundational infrastructure and tooling today will define what's possible tomorrow.

---

*Exploring AI agents in your organization? I'd love to hear about your use cases — connect on [LinkedIn](https://www.linkedin.com/in/shashi-shekhar-18octo/).*

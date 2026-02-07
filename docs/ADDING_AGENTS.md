# Adding New Agents to Holus

## Quick Guide

### 1. Create the agent directory

```
agents/my_agent/
├── __init__.py
├── agent.py      # Main agent class
├── tools.py      # Optional: complex tools in separate file
└── prompts.py    # Optional: prompts in separate file
```

### 2. Implement the agent class

```python
# agents/my_agent/agent.py
from core.base_agent import BaseAgent
from langchain_core.tools import tool

class MyAgent(BaseAgent):
    name = "my_agent"                           # Must be unique
    description = "What this agent does"
    schedule = "every 2 hours"                  # Default schedule
    
    def get_tools(self) -> list:
        @tool
        def my_tool(input: str) -> str:
            """Description of what this tool does."""
            # Your implementation
            return "result"
        
        return [my_tool]
    
    def get_system_prompt(self) -> str:
        return """You are the [role] agent for Holus.
        
        Your mission: [what you do]
        
        WORKFLOW:
        1. Step one
        2. Step two
        
        RULES:
        - Rule one
        - Rule two
        """
    
    async def run(self) -> dict:
        result = await self.execute("Do your main task")
        await self.notify(f"Done: {result[:200]}")
        return {"status": "completed", "result": result}
```

### 3. Register in the orchestrator

Add your import to `core/orchestrator.py` in the `discover_agents` method:

```python
from agents.my_agent.agent import MyAgent
agent_classes = [
    # ... existing agents ...
    MyAgent,
]
```

### 4. Add config

In `config/config.yaml`:

```yaml
agents:
  my_agent:
    enabled: true
    schedule: "every 2 hours"
    llm_provider: "ollama"  # or "anthropic" for complex tasks
    # your custom config keys...
```

### 5. Test

```bash
python -m holus.main --agent my_agent
```

## Agent Capabilities

Every agent inherits these from `BaseAgent`:

| Method | What It Does |
|--------|-------------|
| `self.execute(task)` | Run an LLM agent with your tools |
| `self.notify(msg)` | Send Telegram notification |
| `self.request_approval(action, details)` | Ask user for approval |
| `self.remember(content)` | Store in agent's memory |
| `self.recall(query)` | Search agent's memory |
| `self.get_llm(complexity)` | Get LLM (routes simple→local, complex→cloud) |

## Tips

- Keep tools focused — one tool per action
- Use `@tool` decorator with good docstrings (the LLM reads them)
- Store important state in memory via `self.remember()`
- Check memory at start of `run()` to avoid duplicates
- Use `shared=True` in memory to share data between agents
- Always send summaries via `self.notify()`

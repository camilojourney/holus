# 🔮 HOLUS — Personal AI Agent Workforce

> *"Like Ultron, but it works for you."*
> Inspired by [AI Jason's Agent Workforce](https://www.ai-jason.com/learning-ai/ai-agent-tutorial-2) concept — a system of specialized AI agents running 24/7 on your local machine, each handling a different domain of your life.

## What Is Holus?

Holus is a **local-first AI agent orchestrator** that runs on your Mac Mini M4 (or any always-on machine). Instead of one monolithic AI, you deploy a **team of specialized agents** — each with its own tools, memory, and scheduled tasks — coordinated by a central hub.

Think of it as your personal AI company where each agent is an "employee" with a specific role.

```
┌─────────────────────────────────────────────────┐
│                  HOLUS HUB                       │
│            (Orchestrator + Router)               │
├──────────┬──────────┬──────────┬────────────────┤
│ 🎯       │ 📈       │ 📱       │ 🔬             │
│ Job      │ Trading  │ Social   │ Research       │
│ Hunter   │ Monitor  │ Media    │ Scout          │
├──────────┼──────────┼──────────┼────────────────┤
│ 📧       │ 📋       │ 🧠       │ 📊             │
│ Inbox    │ Task     │ Memory   │ Dashboard      │
│ Manager  │ Scheduler│ Store    │ (Web UI)       │
└──────────┴──────────┴──────────┴────────────────┘
         ▼              ▼              ▼
   [Telegram/SMS]  [Local LLM]   [API Services]
   Notifications   Ollama/Cloud   Gmail, GitHub...
```

## Architecture

Holus follows the same philosophy as AI Jason's system but adapted for a solo founder/job seeker:

| Layer | What It Does | Tech |
|-------|-------------|------|
| **Orchestrator** | Routes tasks to the right agent, manages scheduling | Python + APScheduler |
| **Agents** | Specialized workers with their own tools and prompts | LangChain / LangGraph agents |
| **Tools** | Shared capabilities (browser, email, search, etc.) | Playwright, Gmail API, etc. |
| **Memory** | Per-agent + shared memory store | ChromaDB (local vector DB) |
| **Notifications** | Sends you updates via Telegram/SMS | Telegram Bot API |
| **Dashboard** | Web UI to monitor agents, view logs, approve actions | FastAPI + HTMX |

## The Agent Team

### 🎯 Job Hunter Agent
Automates your job search pipeline:
- Scrapes job boards (LinkedIn, Wellfound, Lever, Greenhouse)
- Matches roles against your resume + preferences ($150k-180k, AI/data roles, NYC)
- Auto-fills applications where possible
- Generates tailored cover letters
- Reports daily: "Found 12 matches, applied to 5, 3 need your review"
- **Schedule:** Every 6 hours

### 📈 Trading Monitor Agent
Watches markets and executes your strategy:
- Monitors crypto perpetual futures positions
- Tracks key indicators and signals
- Sends alerts on significant moves
- Generates daily P&L summaries
- Can execute trades via API (with confirmation gate)
- **Schedule:** Every 15 minutes (market hours) / hourly (off-hours)

### 📱 Social Media Agent
Manages your online presence:
- Drafts tweets/posts based on your interests (AI, startups, data science)
- Monitors mentions and DMs across platforms
- Engages with relevant content in your niche
- Curates content for scheduled posting
- **Schedule:** 3x daily posting, continuous monitoring

### 🔬 Research Scout Agent
Your personal research assistant:
- Monitors GitHub trending for AI/ML projects
- Tracks arxiv papers in your domains
- Summarizes newsletters and RSS feeds
- Generates weekly digest reports
- **Schedule:** Daily digest, continuous monitoring

### 📧 Inbox Manager Agent
Handles email triage (AI Jason's original use case):
- Categorizes incoming emails (opportunity / spam / action needed / FYI)
- Drafts responses for routine emails
- Escalates important ones to you via Telegram
- Researches senders/prospects automatically
- **Schedule:** Every 30 minutes

## Quick Start

### Prerequisites
- Python 3.11+
- Mac Mini M4 (or any always-on machine)
- Ollama installed (`brew install ollama`)
- API keys for services you want to use

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/holus.git
cd holus

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit config
cp config/config.example.yaml config/config.yaml
nano config/config.yaml  # Add your API keys and preferences

# Pull a local model (optional, can use cloud APIs)
ollama pull qwen2.5:7b

# Run the setup wizard
python scripts/setup.py

# Start Holus
python -m holus.main
```

### Configuration

Edit `config/config.yaml` to:
1. Set your LLM provider (Ollama local, OpenAI, Anthropic)
2. Add API keys for services (Gmail, Telegram, etc.)
3. Configure each agent's schedule and preferences
4. Set notification preferences

## Project Structure

```
holus/
├── README.md
├── requirements.txt
├── pyproject.toml
├── config/
│   ├── config.example.yaml    # Template config
│   └── config.yaml            # Your config (gitignored)
├── core/
│   ├── __init__.py
│   ├── orchestrator.py        # Central hub that routes and schedules
│   ├── base_agent.py          # Base class all agents inherit from
│   ├── memory.py              # ChromaDB memory management
│   ├── notifier.py            # Telegram/SMS notification system
│   └── llm.py                 # LLM provider abstraction
├── agents/
│   ├── __init__.py
│   ├── job_hunter/
│   │   ├── __init__.py
│   │   ├── agent.py           # Job Hunter agent logic
│   │   ├── tools.py           # Job-specific tools
│   │   └── prompts.py         # System prompts
│   ├── trading_monitor/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── prompts.py
│   ├── social_media/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── prompts.py
│   ├── research_scout/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── prompts.py
│   └── inbox_manager/
│       ├── __init__.py
│       ├── agent.py
│       ├── tools.py
│       └── prompts.py
├── tools/
│   ├── __init__.py
│   ├── browser.py             # Playwright browser automation
│   ├── email_client.py        # Gmail API integration
│   ├── search.py              # Web search (SerpAPI/DuckDuckGo)
│   ├── github_monitor.py      # GitHub trending scraper
│   └── telegram_bot.py        # Telegram bot for notifications + commands
├── dashboard/
│   ├── app.py                 # FastAPI web dashboard
│   ├── templates/
│   └── static/
├── scripts/
│   ├── setup.py               # Interactive setup wizard
│   ├── start.sh               # Startup script for launchd
│   └── healthcheck.py         # Monitor agent health
├── tests/
│   └── ...
└── docs/
    ├── ARCHITECTURE.md
    ├── ADDING_AGENTS.md
    └── DEPLOYMENT.md
```

## Key Design Decisions

### Why Not Just Use OpenClaw?
OpenClaw is great for simple chat-to-action flows, but Holus gives you:
- **Specialized agents** with domain-specific tools and prompts
- **Scheduled autonomous execution** (not just reactive)
- **Persistent memory** per agent (ChromaDB)
- **Human-in-the-loop gates** for high-stakes actions (trades, job apps)
- **A dashboard** to monitor everything

### Why Local-First?
- **Cost:** After setup, local inference is free (Ollama)
- **Privacy:** Your job search, trading data, emails never leave your machine
- **Control:** You own the whole stack
- **Uptime:** No API rate limits or outages for core logic

### Hybrid LLM Strategy
- **Local (Ollama qwen2.5:7b):** Routine tasks, categorization, scheduling
- **Cloud (Claude/GPT-4):** Complex reasoning, cover letter writing, research synthesis
- You control cost by routing simple tasks locally and only calling cloud for heavy lifting

## Adding a New Agent

See [docs/ADDING_AGENTS.md](docs/ADDING_AGENTS.md) for the full guide. TL;DR:

```python
from core.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    name = "my_agent"
    schedule = "every 2 hours"
    
    def get_tools(self):
        return [my_tool_1, my_tool_2]
    
    def get_system_prompt(self):
        return "You are an agent that..."
    
    async def run(self):
        # Your agent logic here
        result = await self.execute("Do the thing")
        await self.notify(f"Done: {result}")
```

Register it in `config/config.yaml` and it auto-starts with the orchestrator.

## Roadmap

- [x] Core orchestrator + scheduling
- [x] Base agent framework
- [x] Memory store (ChromaDB)
- [x] Telegram notifications
- [ ] Job Hunter Agent (MVP)
- [ ] Inbox Manager Agent
- [ ] Trading Monitor Agent
- [ ] Social Media Agent
- [ ] Research Scout Agent
- [ ] Web Dashboard
- [ ] Voice interface (Whisper + TTS)
- [ ] MCP server integration for Claude Code compatibility

## Credits

- **AI Jason (Jason Zhou)** — Original "Agent Workforce" concept and architecture patterns
- **LangChain / LangGraph** — Agent framework
- **Ollama** — Local LLM inference
- **ChromaDB** — Vector memory store

## License

MIT

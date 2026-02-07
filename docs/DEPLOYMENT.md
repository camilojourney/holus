# Deploying Holus on Mac Mini M4

## Overview

Holus is designed to run 24/7 on your Mac Mini M4, acting as your personal AI workforce. This guide covers the complete deployment from scratch.

## Prerequisites

- Mac Mini M4 (16GB RAM, 256GB+)
- SSH access configured (see your existing setup via Tailscale)
- Homebrew installed

## Installation

### 1. SSH into your Mac Mini

```bash
ssh your-username@your-mac-mini-ip
# or via Tailscale
ssh your-username@100.x.x.x
```

### 2. Install dependencies

```bash
# Python 3.11+
brew install python@3.11

# Ollama for local LLMs
brew install ollama
ollama serve &
ollama pull qwen2.5:7b

# Playwright for browser automation
pip install playwright --break-system-packages
playwright install chromium
```

### 3. Clone and setup Holus

```bash
cd ~
git clone https://github.com/yourusername/holus.git
cd holus

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure

```bash
cp config/config.example.yaml config/config.yaml
nano config/config.yaml
# Fill in your API keys, Telegram bot token, etc.
```

### 5. Test

```bash
# Test a single agent
python -m holus.main --agent research_scout

# Check status
python -m holus.main --status
```

## Running as a Background Service (launchd)

Create a launchd plist to auto-start Holus on boot:

```bash
cat > ~/Library/LaunchAgents/com.holus.agent.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.holus.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/holus/.venv/bin/python</string>
        <string>-m</string>
        <string>holus.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/holus</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/.holus/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/.holus/logs/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

# Load it
launchctl load ~/Library/LaunchAgents/com.holus.agent.plist

# Check status
launchctl list | grep holus
```

## Monitoring

### Via Telegram
All agents send notifications to your Telegram. You'll get:
- Startup/shutdown alerts
- Agent run summaries
- Approval requests for high-stakes actions
- Error alerts

### Via Dashboard (optional)
```bash
# Start the web dashboard
python dashboard/app.py
# Access at http://your-mac-mini-ip:8080
```

### Via SSH
```bash
# Check logs
tail -f ~/.holus/logs/holus.log

# Check if running
launchctl list | grep holus

# Manual agent run
cd ~/holus && source .venv/bin/activate
python -m holus.main --agent job_hunter
```

## Cost Optimization

| Component | Cost | Notes |
|-----------|------|-------|
| Ollama (local) | $0 | Handles simple tasks |
| Claude API | ~$5-20/mo | Only for complex tasks (cover letters, research) |
| Telegram | $0 | Free bot API |
| Electricity | ~$5-10/mo | Mac Mini is very efficient |
| **Total** | **~$10-30/mo** | Compared to $1000+/mo for a human assistant |

## Troubleshooting

**Ollama not responding:**
```bash
ollama serve &
# or restart
pkill ollama && ollama serve &
```

**Agent stuck:**
```bash
# Restart Holus
launchctl unload ~/Library/LaunchAgents/com.holus.agent.plist
launchctl load ~/Library/LaunchAgents/com.holus.agent.plist
```

**Memory DB corrupted:**
```bash
rm -rf ~/.holus/memory
# Holus will recreate it on next start
```

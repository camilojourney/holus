# SPEC-004: Subprocess Isolation System

## Overview
Implement subprocess-based isolation for domain orchestrators to ensure crash resilience without K8s complexity.

## Problem Statement
Currently, all agents run in a single process. If one agent crashes (unhandled exception, memory leak, infinite loop), it can take down the entire HOLUS system.

## Solution
Run each domain's orchestrator as a separate subprocess managed by a supervisor in `main.py`.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      main.py (Supervisor)                    │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Process:    │  │ Process:    │  │ Process:    │         │
│  │ content     │  │ job-tracker │  │ trading     │         │
│  │ PID: 1234   │  │ PID: 1235   │  │ PID: 1236   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  Responsibilities:                                           │
│  • Spawn domain processes                                    │
│  • Monitor health (heartbeat)                                │
│  • Restart on crash                                          │
│  • Graceful shutdown                                         │
│  • Log aggregation                                           │
└─────────────────────────────────────────────────────────────┘
```

## Implementation

### Supervisor (main.py)

```python
# main.py
import asyncio
import subprocess
import signal
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from loguru import logger

@dataclass
class DomainProcess:
    name: str
    process: Optional[subprocess.Popen] = None
    restart_count: int = 0
    last_restart: float = 0

class Supervisor:
    """Manages domain orchestrator subprocesses."""
    
    MAX_RESTARTS = 5
    RESTART_COOLDOWN = 60  # seconds
    HEALTH_CHECK_INTERVAL = 30  # seconds
    
    def __init__(self, domains: list[str]):
        self.domains = {d: DomainProcess(name=d) for d in domains}
        self.running = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        logger.info("Shutdown signal received")
        self.running = False
    
    def _get_orchestrator_path(self, domain: str) -> Path:
        """Get path to domain orchestrator script."""
        domain_underscore = domain.replace("-", "_")
        return Path(f"agents/{domain}/{domain_underscore}_orchestrator.py")
    
    def spawn_domain(self, domain: str) -> subprocess.Popen:
        """Spawn a domain orchestrator subprocess."""
        script = self._get_orchestrator_path(domain)
        if not script.exists():
            raise FileNotFoundError(f"Orchestrator not found: {script}")
        
        logger.info(f"Spawning {domain} orchestrator")
        
        process = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Each domain gets its own process group for clean shutdown
            start_new_session=True,
        )
        
        self.domains[domain].process = process
        logger.info(f"{domain} started with PID {process.pid}")
        return process
    
    def check_process(self, domain: str) -> bool:
        """Check if domain process is alive."""
        dp = self.domains[domain]
        if dp.process is None:
            return False
        return dp.process.poll() is None
    
    async def restart_domain(self, domain: str):
        """Restart a crashed domain."""
        import time
        dp = self.domains[domain]
        
        # Check restart limits
        if dp.restart_count >= self.MAX_RESTARTS:
            logger.error(f"{domain} exceeded max restarts ({self.MAX_RESTARTS})")
            return
        
        # Cooldown check
        now = time.time()
        if now - dp.last_restart < self.RESTART_COOLDOWN:
            logger.warning(f"{domain} restart cooldown, skipping")
            return
        
        # Kill if still running
        if dp.process and dp.process.poll() is None:
            dp.process.terminate()
            await asyncio.sleep(1)
            if dp.process.poll() is None:
                dp.process.kill()
        
        # Restart
        dp.restart_count += 1
        dp.last_restart = now
        self.spawn_domain(domain)
        logger.info(f"{domain} restarted (attempt {dp.restart_count})")
    
    async def monitor(self):
        """Continuously monitor and restart crashed domains."""
        while self.running:
            for domain in self.domains:
                if not self.check_process(domain):
                    logger.warning(f"{domain} is not running")
                    await self.restart_domain(domain)
            
            await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
    
    async def shutdown(self):
        """Gracefully shutdown all domains."""
        logger.info("Shutting down all domains...")
        
        for domain, dp in self.domains.items():
            if dp.process and dp.process.poll() is None:
                logger.info(f"Stopping {domain} (PID {dp.process.pid})")
                dp.process.terminate()
        
        # Wait for graceful shutdown
        await asyncio.sleep(2)
        
        # Force kill stragglers
        for domain, dp in self.domains.items():
            if dp.process and dp.process.poll() is None:
                logger.warning(f"Force killing {domain}")
                dp.process.kill()
    
    async def run(self):
        """Main supervisor loop."""
        self.running = True
        
        # Spawn all domains
        for domain in self.domains:
            try:
                self.spawn_domain(domain)
            except Exception as e:
                logger.error(f"Failed to spawn {domain}: {e}")
        
        # Monitor loop
        try:
            await self.monitor()
        finally:
            await self.shutdown()

async def main():
    domains = ["content-strategy", "job-tracker", "trading"]
    supervisor = Supervisor(domains)
    await supervisor.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Domain Orchestrator Template

```python
# agents/content-strategy/content_orchestrator.py
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.base_agent import BaseAgent
from shared.orchestrator import DomainOrchestrator
from loguru import logger

class ContentStrategyOrchestrator(DomainOrchestrator):
    domain = "content-strategy"
    config_path = Path(__file__).parent / "config.yaml"
    
    def discover_agents(self):
        """Import and register domain agents."""
        from .publishers.video_publisher import VideoPublisher
        from .publishers.text_publisher import TextPublisher
        from .core.repurposing_engine import RepurposingEngine
        
        return [
            VideoPublisher,
            TextPublisher,
            RepurposingEngine,
        ]
    
    async def healthcheck(self) -> dict:
        """Return health status for monitoring."""
        return {
            "domain": self.domain,
            "agents": len(self.agents),
            "status": "healthy",
        }

async def main():
    logger.info(f"Starting {ContentStrategyOrchestrator.domain} orchestrator")
    orchestrator = ContentStrategyOrchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Shared Domain Orchestrator Base

```python
# shared/orchestrator.py
from abc import ABC, abstractmethod
from pathlib import Path
import yaml
from loguru import logger

class DomainOrchestrator(ABC):
    """Base class for domain orchestrators."""
    
    domain: str
    config_path: Path
    
    def __init__(self):
        self.config = self._load_config()
        self.agents = {}
        self._setup_agents()
    
    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        return {}
    
    def _setup_agents(self):
        agent_classes = self.discover_agents()
        for agent_class in agent_classes:
            if self.config.get("agents", {}).get(agent_class.name, {}).get("enabled", True):
                self.agents[agent_class.name] = agent_class(
                    config=self.config.get("agents", {}).get(agent_class.name, {})
                )
    
    @abstractmethod
    def discover_agents(self) -> list:
        """Return list of agent classes for this domain."""
        ...
    
    async def run(self):
        """Run the domain orchestrator."""
        logger.info(f"Domain {self.domain} starting with {len(self.agents)} agents")
        
        # Start scheduled tasks
        for name, agent in self.agents.items():
            logger.info(f"  - {name}: {agent.schedule}")
        
        # Run forever
        while True:
            await asyncio.sleep(60)
```

## Inter-Process Communication (IPC)

For domains that need to communicate (e.g., content-strategy needs job-tracker data), use file-based or socket IPC:

### Option 1: Shared Memory File

```python
# shared/ipc.py
import json
from pathlib import Path
from filelock import FileLock

IPC_DIR = Path("~/.holus/ipc").expanduser()

def send_message(from_domain: str, to_domain: str, message: dict):
    """Send message to another domain."""
    IPC_DIR.mkdir(parents=True, exist_ok=True)
    msg_file = IPC_DIR / f"{to_domain}_inbox.json"
    lock_file = IPC_DIR / f"{to_domain}_inbox.lock"
    
    with FileLock(lock_file):
        inbox = []
        if msg_file.exists():
            inbox = json.loads(msg_file.read_text())
        inbox.append({"from": from_domain, "message": message})
        msg_file.write_text(json.dumps(inbox))

def receive_messages(domain: str) -> list[dict]:
    """Receive and clear messages for domain."""
    msg_file = IPC_DIR / f"{domain}_inbox.json"
    lock_file = IPC_DIR / f"{domain}_inbox.lock"
    
    with FileLock(lock_file):
        if not msg_file.exists():
            return []
        messages = json.loads(msg_file.read_text())
        msg_file.write_text("[]")
        return messages
```

### Option 2: Unix Sockets (Lower Latency)

```python
# For real-time communication between domains
# Implementation deferred until needed
```

## Logging

Each subprocess logs to its own file:

```python
# In domain orchestrator
from loguru import logger
import sys

def setup_logging(domain: str):
    logger.remove()  # Remove default handler
    
    # Console output
    logger.add(sys.stderr, level="INFO")
    
    # Domain-specific file
    logger.add(
        f"logs/{domain}.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
    )
```

## Health Monitoring

### Heartbeat File

Each domain writes a heartbeat file:

```python
# In domain orchestrator run loop
import time
from pathlib import Path

HEARTBEAT_DIR = Path("~/.holus/heartbeats").expanduser()

async def run(self):
    heartbeat_file = HEARTBEAT_DIR / f"{self.domain}.txt"
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        heartbeat_file.write_text(str(time.time()))
        await asyncio.sleep(10)
```

### Supervisor Heartbeat Check

```python
# In Supervisor.monitor()
def check_heartbeat(self, domain: str) -> bool:
    heartbeat_file = HEARTBEAT_DIR / f"{domain}.txt"
    if not heartbeat_file.exists():
        return False
    
    last_beat = float(heartbeat_file.read_text())
    return (time.time() - last_beat) < 60  # Stale after 60s
```

## Acceptance Criteria
- [ ] Supervisor spawns all domain processes
- [ ] Crashed domains auto-restart
- [ ] Max restart limit prevents crash loops
- [ ] Graceful shutdown on SIGTERM/SIGINT
- [ ] Each domain logs separately
- [ ] Heartbeat monitoring works
- [ ] IPC between domains works

## Timeline
- Supervisor implementation: 3 hours
- Domain orchestrator base: 2 hours
- Heartbeat monitoring: 1 hour
- IPC system: 2 hours
- Testing: 2 hours
- **Total: 10 hours**

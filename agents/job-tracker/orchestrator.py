"""Job Tracker Domain Orchestrator."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger


class JobTrackerOrchestrator:
    """Orchestrator for job tracking domain."""
    
    domain = "job-tracker"
    config_path = Path(__file__).parent / "config.yaml"
    
    def __init__(self):
        self.config = self._load_config()
        self.agents = {}
        logger.info(f"JobTrackerOrchestrator initialized for domain: {self.domain}")
    
    def _load_config(self) -> dict:
        """Load domain configuration."""
        import yaml
        if self.config_path.exists():
            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def discover_agents(self) -> list:
        """Discover and register domain agents."""
        from agents.job_hunter.agent import JobHunterAgent
        logger.info(f"Discovered agent: {JobHunterAgent.name}")
        return [JobHunterAgent]
    
    async def healthcheck(self) -> dict:
        """Return health status for monitoring."""
        return {
            "domain": self.domain,
            "agents": len(self.agents),
            "status": "healthy",
        }
    
    async def run(self):
        """Run the domain orchestrator."""
        logger.info(f"Starting {self.domain} orchestrator...")
        
        while True:
            health = await self.healthcheck()
            logger.debug(f"Heartbeat: {health}")
            await asyncio.sleep(30)


async def main():
    """Entry point for subprocess."""
    logger.info("Job Tracker orchestrator starting...")
    orchestrator = JobTrackerOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())

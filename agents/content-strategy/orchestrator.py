"""Content Strategy Domain Orchestrator.

Routes content tasks between:
- Automation pipeline (routine daily posts)
- Agentic execution (creative, trending, strategic)

HOLUS = The brain (decides what to do)
Automation = The hands (executes routine work reliably)
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from .adapters.automation_adapter import AutomationAdapter, PipelineTask


class ContentOrchestrator:
    """
    Orchestrator for content strategy domain.
    
    Decides when to:
    - Delegate to automation (routine, scheduled, bulk)
    - Handle directly with agents (trending, creative, strategic)
    """
    
    domain = "content-strategy"
    config_path = Path(__file__).parent / "config.yaml"
    
    def __init__(self):
        self.config = self._load_config()
        self.agents = {}
        self.automation = AutomationAdapter(self.config.get("automation", {}))
        logger.info(f"ContentOrchestrator initialized for domain: {self.domain}")
    
    def _load_config(self) -> dict:
        """Load domain configuration."""
        import yaml
        if self.config_path.exists():
            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def discover_agents(self) -> list:
        """Discover and register domain agents."""
        # TODO: Import actual agent classes when implemented
        # from .publishers.video_publisher import VideoPublisher
        # from .publishers.text_publisher import TextPublisher
        logger.info("Agent discovery - loading publishers...")
        return []
    
    # === Automation Integration ===
    
    async def run_daily_routine(self) -> dict:
        """
        Run the daily routine via automation pipeline.
        
        This handles:
        - Enhancing pending Notion content
        - Posting ready content to all platforms
        """
        logger.info("📅 Running daily routine via automation...")
        
        result = await self.automation.run_daily_pipeline()
        
        if result.success:
            logger.info(f"✅ Daily routine triggered: job_id={result.job_id}")
        else:
            logger.error(f"❌ Daily routine failed: {result.error}")
        
        return {
            "success": result.success,
            "job_id": result.job_id,
            "message": result.message,
        }
    
    async def enhance_batch(self, limit: int = 10) -> dict:
        """Enhance a batch of content via automation."""
        result = await self.automation.enhance_content(limit=limit)
        return {"success": result.success, "job_id": result.job_id}
    
    async def post_now(self, limit: int = 1) -> dict:
        """Post ready content immediately via automation."""
        result = await self.automation.post_ready_content(limit=limit)
        return {"success": result.success, "job_id": result.job_id}
    
    async def check_automation_health(self) -> bool:
        """Check if automation pipeline is available."""
        return await self.automation.health_check()
    
    # === Strategic Decisions ===
    
    async def should_use_automation(self, content_type: str, context: dict) -> bool:
        """
        Decide whether to use automation or agentic approach.
        
        Use AUTOMATION when:
        - Routine daily posts
        - Bulk processing
        - No trending/urgent context
        - Content already in Notion queue
        
        Use AGENTIC when:
        - Responding to trends
        - Creative/strategic decisions needed
        - Real-time engagement
        - Personalized content
        """
        # Check for trending context
        if context.get("trending"):
            return False  # Use agents for trending
        
        # Check for urgency
        if context.get("urgent"):
            return False  # Use agents for urgent
        
        # Check for creative requirement
        if context.get("creative") or context.get("strategic"):
            return False  # Use agents for creative/strategic
        
        # Default: use automation for routine
        return True
    
    # === Health & Status ===
    
    async def healthcheck(self) -> dict:
        """Return health status for monitoring."""
        automation_healthy = await self.check_automation_health()
        
        return {
            "domain": self.domain,
            "agents": len(self.agents),
            "automation_connected": automation_healthy,
            "status": "healthy" if automation_healthy else "degraded",
        }
    
    async def run(self):
        """Run the domain orchestrator."""
        logger.info(f"Starting {self.domain} orchestrator...")
        
        # Check automation connection
        if await self.check_automation_health():
            logger.info("✅ Automation pipeline connected")
        else:
            logger.warning("⚠️ Automation pipeline not available")
        
        # Heartbeat loop
        while True:
            health = await self.healthcheck()
            logger.debug(f"Heartbeat: {health}")
            await asyncio.sleep(30)


async def main():
    """Entry point for subprocess."""
    logger.info("Content Strategy orchestrator starting...")
    orchestrator = ContentOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())

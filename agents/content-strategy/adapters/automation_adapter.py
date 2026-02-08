"""
Automation Pipeline Adapter — Connects HOLUS to social-media-automatization.

This adapter allows HOLUS agents to trigger the automation pipeline for:
- Routine daily posts (enhance + post)
- Bulk content enhancement
- Scheduled posting
- Credential validation

The automation pipeline handles:
- Notion → AI enhance → Translate → Video → Multi-platform posting

HOLUS handles strategy; automation handles execution.
"""
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx
from loguru import logger


class PipelineTask(str, Enum):
    """Available automation tasks."""
    FULL = "full"        # Enhance + Post
    ENHANCE = "enhance"  # AI enhancement + translation
    POST = "post"        # Post ready content
    VALIDATE = "validate"  # Check platform credentials


@dataclass
class PipelineResult:
    """Result from automation pipeline."""
    success: bool
    task: str
    job_id: Optional[str] = None
    message: Optional[str] = None
    details: Optional[dict] = None
    error: Optional[str] = None


class AutomationAdapter:
    """
    Adapter for social-media-automatization pipeline.
    
    Allows HOLUS content-strategy agents to delegate routine posting
    to the automation pipeline while focusing on strategy/creativity.
    """
    
    def __init__(self, config: dict = None):
        config = config or {}
        self.base_url = config.get("automation_url") or os.getenv(
            "AUTOMATION_API_URL", 
            "http://localhost:8000"
        )
        self.api_key = config.get("api_key") or os.getenv("HOLUS_API_KEY", "")
        self.timeout = config.get("timeout", 30)
        
    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    async def trigger_pipeline(
        self, 
        task: PipelineTask = PipelineTask.FULL,
        limit: int = 10,
        wait_for_result: bool = False,
    ) -> PipelineResult:
        """
        Trigger the automation pipeline.
        
        Args:
            task: Which task to run (full, enhance, post, validate)
            limit: Max items to process
            wait_for_result: If True, wait for completion (sync mode)
            
        Returns:
            PipelineResult with job_id or result
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/pipeline/trigger",
                    headers=self._get_headers(),
                    json={
                        "task": task.value,
                        "limit": limit,
                        "async_mode": not wait_for_result,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                return PipelineResult(
                    success=data.get("success", False),
                    task=task.value,
                    job_id=data.get("job_id"),
                    message=data.get("message"),
                    details=data.get("result"),
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Pipeline API error: {e.response.status_code}")
            return PipelineResult(
                success=False,
                task=task.value,
                error=f"HTTP {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            logger.error(f"Failed to trigger pipeline: {e}")
            return PipelineResult(
                success=False,
                task=task.value,
                error=str(e),
            )
    
    async def get_job_status(self, job_id: str) -> dict:
        """
        Check status of a pipeline job.
        
        Args:
            job_id: Job ID from trigger response
            
        Returns:
            Job status dict
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/pipeline/status/{job_id}",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def health_check(self) -> bool:
        """Check if automation API is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    # Convenience methods for common operations
    
    async def run_daily_pipeline(self) -> PipelineResult:
        """Run the full daily pipeline (enhance + post)."""
        logger.info("🤖 Delegating to automation: daily pipeline")
        return await self.trigger_pipeline(PipelineTask.FULL, limit=10)
    
    async def enhance_content(self, limit: int = 10) -> PipelineResult:
        """Run enhancement on pending content."""
        logger.info(f"🤖 Delegating to automation: enhance {limit} items")
        return await self.trigger_pipeline(PipelineTask.ENHANCE, limit=limit)
    
    async def post_ready_content(self, limit: int = 1) -> PipelineResult:
        """Post ready content to platforms."""
        logger.info(f"🤖 Delegating to automation: post {limit} items")
        return await self.trigger_pipeline(PipelineTask.POST, limit=limit)
    
    async def validate_credentials(self) -> PipelineResult:
        """Validate all platform credentials."""
        logger.info("🤖 Delegating to automation: validate credentials")
        return await self.trigger_pipeline(
            PipelineTask.VALIDATE, 
            wait_for_result=True
        )

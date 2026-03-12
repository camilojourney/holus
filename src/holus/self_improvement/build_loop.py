import json
import logging
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import yaml

from holus.core.capability_gap import CapabilityGap, CapabilityRequest, CapabilityTier
from holus.core.kill_switch import KillSwitch

logger = logging.getLogger(__name__)


class BuildLoop:
    """Tier 2 & 3 Self-Improvement: Handles code builds and architecture requests."""

    def __init__(
        self,
        root_dir: Path = Path("."),
        request_dir: Path = Path(".self-improvement/capability-requests"),
        history_path: Path = Path(".self-improvement/memory/build_history.jsonl"),
        guardrails_path: Path = Path("config/guardrails.yaml"),
    ):
        self.root_dir = root_dir
        self.request_dir = request_dir
        self.history_path = history_path
        self.guardrails_path = guardrails_path

        self.request_dir.mkdir(parents=True, exist_ok=True)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def file_request(self, gap: CapabilityGap) -> str:
        """File a structured build or architecture request."""
        slug = gap.what.lower().replace(" ", "-")[:30]
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        filename = f"{date_str}-{slug}.yaml"
        path = self.request_dir / filename

        request = CapabilityRequest(
            what=gap.what,
            why=gap.why,
            tier=gap.tier,
            evidence=gap.evidence,
            workaround=gap.workaround,
            slug=slug,
            status="pending" if gap.tier == CapabilityTier.TIER_2_CODE else "pending_human",
        )

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(request.model_dump(mode="json"), f, default_flow_style=False)

        logger.info(f"Filed {gap.tier} request: {path}")

        if gap.tier == CapabilityTier.TIER_3_ARCHITECTURE:
            self.notify_human(f"New Architecture Request: {gap.what}", gap.why)

        return str(path)

    def notify_human(self, title: str, message: str) -> None:
        """Send a macOS notification."""
        try:
            cmd = ["osascript", "-e", f'display notification "{message}" with title "{title}"']
            subprocess.run(cmd, check=False)
            print(f"NOTIFICATION: {title} - {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def run_pending_builds(self, kill_switch: KillSwitch) -> None:
        """Check for pending Tier 2 requests and dispatch ONE if budget allows."""
        if kill_switch.builds_paused():
            logger.info("Builds are paused via kill switch.")
            return

        if not self.check_budget():
            logger.info("Build budget exceeded for today/week.")
            return

        # Find first pending Tier 2 request
        pending = sorted(self.request_dir.glob("*.yaml"))
        target_request: CapabilityRequest | None = None
        target_path: Path | None = None

        for p in pending:
            with open(p) as f:
                data = yaml.safe_load(f)
                req = CapabilityRequest(**data)
                if req.status == "pending" and req.tier == CapabilityTier.TIER_2_CODE:
                    target_request = req
                    target_path = p
                    break

        if target_request and target_path:
            self.dispatch_build(target_request, target_path)

    def check_budget(self) -> bool:
        """Check if we are within the daily (2) and weekly (5) build limits."""
        if not self.history_path.exists():
            return True

        now = datetime.now(UTC)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        daily_count = 0
        weekly_count = 0

        with open(self.history_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if ts > day_ago:
                        daily_count += 1
                    if ts > week_ago:
                        weekly_count += 1
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        # Hardcoded limits as per spec, should ideally read from guardrails.yaml
        return daily_count < 2 and weekly_count < 5

    def dispatch_build(self, request: CapabilityRequest, path: Path) -> None:
        """Invoke the build via Claude/Codex proxy."""
        logger.info(f"Dispatching build for: {request.what}")

        # Update status to building
        request.status = "building"
        request.branch = f"feat/self-built-{request.slug}"
        with open(path, "w") as f:
            yaml.dump(request.model_dump(mode="json"), f)

        # Build prompt for Codex
        prompt = (
            f"Implement {request.what} in the holus repo. \n"
            f"Why: {request.why}\n"
            f"Evidence: {request.evidence}\n"
            f"Create on branch {request.branch}. \n"
            f"Write tests. Run just check. Commit if successful."
        )

        # Use the proxy to execute the build
        # In a real scenario, this would be an async call, but we simulate it here
        success = self._execute_via_proxy(prompt)

        # Update final status
        request.status = "built" if success else "failed"
        with open(path, "w") as f:
            yaml.dump(request.model_dump(mode="json"), f)

        # Log to history
        with open(self.history_path, "a") as f:
            log_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "slug": request.slug,
                "status": request.status,
                "tier": request.tier,
            }
            f.write(json.dumps(log_entry) + "\n")

        self.notify_human(
            f"Build {request.status.upper()}: {request.what}",
            f"Branch: {request.branch}" if success else "Check logs for failure.",
        )

    def _execute_via_proxy(self, prompt: str) -> bool:
        """Call the local proxy to execute a CLI agent."""
        # Using the proxy endpoint directly via HTTP
        proxy_url = os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:8080") + "/v1/messages"

        payload = {
            "model": "claude-sonnet-4-6",  # Use sonnet for implementation
            "messages": [{"role": "user", "content": prompt}],
            "system": "You are a professional software engineer. Implement the requested feature, write tests, and ensure justcheck passes before committing.",
        }

        try:
            # We use a long timeout as implementation can take minutes
            with httpx.Client(timeout=600.0) as client:
                response = client.post(proxy_url, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    output = result.get("content", [{}])[0].get("text", "")
                    logger.info(f"Proxy output: {output[:200]}...")
                    return "Error:" not in output and "FAIL" not in output
                else:
                    logger.error(f"Proxy returned status {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Failed to call proxy: {e}")
            return False

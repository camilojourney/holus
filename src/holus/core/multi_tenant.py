"""Multi-tenant support — run Holus for multiple brands.

Each tenant gets isolated:
- Config (brand.yaml, products.yaml, guardrails.yaml)
- Trajectory data
- Prompt populations
- Bandit arm states
- Knowledge files
- Content queue

Shared across tenants:
- Code (one codebase)
- Judge framework (same evaluators, different rubrics)
- Infrastructure (same orchestrator, different data paths)

Usage::

    tenant = Tenant.load("camilo")
    with tenant.context():
        # All paths resolve to tenant-specific directories
        run_from_idea("AI agents that improve themselves")

    # Multi-tenant orchestration
    manager = TenantManager()
    for tenant in manager.list_active():
        with tenant.context():
            await content_cycle()
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TENANTS_DIR = Path("tenants")


@dataclass
class Tenant:
    """A single tenant (brand) in the multi-tenant system."""

    tenant_id: str
    display_name: str
    config_dir: Path
    data_dir: Path
    active: bool = True

    @classmethod
    def load(cls, tenant_id: str) -> Tenant:
        """Load a tenant from the tenants directory."""
        tenant_dir = TENANTS_DIR / tenant_id
        if not tenant_dir.exists():
            msg = f"Tenant '{tenant_id}' not found at {tenant_dir}"
            raise FileNotFoundError(msg)

        config_dir = tenant_dir / "config"
        data_dir = tenant_dir / "data"

        # Read display name from brand.yaml if exists
        display_name = tenant_id
        brand_path = config_dir / "brand.yaml"
        if brand_path.exists():
            import yaml
            brand = yaml.safe_load(brand_path.read_text(encoding="utf-8")) or {}
            display_name = brand.get("name", tenant_id)

        return cls(
            tenant_id=tenant_id,
            display_name=display_name,
            config_dir=config_dir,
            data_dir=data_dir,
        )

    @contextmanager
    def context(self) -> Any:
        """Set environment for tenant-scoped execution.

        All data paths resolve to tenant-specific directories:
        - HOLUS_CONFIG_DIR → tenants/{id}/config/
        - HOLUS_DATA_DIR → tenants/{id}/data/
        - HOLUS_TENANT_ID → {id}
        """
        old_env = {
            "HOLUS_CONFIG_DIR": os.environ.get("HOLUS_CONFIG_DIR"),
            "HOLUS_DATA_DIR": os.environ.get("HOLUS_DATA_DIR"),
            "HOLUS_TENANT_ID": os.environ.get("HOLUS_TENANT_ID"),
        }

        os.environ["HOLUS_CONFIG_DIR"] = str(self.config_dir)
        os.environ["HOLUS_DATA_DIR"] = str(self.data_dir)
        os.environ["HOLUS_TENANT_ID"] = self.tenant_id

        try:
            yield self
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    @property
    def trajectory_path(self) -> Path:
        return self.data_dir / "trajectory.jsonl"

    @property
    def content_queue_dir(self) -> Path:
        return self.data_dir / "content-queue"

    @property
    def bandit_arms_path(self) -> Path:
        return self.data_dir / "bandit_arms.json"

    @property
    def knowledge_dir(self) -> Path:
        return self.data_dir / "knowledge" / "current"

    @property
    def prompts_dir(self) -> Path:
        return self.config_dir / "prompts"


class TenantManager:
    """Manage multiple tenants."""

    def __init__(self, tenants_dir: Path = TENANTS_DIR) -> None:
        self._dir = tenants_dir

    def list_all(self) -> list[Tenant]:
        """List all tenants."""
        if not self._dir.exists():
            return []

        tenants = []
        for tenant_dir in sorted(self._dir.iterdir()):
            if tenant_dir.is_dir() and (tenant_dir / "config").exists():
                try:
                    tenants.append(Tenant.load(tenant_dir.name))
                except Exception as exc:
                    logger.warning("Failed to load tenant %s: %s", tenant_dir.name, exc)
        return tenants

    def list_active(self) -> list[Tenant]:
        """List only active tenants."""
        return [t for t in self.list_all() if t.active]

    def create(
        self,
        tenant_id: str,
        *,
        brand_config: dict[str, Any] | None = None,
    ) -> Tenant:
        """Create a new tenant with directory structure."""
        tenant_dir = self._dir / tenant_id
        if tenant_dir.exists():
            msg = f"Tenant '{tenant_id}' already exists"
            raise FileExistsError(msg)

        # Create directory structure
        (tenant_dir / "config").mkdir(parents=True)
        (tenant_dir / "data" / "content-queue").mkdir(parents=True)
        (tenant_dir / "data" / "knowledge" / "current").mkdir(parents=True)
        (tenant_dir / "data" / "knowledge" / "requests").mkdir(parents=True)

        # Write brand config if provided
        if brand_config:
            import yaml
            brand_path = tenant_dir / "config" / "brand.yaml"
            brand_path.write_text(yaml.dump(brand_config, default_flow_style=False))

        logger.info("Created tenant: %s at %s", tenant_id, tenant_dir)
        return Tenant.load(tenant_id)

    def summary(self) -> dict[str, Any]:
        """Return summary of all tenants."""
        tenants = self.list_all()
        return {
            "total": len(tenants),
            "active": sum(1 for t in tenants if t.active),
            "tenants": [
                {"id": t.tenant_id, "name": t.display_name, "active": t.active}
                for t in tenants
            ],
        }

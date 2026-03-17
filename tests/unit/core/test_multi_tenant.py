"""Tests for multi-tenant support."""

import os

import pytest

from holus.core.multi_tenant import Tenant, TenantManager


@pytest.fixture
def tenants_dir(tmp_path):
    """Create a temp tenants directory with one tenant."""
    tenant_dir = tmp_path / "camilo"
    (tenant_dir / "config").mkdir(parents=True)
    (tenant_dir / "data" / "content-queue").mkdir(parents=True)
    (tenant_dir / "data" / "knowledge" / "current").mkdir(parents=True)
    return tmp_path


class TestTenant:
    def test_load(self, tenants_dir, monkeypatch):
        import holus.core.multi_tenant as mod
        monkeypatch.setattr(mod, "TENANTS_DIR", tenants_dir)

        tenant = Tenant.load("camilo")
        assert tenant.tenant_id == "camilo"
        assert tenant.config_dir.exists()

    def test_context_sets_env(self, tenants_dir, monkeypatch):
        import holus.core.multi_tenant as mod
        monkeypatch.setattr(mod, "TENANTS_DIR", tenants_dir)

        tenant = Tenant.load("camilo")
        with tenant.context():
            assert os.environ["HOLUS_TENANT_ID"] == "camilo"
            assert os.environ["HOLUS_CONFIG_DIR"] == str(tenant.config_dir)

        # Cleaned up after context
        assert "HOLUS_TENANT_ID" not in os.environ

    def test_paths(self, tenants_dir, monkeypatch):
        import holus.core.multi_tenant as mod
        monkeypatch.setattr(mod, "TENANTS_DIR", tenants_dir)

        tenant = Tenant.load("camilo")
        assert "camilo" in str(tenant.trajectory_path)
        assert "camilo" in str(tenant.content_queue_dir)
        assert "camilo" in str(tenant.bandit_arms_path)


class TestTenantManager:
    def test_list_all(self, tenants_dir, monkeypatch):
        import holus.core.multi_tenant as mod
        monkeypatch.setattr(mod, "TENANTS_DIR", tenants_dir)

        mgr = TenantManager(tenants_dir)
        tenants = mgr.list_all()
        assert len(tenants) == 1
        assert tenants[0].tenant_id == "camilo"

    def test_create(self, tmp_path, monkeypatch):
        import holus.core.multi_tenant as mod
        monkeypatch.setattr(mod, "TENANTS_DIR", tmp_path)

        mgr = TenantManager(tmp_path)
        tenant = mgr.create("brand_x", brand_config={"name": "Brand X"})
        assert tenant.tenant_id == "brand_x"
        assert (tmp_path / "brand_x" / "config").exists()
        assert (tmp_path / "brand_x" / "data" / "content-queue").exists()

    def test_summary(self, tenants_dir, monkeypatch):
        import holus.core.multi_tenant as mod
        monkeypatch.setattr(mod, "TENANTS_DIR", tenants_dir)

        mgr = TenantManager(tenants_dir)
        s = mgr.summary()
        assert s["total"] == 1
        assert s["active"] == 1

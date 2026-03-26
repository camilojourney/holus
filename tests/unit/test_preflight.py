"""Tests for the preflight check module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from holus.preflight import (
    CheckResult,
    _read_key_from_dotenv,
    check_api_key,
    check_brand_yaml,
    check_data_dirs,
    check_knowledge_files,
    check_memory_file,
    check_products_yaml,
    print_results,
    run_preflight,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


# ---------------------------------------------------------------------------
# check_api_key
# ---------------------------------------------------------------------------


class TestCheckApiKey:
    def test_valid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-test1234")
        result = check_api_key()
        assert result.passed is True
        assert "sk-ant-" in result.detail

    def test_missing_key(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Patch .env path to a non-existent file so dotenv fallback also fails
        with patch("holus.preflight._read_key_from_dotenv", return_value=""):
            result = check_api_key()
        assert result.passed is False
        assert "Not set" in result.detail
        assert result.fix

    def test_invalid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        with patch("holus.preflight._read_env_var_from_dotenv", return_value=""):
            result = check_api_key()
        assert result.passed is False
        assert "doesn't look like" in result.detail

    def test_proxy_dummy_key_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key-for-proxy")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8080")
        result = check_api_key()
        assert result.passed is True
        assert "proxy" in result.detail.lower()

    def test_key_from_dotenv(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch(
            "holus.preflight._read_key_from_dotenv",
            return_value="sk-ant-api03-from-dotenv",
        ):
            result = check_api_key()
        assert result.passed is True
        assert ".env" in result.detail


class TestReadKeyFromDotenv:
    def test_reads_from_dotenv(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("ANTHROPIC_API_KEY=sk-ant-test123\nOTHER_VAR=foo\n")
        with patch("holus.preflight.Path", return_value=env):
            # Directly test the function with a patched path
            pass
        # Direct test without patching Path (use monkeypatch chdir instead)
        import os

        old = os.getcwd()
        try:
            os.chdir(tmp_path)
            key = _read_key_from_dotenv()
        finally:
            os.chdir(old)
        assert key == "sk-ant-test123"

    def test_no_dotenv_file(self, tmp_path: Path) -> None:
        import os

        old = os.getcwd()
        try:
            os.chdir(tmp_path)
            key = _read_key_from_dotenv()
        finally:
            os.chdir(old)
        assert key == ""

    def test_quoted_value(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text('ANTHROPIC_API_KEY="sk-ant-quoted"\n')
        import os

        old = os.getcwd()
        try:
            os.chdir(tmp_path)
            key = _read_key_from_dotenv()
        finally:
            os.chdir(old)
        assert key == "sk-ant-quoted"


# ---------------------------------------------------------------------------
# check_brand_yaml
# ---------------------------------------------------------------------------


class TestCheckBrandYaml:
    def test_exists_and_parses(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        brand = tmp_path / "config" / "brand.yaml"
        brand.parent.mkdir(parents=True)
        brand.write_text("story:\n  origin: test\npositioning:\n  tagline: test\n")
        with patch("holus.preflight._BRAND_PATH", brand):
            result = check_brand_yaml()
        assert result.passed is True
        assert "2 sections" in result.detail

    def test_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "config" / "brand.yaml"
        with patch("holus.preflight._BRAND_PATH", missing):
            result = check_brand_yaml()
        assert result.passed is False
        assert "not found" in result.detail

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "brand.yaml"
        bad.write_text(":\n  bad: [yaml\n")
        with patch("holus.preflight._BRAND_PATH", bad):
            result = check_brand_yaml()
        assert result.passed is False
        assert "parse error" in result.detail

    def test_not_a_dict(self, tmp_path: Path) -> None:
        bad = tmp_path / "brand.yaml"
        bad.write_text("- just\n- a\n- list\n")
        with patch("holus.preflight._BRAND_PATH", bad):
            result = check_brand_yaml()
        assert result.passed is False
        assert "not a valid YAML mapping" in result.detail

    def test_counts_todos(self, tmp_path: Path) -> None:
        brand = tmp_path / "brand.yaml"
        brand.write_text("story:\n  origin: test\n  # TODO: Camilo input\n  # TODO: fill in\n")
        with patch("holus.preflight._BRAND_PATH", brand):
            result = check_brand_yaml()
        assert result.passed is True
        assert "2 TODO" in result.detail


# ---------------------------------------------------------------------------
# check_products_yaml
# ---------------------------------------------------------------------------


class TestCheckProductsYaml:
    def test_exists_and_parses(self, tmp_path: Path) -> None:
        products = tmp_path / "products.yaml"
        products.write_text(
            "products:\n  pilaster:\n    name: Pilaster\n  genpeli:\n    name: Genpeli\n"
        )
        with patch("holus.preflight._PRODUCTS_PATH", products):
            result = check_products_yaml()
        assert result.passed is True
        assert "2 products" in result.detail

    def test_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "products.yaml"
        with patch("holus.preflight._PRODUCTS_PATH", missing):
            result = check_products_yaml()
        assert result.passed is False

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "products.yaml"
        bad.write_text(":\n  bad: [yaml\n")
        with patch("holus.preflight._PRODUCTS_PATH", bad):
            result = check_products_yaml()
        assert result.passed is False


# ---------------------------------------------------------------------------
# check_knowledge_files
# ---------------------------------------------------------------------------


class TestCheckKnowledgeFiles:
    def test_all_present(self, tmp_path: Path) -> None:
        kdir = tmp_path / "knowledge"
        kdir.mkdir()
        for name in [
            "audience-profiles.md",
            "content-frameworks.md",
            "content-marketing-strategy.md",
            "platforms.md",
            "voice-profile.md",
            "viral-frameworks.md",
            "niche-research-queries.md",
            "extra-file.md",
        ]:
            (kdir / name).write_text("# content")
        with patch("holus.preflight._KNOWLEDGE_DIR", kdir):
            result = check_knowledge_files()
        assert result.passed is True
        assert "8 files" in result.detail
        assert "7 required" in result.detail

    def test_missing_some(self, tmp_path: Path) -> None:
        kdir = tmp_path / "knowledge"
        kdir.mkdir()
        (kdir / "audience-profiles.md").write_text("# content")
        with patch("holus.preflight._KNOWLEDGE_DIR", kdir):
            result = check_knowledge_files()
        assert result.passed is False
        assert "Missing" in result.detail

    def test_dir_missing(self, tmp_path: Path) -> None:
        kdir = tmp_path / "nonexistent"
        with patch("holus.preflight._KNOWLEDGE_DIR", kdir):
            result = check_knowledge_files()
        assert result.passed is False
        assert "not found" in result.detail


# ---------------------------------------------------------------------------
# check_memory_file
# ---------------------------------------------------------------------------


class TestCheckMemoryFile:
    def test_exists(self, tmp_path: Path) -> None:
        mem = tmp_path / "MEMORY.md"
        mem.write_text("# System Memory\nSome content here\n")
        with patch("holus.preflight._MEMORY_PATH", mem):
            result = check_memory_file()
        assert result.passed is True
        assert "bytes" in result.detail

    def test_missing(self, tmp_path: Path) -> None:
        mem = tmp_path / "MEMORY.md"
        with patch("holus.preflight._MEMORY_PATH", mem):
            result = check_memory_file()
        assert result.passed is False


# ---------------------------------------------------------------------------
# check_data_dirs
# ---------------------------------------------------------------------------


class TestCheckDataDirs:
    def test_creates_missing(self, tmp_path: Path) -> None:
        data = tmp_path / "data"
        queue = tmp_path / "data" / "content-queue"
        trajectory = tmp_path / "memory"
        with (
            patch("holus.preflight._DATA_DIR", data),
            patch("holus.preflight._QUEUE_DIR", queue),
            patch("holus.preflight._TRAJECTORY_DIR", trajectory),
        ):
            result = check_data_dirs()
        assert result.passed is True
        assert "Created" in result.detail
        assert data.exists()
        assert queue.exists()
        assert trajectory.exists()

    def test_already_exist(self, tmp_path: Path) -> None:
        data = tmp_path / "data"
        queue = tmp_path / "data" / "content-queue"
        trajectory = tmp_path / "memory"
        data.mkdir(parents=True)
        queue.mkdir(parents=True)
        trajectory.mkdir(parents=True)
        with (
            patch("holus.preflight._DATA_DIR", data),
            patch("holus.preflight._QUEUE_DIR", queue),
            patch("holus.preflight._TRAJECTORY_DIR", trajectory),
        ):
            result = check_data_dirs()
        assert result.passed is True
        assert "OK" in result.detail


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


class TestRunPreflight:
    def test_returns_all_checks(self) -> None:
        results = run_preflight()
        assert len(results) == 6
        assert all(isinstance(r, CheckResult) for r in results)

    def test_print_results_all_pass(self, capsys: pytest.CaptureFixture[str]) -> None:
        results = [
            CheckResult("Test1", passed=True, detail="OK"),
            CheckResult("Test2", passed=True, detail="OK"),
        ]
        ok = print_results(results)
        assert ok is True
        out = capsys.readouterr().out
        assert "All checks passed" in out

    def test_print_results_some_fail(self, capsys: pytest.CaptureFixture[str]) -> None:
        results = [
            CheckResult("Test1", passed=True, detail="OK"),
            CheckResult("Test2", passed=False, detail="Bad", fix="Do X"),
        ]
        ok = print_results(results)
        assert ok is False
        out = capsys.readouterr().out
        assert "1 check(s) failed" in out
        assert "Fix: Do X" in out

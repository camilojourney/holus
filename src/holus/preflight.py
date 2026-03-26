"""Preflight checks for the Holus marketing agent.

Validates the environment before running: config files, knowledge base,
data directories, and API keys. Prints clear pass/fail with fix instructions.

Usage:
    uv run python -m holus.preflight
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants — must match agent.py paths
# ---------------------------------------------------------------------------

_BRAND_PATH = Path("config/brand.yaml")
_PRODUCTS_PATH = Path("config/products.yaml")
_KNOWLEDGE_DIR = Path(".self-improvement/knowledge/current")
_MEMORY_PATH = Path(".self-improvement/MEMORY.md")
_QUEUE_DIR = Path("data/content-queue")
_DATA_DIR = Path("data")
_TRAJECTORY_DIR = Path(".self-improvement/memory")

# Minimum knowledge files the agent needs for good output
_REQUIRED_KNOWLEDGE = [
    "audience-profiles.md",
    "content-frameworks.md",
    "content-marketing-strategy.md",
    "platforms.md",
    "voice-profile.md",
    "viral-frameworks.md",
    "niche-research-queries.md",
]


# ---------------------------------------------------------------------------
# Check result
# ---------------------------------------------------------------------------


class CheckResult:
    """Single preflight check result."""

    def __init__(self, name: str, passed: bool, detail: str, fix: str = "") -> None:
        self.name = name
        self.passed = passed
        self.detail = detail
        self.fix = fix


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _read_env_var_from_dotenv(var_name: str) -> str:
    """Read a variable from .env file (fallback when not in os.environ)."""
    env_path = Path(".env")
    if not env_path.exists():
        return ""
    try:
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            name, _, value = stripped.partition("=")
            if name.strip() == var_name:
                return value.strip().strip("\"'")
    except Exception:
        pass
    return ""


def _read_key_from_dotenv() -> str:
    """Read ANTHROPIC_API_KEY from .env file (fallback when not in os.environ)."""
    return _read_env_var_from_dotenv("ANTHROPIC_API_KEY")


def check_api_key() -> CheckResult:
    """Check that ANTHROPIC_API_KEY is set (env var or .env file).

    Accepts either a real Anthropic key (sk-ant-...) or a proxy dummy key
    when ANTHROPIC_BASE_URL points to a local proxy (not api.anthropic.com).
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    source = "env"
    if not key:
        key = _read_key_from_dotenv()
        source = ".env"

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if not base_url:
        base_url = _read_env_var_from_dotenv("ANTHROPIC_BASE_URL")
    using_proxy = base_url and "api.anthropic.com" not in base_url

    if key and key.startswith("sk-ant-"):
        return CheckResult(
            "ANTHROPIC_API_KEY",
            passed=True,
            detail=f"Set via {source} (sk-ant-...{key[-4:]})",
        )
    if key and using_proxy:
        return CheckResult(
            "ANTHROPIC_API_KEY",
            passed=True,
            detail=f"Set via {source} (proxy key, base_url={base_url})",
        )
    if key:
        return CheckResult(
            "ANTHROPIC_API_KEY",
            passed=False,
            detail="Set but doesn't look like a valid key (set ANTHROPIC_BASE_URL for proxy)",
            fix="Export a valid key: export ANTHROPIC_API_KEY=sk-ant-... or set ANTHROPIC_BASE_URL for proxy",
        )
    return CheckResult(
        "ANTHROPIC_API_KEY",
        passed=False,
        detail="Not set",
        fix="Export your key: export ANTHROPIC_API_KEY=sk-ant-... (or add to .env)",
    )


def check_brand_yaml() -> CheckResult:
    """Check that config/brand.yaml exists and parses."""
    if not _BRAND_PATH.exists():
        return CheckResult(
            "config/brand.yaml",
            passed=False,
            detail="File not found",
            fix="Copy from template or run Sprint 2 build tasks",
        )
    try:
        with open(_BRAND_PATH) as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            return CheckResult(
                "config/brand.yaml",
                passed=False,
                detail="Parsed but not a valid YAML mapping",
                fix="Check the file format — should be a YAML dict",
            )
        sections = len(data)
        todos = _count_todos(_BRAND_PATH)
        detail = f"OK ({sections} sections"
        if todos:
            detail += f", {todos} TODO blocks for Camilo"
        detail += ")"
        return CheckResult("config/brand.yaml", passed=True, detail=detail)
    except yaml.YAMLError as exc:
        return CheckResult(
            "config/brand.yaml",
            passed=False,
            detail=f"YAML parse error: {exc}",
            fix="Fix the YAML syntax in config/brand.yaml",
        )


def check_products_yaml() -> CheckResult:
    """Check that config/products.yaml exists and parses."""
    if not _PRODUCTS_PATH.exists():
        return CheckResult(
            "config/products.yaml",
            passed=False,
            detail="File not found",
            fix="Create config/products.yaml with product definitions",
        )
    try:
        with open(_PRODUCTS_PATH) as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            return CheckResult(
                "config/products.yaml",
                passed=False,
                detail="Parsed but not a valid YAML mapping",
                fix="Check the file format — should be a YAML dict",
            )
        products = data.get("products", data)
        count = len(products) if isinstance(products, dict) else 0
        return CheckResult(
            "config/products.yaml",
            passed=True,
            detail=f"OK ({count} products)",
        )
    except yaml.YAMLError as exc:
        return CheckResult(
            "config/products.yaml",
            passed=False,
            detail=f"YAML parse error: {exc}",
            fix="Fix the YAML syntax in config/products.yaml",
        )


def check_knowledge_files() -> CheckResult:
    """Check that required knowledge files exist."""
    if not _KNOWLEDGE_DIR.exists():
        return CheckResult(
            "Knowledge files",
            passed=False,
            detail=f"Directory not found: {_KNOWLEDGE_DIR}",
            fix="Run Sprint 1 build tasks to seed knowledge files",
        )
    existing = {f.name for f in _KNOWLEDGE_DIR.glob("*.md")}
    missing = [f for f in _REQUIRED_KNOWLEDGE if f not in existing]
    if missing:
        return CheckResult(
            "Knowledge files",
            passed=False,
            detail=f"Missing {len(missing)}: {', '.join(missing)}",
            fix=f"Create missing files in {_KNOWLEDGE_DIR}/",
        )
    total = len(existing)
    return CheckResult(
        "Knowledge files",
        passed=True,
        detail=f"OK ({total} files, all {len(_REQUIRED_KNOWLEDGE)} required present)",
    )


def check_memory_file() -> CheckResult:
    """Check that MEMORY.md exists."""
    if not _MEMORY_PATH.exists():
        return CheckResult(
            "MEMORY.md",
            passed=False,
            detail="File not found",
            fix=f"Create {_MEMORY_PATH} with system memory header",
        )
    size = _MEMORY_PATH.stat().st_size
    return CheckResult(
        "MEMORY.md",
        passed=True,
        detail=f"OK ({size:,} bytes)",
    )


def check_data_dirs() -> CheckResult:
    """Check that data directories exist (create if missing)."""
    dirs = [_DATA_DIR, _QUEUE_DIR, _TRAJECTORY_DIR]
    created: list[str] = []
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))
    if created:
        return CheckResult(
            "Data directories",
            passed=True,
            detail=f"Created missing: {', '.join(created)}",
        )
    return CheckResult(
        "Data directories",
        passed=True,
        detail=f"OK ({', '.join(str(d) for d in dirs)})",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_todos(path: Path) -> int:
    """Count lines containing TODO in a file."""
    text = path.read_text()
    return sum(1 for line in text.splitlines() if "TODO" in line)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_preflight() -> list[CheckResult]:
    """Run all preflight checks and return results."""
    return [
        check_api_key(),
        check_brand_yaml(),
        check_products_yaml(),
        check_knowledge_files(),
        check_memory_file(),
        check_data_dirs(),
    ]


def print_results(results: list[CheckResult]) -> bool:
    """Print preflight results. Returns True if all passed."""
    print("\n=== Holus Preflight Check ===\n")

    all_passed = True
    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        print(f"  [{icon}] {r.name}: {r.detail}")
        if not r.passed and r.fix:
            print(f"         Fix: {r.fix}")
            all_passed = False

    print()
    if all_passed:
        print("All checks passed. Ready to run.")
    else:
        failed = sum(1 for r in results if not r.passed)
        print(f"{failed} check(s) failed. Fix the issues above before running.")
    print()
    return all_passed


def main() -> None:
    """CLI entry point."""
    results = run_preflight()
    ok = print_results(results)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

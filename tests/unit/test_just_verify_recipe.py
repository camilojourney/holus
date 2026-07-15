from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
JUSTFILE = REPO_ROOT / "justfile"
JUST_BIN = shutil.which("just")


def _write_verifier(path: Path, marker: str, exit_code: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "import sys",
                f"print({marker!r})",
                "print('args=' + ' '.join(sys.argv[1:]))",
                f"raise SystemExit({exit_code})",
                "",
            ]
        ),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_verify(tmp_path: Path, env: dict[str, str | None]) -> subprocess.CompletedProcess[str]:
    python_bin = tmp_path / "python-bin"
    python_bin.mkdir(exist_ok=True)
    python_link = python_bin / "python3"
    if not python_link.exists():
        python_link.symlink_to(sys.executable)
    path_parts = [str(python_bin), *os.defpath.split(os.pathsep)]
    if env.get("PATH"):
        path_parts.insert(0, env["PATH"])
    run_env = {
        "HOME": str(tmp_path / "home"),
        "PATH": os.pathsep.join(path_parts),
    }
    for key, value in env.items():
        if value is None:
            run_env.pop(key, None)
        else:
            run_env[key] = value
    run_env["PATH"] = os.pathsep.join(path_parts)
    return subprocess.run(
        [
            JUST_BIN or "just",
            "--justfile",
            str(JUSTFILE),
            "--working-directory",
            str(tmp_path),
            "verify",
        ],
        text=True,
        capture_output=True,
        env=run_env,
        check=False,
    )


pytestmark = pytest.mark.skipif(
    JUST_BIN is None,
    reason="just is required to exercise the verify recipe",
)


def test_verify_prefers_explicit_repo_verify_path(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit" / "repo_verify.py"
    path_bin = tmp_path / "bin" / "repo_verify.py"
    fleet = tmp_path / "fleet" / "system" / "shared" / "scripts" / "repo_verify.py"
    home = (
        tmp_path
        / "home"
        / "github"
        / "fleet-system"
        / "system"
        / "shared"
        / "scripts"
        / "repo_verify.py"
    )
    _write_verifier(explicit, "explicit")
    _write_verifier(path_bin, "path")
    _write_verifier(fleet, "fleet")
    _write_verifier(home, "home")

    result = _run_verify(
        tmp_path,
        {
            "REPO_VERIFY_PATH": str(explicit),
            "FLEET_SYSTEM_ROOT": str(tmp_path / "fleet"),
            "PATH": str(tmp_path / "bin"),
        },
    )

    assert result.returncode == 0
    assert "explicit" in result.stdout
    assert "path" not in result.stdout
    assert "--repo holus --skip tests" in result.stdout


def test_verify_uses_path_before_fleet_root_and_home(tmp_path: Path) -> None:
    path_bin = tmp_path / "bin" / "repo_verify.py"
    fleet = tmp_path / "fleet" / "system" / "shared" / "scripts" / "repo_verify.py"
    home = (
        tmp_path
        / "home"
        / "github"
        / "fleet-system"
        / "system"
        / "shared"
        / "scripts"
        / "repo_verify.py"
    )
    _write_verifier(path_bin, "path")
    _write_verifier(fleet, "fleet")
    _write_verifier(home, "home")

    result = _run_verify(
        tmp_path,
        {
            "FLEET_SYSTEM_ROOT": str(tmp_path / "fleet"),
            "PATH": str(tmp_path / "bin"),
        },
    )

    assert result.returncode == 0
    assert "path" in result.stdout
    assert "fleet" not in result.stdout


def test_verify_uses_fleet_root_before_home(tmp_path: Path) -> None:
    fleet = tmp_path / "fleet" / "system" / "shared" / "scripts" / "repo_verify.py"
    home = (
        tmp_path
        / "home"
        / "github"
        / "fleet-system"
        / "system"
        / "shared"
        / "scripts"
        / "repo_verify.py"
    )
    _write_verifier(fleet, "fleet")
    _write_verifier(home, "home")

    result = _run_verify(
        tmp_path,
        {
            "FLEET_SYSTEM_ROOT": str(tmp_path / "fleet"),
            "PATH": "",
        },
    )

    assert result.returncode == 0
    assert "fleet" in result.stdout
    assert "home" not in result.stdout


def test_verify_uses_home_fleet_system_last(tmp_path: Path) -> None:
    home = (
        tmp_path
        / "home"
        / "github"
        / "fleet-system"
        / "system"
        / "shared"
        / "scripts"
        / "repo_verify.py"
    )
    _write_verifier(home, "home")

    result = _run_verify(tmp_path, {"PATH": ""})

    assert result.returncode == 0
    assert "home" in result.stdout


def test_verify_fails_with_override_guidance_when_verifier_is_missing(tmp_path: Path) -> None:
    result = _run_verify(tmp_path, {"PATH": ""})

    assert result.returncode == 127
    assert "Set REPO_VERIFY_PATH=/path/to/repo_verify.py" in result.stderr
    assert "add executable repo_verify.py to PATH" in result.stderr
    assert "set FLEET_SYSTEM_ROOT=/path/to/fleet-system" in result.stderr


def test_verify_fails_with_override_guidance_when_home_is_unset(tmp_path: Path) -> None:
    result = _run_verify(tmp_path, {"HOME": None, "PATH": ""})

    assert result.returncode == 127
    assert "Set REPO_VERIFY_PATH=/path/to/repo_verify.py" in result.stderr
    assert "add executable repo_verify.py to PATH" in result.stderr
    assert "set FLEET_SYSTEM_ROOT=/path/to/fleet-system" in result.stderr
    assert "unbound variable" not in result.stderr


def test_verify_accepts_recognized_warning_result(tmp_path: Path) -> None:
    verifier = tmp_path / "repo_verify.py"
    _write_verifier(verifier, "RESULT: PASS WITH WARNINGS", exit_code=2)

    result = _run_verify(tmp_path, {"REPO_VERIFY_PATH": str(verifier), "PATH": ""})

    assert result.returncode == 0
    assert "RESULT: PASS WITH WARNINGS" in result.stdout


def test_verify_rejects_unrecognized_exit_two_result(tmp_path: Path) -> None:
    verifier = tmp_path / "repo_verify.py"
    _write_verifier(verifier, "RESULT: FAIL", exit_code=2)

    result = _run_verify(tmp_path, {"REPO_VERIFY_PATH": str(verifier), "PATH": ""})

    assert result.returncode == 2
    assert "RESULT: FAIL" in result.stdout


def test_verify_preserves_non_warning_failure_with_warning_text(tmp_path: Path) -> None:
    verifier = tmp_path / "repo_verify.py"
    _write_verifier(verifier, "RESULT: PASS WITH WARNINGS", exit_code=1)

    result = _run_verify(tmp_path, {"REPO_VERIFY_PATH": str(verifier), "PATH": ""})

    assert result.returncode == 1
    assert "RESULT: PASS WITH WARNINGS" in result.stdout

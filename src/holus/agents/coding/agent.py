"""Coding agent: Claude Code CLI integration with self-improvement loop.

Architecture:
  - Primary interface: Claude Code CLI (``claude -p "..." --model ...``)
  - PR review automation via GitHub Actions + claude-code-action
  - Cross-repo dependency management
  - Weekly self-improvement cycles (Manager -> Code Improver -> Judge)

The coding agent does NOT run LangGraph in the same way as marketing.
Instead, it orchestrates Claude Code CLI invocations and manages the
self-improvement pipeline.
"""

from __future__ import annotations

import logging
import operator
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from holus.agents.base import BaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class CodingState(TypedDict):
    """State for the coding agent LangGraph."""

    # Inputs
    task_type: str  # "pr_review" | "improvement" | "maintenance"
    repo_path: str
    task_description: str

    # PR review
    pr_diff: str | None
    review_result: dict | None

    # Improvement
    improvement_target: str | None
    improvement_result: dict | None

    # Cross-repo
    dependency_report: dict | None

    # Observability
    messages: Annotated[list, operator.add]
    error: str | None


# ---------------------------------------------------------------------------
# Claude Code CLI wrapper
# ---------------------------------------------------------------------------


@dataclass
class ClaudeCodeRunner:
    """Wrapper around the Claude Code CLI for programmatic invocation."""

    model: str = "claude-sonnet-4-5-20250514"
    max_turns: int = 25
    timeout_seconds: int = 300

    def run(
        self,
        prompt: str,
        *,
        cwd: str | Path | None = None,
        model: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute a Claude Code CLI command.

        Args:
            prompt: The task prompt.
            cwd: Working directory for the command.
            model: Override the default model.
            allowed_tools: Restrict available tools.

        Returns:
            Dict with ``stdout``, ``stderr``, ``returncode``, and ``success``.
        """
        cmd = [
            "claude",
            "-p",
            prompt,
            "--model",
            model or self.model,
            "--max-turns",
            str(self.max_turns),
            "--output-format",
            "json",
        ]

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1,
                "success": False,
            }
        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": "claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
                "returncode": -1,
                "success": False,
            }


# ---------------------------------------------------------------------------
# Cross-repo management
# ---------------------------------------------------------------------------


@dataclass
class RepoConfig:
    """Configuration for a managed repository."""

    name: str
    path: str
    github_url: str
    language: str
    dependencies: list[str] = field(default_factory=list)


MANAGED_REPOS = [
    RepoConfig("holus", "/repos/holus", "github.com/user/holus", "python"),
    RepoConfig("pilaster", "/repos/pilaster", "github.com/user/pilaster", "python", ["holus"]),
]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def pr_review_node(state: CodingState) -> dict[str, Any]:
    """Review a PR diff using Claude Code CLI."""
    diff = state.get("pr_diff", "")
    if not diff:
        return {
            "review_result": {"verdict": "skipped", "reason": "No diff provided"},
            "messages": [{"node": "pr_review", "output": "Skipped (no diff)"}],
        }

    runner = ClaudeCodeRunner(model="claude-sonnet-4-5-20250514")
    result = runner.run(
        prompt=(
            f"Review this PR diff. Read CLAUDE.md first for project context.\n"
            f"Focus on: correctness, security, test coverage, spec compliance.\n\n"
            f"```diff\n{diff[:10000]}\n```"
        ),
        cwd=state.get("repo_path") or ".",
        allowed_tools=["Read", "Glob", "Grep"],
    )

    return {
        "review_result": {
            "verdict": "completed" if result["success"] else "failed",
            "output": result["stdout"][:5000],
            "error": result["stderr"][:1000] if not result["success"] else None,
        },
        "messages": [{"node": "pr_review", "output": "Review completed"}],
    }


def improvement_node(state: CodingState) -> dict[str, Any]:
    """Execute one self-improvement cycle using Claude Code CLI (Opus)."""
    target = state.get("improvement_target", "")
    if not target:
        return {
            "improvement_result": {"status": "skipped", "reason": "No target"},
            "messages": [{"node": "improvement", "output": "Skipped"}],
        }

    runner = ClaudeCodeRunner(model="claude-opus-4-20250514", max_turns=25)
    result = runner.run(
        prompt=(
            f"You are the Code Improver agent.\n"
            f"Read .claude/agents/code-improver.md for full instructions.\n"
            f"Execute this improvement: {target}\n"
            f"Write your report to .self-improvement/reports/code-improver/"
        ),
        cwd=state.get("repo_path") or ".",
        allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
    )

    return {
        "improvement_result": {
            "status": "completed" if result["success"] else "failed",
            "output": result["stdout"][:5000],
        },
        "messages": [{"node": "improvement", "output": "Improvement cycle completed"}],
    }


def maintenance_node(state: CodingState) -> dict[str, Any]:
    """Cross-repo dependency check and maintenance."""
    report: dict[str, Any] = {"repos_checked": [], "issues": []}

    for repo in MANAGED_REPOS:
        repo_path = Path(repo.path)
        if repo_path.exists():
            report["repos_checked"].append(repo.name)
        else:
            report["issues"].append(f"Repo {repo.name} not found at {repo.path}")

    return {
        "dependency_report": report,
        "messages": [
            {"node": "maintenance", "output": f"Checked {len(report['repos_checked'])} repos"}
        ],
    }


def route_task(state: CodingState) -> str:
    """Route to the appropriate node based on task type."""
    task_type = state.get("task_type", "maintenance")
    if task_type == "pr_review":
        return "pr_review"
    elif task_type == "improvement":
        return "improvement"
    return "maintenance"


# ---------------------------------------------------------------------------
# CodingAgent
# ---------------------------------------------------------------------------


class CodingAgent(BaseAgent):
    """Claude Code CLI-based coding agent."""

    agent_name = "coding-agent"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(CodingState)

        graph.add_node("pr_review", pr_review_node)
        graph.add_node("improvement", improvement_node)
        graph.add_node("maintenance", maintenance_node)

        graph.add_conditional_edges(
            START,
            route_task,
            {
                "pr_review": "pr_review",
                "improvement": "improvement",
                "maintenance": "maintenance",
            },
        )

        graph.add_edge("pr_review", END)
        graph.add_edge("improvement", END)
        graph.add_edge("maintenance", END)

        return graph

    def default_state(self) -> dict[str, Any]:
        return {
            "task_type": "maintenance",
            "repo_path": ".",
            "task_description": "",
            "pr_diff": None,
            "review_result": None,
            "improvement_target": None,
            "improvement_result": None,
            "dependency_report": None,
            "messages": [],
            "error": None,
        }

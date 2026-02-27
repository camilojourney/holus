"""Pilaster agent: ComfyUI workflow management with quality assessment.

Architecture:
  1. Workflow Intelligence -- Opus analyzes workflow structure, recommends optimizations.
  2. ComfyUI API -- submit workflows, poll for results, retrieve images.
  3. Quality Assessment -- Claude Vision scores generated images.
  4. Config-to-Outcome Memory -- maps parameter configurations to quality scores.

Workflows are JSON node graphs, version-controlled with hash-based dedup.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import operator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from holus.agents.base import BaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class PilasterState(TypedDict):
    """State for the Pilaster agent LangGraph."""

    # Inputs
    workflow_name: str
    workflow_json: dict
    generation_prompt: str
    quality_criteria: dict

    # Pipeline outputs
    prompt_id: str | None
    generated_images: list[str]  # file paths or URLs
    quality_scores: list[dict]
    workflow_version_hash: str | None

    # Memory
    config_outcome_entry: dict | None

    # Observability
    messages: Annotated[list, operator.add]
    error: str | None


# ---------------------------------------------------------------------------
# Workflow version control
# ---------------------------------------------------------------------------


class WorkflowVersionManager:
    """Version-control ComfyUI workflows with hash-based deduplication."""

    def __init__(self, workflows_dir: Path = Path("data/comfyui_workflows")) -> None:
        self.workflows_dir = workflows_dir

    def save_workflow(
        self,
        name: str,
        workflow_json: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save a workflow version.  Returns the content hash."""
        content = json.dumps(workflow_json, sort_keys=True)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        filename = f"{name}_{timestamp}_{content_hash}.json"
        filepath = self.workflows_dir / name / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        filepath.write_text(
            json.dumps(
                {
                    "workflow": workflow_json,
                    "metadata": {
                        "name": name,
                        "hash": content_hash,
                        "created": timestamp,
                        **(metadata or {}),
                    },
                },
                indent=2,
            )
        )

        logger.info("Saved workflow %s version %s", name, content_hash)
        return content_hash

    def load_latest(self, name: str) -> dict[str, Any] | None:
        """Load the most recent version of a named workflow."""
        workflow_dir = self.workflows_dir / name
        if not workflow_dir.exists():
            return None

        files = sorted(workflow_dir.glob("*.json"), reverse=True)
        if not files:
            return None

        return json.loads(files[0].read_text())

    def diff_workflows(self, wf_a: dict, wf_b: dict) -> dict[str, Any]:
        """Compare two workflow versions, returning changed nodes."""
        nodes_a = set(wf_a.get("workflow", {}).keys())
        nodes_b = set(wf_b.get("workflow", {}).keys())

        return {
            "added_nodes": list(nodes_b - nodes_a),
            "removed_nodes": list(nodes_a - nodes_b),
            "modified_nodes": [
                node
                for node in nodes_a & nodes_b
                if wf_a["workflow"][node] != wf_b["workflow"][node]
            ],
        }


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def submit_workflow(state: PilasterState) -> dict[str, Any]:
    """Submit a ComfyUI workflow for execution."""
    workflow = state.get("workflow_json", {})
    if not workflow:
        return {
            "error": "No workflow JSON provided",
            "messages": [{"node": "submit_workflow", "error": "No workflow"}],
        }

    # In production: call ComfyUI API
    # from holus.integrations.comfyui import ComfyUIClient
    # client = ComfyUIClient()
    # prompt_id = await client.queue_workflow(workflow)

    logger.info("Workflow submitted: %s", state.get("workflow_name", "unnamed"))

    return {
        "prompt_id": "placeholder-prompt-id",
        "messages": [{"node": "submit_workflow", "output": "Workflow queued"}],
    }


def assess_quality(state: PilasterState) -> dict[str, Any]:
    """Assess generated image quality using Claude Vision."""
    images = state.get("generated_images", [])
    criteria = state.get("quality_criteria", {})
    prompt_used = state.get("generation_prompt", "")

    if not images:
        return {
            "quality_scores": [],
            "messages": [{"node": "assess_quality", "output": "No images to assess"}],
        }

    default_criteria = {
        "technical_quality": "Sharpness, noise, artifacts, resolution",
        "prompt_adherence": "How well does the image match the generation prompt?",
        "aesthetic_quality": "Composition, color harmony, visual appeal",
        "commercial_viability": "Would this work as a product/marketing image?",
    }
    criteria = criteria or default_criteria

    scores: list[dict[str, Any]] = []

    for image_path_str in images:
        image_path = Path(image_path_str)
        if not image_path.exists():
            scores.append({"image": image_path_str, "error": "File not found"})
            continue

        # Encode image for Claude Vision
        image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
        media_type = "image/png" if image_path.suffix == ".png" else "image/jpeg"

        criteria_text = "\n".join(f"- {k}: {v}" for k, v in criteria.items())

        try:
            import anthropic

            client = anthropic.Anthropic()
            response = client.messages.create(
                model="claude-sonnet-4-5-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    f"Assess this generated image quality.\n\n"
                                    f'Generation prompt: "{prompt_used}"\n\n'
                                    f"Score each criterion 1-10:\n{criteria_text}\n\n"
                                    f'Return JSON: {{"scores": {{"criterion": {{"score": N, '
                                    f'"reason": "..."}}}}, "overall": N, "pass": true/false}}\n'
                                    f"Pass threshold: overall >= 7"
                                ),
                            },
                        ],
                    }
                ],
            )

            try:
                assessment = json.loads(response.content[0].text)
            except (json.JSONDecodeError, IndexError):
                assessment = {"error": "Could not parse assessment"}

            scores.append({"image": image_path_str, **assessment})

        except Exception as exc:
            scores.append({"image": image_path_str, "error": str(exc)})

    return {
        "quality_scores": scores,
        "messages": [{"node": "assess_quality", "output": f"Assessed {len(scores)} images"}],
    }


def version_workflow(state: PilasterState) -> dict[str, Any]:
    """Save the workflow version if quality passed."""
    scores = state.get("quality_scores", [])
    workflow = state.get("workflow_json", {})
    name = state.get("workflow_name", "unnamed")

    passing = [s for s in scores if s.get("pass", False)]

    version_hash = None
    if passing and workflow:
        manager = WorkflowVersionManager()
        avg_score = sum(s.get("overall", 0) for s in passing) / len(passing)
        version_hash = manager.save_workflow(
            name=name,
            workflow_json=workflow,
            metadata={
                "avg_quality_score": avg_score,
                "images_assessed": len(scores),
                "images_passed": len(passing),
            },
        )

    return {
        "workflow_version_hash": version_hash,
        "config_outcome_entry": {
            "workflow_name": name,
            "version_hash": version_hash,
            "quality_scores": scores,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        "messages": [{"node": "version_workflow", "output": f"Version hash: {version_hash}"}],
    }


# ---------------------------------------------------------------------------
# PilasterAgent
# ---------------------------------------------------------------------------


class PilasterAgent(BaseAgent):
    """ComfyUI-powered image generation agent with quality assessment."""

    agent_name = "pilaster-agent"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(PilasterState)

        graph.add_node("submit_workflow", submit_workflow)
        graph.add_node("assess_quality", assess_quality)
        graph.add_node("version_workflow", version_workflow)

        graph.add_edge(START, "submit_workflow")
        graph.add_edge("submit_workflow", "assess_quality")
        graph.add_edge("assess_quality", "version_workflow")
        graph.add_edge("version_workflow", END)

        return graph

    def default_state(self) -> dict[str, Any]:
        return {
            "workflow_name": "",
            "workflow_json": {},
            "generation_prompt": "",
            "quality_criteria": {},
            "prompt_id": None,
            "generated_images": [],
            "quality_scores": [],
            "workflow_version_hash": None,
            "config_outcome_entry": None,
            "messages": [],
            "error": None,
        }

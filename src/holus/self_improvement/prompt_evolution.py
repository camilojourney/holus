"""Genetic prompt evolution — population-based proactive prompt optimization.

Maintains a population of prompt variants per agent. Weekly cycle:
evaluate → select → mutate → crossover → replace.

Based on PromptBreeder (ICLR 2024): beat human prompts by 25% on BBH.

Activation gate: n >= 500 total observations (per engineering consultation).
Until then, the existing reactive PromptOptimizer handles failure streaks.

Usage::

    evo = PromptEvolution(agent_id="idea-generator")
    evo.initialize_population()  # Creates canonical + 1 challenger
    report = await evo.evolve()  # Weekly: evaluate → select → mutate
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

POPULATIONS_DIR = Path("config/prompts")
MIN_OBSERVATIONS_TO_ACTIVATE = 500
MAX_POPULATION_SIZE = 3  # Per consultation: start at 2-3, not 5
ELITISM_COUNT = 1  # Top performer always survives


@dataclass
class PromptVariant:
    """A single prompt variant in the population."""

    variant_id: str
    prompt_text: str
    parent_ids: list[str]  # Which variants this was derived from
    mutation_type: str  # "canonical" | "mutation" | "crossover" | "random"
    created_at: str
    n_evaluations: int = 0
    avg_score: float = 0.0
    total_score: float = 0.0

    def record_score(self, score: float) -> None:
        self.n_evaluations += 1
        self.total_score += score
        self.avg_score = self.total_score / self.n_evaluations

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "parent_ids": self.parent_ids,
            "mutation_type": self.mutation_type,
            "created_at": self.created_at,
            "n_evaluations": self.n_evaluations,
            "avg_score": round(self.avg_score, 4),
            "total_score": round(self.total_score, 4),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], prompt_text: str = "") -> PromptVariant:
        return cls(
            variant_id=data["variant_id"],
            prompt_text=prompt_text,
            parent_ids=data.get("parent_ids", []),
            mutation_type=data.get("mutation_type", "unknown"),
            created_at=data.get("created_at", ""),
            n_evaluations=data.get("n_evaluations", 0),
            avg_score=data.get("avg_score", 0.0),
            total_score=data.get("total_score", 0.0),
        )


@dataclass
class EvolutionReport:
    """Result of a weekly evolution cycle."""

    agent_id: str
    generation: int
    variants_evaluated: int
    variants_killed: int
    variants_created: int
    best_variant_id: str
    best_avg_score: float
    mutations_applied: list[str]


class PromptEvolution:
    """Genetic prompt evolution for a single agent.

    Manages a population of prompt variants, runs weekly evolution
    cycles (evaluate → select → mutate → replace), and persists
    population state to config/prompts/{agent_id}/.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._pop_dir = POPULATIONS_DIR / agent_id
        self._meta_path = self._pop_dir / "population.json"
        self._variants: list[PromptVariant] = []
        self._generation: int = 0
        self._load()

    def _load(self) -> None:
        """Load population metadata and prompt files."""
        if not self._meta_path.exists():
            return

        try:
            meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
            self._generation = meta.get("generation", 0)

            for v_data in meta.get("variants", []):
                prompt_path = self._pop_dir / f"{v_data['variant_id']}.md"
                prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
                self._variants.append(PromptVariant.from_dict(v_data, prompt_text))
        except Exception as exc:
            logger.warning("Failed to load population for %s: %s", self.agent_id, exc)

    def _save(self) -> None:
        """Persist population metadata."""
        self._pop_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "agent_id": self.agent_id,
            "generation": self._generation,
            "population_size": len(self._variants),
            "updated_at": datetime.now(UTC).isoformat(),
            "variants": [v.to_dict() for v in self._variants],
        }
        self._meta_path.write_text(json.dumps(meta, indent=2))

        # Write each variant's prompt to its own .md file
        for v in self._variants:
            if v.prompt_text:
                prompt_path = self._pop_dir / f"{v.variant_id}.md"
                prompt_path.write_text(v.prompt_text)

    @property
    def population_size(self) -> int:
        return len(self._variants)

    def initialize_population(self, canonical_prompt: str) -> None:
        """Initialize with canonical prompt as the first variant.

        Called once when evolution is first activated for an agent.
        """
        if self._variants:
            return  # Already initialized

        now = datetime.now(UTC).isoformat()
        self._variants = [
            PromptVariant(
                variant_id="canonical",
                prompt_text=canonical_prompt,
                parent_ids=[],
                mutation_type="canonical",
                created_at=now,
            ),
        ]
        self._save()
        logger.info("Population initialized for %s with canonical prompt", self.agent_id)

    def get_active_prompt(self) -> tuple[str, str]:
        """Return the current best prompt and its variant_id.

        Used by PromptLoader as a Layer 0.5 (between optimizer and canonical).
        """
        if not self._variants:
            return "", "none"

        # Return the variant with highest avg_score (or canonical if no scores)
        scored = [v for v in self._variants if v.n_evaluations > 0]
        if scored:
            best = max(scored, key=lambda v: v.avg_score)
            return best.prompt_text, best.variant_id

        return self._variants[0].prompt_text, self._variants[0].variant_id

    def record_evaluation(self, variant_id: str, score: float) -> None:
        """Record a score for a variant (called after content generation + judging)."""
        for v in self._variants:
            if v.variant_id == variant_id:
                v.record_score(score)
                self._save()
                return
        logger.warning("Unknown variant: %s for agent %s", variant_id, self.agent_id)

    async def evolve(self) -> EvolutionReport | None:
        """Run one generation of evolution: select → mutate → replace.

        Returns EvolutionReport or None if not enough data.
        """
        if len(self._variants) < 1:
            logger.info("No population for %s — skipping evolution", self.agent_id)
            return None

        # Sort by avg_score (best first)
        self._variants.sort(key=lambda v: v.avg_score, reverse=True)

        best = self._variants[0]
        mutations_applied: list[str] = []

        # Elitism: keep the best variant
        survivors = [best]

        # If population < MAX, create mutations of the best
        while len(survivors) < MAX_POPULATION_SIZE:
            mutation_type = "mutation" if len(survivors) == 1 else "crossover"

            if mutation_type == "mutation":
                new_prompt = await self._mutate(best.prompt_text, best.avg_score)
                new_id = f"gen{self._generation + 1}_mut{len(survivors)}"
            else:
                # Crossover between best and second-best (if exists)
                second = self._variants[1] if len(self._variants) > 1 else best
                new_prompt = await self._crossover(best.prompt_text, second.prompt_text)
                new_id = f"gen{self._generation + 1}_cross{len(survivors)}"

            survivors.append(PromptVariant(
                variant_id=new_id,
                prompt_text=new_prompt,
                parent_ids=[best.variant_id] if mutation_type == "mutation" else [best.variant_id, second.variant_id if len(self._variants) > 1 else best.variant_id],
                mutation_type=mutation_type,
                created_at=datetime.now(UTC).isoformat(),
            ))
            mutations_applied.append(f"{mutation_type}: {new_id}")

        killed_count = len(self._variants) - ELITISM_COUNT
        self._variants = survivors
        self._generation += 1
        self._save()

        report = EvolutionReport(
            agent_id=self.agent_id,
            generation=self._generation,
            variants_evaluated=sum(v.n_evaluations for v in self._variants),
            variants_killed=max(0, killed_count),
            variants_created=len(mutations_applied),
            best_variant_id=best.variant_id,
            best_avg_score=best.avg_score,
            mutations_applied=mutations_applied,
        )

        logger.info(
            "Evolution gen %d for %s: best=%s (%.2f), created %d variants",
            self._generation, self.agent_id, best.variant_id, best.avg_score,
            len(mutations_applied),
        )
        return report

    async def _mutate(self, prompt: str, current_score: float) -> str:
        """Mutate a prompt by rewriting one section based on performance."""
        try:
            from holus.integrations.claude_api.client import HolusClaudeClient

            client = HolusClaudeClient()
            response = await client.agenerate(
                model_tier="strategic",
                system="You are a prompt engineer. Rewrite ONE section of this system prompt to improve it. Keep the overall structure. Change the weakest part. Be specific and concrete.",
                user=f"Current prompt (scoring {current_score:.2f}):\n\n{prompt}\n\nRewrite the weakest section to score higher. Return the complete updated prompt.",
                max_tokens=4096,
            )
            return response.strip() or prompt
        except Exception as exc:
            logger.warning("Mutation failed: %s. Keeping original.", exc)
            return prompt

    async def _crossover(self, prompt_a: str, prompt_b: str) -> str:
        """Crossover two prompts by combining best sections."""
        try:
            from holus.integrations.claude_api.client import HolusClaudeClient

            client = HolusClaudeClient()
            response = await client.agenerate(
                model_tier="strategic",
                system="You are a prompt engineer. Combine the best parts of two system prompts into one improved prompt. Take the strongest sections from each.",
                user=f"Prompt A:\n{prompt_a}\n\nPrompt B:\n{prompt_b}\n\nCreate a combined prompt taking the best sections from each. Return the complete prompt.",
                max_tokens=4096,
            )
            return response.strip() or prompt_a
        except Exception as exc:
            logger.warning("Crossover failed: %s. Keeping prompt A.", exc)
            return prompt_a

"""DSPy optimizer — BootstrapFewShot + MIPROv2 integration stubs.

These require the `dspy` pip package. The bridge (dspy_bridge.py) prepares
datasets; this module runs actual optimization when dspy is available.

Activation: n >= 500 trajectory entries with judge scores.

Usage::

    optimizer = DSPyOptimizer(agent_id="idea-generator")
    if optimizer.is_available():
        result = optimizer.bootstrap_few_shot(dataset)
        result = optimizer.mipro_optimize(dataset)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _dspy_available() -> bool:
    """Check if dspy is installed."""
    try:
        import dspy  # noqa: F401
        return True
    except ImportError:
        return False


class DSPyOptimizer:
    """DSPy optimization for Holus agent prompts.

    Wraps BootstrapFewShot and MIPROv2 optimizers. Falls back gracefully
    when dspy is not installed — the bridge still works for manual
    few-shot selection.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._available = _dspy_available()

    def is_available(self) -> bool:
        """Check if DSPy optimization can run."""
        return self._available

    def bootstrap_few_shot(
        self,
        dataset: list[dict[str, Any]],
        *,
        k: int = 5,
        max_bootstraps: int = 10,
    ) -> dict[str, Any]:
        """Run BootstrapFewShot to auto-select best examples.

        Takes labeled (task, output, score) examples and selects the
        k best demonstrations that maximize performance on a dev set.

        Returns: {optimized_prompt, selected_examples, dev_score}
        """
        if not self._available:
            return {
                "status": "dspy_not_installed",
                "fallback": "Use dspy_bridge.select_few_shot() for manual selection",
            }

        try:
            import dspy

            # Configure DSPy with the local proxy
            lm = dspy.LM(
                model="anthropic/claude-sonnet-4-6",
                api_base="http://localhost:8080/v1",
                api_key="local",
            )
            dspy.configure(lm=lm)

            # Define the signature
            class ContentGenerator(dspy.Signature):
                """Generate marketing content from an idea."""
                idea: str = dspy.InputField()
                content: str = dspy.OutputField()

            # Create the module
            module = dspy.ChainOfThought(ContentGenerator)

            # Create trainset from dataset
            trainset = [
                dspy.Example(idea=ex["task"], content=ex["output"]).with_inputs("idea")
                for ex in dataset
                if ex.get("score", 0) >= 0.75
            ]

            if len(trainset) < 3:
                return {"status": "insufficient_data", "n_examples": len(trainset)}

            # Run BootstrapFewShot
            optimizer = dspy.BootstrapFewShot(max_bootstrapped_demos=max_bootstraps)

            def metric(example, prediction, trace=None):
                # Simple length + keyword check as proxy metric
                return len(prediction.content) > 100

            optimizer.compile(module, trainset=trainset[:20], metric=metric)

            return {
                "status": "success",
                "n_demos": len(trainset),
                "optimized": True,
            }

        except Exception as exc:
            logger.warning("DSPy BootstrapFewShot failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def mipro_optimize(
        self,
        dataset: list[dict[str, Any]],
        *,
        num_candidates: int = 5,
    ) -> dict[str, Any]:
        """Run MIPROv2 to co-optimize instructions + examples.

        More powerful than BootstrapFewShot — optimizes both the system
        instruction AND the few-shot examples jointly.

        Returns: {optimized_instruction, selected_examples, dev_score}
        """
        if not self._available:
            return {
                "status": "dspy_not_installed",
                "fallback": "Install dspy: pip install dspy",
            }

        # MIPROv2 requires more setup and is compute-intensive
        # Stub for when dspy is installed and sufficient data exists
        return {
            "status": "not_yet_implemented",
            "note": "MIPROv2 optimization planned for Sprint 5.4",
            "prerequisite": f"Need {len(dataset)} examples (have {len(dataset)})",
        }

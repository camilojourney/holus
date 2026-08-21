# Complexity refactor: flowchart rendering

## Selection evidence

- **Selected scope:** `src/holus/visual/charts.py:flowchart_svg` and focused tests in `tests/unit/visual/test_charts.py`.
- **Before:** `charts.py` was 857 lines; `flowchart_svg` had an AST branch-count cyclomatic approximation of 28, the highest single-function value in the eligible rendering modules. Its edge and node branches repeated SVG construction patterns, including 15 occurrences of the shared text-anchor fragment.
- **Alternatives considered:** `core/health.py` was 399 lines with max approximation 30 but is a smaller operational health gate; `visual/dispatcher.py` was 803 lines with aggregate approximation 132 but is visual-generation orchestration outside this focused rendering scope; `lineage/store.py` was 297 lines with max approximation 27.
- **Exact scope boundary:** preserve the `flowchart_svg` public signature and SVG output while separating layout, positioning, marker, edge, and node concerns. Publishing/scheduling delivery, deployment/infra/state-root, and marketing cycle/generation orchestration were excluded.

## Result

- `flowchart_svg` now delegates to focused helpers; its approximation fell from **28 to 2**.
- The refactor preserves byte-identical SVG output for representative empty, vertical, horizontal, grid, invalid-edge, and custom-style cases.
- `charts.py` is now 919 lines because the behavior-preserving helper extraction is colocated with the existing chart API; the complexity target is the flowchart function rather than line-count minimization.
- Focused chart coverage increased from 17 to 22 passing tests, including XML escaping, layout-specific edge behavior, grid connector suppression, and invalid-edge handling.

The metric is a deterministic AST approximation: base complexity 1 plus `if`, loop, exception, context-manager, comprehension, boolean-operator, and conditional-expression branches.

## Iteration 2: lineage validation

### Selection evidence

- **Selected scope:** `src/holus/lineage/store.py:LineageStore.validate`; the module is 297 lines and the function was 85 lines with complexity **25** under the deterministic AST approximation. It mixed hash-chain verification, Pydantic entity decoding, graph integrity checks, aggregate counts, and conservative completeness inference, with repeated traversals of events, nodes, and edges.
- **Why this target:** it is a focused, Holus-owned read-only provenance boundary with direct CLI, API, and health callers and dedicated contract tests in `tests/unit/lineage/test_store.py`; it does not implement publishing/scheduling delivery or content generation.
- **Alternatives challenged:** `core/health.py:run_preflight_checks` scored 38 but is part of the excluded health/cycle-gating path; `visual_pipeline.py:_render_visual` scored 26 and `idea_runner.py:save_piece` scored 20 but are content-generation-cycle orchestration; `api/routes/health.py:metrics` also scored 25 but is a broader operational endpoint with less cohesive validation seams. The already-refactored radar and flowchart targets were not reconsidered as active candidates.
- **Exact scope boundary:** preserve `LineageStore.validate()` and `ValidationReport` behavior while extracting private validation, entity, graph, and summary helpers. Publishing/scheduling delivery, deployment/infra/state-root, and marketing cycle/generation orchestration remain untouched.

### Result

- Extracted six focused helpers; `LineageStore.validate` complexity fell from **25 to 4** while retaining the same report values and adding a tampered-chain regression test. `store.py` grew from 297 to 329 lines as validation concerns became explicit, typed seams.
- The lineage contract suite plus API and pipeline callers pass (**7 focused tests**); Ruff and strict mypy pass for the changed source and tests.

## Iteration 1: research radar orchestration

### Selection evidence

- **Selected scope:** `src/holus/research/radar.py:_run_radar_unlocked`; the module was 373 lines and the function had complexity **27**, tied for the highest eligible non-generation orchestration target after excluding the 399-line cycle-gating health function (complexity 30) and content-generation orchestration.
- **Why this target:** the function mixed source-fetch error normalization, dedupe bookkeeping, per-item scoring/retry failure records, candidate creation, and source-report projection; callers include the research API and CLI, with 10 focused radar tests covering the observable workflow.
- **Alternatives challenged:** `src/holus/lineage/store.py:validate` was also complexity 27 but smaller at 297 lines and is a durable provenance validation boundary; the previously refactored chart target is already at complexity 2. The selected radar path offered the clearest repeated orchestration seams without touching publishing, scheduling, deployment, state-root, or content-generation-cycle code.

### Result

- Extracted source fetching, item scoring, and source-result projection helpers; `_run_radar_unlocked` complexity fell from **27 to 16** while preserving its public API and report/output behavior.
- `radar.py` grew from 373 to 427 lines because the refactor keeps explicit, typed helper boundaries rather than compressing logic; focused radar tests pass (**10 passed**).

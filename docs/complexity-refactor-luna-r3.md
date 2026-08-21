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

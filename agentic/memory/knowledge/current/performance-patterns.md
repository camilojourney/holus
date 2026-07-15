# Knowledge: Performance Patterns

**Last updated:** 2026-03-01
**Updated by:** builder agent (cycle 15, initial seed)
**Confidence:** none (no analytics data yet)
**Affects:** marketing agent content decisions, weekly learning loop
**Research cadence:** weekly (auto-updated by `just learn`)

---

## Summary

No analytics data available yet. This file will be populated automatically by the
weekly learning loop (`WeeklyLearningLoop` in `src/holus/self_improvement/learning_loop.py`)
when it runs via `just learn`.

The loop reads trajectory data, aggregates by product x content_type x platform,
extracts statistical insights, and writes results here.

## Insights

_No insights yet. Run `just learn` after the marketing agent has produced content._

## Content Type x Platform Breakdown

| Product | Content Type | Platform | Count | Success Rate |
|---------|-------------|----------|-------|-------------|
| - | - | - | 0 | N/A |

## How This File Gets Updated

1. Marketing agent creates content and logs to `trajectory.jsonl`
2. Weekly learning loop reads trajectory entries from the last 30 days
3. Loop aggregates patterns and writes insights to this file
4. Old versions are archived to `agentic/memory/knowledge/archive/`

## Expected Patterns (to be confirmed by data)

Once analytics flow in, expect patterns like:
- Which content type gets the most engagement per product
- Which platform performs best for each audience
- Optimal posting cadence
- Framework effectiveness (which content frameworks produce winners)

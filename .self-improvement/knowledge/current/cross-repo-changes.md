# Knowledge: Cross-Repo Change Log

**Last updated:** 2026-03-01
**Updated by:** builder agent (auto-maintained)
**Confidence:** high (factual log)
**Affects:** all sibling repo integrations
**Research cadence:** updated every cycle that touches another repo

---

## Change Log

## 2026-03-01 — social-media-automatization
- **Files changed:** `src/api/routes/analytics.py` (new), `src/api/app.py`, `mcp_server/tools.py`, `mcp_server/server.py`
- **What:** Added `get_analytics` and `get_top_posts` MCP tools + FastAPI analytics endpoints
- **Why:** Holus marketing agent needs to read publishing analytics via MCP to close the observe→reason→act loop (Spec 016 SPEC-004)
- **Cycle:** 8
- **Tested:** ruff lint pass, MCP tool import + registration verified (12 tools), committed as b842ed0

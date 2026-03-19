# Acceptance Criteria

Testable acceptance criteria derived from specs 010, 012, 027, 028, and 031.
Each criterion follows Given/When/Then format and satisfies five rules:
binary, measurable, behavioral, independent, specific enough to write a test.

---

## SPEC-010: Marketing Agent

### AC-001: Observe stage reads analytics via MCP
**Priority:** P0
**Spec:** SPEC-010
**Given** the marketing agent is running and the social-media MCP server is reachable
**When** the `observe` method executes on `MarketingAgent`
**Then** `state["analytics"]` contains a dict with keys from `social-media-mcp.get_analytics(days=7)` and `state["analytics"]` is not empty

### AC-002: Observe stage loads product config
**Priority:** P0
**Spec:** SPEC-010
**Given** `config/products.yaml` exists with at least one product entry
**When** the `observe` method executes on `MarketingAgent`
**Then** `state["product_updates"]` is a dict containing a `products` key with at least one product whose keys include `name`, `tagline`, and `platforms`

### AC-003: Observe stage loads knowledge files
**Priority:** P0
**Spec:** SPEC-010
**Given** `.self-improvement/knowledge/current/` contains at least one `.md` file
**When** the `observe` method executes on `MarketingAgent`
**Then** `state["knowledge"]` is a dict with at least one key matching a filename stem from `knowledge/current/`, and each value is a non-empty string

### AC-004: Reason stage produces ContentDecision with platform field
**Priority:** P0
**Spec:** SPEC-010, SPEC-031
**Given** the observe stage completed and `state["analytics"]`, `state["product_updates"]`, and `state["knowledge"]` are populated
**When** the `reason` method executes on `MarketingAgent`
**Then** `state["content_decisions"]` is a list of 1-3 dicts, and each dict successfully validates against the `ContentDecision` Pydantic model with required fields `product`, `platform`, `content_type`, `topic`, and `reasoning`

### AC-005: ContentDecision includes platform field set to linkedin
**Priority:** P0
**Spec:** SPEC-031
**Given** the reason stage runs in LinkedIn Content Pipeline mode
**When** a `ContentDecision` is produced
**Then** the `platform` field equals `"linkedin"` (matches `Platform.LINKEDIN` enum value)

### AC-006: MarketingAgent graph has five stages
**Priority:** P1
**Spec:** SPEC-010
**Given** `MarketingAgent` is instantiated
**When** `build_graph()` is called
**Then** the returned `StateGraph` has exactly five nodes named `observe`, `reason`, `act`, `render`, and `evaluate`, connected in that order from START to END

---

## SPEC-012: Knowledge & Learning

### AC-007: TrajectoryLogger.append writes one JSON line
**Priority:** P0
**Spec:** SPEC-012
**Given** a `TrajectoryLogger` is initialized with a temporary file path
**When** `append(TrajectoryEntry(agent_id="marketing-agent", task_type="content_creation", status="success"))` is called
**Then** the file contains exactly one line, and `json.loads()` on that line returns a dict with keys `agent_id`, `timestamp`, `task_type`, and `status`

### AC-008: TrajectoryLogger.read_filtered returns entries matching agent_id
**Priority:** P0
**Spec:** SPEC-012
**Given** a trajectory file with 5 entries: 3 from `agent_id="marketing-agent"` and 2 from `agent_id="code-improver"`
**When** `read_filtered(agent_id="marketing-agent")` is called
**Then** the returned list has exactly 3 entries, and all have `agent_id == "marketing-agent"`

### AC-009: TrajectoryLogger.summary returns aggregate stats
**Priority:** P1
**Spec:** SPEC-012
**Given** a trajectory file with 10 entries: 7 with `status="success"`, 2 with `status="failure"`, 1 with `status="error"`, and total `cost_usd` summing to 1.50
**When** `summary()` is called
**Then** the returned dict has `total == 10`, `statuses` mapping `{"success": 7, "failure": 2, "error": 1}`, and `total_cost_usd == 1.50`

### AC-010: Evaluate stage logs decision to trajectory.jsonl
**Priority:** P0
**Spec:** SPEC-012
**Given** the act stage produced one `GeneratedPiece` with `platform="linkedin"` and `content_type="tutorial"`
**When** the `evaluate` method executes on `MarketingAgent`
**Then** a new line is appended to `.self-improvement/memory/trajectory.jsonl` containing a JSON object with keys `agent_id`, `task_type`, `status`, `timestamp`, and `metadata`, where `metadata` includes `platform` and `content_type`

### AC-011: Knowledge gap request creates a markdown file
**Priority:** P1
**Spec:** SPEC-012
**Given** the `file_knowledge_gap` function is called with `filed_by="marketing-agent"`, `what_i_need="LinkedIn carousel best practices"`, `why_i_need_it="No data on carousel engagement"`, `priority="high"`
**When** the function completes
**Then** a new `.md` file exists in `.self-improvement/knowledge/requests/` whose content contains the strings `Filed by: marketing-agent`, `Priority: high`, and `LinkedIn carousel best practices`

---

## SPEC-027: Resilient Agent Loop

### AC-012: Kill switch blocks agent execution
**Priority:** P0
**Spec:** SPEC-027
**Given** a Redis instance with key `holus:kill:global` set to a valid `KillSwitchState` JSON
**When** `KillSwitch.is_active("marketing-agent")` is called
**Then** the return value is `True`

### AC-013: Kill switch deactivation allows agent execution
**Priority:** P0
**Spec:** SPEC-027
**Given** the global kill switch was active and `deactivate(scope="global")` is called
**When** `KillSwitch.is_active("marketing-agent")` is called after deactivation
**Then** the return value is `False`

### AC-014: CycleContext.transition logs state change to trajectory
**Priority:** P0
**Spec:** SPEC-027
**Given** a `CycleContext` created via `CycleContext.new(trajectory_path=tmp_path)` in state `STARTING`
**When** `transition(CycleState.HEALTH_CHECK)` is called
**Then** the trajectory file at `tmp_path` contains one JSON line with `"event": "transition"`, `"from_state": "starting"`, `"to_state": "health_check"`, and a valid ISO 8601 `timestamp`

### AC-015: write_trajectory_entry writes final cycle summary
**Priority:** P0
**Spec:** SPEC-027
**Given** a `CycleContext` with `current_state=CycleState.DONE`, `content_created=2`, `content_posted=2`, `content_failed=0`, and `quality_scores=[0.87, 0.92]`
**When** `write_trajectory_entry(context)` is called
**Then** the trajectory file contains a JSON line with `"phase": "done"`, `"content_created": 2`, `"content_posted": 2`, `"content_failed": 0`, `"quality_scores": [0.87, 0.92]`, and `"error": null`

### AC-016: Preflight check returns blocking_ok=False when kill switch is active
**Priority:** P0
**Spec:** SPEC-027
**Given** the global Redis kill switch key `holus:kill:global` is set
**When** `run_preflight_checks()` is called
**Then** the returned `HealthResult` has `blocking_ok == False` and `warnings` contains a string matching `"kill switch"`

---

## SPEC-028: Observatory API

### AC-017: GET /api/v1/health returns agent health status
**Priority:** P0
**Spec:** SPEC-028
**Given** the Observatory FastAPI app is running and `agents/AGENTS.yaml` exists
**When** `GET /api/v1/health` is called
**Then** the response has status 200 and the JSON body contains boolean fields `kill_switch_active`, `trajectory_file_exists`, `eval_history_file_exists`, `agents_yaml_exists`, integer field `content_queue_count`, and nullable float field `error_rate_1h`

### AC-018: GET /api/v1/agents returns all agents from AGENTS.yaml
**Priority:** P0
**Spec:** SPEC-028
**Given** `agents/AGENTS.yaml` contains entries for N agents (where N >= 1)
**When** `GET /api/v1/agents` is called
**Then** the response has status 200 and the JSON body is a list with exactly N elements, each having fields `id`, `name`, `model`, and `role`

### AC-019: GET /api/v1/agents/{agent_id} returns 404 for unknown agent
**Priority:** P1
**Spec:** SPEC-028
**Given** `agents/AGENTS.yaml` does not contain an agent with id `nonexistent-agent-xyz`
**When** `GET /api/v1/agents/nonexistent-agent-xyz` is called
**Then** the response has status 404

### AC-020: GET /api/v1/trajectory returns paginated results
**Priority:** P0
**Spec:** SPEC-028
**Given** `trajectory.jsonl` contains 120 valid entries
**When** `GET /api/v1/trajectory?page=1&page_size=50` is called
**Then** the response has status 200 and the JSON body has `total == 120`, `page == 1`, `page_size == 50`, `has_more == true`, and `entries` is a list of exactly 50 elements

---

## SPEC-031: LinkedIn Content Pipeline

### AC-021: Quality gate rejects content scoring below 0.7
**Priority:** P0
**Spec:** SPEC-031
**Given** the `enforce_quality_gate` function receives a content piece and a scorer that returns `3.0` (below hard-fail threshold of 4.0)
**When** `enforce_quality_gate([piece], scorer=low_scorer)` is called
**Then** `result.accepted_pieces` is empty, `result.discarded_pieces` has exactly 1 element, and `result.hard_fail_count == 1`

### AC-022: Quality gate accepts content scoring 7.0 or above
**Priority:** P0
**Spec:** SPEC-031
**Given** the `enforce_quality_gate` function receives a content piece and a scorer that returns `8.5`
**When** `enforce_quality_gate([piece], scorer=high_scorer)` is called
**Then** `result.accepted_pieces` has exactly 1 element, `result.discarded_pieces` is empty, and `result.pass_count == 1`

### AC-023: Schedule post calls MCP with approval_required=true
**Priority:** P0
**Spec:** SPEC-031
**Given** the act stage produced a LinkedIn post that passed the quality gate with score >= 7.0
**When** `social-media-mcp.schedule_post()` is called
**Then** the call includes parameters `platform="linkedin"` and `approval_required=True`

### AC-024: Missing data files return empty collections not 500 errors
**Priority:** P1
**Spec:** SPEC-028
**Given** `trajectory.jsonl` does not exist
**When** `GET /api/v1/trajectory` is called
**Then** the response has status 200 and the JSON body has `entries == []`, `total == 0`, and `has_more == false`

---

## Cross-Spec Coverage Summary

| Spec | P0 | P1 | P2 | Total |
|------|----|----|-----|-------|
| SPEC-010 (Marketing Agent) | 4 | 1 | 0 | 5 |
| SPEC-012 (Knowledge & Learning) | 2 | 3 | 0 | 5 |
| SPEC-027 (Resilient Agent Loop) | 5 | 0 | 0 | 5 |
| SPEC-028 (Observatory API) | 3 | 2 | 0 | 5 |
| SPEC-031 (LinkedIn Content Pipeline) | 3 | 1 | 0 | 4 |
| **Total** | **17** | **7** | **0** | **24** |

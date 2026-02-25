# Spec NNN: Feature Name

## Feature: One-Line Description

### Overview

2-4 sentences. What does this feature do? Why does it matter? What problem does it solve?
Link to the architectural decision or research if relevant (e.g., "see docs/decisions/0001-federated-over-unified.md").

### User Stories

- As a [role], I want [capability] so that [benefit].
- As a [role], I want [capability] so that [benefit].
- (2-4 stories max)

---

### Core Specifications

**SPEC-001: Component Name**

| Field | Value |
|-------|-------|
| Description | What this component does |
| Trigger | What causes it to run |
| Input | Data it receives (types, shapes) |
| Output | Data it produces (types, shapes) |
| Validation | Input constraints, edge cases |
| Auth Required | Yes/No |

Acceptance Criteria:
- [ ] Criterion 1 (testable, binary -- passes or fails)
- [ ] Criterion 2
- [ ] Criterion 3

---

### Data Structures

Show the actual JSON/Python shapes. Include example payloads.

```python
class ExampleModel(BaseModel):
    field_name: str
    field_value: int
```

```json
{
  "example_field": "example_value",
  "nested": {
    "key": 42
  }
}
```

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/path/to/file.py` | New | What this file does |
| `src/holus/path/to/existing.py` | Modified | What changes |
| `config/something.yaml` | New | Configuration for this feature |
| `tests/unit/test_feature.py` | New | Unit tests |

---

### Edge Cases & Error Handling

**EDGE-001: Descriptive name**
- Scenario: What happens
- Expected behavior: What the system does
- Error message: Exact string shown (API response + internal log)
- Recovery: How the user or system recovers

**EDGE-002: Descriptive name**
- Scenario: What happens
- Expected behavior: What the system does
- Error message: Exact string shown
- Recovery: How to recover

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Latency | < Xms | Timestamp before/after in Langfuse trace |
| Throughput | N/sec | Count over time window |
| Cost | < $X/day | Langfuse cost dashboard |

---

### Security Considerations

- Bullet points on privacy, auth, data exposure.

---

### Out of Scope

- What this spec explicitly does NOT cover (prevents scope creep).

---

### Related Specs

- [NNN-name.md](./NNN-name.md) -- relationship description

---

**Last Updated:** YYYY-MM-DD
**Status:** Draft | Not Started | In Progress | Implemented
**Owner:** Name

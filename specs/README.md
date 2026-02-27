# Specs -- Holus

Forward-looking implementation blueprints. Written BEFORE coding a feature.

**Naming:** 3-digit zero-padded, assigned chronologically. Numbers are never reused.
**Template:** See [000-template.md](000-template.md).
**How to write specs:** See [HOW-TO-WRITE-PERFECT-SPECS](../../HOW-TO-WRITE-PERFECT-SPECS.md).

---

## Backend / Infrastructure

| #   | Spec                                                             | Type    | Status      |
| --- | ---------------------------------------------------------------- | ------- | ----------- |
| 000 | [Spec Template](000-template.md)                                 | --      | --          |
| 001 | [Core Infrastructure](001-core-infrastructure.md)                | Backend | Partial     |
| 002 | ~~Trading Agent~~ (removed — trading is separate from Holus)     | Backend | Deprecated  |
| 003 | [Content Pipeline](003-content-pipeline.md)                      | Backend | Not Started |
| 004 | Coding Agent Integration                                         | Backend | Not Started |
| 005 | Pilaster Agent                                                   | Backend | Not Started |
| 006 | Coordinator Agent                                                | Backend | Not Started |
| 007 | Self-Improvement Loop                                            | Backend | Not Started |

## Full-Stack

| #   | Spec                                                             | Type       | Status      |
| --- | ---------------------------------------------------------------- | ---------- | ----------- |
| 008 | Kill Switch and Guardrails                                       | Full-Stack | Not Started |

## Autonomous Marketing Sprint (Priority)

| #   | Spec                                                             | Type    | Status      |
| --- | ---------------------------------------------------------------- | ------- | ----------- |
| 009 | [Autonomous Build System](009-autonomous-build-system.md)        | Backend | Not Started |
| 010 | [Marketing Agent](010-marketing-agent.md)                        | Backend | Not Started |
| 011 | [Social Media Integration](011-social-media-integration.md)      | Backend | Not Started |
| 012 | [Knowledge & Learning](012-knowledge-learning.md)                | Backend | Not Started |
| 013 | [Scheduling & Runtime](013-scheduling-runtime.md)                | Backend | Not Started |

---

## Spec Status Legend

- **Not Started** -- Spec written, implementation has not begun
- **In Progress** -- Actively being implemented
- **Implemented** -- Code shipped, tests passing
- **Deprecated** -- Superseded by a later spec (link to replacement)

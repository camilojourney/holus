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
| 003 | ~~[Content Pipeline](003-content-pipeline.md)~~ (superseded by 010-016) | Backend | Deprecated  |
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
| 009 | [Autonomous Build System](009-autonomous-build-system.md)        | Backend | Partial     |
| 010 | [Marketing Agent](010-marketing-agent.md)                        | Backend | Implemented |
| 011 | ~~[Social Media Integration](011-social-media-integration.md)~~ (superseded by 016) | Backend | Deprecated  |
| 012 | [Knowledge & Learning](012-knowledge-learning.md)                | Backend | Implemented |
| 013 | [Scheduling & Runtime](013-scheduling-runtime.md)                | Backend | Partial     |

## Silo Integration Specs

| #   | Spec                                                             | Type    | Status      |
| --- | ---------------------------------------------------------------- | ------- | ----------- |
| 014 | [Genpeli Integration](014-genpeli-integration.md)                | Backend | Partial     |
| 015 | [Pilaster Integration](015-pilaster-integration.md)              | Backend | Partial     |
| 016 | [Social Media Integration V2](016-social-media-integration-v2.md) | Backend | Partial     |

## Authority Engine Sprint

| #   | Spec                                                             | Type    | Status      |
| --- | ---------------------------------------------------------------- | ------- | ----------- |
| 017 | [Authority Engine Agent Update](017-authority-engine-agent-update.md) | Backend | Implemented |

## Resilient Infrastructure

| #   | Spec                                                             | Type    | Status      |
| --- | ---------------------------------------------------------------- | ------- | ----------- |
| 027 | [Resilient Agent Loop](027-resilient-agent-loop.md)              | Backend | Implemented |

## Observatory

| #   | Spec                                                             | Type       | Status      |
| --- | ---------------------------------------------------------------- | ---------- | ----------- |
| 028 | [Observatory API](028-observatory-api.md)                        | Backend    | Implemented |
| 029 | [Observatory Frontend](029-observatory-frontend.md)              | Full-Stack | Partial     |

## Agent Intelligence Sprint

| #   | Spec                                                             | Type    | Status  |
| --- | ---------------------------------------------------------------- | ------- | ------- |
| 030 | [Agent Registry & Self-Improvement Wiring](030-agent-registry-self-improvement.md) | Backend | Implemented |

## LinkedIn Content Pipeline

| #   | Spec                                                             | Type    | Status      |
| --- | ---------------------------------------------------------------- | ------- | ----------- |
| 031 | [LinkedIn Content Pipeline](031-linkedin-content-pipeline.md)    | Backend | Implemented |
| 032 | [Humanization Gate](032-humanization-gate.md)                    | Full-Stack | Implemented |
| 033 | [Animated Infographics](033-animated-infographics.md)            | Backend    | Implemented |

## Visual Pipeline

| #   | Spec                                                             | Type    | Status      |
| --- | ---------------------------------------------------------------- | ------- | ----------- |
| 034 | [Creative Tool Registry](034-creative-tool-registry.md)          | Backend | Not Started |

---

## Spec Status Legend

- **Not Started** -- Spec written, implementation has not begun
- **Partial** -- Some components implemented, others pending
- **In Progress** -- Actively being implemented
- **Implemented** -- Code shipped, tests passing
- **Deprecated** -- Superseded by a later spec (link to replacement)

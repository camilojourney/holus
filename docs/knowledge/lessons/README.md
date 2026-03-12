# Content Lessons Log

This directory tracks what we've actually learned from running content experiments.
Holus reads this before making content decisions in the ReAct loop.

---

## Format

Each lesson is a YAML entry in `content-lessons.yaml`:

```yaml
lessons:
  - date: YYYY-MM-DD
    what_we_tried: >
      Short description of the experiment or change.
      What post, prompt version, or routing decision was tested.
    what_happened: >
      Measured outcome. Be specific: reach numbers, engagement rate,
      save rate, comment count. Not "it did well" — "reach 4,200, 3x baseline".
    what_changed: >
      What was updated as a result. Which prompt file, routing rule,
      platform config, or strategy assumption changed.
    applied_to:
      - prompt: specialists/carousel.yaml    # if a prompt was updated
      - platform: platforms/linkedin.md      # if a platform rule was updated
      - routing: routing.yaml               # if routing logic changed
      - strategy: MEMORY.md                 # if a top-level strategy shifted
```

---

## When to Add a Lesson

- After any A/B test result (two variants posted, measured difference)
- After a prompt update that was prompted by observed performance
- After a routing change based on platform behavior
- After any week where one content type significantly outperformed or underperformed

## Who Adds Lessons

- The marketing agent writes a draft lesson entry after each weekly cycle report
- Camilo reviews and approves before it becomes canonical
- Judge agent can flag lessons that contradict earlier entries (flag, don't delete)

---

## Reading Order for the Agent

1. Read `content-lessons.yaml` — scan for lessons relevant to the current platform + pillar
2. Cross-reference with `platforms/linkedin.md` (or relevant platform file)
3. Lessons override general platform knowledge when there's a conflict — we trust measured results over assumptions

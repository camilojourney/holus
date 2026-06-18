import {
  Callout,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

export default function HolusUserCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="warning">P0</Pill>
          <Text size="small" tone="tertiary">holus - block 01 - user</Text>
        </Row>
        <H1>User and journey</H1>
        <Text tone="secondary">
          Holus exists to turn one thought from a person or online source into a
          platform-native content set: text, image, carousel, review state,
          scheduled post, publish result, and learning signal.
        </Text>
      </Stack>

      <H2>Personas</H2>
      <Table
        headers={["Persona", "Job", "Needs", "Success signal"]}
        rows={[
          [
            "Solo founder / operator",
            "Turn a raw thought into credible social content",
            "Thought intake, useful variants, visuals, approvals, scheduling, and learning in one loop",
            "One thought reliably becomes a reviewed content set",
          ],
          [
            "Marketing strategist agent",
            "Normalize thoughts, plan content sets, adapt platforms, evaluate, and learn",
            "Source context, platform rules, visual specs, guardrails, and prompt memory",
            "Decisions logged to trajectory with judge scores and rationale",
          ],
          [
            "Human reviewer",
            "Approve, humanize, reject, or publish queued content",
            "Clear queue state, edit-distance guard, and safe publish path",
            "No publish action happens without the configured approval gate",
          ],
        ]}
      />

      <H2>Primary journey</H2>
      <Table
        headers={["Step", "Actor", "System action", "Artifact"]}
        rows={[
          ["1", "Person or web source", "Submit a thought as text or URL", "ThoughtSource"],
          ["2", "Holus", "Normalize source into a usable thought and source metadata", "Thought"],
          ["3", "Holus", "Plan one content set and activated platforms", "ContentSet + PlatformActivation"],
          ["4", "Specialists", "Generate platform variants and visual specs", "ContentVariant + VisualAsset"],
          ["5", "Judges", "Evaluate copy, visual fit, brand voice, and safety", "ReviewDecision"],
          ["6", "Human", "Approve, reject, schedule, or publish explicitly", "ScheduleRequest"],
          ["7", "Holus Social API", "Schedule/post and own platform analytics", "PublishResult + PerformanceSnapshot"],
          ["8", "Holus", "Log trajectory and extract weekly lessons", "trajectory.jsonl + MEMORY.md"],
        ]}
        striped
      />

      <H2>Failure and confusion points</H2>
      <Table
        headers={["Point", "Risk", "Current guardrail"]}
        rows={[
          ["Publishing", "Agent posts without human review", "content approval requires humanization and approval in Phase 1"],
          ["Silo boundaries", "Holus starts owning platform accounts or historical analytics", "Holus Social API owns publishing and analytics; Holus stores only queue/source metadata"],
          ["Repo identity", "Older docs frame Holus as a broad AI OS", "current AGENTS instructions and ARCHITECTURE.md define marketing-only scope"],
          ["Trading", "Marketing system touches pythia or milo", "hard stop in AGENTS instructions and docs"],
        ]}
        rowTone={[undefined, undefined, "warning", "warning"]}
      />

      <Callout tone="success" title="Success definition">
        Phase 1 success is one reliable Thought Studio loop: ingest a thought,
        create text/image/carousel variants, require review, schedule or publish
        through Holus Social API, and log enough trajectory to improve.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "Activation, retention, content throughput, approval latency",
              "No live Holus product-analytics dashboard registered yet",
              "python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/skills/systems-canvas/scripts/audit_dashboards.py /Users/mini/.openclaw/workspace/github/holus holus",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: docs/vision.md, ARCHITECTURE.md, config/content.yaml, AGENTS instructions - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

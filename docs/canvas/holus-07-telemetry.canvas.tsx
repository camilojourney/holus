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

export default function HolusTelemetryCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="info">P1</Pill>
          <Text size="small" tone="tertiary">holus - block 07 - telemetry</Text>
        </Row>
        <H1>Telemetry plan</H1>
        <Text tone="secondary">
          Telemetry should prove the marketing loop is producing useful content
          safely, not just that agents are busy.
        </Text>
      </Stack>

      <H2>Events to track</H2>
      <Table
        headers={["Event", "Meaning", "When fired", "Owner", "Category"]}
        rows={[
          ["cycle_started", "One marketing run began", "before health check", "MarketingAgent", "lifecycle"],
          ["preflight_blocked", "Cycle cannot proceed safely", "blocking health check fails", "core.health", "failure"],
          ["thought_ingested", "Text or URL source entered Thought Studio", "from-thought route accepts request", "ThoughtContentPipeline", "input"],
          ["thought_normalized", "Source became usable thought text", "normalize_source completes", "ThoughtContentPipeline", "input"],
          ["content_set_planned", "Platform activations were selected", "planning completes", "idea-planner", "success"],
          ["content_variant_generated", "A platform-native variant was produced", "queue record is written", "writer/adapters", "success"],
          ["visual_rendered", "Attachment was created", "render phase emits PNG/PDF path", "Holus visual engine", "success"],
          ["judge_evaluated", "Content received domain score", "judge returns verdict", "JudgeAgent", "quality"],
          ["humanized", "Human edit accepted within distance limit", "content_queue.humanize", "human reviewer", "control"],
          ["approved", "Content can be published", "content_queue.approve", "human reviewer", "control"],
          ["scheduled", "Holus Social API accepted schedule request", "explicit schedule endpoint succeeds", "Holus Social API", "success"],
          ["published", "Holus Social API accepted publish request", "explicit publish endpoint succeeds", "Holus Social API", "success"],
          ["rejected", "Human or judge rejected content", "reject path", "reviewer", "quality"],
          ["learning_extracted", "Patterns updated from trajectory", "weekly learning loop", "knowledge-keeper", "learning"],
        ]}
        striped
      />

      <H2>Metrics by class</H2>
      <Table
        headers={["Class", "Metric", "Source", "Target or interpretation"]}
        rows={[
          ["Success", "content pieces generated/week", "content queue + trajectory", "Phase 1 target: 4+ pieces/week"],
          ["Success", "thoughts converted to content sets/week", "content queue + trajectory", "Core product activation metric"],
          ["Success", "published pieces/month", "Holus Social API + trajectory", "Phase 2 target: 30+ pieces/month"],
          ["Quality", "judge pass rate", "eval_history + trajectory", "Watch low pass rate by agent/category"],
          ["Quality", "human rejection rate after judge PASS", "trajectory human feedback", "Judge calibration alert"],
          ["Failure", "consecutive failed cycles", "trajectory", "3 failures can trigger kill switch / pause"],
          ["Failure", "malformed queue or JSONL count", "API loaders", "Should be zero; skip malformed but report"],
          ["Cost", "tokens and cost by agent", "Claude client + Langfuse", "Vision target under $500/month"],
          ["Latency", "p50/p95 generation latency", "Langfuse/API tracing", "Needed before automation scale"],
          ["Freshness", "last trajectory and queue update age", "file mtimes", "Watchdog alerts on silence"],
          ["Engagement", "platform engagement per content type", "Holus Social API", "Never store permanently in Holus"],
        ]}
      />

      <Callout tone="warning" title="Metric boundary">
        Platform analytics are not Holus storage. Holus should record decisions and
        references, then ask Holus Social API for live engagement and top-post
        truth when planning the next cycle.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "Event volume, conversion through queue, quality, cost, freshness",
              "Observatory partial coverage; PostHog/Langfuse/Grafana not registered",
              "GET /api/v1/metrics; GET /api/v1/evaluations/summary; GET /api/v1/health",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: docs/vision.md, src/holus/api/routes/health.py, trajectory.py, learning_loop.py - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

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

export default function HolusUXCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="warning">P0</Pill>
          <Text size="small" tone="tertiary">holus - block 02 - ux</Text>
        </Row>
        <H1>UX and screens</H1>
        <Text tone="secondary">
          Thought Studio is the primary workflow. The Observatory should let an
          operator ingest one thought, review the generated content set, approve or
          schedule items, and see what Holus Social API returned.
        </Text>
      </Stack>

      <H2>Operator surfaces</H2>
      <Table
        headers={["Surface", "Entry", "Primary action", "Key info shown"]}
        rows={[
          ["CLI", "just generate", "Run one content cycle without publishing", "new files in data/content-queue"],
          ["API", "POST /api/v1/content/from-thought", "Create a content set from text or URL", "group_id, variants, source metadata"],
          ["CLI", "just review-content", "Inspect pending content", "piece id, platform, product, status"],
          ["CLI", "just approve-content <id>", "Approve one humanized piece", "status transition result"],
          ["CLI/API", "publish or schedule endpoint", "Explicitly call Holus Social API after approval", "publish id, schedule id, dry-run payload"],
          ["MCP", "holus_queue/list/approve/reject/publish", "Expose queue control to agents", "queue status and publish result"],
        ]}
      />

      <H2>Observatory screens</H2>
      <Table
        headers={["Route", "Primary action", "Key information", "Empty/loading/error state"]}
        rows={[
          ["/", "Scan live KPIs and trajectory", "metrics, health grid, trajectory feed", "loading.tsx and ErrorBanner"],
          ["/agents", "Find agent status", "AGENTS.yaml metadata plus trajectory-derived runs", "demo data fallback in frontend lib"],
          ["/agents/[id]", "Inspect one agent", "role, model tier, run count, score dimensions", "not-found/error through API state"],
          ["/content", "Run and review Thought Studio", "composer, kanban, content details, visuals, approval state", "empty queue count from API"],
          ["/evaluations", "Track judge quality", "eval history, pass rate, score trend", "eval_history missing is degraded"],
          ["/knowledge", "Browse memory and lessons", "MEMORY.md, knowledge/current, lessons.json", "missing file warnings"],
          ["/health", "Check runtime health", "kill switch, trajectory, queue, eval file state", "degraded component cards"],
          ["/results", "Review growth output", "published/content growth signals", "no trajectory message"],
          ["/engagement", "Inspect engagement", "platform and post engagement views", "demo/static fallback"],
          ["/followers", "Inspect audience growth", "channel acquisition and churn", "demo/static fallback"],
          ["/about", "Explain the system", "architecture narrative and stack", "static page"],
        ]}
        striped
      />

      <H2>Navigation model</H2>
      <Table
        headers={["From", "To", "Why"]}
        rows={[
          ["Home", "Health", "A red or degraded KPI needs root-cause context"],
          ["Home", "Content", "Throughput or queue count needs approval action"],
          ["Content", "Evaluations", "A rejected or weak item needs judge detail"],
          ["Agents", "Agent detail", "A failing specialist needs role and rubric context"],
          ["Knowledge", "Content", "A lesson should inform the next queued content review"],
        ]}
      />

      <Callout tone="warning" title="Open question">
        The old read-only mental model is no longer enough. Thought Studio needs
        intentional write controls, but publish/schedule actions must stay explicit
        and visible before Holus Social API receives a live request.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "Per-screen funnel, queue drop-off, approval latency",
              "No PostHog or registered Observatory live surface in systems-canvas registry",
              "Run Observatory manually: uv run uvicorn holus.api.app:app --reload and pnpm dev in observatory/frontend",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: observatory/frontend/src/app, src/holus/api/app.py, justfile - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

import {
  Callout,
  H1,
  H2,
  Link,
  Pill,
  Row,
  Stack,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

export default function HolusDashboardMapCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="info">P1</Pill>
          <Pill tone="warning">draft</Pill>
          <Text size="small" tone="tertiary">holus - block 09 - dashboard-map</Text>
        </Row>
        <H1>Dashboard map</H1>
        <Text tone="secondary">
          The dashboard audit found no Holus entry in the systems-canvas dashboard
          registry. This block records the intended live surfaces and the commands to
          validate them.
        </Text>
      </Stack>

      <Callout tone="warning" title="Audit snapshot">
        audit_dashboards.py result on 2026-05-31: No registry entry for holus.
        Add Holus to references/dashboard-registry.json before treating these links
        as live operational truth.
      </Callout>

      <H2>Block to live-surface wiring</H2>
      <Table
        headers={["Block", "Metric to prove", "Surface", "Status", "Refresh command"]}
        rows={[
          ["01 User", "activation, retention, approval latency", "PostHog or Observatory metrics", "missing", "GET /api/v1/metrics"],
          ["02 UX", "per-screen funnel and drop-off", "PostHog or frontend analytics", "missing", "Instrument Observatory pages"],
          ["03 Data model", "queue counts, JSONL freshness, malformed rows", "Observatory API", "partial", "GET /api/v1/health; GET /api/v1/content"],
          ["04 Database", "Redis health, file growth, storage size", "Grafana/infra monitor", "missing", "just preflight; infrastructure/prometheus.yml"],
          ["05 Logic", "phase errors, API latency, queue depth", "Observatory + logs", "partial", "GET /api/v1/trajectory; tail logs"],
          ["06 AI", "cost, latency, eval score, traces", "Langfuse + evaluations page", "partial", "GET /api/v1/evaluations/summary"],
          ["07 Telemetry", "event volume, conversion, cost, quality", "Observatory + Langfuse + Holus Social API analytics", "partial", "GET /api/v1/metrics"],
          ["08 Ops", "runtime health, plists, incidents", "Fleet Command + health route", "partial", "just validate-plists; GET /api/v1/health"],
          ["09 Dashboard map", "link completeness and freshness", "systems-canvas audit", "missing registry", "python3 .../audit_dashboards.py /Users/mini/.openclaw/workspace/github/holus holus"],
          ["10 Control", "test pass rate, eval history, approval actions", "test output + Observatory", "partial", "just check; GET /api/v1/evaluations"],
        ]}
        rowTone={["warning", "warning", "info", "warning", "info", "info", "info", "info", "warning", "info"]}
        striped
      />

      <H2>Known live or near-live surfaces</H2>
      <Table
        headers={["Surface", "Open / run", "Answers", "Gap"]}
        rows={[
          ["Observatory API", "uv run uvicorn holus.api.app:app --reload", "health, metrics, trajectory, content, agents, evaluations", "not registered in systems-canvas dashboard registry"],
          ["Observatory frontend", "pnpm dev in observatory/frontend", "operator dashboard pages", "demo fallback needs clear live/demo state"],
          ["Fleet Command", "http://127.0.0.1:8765 after rebuild", "fleet-level project health", "Holus-specific dashboard entry missing"],
          ["Langfuse", "external/self-hosted if env configured", "AI traces, cost, latency", "no URL recorded in repo"],
          ["Holus Social API", "Holus Social API MCP/REST", "platform analytics and posting queue", "not permanently stored in Holus"],
          ["Prometheus/Grafana", "infrastructure/prometheus.yml and alerts.yml", "infra metrics when wired", "no running surface confirmed"],
        ]}
      />

      <H2>Registry work to do</H2>
      <Table
        headers={["Task", "File", "Expected effect"]}
        rows={[
          ["Add Holus surfaces", "~fleet-system/system/skills/systems-canvas/references/dashboard-registry.json", "audit_dashboards.py can report real status"],
          ["Document dashboard hashes/URLs", "~fleet-system/system/skills/systems-canvas/references/dashboard-map.md", "blocks link to exact live surfaces"],
          ["Clarify Observatory live/demo mode", "observatory/frontend/src/lib/api.ts", "operators can trust whether data is real"],
          ["Add freshness checks", "Holus dashboard or API", "dashboard flags stale trajectory, queue, and eval files"],
        ]}
      />

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "Dashboard registration and surface health",
              "No live dashboard yet",
              "python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/skills/systems-canvas/scripts/audit_dashboards.py /Users/mini/.openclaw/workspace/github/holus holus",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Wiring source: dashboard-map.md and dashboard-registry.json. Fleet Command default:
          {" "}
          <Link href="http://127.0.0.1:8765#projects">http://127.0.0.1:8765#projects</Link>
        </Text>
      </Stack>
    </Stack>
  );
}

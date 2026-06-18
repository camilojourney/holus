import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Table,
  Text,
  computeDAGLayout,
  useHostTheme,
} from "cursor/canvas";

function RuntimeMap() {
  const theme = useHostTheme();
  const nodes = [
    { id: "launchd" },
    { id: "agent" },
    { id: "redis" },
    { id: "queue" },
    { id: "api" },
    { id: "frontend" },
    { id: "silos" },
    { id: "langfuse" },
  ];
  const edges = [
    { from: "launchd", to: "agent" },
    { from: "agent", to: "redis" },
    { from: "agent", to: "queue" },
    { from: "agent", to: "silos" },
    { from: "agent", to: "langfuse" },
    { from: "api", to: "queue" },
    { from: "api", to: "redis" },
    { from: "frontend", to: "api" },
  ];
  const labels: Record<string, string> = {
    launchd: "launchd",
    agent: "Holus agent",
    redis: "Redis",
    queue: "File state",
    api: "FastAPI",
    frontend: "Next.js",
    silos: "MCP silos",
    langfuse: "Langfuse",
  };
  const layout = computeDAGLayout({
    nodes,
    edges,
    direction: "horizontal",
    nodeWidth: 112,
    nodeHeight: 42,
    rankGap: 54,
    nodeGap: 20,
    padding: 18,
  });

  return (
    <svg width="100%" viewBox={`0 0 ${layout.width} ${layout.height}`} role="img">
      {layout.edges.map((edge) => (
        <line
          key={`${edge.from}-${edge.to}`}
          x1={edge.sourceX}
          y1={edge.sourceY}
          x2={edge.targetX}
          y2={edge.targetY}
          stroke={theme.stroke.primary}
          strokeWidth={1.5}
        />
      ))}
      {layout.nodes.map((node) => (
        <g key={node.id}>
          <rect
            x={node.x}
            y={node.y}
            width={112}
            height={42}
            rx={6}
            fill={theme.fill.secondary}
            stroke={theme.stroke.secondary}
          />
          <text
            x={node.x + 56}
            y={node.y + 22}
            fill={theme.text.primary}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={12}
          >
            {labels[node.id]}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default function HolusOpsCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="neutral">P2</Pill>
          <Text size="small" tone="tertiary">holus - block 08 - ops</Text>
        </Row>
        <H1>Ops and runtime</H1>
        <Text tone="secondary">
          Holus runs as a local/headless marketing system with launchd automation,
          file-backed state, optional Redis, external silos, and a read-only dashboard.
        </Text>
      </Stack>

      <Card>
        <CardHeader>Runtime service map</CardHeader>
        <CardBody>
          <RuntimeMap />
        </CardBody>
      </Card>

      <H2>Services</H2>
      <Table
        headers={["Service", "Tech", "Environment", "Command", "Operational concern"]}
        rows={[
          ["Marketing agent", "Python + LangGraph", "local/server", "just run or just run-marketing", "preflight, run lock, trajectory writes"],
          ["Holus MCP", "FastMCP", "local/server", "just run-mcp", "queue control and publish bypass review"],
          ["Observatory API", "FastAPI", "local/server", "uv run uvicorn holus.api.app:app", "read-only data path and CORS"],
          ["Observatory frontend", "Next.js 15", "local/Vercel scaffold", "pnpm dev in observatory/frontend", "demo fallback vs live API clarity"],
          ["Redis", "Redis pub/sub + streams", "local/docker/env", "docker compose up -d if configured", "kill switch and event bus"],
          ["Langfuse", "external/self-hosted", "env configured", "provider setup outside repo", "trace completeness and cost tracking"],
          ["Silos", "MCP/REST", "external repos", "silo-specific servers", "Holus waits if MCP is down"],
        ]}
        striped
      />

      <H2>Automation jobs</H2>
      <Table
        headers={["Job", "File", "Purpose", "Validation"]}
        rows={[
          ["Marketing", "infra/launchd/com.holus.marketing.plist", "scheduled marketing cycles", "just validate-plists"],
          ["Health", "infra/launchd/com.holus.health.plist", "scheduled health checks", "just schedule-test"],
          ["Improve", "infra/launchd/com.holus.improve.plist", "self-improvement cycle", "just validate-plists"],
          ["Analytics", "infra/launchd/com.holus.analytics.plist", "post-publish engagement collection", "just validate-plists"],
          ["Builder", "infra/launchd/com.holus.builder.plist", "autonomous build sprint support", "just sprint-status"],
        ]}
      />

      <H2>Security and incident path</H2>
      <Table
        headers={["Area", "Rule", "Action"]}
        rows={[
          ["Secrets", "Use .env and env vars only", "never write keys to config or commits"],
          ["Guardrails", "config/guardrails.yaml requires explicit approval", "do not modify during canvas work"],
          ["Products/platforms", "config/products.yaml changes require approval", "propose before changing targeting"],
          ["Publishing", "Phase 1 requires human review", "queue, humanize, approve, then publish"],
          ["Trading isolation", "Never access pythia or milo", "hard stop and escalate"],
          ["Incident", "3 consecutive failures or kill switch active", "pause automation, inspect health, trajectory, queue, and silo status"],
        ]}
        rowTone={[undefined, "warning", "warning", "warning", "warning", "warning"]}
      />

      <Callout tone="info" title="Runbook pointer">
        Start with just preflight, just validate-plists, /api/v1/health, trajectory tail,
        queue inspection, and silo MCP connectivity before changing prompts or runtime config.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "Uptime, incidents, deploys, plist health, queue freshness",
              "Fleet Command can show project health, but Holus has no registered dashboard entry",
              "python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/apps/fleet-command-dashboard/server.py --rebuild --port 8765",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: justfile, infra/launchd, infrastructure/*.yml, CLAUDE.md - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

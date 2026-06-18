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

function FlowGraph() {
  const theme = useHostTheme();
  const nodes = [
    { id: "source" },
    { id: "normalize" },
    { id: "plan" },
    { id: "variants" },
    { id: "visuals" },
    { id: "evaluate" },
    { id: "review" },
    { id: "publish" },
    { id: "learn" },
  ];
  const edges = [
    { from: "source", to: "normalize" },
    { from: "normalize", to: "plan" },
    { from: "plan", to: "variants" },
    { from: "variants", to: "visuals" },
    { from: "visuals", to: "evaluate" },
    { from: "evaluate", to: "review" },
    { from: "review", to: "publish" },
    { from: "publish", to: "learn" },
    { from: "learn", to: "source" },
  ];
  const labels: Record<string, string> = {
    source: "Thought source",
    normalize: "Normalize",
    plan: "Plan set",
    variants: "Variants",
    visuals: "Visuals",
    evaluate: "Evaluate",
    review: "Review",
    publish: "Holus Social API",
    learn: "Learn",
  };
  const layout = computeDAGLayout({
    nodes,
    edges,
    direction: "horizontal",
    nodeWidth: 140,
    nodeHeight: 42,
    rankGap: 56,
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
          strokeDasharray={edge.isBackEdge ? "4 4" : undefined}
        />
      ))}
      {layout.nodes.map((node) => (
        <g key={node.id}>
          <rect
            x={node.x}
            y={node.y}
            width={140}
            height={42}
            rx={6}
            fill={theme.fill.secondary}
            stroke={theme.stroke.secondary}
          />
          <text
            x={node.x + 70}
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

export default function HolusLogicCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="info">P1</Pill>
          <Text size="small" tone="tertiary">holus - block 05 - logic</Text>
        </Row>
        <H1>Logic and APIs</H1>
        <Text tone="secondary">
          The central behavior is Thought Studio: source -> normalize -> plan
          content set -> generate variants -> render visuals -> review ->
          schedule/post via Holus Social API -> learn.
        </Text>
      </Stack>

      <Card>
        <CardHeader>Thought Studio loop</CardHeader>
        <CardBody>
          <FlowGraph />
        </CardBody>
      </Card>

      <H2>Main backend steps</H2>
      <Table
        headers={["Phase", "Module", "Inputs", "Output", "Failure behavior"]}
        rows={[
          ["Ingest", "api.routes.content", "thought, source_type, source_url, platforms", "ThoughtSource", "400 unsupported channel; 502 URL fetch failure"],
          ["Normalize", "ThoughtContentPipeline", "text or URL extraction", "Thought", "deterministic extraction fallback remains local/dev only"],
          ["Plan", "idea-planner/platform config", "thought + requested activations", "ContentSet", "reject unknown activations instead of silently dropping"],
          ["Generate", "writer/adapters", "platform rules + voice", "ContentVariant", "quality gate and platform char limits"],
          ["Render", "Holus visual engine", "visual_spec", "PNG/PDF attachment path", "content can continue with local fallback renderer"],
          ["Evaluate", "JudgeAgent/evaluators", "generated content", "judge score + trajectory entries", "consecutive failures can pause via kill switch"],
          ["Review", "content queue/API", "piece id + local decision", "approved/rejected/scheduled status", "PATCH never posts silently"],
          ["Publish/schedule", "HolusSocialAPIClient", "approved content + platforms payload", "publish id or schedule id", "dry-run shows payload before live call"],
        ]}
        striped
      />

      <H2>API route groups</H2>
      <Table
        headers={["Route group", "Prefix", "Purpose", "Auth / permission note"]}
        rows={[
          ["agents", "/api/v1/agents", "Agent registry plus trajectory-derived activity", "read-only surface"],
          ["alerts", "/api/v1/alerts", "Evaluation anomaly checks", "read-only surface"],
          ["config", "/api/v1/config", "Expose selected config for Observatory", "avoid secrets"],
          ["trajectory", "/api/v1/trajectory", "Paginated JSONL and SSE stream", "read-only event stream"],
          ["content", "/api/v1/content", "Thought intake, queue/detail views, explicit publish/schedule controls", "human review stays default"],
          ["evaluations", "/api/v1/evaluations", "Evaluation history and summaries", "read-only surface"],
          ["knowledge", "/api/v1/knowledge", "Memory, lessons, knowledge files", "read-only surface"],
          ["health/results/improvement", "/api/v1/*", "KPIs, growth, self-improvement analytics", "read-only analytics"],
          ["telegram gate", "/api/telegram", "Approval gate stubs", "future operator-notification wiring"],
          ["ingest", "/api/holus", "Legacy text/URL/file ingest extraction", "video remains deferred behind Genpeli"],
        ]}
      />

      <H2>MCP tools exposed by Holus</H2>
      <Table
        headers={["Tool", "Action", "Boundary"]}
        rows={[
          ["holus_queue", "enqueue text for human review", "writes local queue only"],
          ["holus_list_queue", "list humanizable queue items", "read queue only"],
          ["holus_approve", "humanize if needed, then approve", "local status transition"],
          ["holus_reject", "reject one piece with optional reason", "local status transition"],
          ["holus_publish", "publish immediately through Holus Social API", "requires HOLUS_SOCIAL_API_KEY or legacy POSTING_API_KEY; bypass risk needs approval policy review"],
        ]}
        rowTone={[undefined, undefined, undefined, undefined, "warning"]}
      />

      <Callout tone="warning" title="Failure modes to keep visible">
        Holus Social API down, missing posting key, malformed queue files, malformed JSONL,
        model output validation errors, and non-humanized approval attempts should all
        remain visible in trajectory and health surfaces.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "API latency, error rate, queue depth, phase failure count",
              "No Grafana/Datadog surface registered; Observatory exposes health/metrics",
              "GET /api/v1/health; GET /api/v1/metrics; tail .self-improvement/memory/trajectory.jsonl",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: src/holus/agents/marketing/agent.py, src/holus/api/app.py, src/holus/mcp/server.py - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

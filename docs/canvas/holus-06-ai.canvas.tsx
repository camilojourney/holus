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

function AgentGraph() {
  const theme = useHostTheme();
  const nodes = [
    { id: "strategist" },
    { id: "specialists" },
    { id: "evaluators" },
    { id: "ops" },
    { id: "trajectory" },
    { id: "learning" },
  ];
  const edges = [
    { from: "strategist", to: "specialists" },
    { from: "specialists", to: "evaluators" },
    { from: "evaluators", to: "trajectory" },
    { from: "ops", to: "trajectory" },
    { from: "trajectory", to: "learning" },
    { from: "learning", to: "strategist" },
  ];
  const labels: Record<string, string> = {
    strategist: "Strategist",
    specialists: "25 specialists",
    evaluators: "7 judges",
    ops: "2 ops agents",
    trajectory: "Trajectory",
    learning: "Learning loop",
  };
  const layout = computeDAGLayout({
    nodes,
    edges,
    direction: "horizontal",
    nodeWidth: 122,
    nodeHeight: 44,
    rankGap: 52,
    nodeGap: 24,
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
            width={122}
            height={44}
            rx={6}
            fill={theme.fill.secondary}
            stroke={theme.stroke.secondary}
          />
          <text
            x={node.x + 61}
            y={node.y + 23}
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

export default function HolusAICanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="warning">P0</Pill>
          <Text size="small" tone="tertiary">holus - block 06 - ai</Text>
        </Row>
        <H1>AI and agents</H1>
        <Text tone="secondary">
          AI is the product core for Thought Studio: parse the source thought,
          build context, plan the content set, write platform-native variants,
          design visuals, guard voice, and judge quality before publishing.
        </Text>
      </Stack>

      <Card>
        <CardHeader>Agent routing loop</CardHeader>
        <CardBody>
          <AgentGraph />
        </CardBody>
      </Card>

      <H2>Agent inventory snapshot</H2>
      <Table
        headers={["Group", "Count", "Examples", "Role"]}
        rows={[
          ["Manager", "1", "marketing-strategist", "observe, reason, act, evaluate"],
          ["Written authority", "5", "hook-architect, storyteller, voice-guardian", "LinkedIn/text authority content"],
          ["Visual", "5", "carousel-architect, data-visualizer, visual-designer", "carousels, diagrams, visual consistency"],
          ["Thought pipeline", "5", "idea-injector, context-builder, idea-planner, voice-writer", "thought parsing, content-set planning, and post generation"],
          ["Future video", "3", "script-writer, brief-composer, caption-specialist", "deferred Genpeli/video adapter, not a current blocker"],
          ["Growth", "3", "lead-magnet-designer, comment-trigger-expert", "conversation and conversion mechanics"],
          ["Research", "4", "niche-researcher, audience-analyst", "topics, SEO, audience, competitors"],
          ["Repurposing", "3", "platform-adapter, bilingual-localizer, format-converter", "cross-platform variants"],
          ["Evaluators", "7", "written-content-judge, brand-safety-judge", "domain rubrics and safety gates"],
          ["Ops", "2", "security-sentinel, knowledge-keeper", "security and knowledge freshness"],
        ]}
        striped
      />

      <H2>AI feature matrix</H2>
      <Table
        headers={["Feature", "Role", "Model tier", "Prompt/source", "Tools", "Budget/SLO"]}
        rows={[
          ["Thought normalization", "ingest", "operational -> claude-sonnet-4-6 or deterministic", "idea-injector + context-builder", "source metadata, URL extraction", "Keep source lineage on every variant"],
          ["Content-set planning", "plan", "strategic/operational mix", "idea-planner + platform-adapter", "platform activations, platform config", "One group_id per thought"],
          ["Content generation", "generate", "operational -> claude-sonnet-4-6", "voice-writer + adapters", "content queue, platform config", "Text/image/carousel now; video deferred"],
          ["Visual generation", "render", "operational/local renderer", "visual-designer + carousel-architect", "Holus visual engine", "PNG/PDF in data/rendered-content"],
          ["Voice and brand checks", "evaluate/classify", "classification -> claude-sonnet-4-6", "voice-guardian and brand-safety-judge", "brand.yaml, anti-patterns", "Gate before approval"],
          ["Domain judging", "evaluate", "classification -> claude-sonnet-4-6", "7 evaluator prompt files", "trajectory logger", "Score every content output where applicable"],
          ["Prompt optimization", "learn", "strategic/operational mix", "config/prompts variants + learning loop", "trajectory, lessons, Langfuse", "Only after enough samples"],
          ["Social action planning", "act", "strategic/operational mix", "structured publish/schedule payloads", "Holus Social API", "Publishing requires approval policy"],
        ]}
      />

      <H2>Guardrails and fallbacks</H2>
      <Table
        headers={["Guardrail", "Where", "Fallback"]}
        rows={[
          ["Three-layer prompt resolution", "PromptLoader", "config/prompts -> agents/*.md -> Python fallback"],
          ["Pydantic boundary models", "marketing models and API models", "reject or fallback when output invalid"],
          ["Human approval gate", "content_queue + config/content.yaml", "queue, reject, or hold instead of direct posting"],
          ["Kill switch", "core.kill_switch / guardrails", "pause after failures or explicit operator action"],
          ["Silo isolation", "MCP clients and AGENTS rules", "wait when silo MCP is down"],
        ]}
      />

      <Callout tone="warning" title="Open question">
        Model IDs in config/models.yaml reference future-style names. Before live
        spend, verify proxy routing, real availability, cost accounting, and fallback
        behavior against the current provider inventory.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "AI cost, latency, eval score, trace completeness, model tier usage",
              "Langfuse planned/enabled in code; no registered Holus Langfuse dashboard link",
              "Use Langfuse when configured; GET /api/v1/evaluations; GET /api/v1/improvement/*",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: agents/AGENTS.yaml, config/models.yaml, docs/vision.md, src/holus/core/prompt_loader.py - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

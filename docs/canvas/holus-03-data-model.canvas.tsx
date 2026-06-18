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

export default function HolusDataModelCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="warning">P0</Pill>
          <Text size="small" tone="tertiary">holus - block 03 - data-model</Text>
        </Row>
        <H1>Data model</H1>
        <Text tone="secondary">
          Holus owns the thought-to-content lineage: source metadata, normalized
          thought, content set, platform variants, visual assets, review decisions,
          schedule requests, publish results, and learning artifacts.
        </Text>
      </Stack>

      <H2>Conceptual objects</H2>
      <Table
        headers={["Object", "Meaning", "Owner", "Created by", "Updated by", "Visibility"]}
        rows={[
          ["ThoughtSource", "Text or URL source that produced the thought", "Holus", "person/API/web source", "new intake request", "content queue"],
          ["Thought", "Normalized useful source text", "Holus", "ThoughtContentPipeline", "source extraction", "content queue"],
          ["ContentSet", "One group of generated outputs from one thought", "Holus", "ThoughtContentPipeline", "variant generation", "content queue"],
          ["PlatformActivation", "Requested channel such as linkedin_text or instagram_image", "Holus", "operator/API request", "platform config", "runtime"],
          ["ContentVariant", "Platform-native copy or carousel outline", "Holus", "writer/adapters", "review and publish flow", "content queue"],
          ["VisualAsset", "Rendered PNG/PDF path plus visual spec", "Holus", "Holus visual engine", "visual review choice", "data/rendered-content"],
          ["ReviewDecision", "Approve, reject, hold, or schedule locally", "Holus", "human/judge", "review route", "content queue"],
          ["ScheduleRequest", "Explicit future publish request", "Holus", "operator/API", "Holus Social API call", "content queue + API payload"],
          ["PublishResult", "Accepted publish response from Holus Social API", "Holus Social API", "Holus Social API", "explicit publish endpoint", "content queue reference"],
          ["PerformanceSnapshot", "Engagement and top-post truth", "Holus Social API", "Holus Social API", "platform analytics collector", "read via API/MCP only"],
          ["ProductDefinition", "What Pilaster, genpeli, and invoz mean as proof points", "Holus", "config/products.yaml", "human edits only", "repo"],
          ["BrandIdentity", "Voice, positioning, content pillars, anti-patterns", "Holus", "config/brand*.yaml", "human edits and planned prompt work", "repo"],
          ["AgentDefinition", "Agent role, type, prompt file, model tier, evaluator", "Holus", "agents/AGENTS.yaml", "human/spec work", "repo"],
          ["Prompt", "KERNEL-style role instructions for agents", "Holus", "agents/**/*.md", "human or optimizer promotion", "repo"],
          ["ContentDecision", "Strategy choice: product, platform, pillar, hook, format", "Holus", "marketing-strategist", "trajectory/evaluation loop", "repo runtime"],
          ["GeneratedPiece", "Generated social content and optional visual attachment", "Holus", "marketing agent/specialists", "review and publishing commands", "content queue"],
          ["QueuedContent", "Human approval state for one content item", "Holus", "content_queue.enqueue", "humanize/approve/reject/publish", "data/content-queue"],
          ["TrajectoryEntry", "Append-only event/audit/quality/cost record", "Holus", "agents, cycle state, evaluators", "append only", ".self-improvement/memory"],
          ["EvaluationResult", "Domain judge score and critique", "Holus", "JudgeAgent/evaluators", "append only", "eval history/trajectory"],
          ["ImageResult", "Future optional AI-image generation metadata", "Pilaster adapter", "pilaster", "pilaster", "future optional adapter"],
          ["VideoJob", "Future video edit job, preview, approval, delivery result", "Genpeli adapter", "genpeli", "genpeli", "deferred"],
        ]}
        striped
      />

      <H2>Relationships</H2>
      <Table
        headers={["Relationship", "Cardinality", "Lineage rule"]}
        rows={[
          ["ThoughtSource -> Thought", "one source normalizes to one useful thought", "source_type/source_url/source_raw_input stay with every queue item"],
          ["Thought -> ContentSet", "one thought creates one grouped content set", "group_id ties all variants together"],
          ["ContentSet -> ContentVariant", "one set contains many platform variants", "platform and content_type are stored per variant"],
          ["ContentVariant -> VisualAsset", "some variants render PNG/PDF assets", "rendered paths are attached, not embedded"],
          ["ReviewDecision -> ScheduleRequest", "approval can lead to scheduling", "PATCH review does not publish silently"],
          ["ScheduleRequest -> PublishResult", "explicit API call only", "payload uses platforms and records returned ids"],
          ["PublishResult -> PerformanceSnapshot", "many snapshots per published item", "snapshots stay in Holus Social API unless summarized"],
          ["ProductDefinition -> ContentDecision", "one product can seed many decisions", "product config is context, not analytics storage"],
          ["AgentDefinition -> Prompt", "one registry row points to one canonical prompt file", "PromptLoader may prefer config/prompts variant first"],
          ["ContentDecision -> GeneratedPiece", "one decision can become multiple platform variants", "decision reasoning is preserved with content"],
          ["GeneratedPiece -> QueuedContent", "one generated piece becomes one queue file per platform artifact", "queue file is the approval source of truth"],
          ["QueuedContent -> TrajectoryEntry", "many lifecycle events per content item", "approval, rejection, publishing, and feedback log append-only"],
          ["TrajectoryEntry -> MEMORY.md/lessons.json", "many entries feed weekly learning", "learning loop extracts patterns, not raw analytics copies"],
          ["Holus -> silos", "tool calls only", "MCP boundary forbids direct DB reads and package imports"],
        ]}
      />

      <Callout tone="warning" title="Data contract drift">
        The public AGENTS instructions say 5 agents in the summary table, while
        agents/AGENTS.yaml lists 35 agents. Treat agents/AGENTS.yaml as the source
        of truth for actual agent definitions.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "Row counts, malformed JSONL rate, queue status counts, freshness",
              "Observatory API can compute some values; no DB/freshness dashboard registered",
              "GET /api/v1/health, /api/v1/metrics, /api/v1/content, /api/v1/trajectory",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: agents/AGENTS.yaml, src/holus/agents/marketing/models.py, src/holus/memory/trajectory.py - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

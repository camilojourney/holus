import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Grid,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

export default function HolusDatabaseCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="info">P1</Pill>
          <Text size="small" tone="tertiary">holus - block 04 - database</Text>
        </Row>
        <H1>Database and storage</H1>
        <Text tone="secondary">
          Holus is intentionally file-backed for operator clarity. Durable product
          analytics and media assets remain in their owning silos.
        </Text>
      </Stack>

      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader trailing={<Pill size="sm" tone="success">hot</Pill>}>
            Queue files
          </CardHeader>
          <CardBody>
            <Text>YAML/JSON files under data/content-queue store thought source metadata, variants, review state, schedule state, and publish references.</Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm" tone="info">append</Pill>}>
            Trajectory JSONL
          </CardHeader>
          <CardBody>
            <Text>.self-improvement/memory/trajectory.jsonl is the audit trail for cycles, evaluations, costs, failures, and learning inputs.</Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm" tone="neutral">external</Pill>}>
            Silo stores
          </CardHeader>
          <CardBody>
            <Text>Holus Social API owns social accounts, posting queues, and analytics. Genpeli/video stays deferred.</Text>
          </CardBody>
        </Card>
      </Grid>

      <H2>Physical stores</H2>
      <Table
        headers={["Store", "Path or system", "Type", "Hot/cold", "Retention / owner"]}
        rows={[
          ["Configuration", "config/*.yaml", "YAML", "hot", "git durable; config changes require approval for products/guardrails"],
          ["Agent registry", "agents/AGENTS.yaml + agents/**/*.md", "YAML + Markdown", "hot", "git durable; single source for agent behavior"],
          ["Content queue", "data/content-queue/*.yaml|*.json", "file queue", "hot", "operator-owned lifecycle state"],
          ["Rendered content", "data/rendered-content/*.{png,pdf}", "media artifacts", "hot", "Holus visual engine outputs for review/publish"],
          ["Trajectory", ".self-improvement/memory/trajectory.jsonl", "append-only JSONL", "hot", "git-ignored runtime audit state"],
          ["Lessons", ".self-improvement/memory/lessons.json", "JSON", "warm", "git-ignored learned patterns"],
          ["Memory", ".self-improvement/MEMORY.md", "Markdown", "warm", "git durable system memory"],
          ["Knowledge", ".self-improvement/knowledge/current/*.md", "Markdown", "warm", "operator-curated marketing context"],
          ["Corpus", "src/holus/data/corpus.py SQLite path", "SQLite", "warm", "local few-shot/reference corpus"],
          ["Redis", "REDIS_URL", "pub/sub + streams", "hot", "event bus and kill switch backend"],
          ["Langfuse", "external/self-hosted", "traces/cost", "warm", "observability and eval datasets"],
          ["Social analytics", "Holus Social API", "external DB", "hot", "owned by Holus Social API, read via API/MCP"],
          ["Future video", "Genpeli storage", "object/media", "cold", "deferred adapter, not required for current build"],
        ]}
        striped
      />

      <Callout tone="warning" title="No central analytics warehouse">
        By design, Holus does not permanently store social performance analytics.
        Any dashboard that needs engagement history should query Holus Social API
        or show dated snapshots with source labels.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "Queue file count, JSONL freshness, Redis state, storage growth",
              "No Grafana/DB dashboard registered for Holus",
              "just preflight; GET /api/v1/health; infrastructure/prometheus.yml if wired",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: src/holus/core/health.py, content_queue.py, trajectory.py, config/base.yaml - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

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

export default function HolusControlCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Row gap={8} align="center">
          <Pill tone="neutral">P2</Pill>
          <Text size="small" tone="tertiary">holus - block 10 - control</Text>
        </Row>
        <H1>Control and tests</H1>
        <Text tone="secondary">
          This is the boundary between safe operator tuning and changes that need a
          PR, explicit approval, or a hard stop.
        </Text>
      </Stack>

      <H2>Safe to edit from canvas/chat</H2>
      <Table
        headers={["Area", "Examples", "Verification"]}
        rows={[
          ["Agent prompts", "agents/**/*.md when behavior change is requested", "unit tests plus one dry-run content cycle"],
          ["Knowledge and memory", ".self-improvement/MEMORY.md, knowledge/current/*.md", "knowledge page and trajectory references still load"],
          ["Reports", ".self-improvement/reports/*", "no app behavior change"],
          ["Specs and docs", "docs/*, specs/*, docs/canvas/*", "audit_canvas.py and markdown review"],
          ["Non-publishing drafts", "data/content-queue pending review drafts", "review-content shows expected state"],
        ]}
      />

      <H2>Ask first or use PR discipline</H2>
      <Table
        headers={["Area", "Why risky", "Required verification"]}
        rows={[
          ["config/products.yaml", "changes target products, platforms, and accounts", "explicit approval, then content dry run"],
          ["config/*.yaml", "runtime and guardrail behavior changes", "approval plus just check"],
          ["Pydantic silo boundary models", "can break MCP/API contracts", "unit, integration, and contract tests"],
          ["pyproject.toml dependencies", "changes runtime and supply chain", "approval, lock update, just check, audit"],
          ["API mutations", "can change approval/publish behavior", "unit + e2e publish pipeline tests"],
          ["launchd plists", "can automate real actions", "just validate-plists and schedule-test"],
        ]}
        rowTone={["warning", "warning", "warning", "warning", "warning", "warning"]}
      />

      <H2>Hard stops</H2>
      <Table
        headers={["Rule", "Reason", "Action"]}
        rows={[
          ["Never expose secrets", "credentials must not enter code or commits", "stop and remove from source before proceeding"],
          ["Never force-push main", "destructive history rewrite", "ask for explicit human direction"],
          ["Never touch pythia or milo", "trading isolation is mandatory", "hard stop and escalate"],
          ["Never modify guardrails without approval", "safety policy boundary", "ask first"],
          ["Never delete performance data or trajectory logs", "learning/audit loss", "archive or propose retention policy instead"],
          ["Never post trading or investment advice", "scope and compliance boundary", "reject content path"],
        ]}
        rowTone={["warning", "warning", "warning", "warning", "warning", "warning"]}
      />

      <H2>Verification ladder</H2>
      <Table
        headers={["Change type", "Minimum test", "Broader test"]}
        rows={[
          ["Canvas/docs only", "audit_canvas.py", "link-canvas.sh and open registry in Cursor"],
          ["Thought/content behavior", "targeted unit tests", "POST /api/v1/content/from-thought with dry-run publish/schedule"],
          ["Queue lifecycle", "tests/unit/agents/test_review.py and test_content routes", "tests/e2e/test_publish_pipeline.py"],
          ["API route", "tests/unit/api/*", "start API and verify frontend calls"],
          ["Visual pipeline", "tests/unit/visual/*", "tests/integration/test_carousel_e2e.py"],
          ["Silo integration", "unit client tests", "integration tests with live MCP only when approved"],
          ["Full repo change", "just check", "manual queue and Observatory smoke test"],
        ]}
      />

      <Callout tone="danger" title="Publishing control">
        Publish and schedule_post require explicit operator intent and human review
        by default. Genpeli/video creation is deferred; any future video or paid
        generation action must still respect the approved daily budget.
      </Callout>

      <Stack gap={6}>
        <H2>Live dashboard</H2>
        <Table
          headers={["Metric", "Surface", "Refresh"]}
          rows={[
            [
              "Test pass rate, eval history, approval actions, blocked hard-stop events",
              "No dedicated control dashboard registered; use tests, Observatory, and Fleet Command",
              "just check; GET /api/v1/health; GET /api/v1/evaluations; http://127.0.0.1:8765#plans",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: AGENTS instructions, CLAUDE.md, justfile, tests/ tree - 2026-05-31.
        </Text>
      </Stack>
    </Stack>
  );
}

import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  H1,
  Pill,
  Row,
  Stack,
  Text,
  useCanvasAction,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

const CANVAS_ROOT =
  "~/.cursor/projects/Users-mini-openclaw-workspace-github-holus/canvases";

type Tier = "P0" | "P1" | "P2";
type Status = "ready" | "draft";

type CanvasEntry = {
  id: string;
  tier: Tier;
  order: number;
  title: string;
  block: string;
  file: string;
  notes: string;
  status: Status;
};

const ENTRIES: CanvasEntry[] = [
  {
    id: "01",
    tier: "P0",
    order: 1,
    title: "User and journey",
    block: "user",
    file: `${CANVAS_ROOT}/holus-01-user.canvas.tsx`,
    notes: "Thought Studio journey, approval gate, Holus Social API handoff, and learning metric.",
    status: "ready",
  },
  {
    id: "02",
    tier: "P0",
    order: 2,
    title: "UX and screens",
    block: "ux",
    file: `${CANVAS_ROOT}/holus-02-ux.canvas.tsx`,
    notes: "Observatory pages, CLI controls, route states, and navigation.",
    status: "ready",
  },
  {
    id: "03",
    tier: "P0",
    order: 3,
    title: "Data model",
    block: "data-model",
    file: `${CANVAS_ROOT}/holus-03-data-model.canvas.tsx`,
    notes: "Conceptual objects, owners, lineage, and silo boundaries.",
    status: "ready",
  },
  {
    id: "04",
    tier: "P1",
    order: 4,
    title: "Database and storage",
    block: "database",
    file: `${CANVAS_ROOT}/holus-04-database.canvas.tsx`,
    notes: "File-backed state, Redis, Langfuse, external silo storage, and retention.",
    status: "ready",
  },
  {
    id: "05",
    tier: "P1",
    order: 5,
    title: "Logic and APIs",
    block: "logic",
    file: `${CANVAS_ROOT}/holus-05-logic.canvas.tsx`,
    notes: "Thought-to-content flow, Observatory API, Holus Social API tools, and failure modes.",
    status: "ready",
  },
  {
    id: "06",
    tier: "P0",
    order: 6,
    title: "AI and agents",
    block: "ai",
    file: `${CANVAS_ROOT}/holus-06-ai.canvas.tsx`,
    notes: "35-agent registry, model tiers, prompt layers, judge routing, and guardrails.",
    status: "ready",
  },
  {
    id: "07",
    tier: "P1",
    order: 7,
    title: "Telemetry plan",
    block: "telemetry",
    file: `${CANVAS_ROOT}/holus-07-telemetry.canvas.tsx`,
    notes: "Events, success/failure/cost/quality metrics, and source ownership.",
    status: "ready",
  },
  {
    id: "08",
    tier: "P2",
    order: 8,
    title: "Ops and runtime",
    block: "ops",
    file: `${CANVAS_ROOT}/holus-08-ops.canvas.tsx`,
    notes: "Runtime services, launchd jobs, secrets, kill switch, and incident path.",
    status: "ready",
  },
  {
    id: "09",
    tier: "P1",
    order: 9,
    title: "Dashboard map",
    block: "dashboard-map",
    file: `${CANVAS_ROOT}/holus-09-dashboard-map.canvas.tsx`,
    notes: "Live surfaces per block. Draft because Holus is not in dashboard-registry.json.",
    status: "draft",
  },
  {
    id: "10",
    tier: "P2",
    order: 10,
    title: "Control and tests",
    block: "control",
    file: `${CANVAS_ROOT}/holus-10-control.canvas.tsx`,
    notes: "Safe edits, approval-only edits, hard stops, and verification commands.",
    status: "ready",
  },
];

function tierTone(tier: Tier) {
  if (tier === "P0") return "warning" as const;
  if (tier === "P1") return "info" as const;
  return "neutral" as const;
}

function statusTone(status: Status) {
  return status === "ready" ? ("success" as const) : ("warning" as const);
}

export default function HolusCanvasRegistry() {
  const theme = useHostTheme();
  const dispatch = useCanvasAction();
  const [selectedId, setSelectedId] = useCanvasState("selectedCanvas", "01");
  const selected = ENTRIES.find((entry) => entry.id === selectedId) ?? ENTRIES[0];

  return (
    <Stack gap={16} style={{ padding: 20, maxWidth: 980, color: theme.text.primary }}>
      <Stack gap={4}>
        <Text size="small" tone="tertiary">
          SYSTEMS CANVAS - HOLUS
        </Text>
        <H1>Holus system blueprint</H1>
        <Text tone="secondary">
          Design canvases for the Holus Thought Studio: one thought becomes
          platform-native text, images, carousels, scheduled posts, and learning.
        </Text>
      </Stack>

      <Callout tone="info" title="Design vs dashboard vs control">
        Canvas = how it should work. Dashboard = what is happening now. Control = what
        can change safely. Numbers here are dated snapshots, not live metrics.
      </Callout>

      <Row gap={16} align="start">
        <Card style={{ flex: "0 0 330px" }}>
          <CardHeader trailing={<Pill size="sm" tone="neutral">{ENTRIES.length}</Pill>}>
            Blocks
          </CardHeader>
          <CardBody style={{ padding: 0 }}>
            <Stack gap={0}>
              {ENTRIES.map((entry, idx) => {
                const active = entry.id === selectedId;
                return (
                  <div key={entry.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(entry.id)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        padding: "12px 16px",
                        border: "none",
                        cursor: "pointer",
                        background: active ? theme.fill.secondary : "transparent",
                        color: theme.text.primary,
                        font: "inherit",
                      }}
                    >
                      <Row gap={8} align="center">
                        <Text size="small" tone="tertiary" style={{ width: 24 }}>
                          {entry.order}
                        </Text>
                        <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
                          <Row gap={6} align="center">
                            <Pill size="sm" tone={tierTone(entry.tier)}>
                              {entry.tier}
                            </Pill>
                            <Pill size="sm" tone={statusTone(entry.status)}>
                              {entry.status}
                            </Pill>
                          </Row>
                          <Text weight="semibold" truncate>
                            {entry.title}
                          </Text>
                        </Stack>
                      </Row>
                    </button>
                    {idx < ENTRIES.length - 1 ? <Divider /> : null}
                  </div>
                );
              })}
            </Stack>
          </CardBody>
        </Card>

        <Stack gap={12} style={{ flex: 1, minWidth: 0 }}>
          <Card>
            <CardHeader>{selected.title}</CardHeader>
            <CardBody>
              <Stack gap={10}>
                <Row gap={8} align="center" wrap>
                  <Pill tone={tierTone(selected.tier)}>{selected.tier}</Pill>
                  <Pill tone={statusTone(selected.status)}>{selected.status}</Pill>
                  <Text tone="tertiary">block {selected.order}</Text>
                </Row>
                <Text tone="secondary">{selected.notes}</Text>
                <Code>{selected.file}</Code>
                <Row gap={8}>
                  <Button
                    variant="primary"
                    onClick={() =>
                      dispatch({
                        type: "newComposerChat",
                        userPrompt: `/systems-canvas holus --block ${selected.block} refresh this block against the current repo. Notes: ${selected.notes}`,
                      })
                    }
                  >
                    Edit in chat
                  </Button>
                </Row>
              </Stack>
            </CardBody>
          </Card>

          <Callout tone="warning" title="Dashboard wiring">
            The systems-canvas dashboard audit found no registry entry for Holus. Block
            09 lists the missing live surfaces and refresh commands to wire next.
          </Callout>

          <Callout tone="neutral">
            P0 = ship blocker. P1 = core workflow. P2 = operational depth.
          </Callout>
        </Stack>
      </Row>
    </Stack>
  );
}

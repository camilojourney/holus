import Image from 'next/image';
import type { CSSProperties } from 'react';
import { contentImageUrl, fetchAgents, fetchContent, fetchContentDetail } from '@/lib/api';
import CarouselPreview from '@/components/CarouselPreview';
import ContentKanban from '@/components/ContentKanban';
import ErrorBanner from '@/components/ErrorBanner';
import ThoughtComposer from '@/components/ThoughtComposer';
import type { Agent, AgentTraceStep, ContentDetail, ContentItem } from '@/lib/types';

export const revalidate = 0;

const platformOrder = ['linkedin', 'facebook', 'instagram', 'threads', 'twitter', 'twitter_x'];

const platformLabels: Record<string, string> = {
  linkedin: 'LinkedIn',
  facebook: 'Facebook',
  instagram: 'Instagram',
  threads: 'Threads',
  twitter: 'Twitter/X',
  twitter_x: 'Twitter/X',
};

const assetLabels: Record<string, string> = {
  caption: 'Caption',
  carousel_outline: 'Carousel',
  image_caption: 'Image',
  text_post: 'Post',
  thread: 'Thread',
};

const agentLabels: Record<string, string> = {
  'idea-injector': 'Idea Injector',
  'context-builder': 'Context Builder',
  'idea-planner': 'Idea Planner',
  'idea-generator': 'Idea Generator',
  'voice-writer': 'Voice Writer',
  storyteller: 'Storyteller',
  'script-writer': 'Script Writer',
  'visual-designer': 'Visual Designer',
  'brand-designer': 'Brand Designer',
  'platform-adapter': 'Platform Adapter',
  'voice-guardian': 'Voice Guardian',
  'written-content-judge': 'Written Judge',
  'visual-content-judge': 'Visual Judge',
};

const agentOrder = [
  'idea-injector',
  'context-builder',
  'idea-planner',
  'idea-generator',
  'voice-writer',
  'storyteller',
  'script-writer',
  'visual-designer',
  'brand-designer',
  'platform-adapter',
  'voice-guardian',
  'written-content-judge',
  'visual-content-judge',
];

const systemGroupOrder = [
  'Strategy',
  'Content pipeline',
  'Written authority',
  'Visual content',
  'Future video',
  'Growth',
  'Research',
  'Repurposing',
  'Evaluators',
  'Ops',
];

const systemGroupCopy: Record<string, string> = {
  Strategy: 'Decides what to create and learns from results.',
  'Content pipeline': 'Turns one raw thought into planned outputs.',
  'Written authority': 'Makes the words sharp, technical, human, and useful.',
  'Visual content': 'Creates images, carousels, charts, and brand direction.',
  'Future video': 'Deferred path for scripts, production briefs, and caption strategy.',
  Growth: 'Designs CTAs, lead magnets, and conversation loops.',
  Research: 'Feeds the system with audience, SEO, and market signal.',
  Repurposing: 'Adapts the same idea across native platform formats.',
  Evaluators: 'Judges quality, platform fit, brand safety, and publish readiness.',
  Ops: 'Keeps security, knowledge freshness, and system hygiene in view.',
};

const workflowSteps = [
  { label: 'Thought', detail: 'Raw idea' },
  { label: 'Formats', detail: 'Native platform set' },
  { label: 'Assets', detail: 'Copy, image, carousel' },
  { label: 'Review', detail: 'Voice and brand gates' },
  { label: 'Schedule', detail: 'Human-approved queue' },
];

const studioTheme = {
  '--surface-0': '#f6f8fb',
  '--surface-1': '#ffffff',
  '--surface-2': '#f8fafc',
  '--surface-raised': '#ffffff',
  '--text-primary': '#111827',
  '--text-secondary': '#475569',
  '--text-tertiary': '#64748b',
  '--text-inverse': '#ffffff',
  '--border-default': '#dbe3ef',
  '--border-subtle': '#edf2f7',
  '--border-strong': '#b8c4d6',
  '--brand': '#4f46e5',
  '--brand-light': '#6366f1',
  '--brand-subtle': '#eef2ff',
  '--brand-muted-oklch': '#c7d2fe',
  '--warning': '#b45309',
  '--warning-subtle': '#fff7ed',
  '--success': '#047857',
  '--success-subtle': '#ecfdf5',
  '--info': '#2563eb',
  '--info-subtle': '#eff6ff',
  '--verdict-pass-bg': '#dcfce7',
  '--verdict-pass-text': '#166534',
  '--verdict-fail-bg': '#fee2e2',
  '--verdict-fail-text': '#991b1b',
  '--button-approve-bg': '#4f46e5',
  '--button-schedule-bg': '#0f766e',
  '--button-reject-border': '#fecaca',
  '--button-reject-text': '#b91c1c',
  '--shadow-sm': '0 1px 2px rgba(15, 23, 42, 0.06)',
  '--shadow-md': '0 12px 30px rgba(15, 23, 42, 0.10)',
  '--shadow-lg': '0 24px 60px rgba(15, 23, 42, 0.14)',
  background:
    'radial-gradient(circle at top left, rgba(79, 70, 229, 0.11), transparent 32rem), linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%)',
  color: '#111827',
  minHeight: '100vh',
  padding: '2rem',
} as CSSProperties;

function formatLabel(item: ContentItem): string {
  if (item.platform === 'instagram' && item.content_type === 'image_caption') {
    return 'Instagram Image';
  }
  if (item.content_type === 'carousel_outline') {
    const platform = platformLabels[item.platform ?? ''] ?? item.platform ?? 'Unknown';
    return `${platform} Carousel`;
  }
  if (item.platform === 'twitter_x' || item.platform === 'twitter') {
    return 'X Thread';
  }
  const platform = platformLabels[item.platform ?? ''] ?? item.platform ?? 'Unknown';
  const asset = assetLabels[item.content_type] ?? item.content_type.replace(/_/g, ' ');
  return `${platform} ${asset}`;
}

function uniquePlatforms(group: ContentItem[]): Set<string> {
  return new Set(group.map((item) => item.platform).filter((platform): platform is string => Boolean(platform)));
}

function groupKey(item: ContentItem): string {
  return item.group_id || item.idea_source || item.title || item.id;
}

function platformSort(a: ContentItem, b: ContentItem): number {
  const aIndex = platformOrder.indexOf(a.platform ?? '');
  const bIndex = platformOrder.indexOf(b.platform ?? '');
  return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
}

function newestTime(group: ContentItem[]): number {
  return Math.max(
    ...group.map((item) => new Date(item.created_at ?? 0).getTime()).filter(Number.isFinite),
    0,
  );
}

function statusLabel(status: string): string {
  return status.replace(/_/g, ' ');
}

function platformShortLabel(platform?: string): string {
  if (!platform) return 'Other';
  if (platform === 'twitter_x' || platform === 'twitter') return 'X';
  return platformLabels[platform] ?? platform;
}

function rendererLabel(detail: ContentDetail | undefined): string {
  const renderer = detail?.visual_spec?.renderer;
  if (renderer === 'holus/carousel-renderer') return 'Holus carousel renderer';
  if (renderer === 'holus/visual-renderer') return 'Holus visual renderer';
  if (renderer === 'holus/carousel-fallback') return 'Local fallback PDF';
  if (renderer === 'holus/local-preview') return 'Local fallback preview';
  return 'Asset preview';
}

function textPreview(detail: ContentDetail | undefined): string {
  const text = detail?.text?.trim();
  if (!text) return 'Content text is available by opening the review card.';
  return text.length > 360 ? `${text.slice(0, 357).trim()}...` : text;
}

function campaignAgents(details: Record<string, ContentDetail>): AgentTraceStep[] {
  const agents = new Map<string, AgentTraceStep>();
  for (const detail of Object.values(details)) {
    for (const step of detail.agent_trace ?? []) {
      if (!agents.has(step.agent_id)) agents.set(step.agent_id, step);
    }
  }
  return [...agents.values()].sort((a, b) => {
    const aIndex = agentOrder.indexOf(a.agent_id);
    const bIndex = agentOrder.indexOf(b.agent_id);
    return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
  });
}

function systemGroupFor(agent: Agent): string {
  if (agent.type === 'manager') return 'Strategy';
  if (agent.type === 'evaluator') return 'Evaluators';
  if (agent.type === 'ops') return 'Ops';
  if (agent.category === 'content') return 'Content pipeline';
  if (agent.category === 'written-authority') return 'Written authority';
  if (agent.category === 'visual') return 'Visual content';
  if (agent.category === 'video') return 'Future video';
  if (agent.category === 'growth') return 'Growth';
  if (agent.category === 'research') return 'Research';
  if (agent.category === 'repurposing') return 'Repurposing';
  return 'Content pipeline';
}

function groupSystemAgents(agents: Agent[]): { name: string; agents: Agent[] }[] {
  const groups = new Map<string, Agent[]>();
  for (const agent of agents) {
    const group = systemGroupFor(agent);
    groups.set(group, [...(groups.get(group) ?? []), agent]);
  }
  return [...groups.entries()]
    .map(([name, groupAgents]) => ({
      name,
      agents: groupAgents.slice().sort((a, b) => a.id.localeCompare(b.id)),
    }))
    .sort((a, b) => systemGroupOrder.indexOf(a.name) - systemGroupOrder.indexOf(b.name));
}

function modelLaneSummary(agents: Agent[]): { lane: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const agent of agents) {
    const lane = agent.model || agent.model_tier || 'unknown';
    counts.set(lane, (counts.get(lane) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([lane, count]) => ({ lane, count }))
    .sort((a, b) => b.count - a.count || a.lane.localeCompare(b.lane));
}

function agentRuntimeState(agent: Agent, involvedIds: Set<string>): {
  label: string;
  style: CSSProperties;
  issue: string;
} {
  if (involvedIds.has(agent.id)) {
    return {
      label: 'ran',
      style: { background: 'var(--verdict-pass-bg)', color: 'var(--verdict-pass-text)' },
      issue: 'Used in this thought set trace.',
    };
  }
  if (agent.registry_status === 'planned' || agent.status === 'planned') {
    return {
      label: 'planned',
      style: { background: 'var(--surface-raised)', color: 'var(--text-tertiary)' },
      issue: 'Registered as planned; not available in the current execution path.',
    };
  }
  if (agent.type === 'evaluator') {
    return {
      label: 'judge idle',
      style: { background: 'var(--warning-subtle)', color: 'var(--warning)' },
      issue: 'Evaluator prompt exists, but this deterministic Thought Studio path did not call it as a model-backed judge.',
    };
  }
  if ((agent.run_count_7d ?? 0) === 0) {
    return {
      label: 'no telemetry',
      style: { background: 'var(--status-draft-bg)', color: 'var(--status-draft-text)' },
      issue: 'Active in registry, but no trajectory runs were recorded in the last 7 days.',
    };
  }
  return {
    label: 'available',
    style: { background: 'var(--brand-subtle)', color: 'var(--brand)' },
    issue: 'Available in registry; not selected for this thought set.',
  };
}

export default async function ContentPage() {
  let items: ContentItem[] = [];
  let agents: Agent[] = [];
  let featuredGroup: ContentItem[] = [];
  let featuredDetails: Record<string, ContentDetail> = {};
  let error = false;

  try {
    items = await fetchContent();
    const groups = new Map<string, ContentItem[]>();
    for (const item of items) {
      const key = groupKey(item);
      groups.set(key, [...(groups.get(key) ?? []), item]);
    }
    featuredGroup =
      [...groups.values()]
        .filter((group) => uniquePlatforms(group).size > 1)
        .sort(
          (a, b) =>
            uniquePlatforms(b).size - uniquePlatforms(a).size ||
            newestTime(b) - newestTime(a) ||
            b.length - a.length,
        )[0]
        ?.slice()
        .sort(platformSort) ?? [];

    const detailResults = await Promise.allSettled(
      featuredGroup.map((item) => fetchContentDetail(item.id)),
    );
    featuredDetails = Object.fromEntries(
      detailResults.flatMap((result) =>
        result.status === 'fulfilled' ? [[result.value.id, result.value]] : [],
      ),
    );
  } catch {
    error = true;
  }
  try {
    agents = await fetchAgents();
  } catch {
    agents = [];
  }

  // Status counts from real data
  const counts = {
    draft: items.filter((i) => i.status === 'draft').length,
    review: items.filter((i) => i.status === 'pending_review').length,
    approved: items.filter((i) => ['approved', 'scheduled'].includes(i.status)).length,
    published: items.filter((i) => i.status === 'published').length,
    rejected: items.filter((i) => i.status === 'rejected').length,
  };

  const countCards = [
    { label: 'Drafting', value: counts.draft, color: 'var(--text-secondary)' },
    { label: 'Awaiting Review', value: counts.review, color: 'var(--warning)' },
    { label: 'Gate Passed', value: counts.approved, color: 'var(--info)' },
    { label: 'Live', value: counts.published, color: 'var(--success)' },
  ];
  const visualItems = featuredGroup.filter((item) =>
    ['image_caption', 'carousel_outline'].includes(item.content_type),
  );
  const copyItems = featuredGroup.filter((item) => !visualItems.some((visual) => visual.id === item.id));
  const involvedAgents = campaignAgents(featuredDetails);
  const involvedIds = new Set(involvedAgents.map((agent) => agent.agent_id));
  const systemGroups = groupSystemAgents(agents);
  const activeAgents = agents.filter((agent) => agent.registry_status !== 'planned').length;
  const plannedAgents = agents.filter((agent) => agent.registry_status === 'planned').length;
  const evaluatorAgents = agents.filter((agent) => agent.type === 'evaluator');
  const noTelemetryAgents = agents.filter((agent) => (agent.run_count_7d ?? 0) === 0);
  const activeNotUsedAgents = agents.filter(
    (agent) =>
      agent.registry_status !== 'planned' &&
      agent.status !== 'planned' &&
      !involvedIds.has(agent.id),
  );
  const modelLanes = modelLaneSummary(agents);
  const pendingActions = counts.review + counts.draft;
  const readyToSchedule = counts.approved;
  const latestTitle = featuredGroup[0]?.title ?? featuredGroup[0]?.idea_source ?? 'No campaign selected yet';
  const featuredPlatforms = [...uniquePlatforms(featuredGroup)].sort((a, b) => {
    const aIndex = platformOrder.indexOf(a);
    const bIndex = platformOrder.indexOf(b);
    return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
  });

  return (
    <div style={studioTheme} className="page-transition">
      <div className="mx-auto max-w-7xl space-y-6">
      <div
        className="rounded-2xl p-6 shadow-sm"
        style={{
          border: '1px solid rgba(79, 70, 229, 0.14)',
          background: 'rgba(255, 255, 255, 0.78)',
          backdropFilter: 'blur(18px)',
        }}
      >
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em]" style={{ color: 'var(--brand)' }}>
              Holus Content Studio
            </p>
            <h1 className="text-3xl font-bold mt-2 leading-tight" style={{ color: 'var(--text-primary)' }}>
              Turn one thought into a full content set.
            </h1>
            <p className="text-sm mt-2 max-w-2xl leading-6" style={{ color: 'var(--text-secondary)' }}>
              Draft platform-native posts, inspect generated visuals, approve the package, and schedule it without leaving the creation flow.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3 min-w-full lg:min-w-[26rem]">
            <div className="rounded-xl px-4 py-3" style={{ border: '1px solid var(--border-default)', background: '#ffffff' }}>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Review</p>
              <p className="text-2xl font-bold mt-1" style={{ color: 'var(--warning)' }}>{pendingActions}</p>
            </div>
            <div className="rounded-xl px-4 py-3" style={{ border: '1px solid var(--border-default)', background: '#ffffff' }}>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Ready</p>
              <p className="text-2xl font-bold mt-1" style={{ color: 'var(--info)' }}>{readyToSchedule}</p>
            </div>
            <div className="rounded-xl px-4 py-3" style={{ border: '1px solid var(--border-default)', background: '#ffffff' }}>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Live</p>
              <p className="text-2xl font-bold mt-1" style={{ color: 'var(--success)' }}>{counts.published}</p>
            </div>
          </div>
        </div>
      </div>

      {error && <ErrorBanner message="Could not load content data" />}

      {!error && (
        <>
          <section className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.25fr)_minmax(22rem,0.75fr)] gap-5">
            <ThoughtComposer />

            <aside
              className="rounded-2xl overflow-hidden animate-fade-in shadow-sm"
              style={{
                border: '1px solid var(--border-default)',
                background: 'var(--surface-raised)',
              }}
            >
              <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <p className="text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: 'var(--text-tertiary)' }}>
                  Workflow
                </p>
                <h2 className="text-lg font-semibold mt-1" style={{ color: 'var(--text-primary)' }}>
                  A gated path to publishing
                </h2>
              </div>
              <div className="p-5 space-y-4">
                {workflowSteps.map((step, index) => (
                  <div key={step.label} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <span
                        className="grid h-7 w-7 place-items-center rounded-full text-xs font-bold"
                        style={{
                          background: index === 0 ? 'var(--brand)' : 'var(--brand-subtle)',
                          color: index === 0 ? 'var(--text-inverse)' : 'var(--brand)',
                        }}
                      >
                        {index + 1}
                      </span>
                      {index < workflowSteps.length - 1 && (
                        <span className="mt-1 h-6 w-px" style={{ background: 'var(--border-default)' }} />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {step.label}
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                        {step.detail}
                      </p>
                    </div>
                  </div>
                ))}
                <div className="rounded-xl px-4 py-3" style={{ background: 'var(--warning-subtle)', border: '1px solid #fed7aa' }}>
                  <p className="text-xs font-semibold leading-5" style={{ color: 'var(--warning)' }}>
                    Publishing is still gated. Approval prepares the content for scheduling; it does not bypass human review.
                  </p>
                </div>
              </div>
            </aside>
          </section>

          {featuredGroup.length > 0 && (
            <section
              className="rounded-2xl overflow-hidden animate-fade-in shadow-sm"
              style={{
                border: '1px solid var(--border-default)',
                background: 'var(--surface-raised)',
              }}
            >
              <div
                className="px-6 py-5"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}
              >
                <p
                  className="text-xs font-semibold uppercase tracking-[0.12em]"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  Current content set
                </p>
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h2
                      className="text-xl font-semibold mt-1 leading-snug max-w-4xl"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {latestTitle}
                    </h2>
                    <div className="flex items-center gap-2 mt-3 flex-wrap">
                      {featuredPlatforms.map((platform) => (
                        <span
                          key={platform}
                          className="text-xs px-2 py-1 rounded font-medium"
                          style={{
                            background: 'var(--brand-subtle)',
                            color: 'var(--brand)',
                          }}
                        >
                          {platformShortLabel(platform)}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 min-w-full lg:min-w-[18rem]">
                    <div className="rounded-lg px-3 py-2" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-default)' }}>
                      <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Drafts</p>
                      <p className="text-lg font-bold mt-0.5" style={{ color: 'var(--text-primary)' }}>{featuredGroup.length}</p>
                    </div>
                    <div className="rounded-lg px-3 py-2" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-default)' }}>
                      <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Visuals</p>
                      <p className="text-lg font-bold mt-0.5" style={{ color: 'var(--text-primary)' }}>{visualItems.length}</p>
                    </div>
                    <div className="rounded-lg px-3 py-2" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-default)' }}>
                      <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Agents</p>
                      <p className="text-lg font-bold mt-0.5" style={{ color: 'var(--text-primary)' }}>{involvedAgents.length}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-6 p-5">
                {involvedAgents.length > 0 && (
                  <section>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                      <p
                        className="text-xs font-semibold uppercase tracking-[0.12em]"
                        style={{ color: 'var(--text-tertiary)' }}
                      >
                        Built by Holus
                      </p>
                      <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                        The campaign keeps a trace, but the content stays first.
                      </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                      {involvedAgents.map((agent, index) => (
                        <span
                          key={agent.agent_id}
                          className="rounded-full px-3 py-1 text-xs font-semibold"
                          style={{
                            border: '1px solid var(--border-default)',
                            background: index < 4 ? 'var(--brand-subtle)' : 'var(--surface-2)',
                            color: index < 4 ? 'var(--brand)' : 'var(--text-secondary)',
                          }}
                        >
                          {String(index + 1).padStart(2, '0')} {agentLabels[agent.agent_id] ?? agent.agent_id}
                        </span>
                      ))}
                      </div>
                    </div>
                  </section>
                )}

                {visualItems.length > 0 && (
                  <section>
                    <div className="mb-3">
                      <p
                        className="text-xs font-semibold uppercase tracking-[0.12em]"
                        style={{ color: 'var(--text-tertiary)' }}
                      >
                        Visual assets generated by Holus
                      </p>
                      <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                        Images and carousel slide sets are rendered in Holus before they move to review.
                      </p>
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {visualItems.map((item) => {
                        const detail = featuredDetails[item.id];
                        return (
                          <article
                            key={item.id}
                            className="rounded-2xl overflow-hidden"
                            style={{
                              border: '1px solid var(--border-default)',
                              background: 'var(--surface-2)',
                            }}
                          >
                            <div className="px-4 py-3 flex items-center justify-between gap-3">
                              <div>
                                <h3
                                  className="text-sm font-semibold"
                                  style={{ color: 'var(--text-primary)' }}
                                >
                                  {formatLabel(item)}
                                </h3>
                                <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                                  {rendererLabel(detail)}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                {item.quality?.voice_check && (
                                  <span
                                    className="text-xs px-2 py-0.5 rounded font-medium"
                                    style={{
                                      background:
                                        item.quality.voice_check === 'PASS'
                                          ? 'var(--verdict-pass-bg)'
                                          : 'var(--verdict-fail-bg)',
                                      color:
                                        item.quality.voice_check === 'PASS'
                                          ? 'var(--verdict-pass-text)'
                                          : 'var(--verdict-fail-text)',
                                    }}
                                  >
                                    Voice {item.quality.voice_check}
                                  </span>
                                )}
                                <span
                                  className="text-xs px-2 py-0.5 rounded font-medium capitalize"
                                  style={{
                                    background: 'var(--warning-subtle)',
                                    color: 'var(--warning)',
                                  }}
                                >
                                  {statusLabel(item.status)}
                                </span>
                              </div>
                            </div>
                            {detail?.image_url ? (
                              <div
                                className="relative mx-4 overflow-hidden rounded-lg"
                                style={{
                                  border: '1px solid var(--border-default)',
                                  background: 'var(--surface-raised)',
                                  aspectRatio:
                                    detail.visual_spec?.renderer === 'holus/visual-renderer'
                                      ? '1 / 1'
                                      : '4 / 5',
                                }}
                              >
                                <Image
                                  src={contentImageUrl(item.id)}
                                  alt={`${formatLabel(item)} visual preview`}
                                  fill
                                  sizes="(min-width: 1024px) 38vw, 90vw"
                                  style={{ objectFit: 'contain' }}
                                  unoptimized
                                />
                              </div>
                            ) : detail?.pdf_url ? (
                              <div className="mx-4">
                                <CarouselPreview
                                  detail={detail}
                                  pieceId={item.id}
                                  label={formatLabel(item)}
                                  maxSlides={3}
                                />
                              </div>
                            ) : (
                              <div
                                className="mx-4 rounded-lg px-4 py-8 text-center"
                                style={{
                                  border: '1px dashed var(--border-default)',
                                  color: 'var(--text-tertiary)',
                                }}
                              >
                                Visual pending
                              </div>
                            )}
                            <p
                              className="text-sm m-4 leading-relaxed whitespace-pre-wrap"
                              style={{
                                color: 'var(--text-secondary)',
                                maxHeight: '8rem',
                                overflow: 'hidden',
                              }}
                            >
                              {textPreview(detail)}
                            </p>
                          </article>
                        );
                      })}
                    </div>
                  </section>
                )}

                <section>
                  <p
                    className="text-xs font-semibold uppercase tracking-[0.12em] mb-3"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    Copy drafts
                  </p>
                  <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-3">
                    {copyItems.map((item) => {
                      const detail = featuredDetails[item.id];
                      return (
                        <article
                          key={item.id}
                          className="rounded-2xl px-4 py-3"
                          style={{
                            border: '1px solid var(--border-default)',
                            background: 'var(--surface-2)',
                          }}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <h3
                              className="text-sm font-semibold"
                              style={{ color: 'var(--text-primary)' }}
                            >
                              {formatLabel(item)}
                            </h3>
                            {item.quality?.voice_check && (
                              <span
                                className="text-xs px-2 py-0.5 rounded font-medium"
                                style={{
                                  background:
                                    item.quality.voice_check === 'PASS'
                                      ? 'var(--verdict-pass-bg)'
                                      : 'var(--verdict-fail-bg)',
                                  color:
                                    item.quality.voice_check === 'PASS'
                                      ? 'var(--verdict-pass-text)'
                                      : 'var(--verdict-fail-text)',
                                }}
                              >
                                {item.quality.voice_check}
                              </span>
                            )}
                          </div>
                          <p
                            className="text-xs mt-1"
                            style={{ color: 'var(--text-tertiary)' }}
                          >
                            {assetLabels[item.content_type] ?? item.content_type.replace(/_/g, ' ')}
                            {detail?.char_count ? ` · ${detail.char_count} chars` : ''}
                          </p>
                          <p
                            className="text-sm mt-3 leading-relaxed whitespace-pre-wrap"
                            style={{
                              color: 'var(--text-secondary)',
                              maxHeight: '10rem',
                              overflow: 'hidden',
                            }}
                          >
                            {textPreview(detail)}
                          </p>
                        </article>
                      );
                    })}
                  </div>
                </section>
              </div>
            </section>
          )}

          <section className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {countCards.map(({ label, value, color }, i) => (
                <div
                  key={label}
                  className={`rounded-lg px-4 py-3 animate-fade-in stagger-${i + 1}`}
                  style={{
                    border: '1px solid var(--border-default)',
                    background: 'var(--surface-raised)',
                  }}
                >
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
                  <p className="text-xl font-bold mt-1" style={{ color }}>{value}</p>
                </div>
              ))}
            </div>
          </section>

          <ContentKanban
            items={items}
            maxPerColumn={6}
            title="Thought sets for review"
            description="Open one generated output inside a thought set to inspect copy, visuals, destination, quality, and schedule state."
          />

          {systemGroups.length > 0 && (
            <details
              className="rounded-lg overflow-hidden animate-fade-in"
              style={{
                border: '1px solid var(--border-default)',
                background: 'var(--surface-raised)',
              }}
            >
              <summary
                className="px-5 py-4 cursor-pointer list-none focus-ring"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p
                      className="text-xs font-semibold uppercase"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Holus operating system
                    </p>
                    <h2 className="text-base font-semibold mt-1" style={{ color: 'var(--text-primary)' }}>
                      Agent wiring and prompt health
                    </h2>
                    <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                      Registered agents, current-run trace, model lanes, prompt versions, evaluators, and missing telemetry.
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xl font-bold" style={{ color: 'var(--brand)' }}>{agents.length}</p>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {activeAgents} active · {plannedAgents} planned
                    </p>
                  </div>
                </div>
              </summary>

              <div className="space-y-4 p-4">
                <section
                  className="rounded-lg p-4"
                  style={{ border: '1px solid var(--border-default)', background: 'var(--surface-2)' }}
                >
                  <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                    {[
                      { label: 'Registered', value: agents.length, note: 'AGENTS.yaml entries' },
                      { label: 'Ran here', value: involvedAgents.length, note: 'current thought trace' },
                      { label: 'Active not used', value: activeNotUsedAgents.length, note: 'available but not routed' },
                      { label: 'Judges', value: evaluatorAgents.length, note: 'mostly idle in this path' },
                      { label: 'No stored telemetry', value: noTelemetryAgents.length, note: 'missing durable run/eval history' },
                    ].map((card) => (
                      <div
                        key={card.label}
                        className="rounded-lg px-3 py-2"
                        style={{ border: '1px solid var(--border-default)', background: 'var(--surface-raised)' }}
                      >
                        <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{card.label}</p>
                        <p className="mt-1 text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{card.value}</p>
                        <p className="mt-1 text-xs leading-snug" style={{ color: 'var(--text-tertiary)' }}>{card.note}</p>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-3">
                    <div>
                      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        What happened in this run
                      </h3>
                      <p className="mt-1 text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                        Thought Studio used a deterministic pipeline and stamped specialist names into
                        the trace. It did not spin up every registered prompt as an independent model call.
                      </p>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        Why agents look idle
                      </h3>
                      <p className="mt-1 text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                        Many agents are prompt definitions or planned capabilities. They need router rules,
                        model lanes, evaluator calls, and trajectory writes before they count as working agents.
                      </p>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        Hard-mode wiring target
                      </h3>
                      <p className="mt-1 text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                        Add prompt-version experiments, evaluator rubrics, model-backed judge passes,
                        cost/latency logging, and per-agent pass/fail history for each generated output.
                      </p>
                    </div>
                  </div>
                </section>

                <section className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <div
                    className="rounded-lg p-4"
                    style={{ border: '1px solid var(--border-default)', background: 'var(--surface-2)' }}
                  >
                    <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                      Model lanes
                    </h3>
                    <div className="mt-3 space-y-2">
                      {modelLanes.map((lane) => (
                        <div key={lane.lane} className="flex items-center justify-between gap-3 text-xs">
                          <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{lane.lane}</span>
                          <span className="px-2 py-0.5 rounded" style={{ background: 'var(--brand-subtle)', color: 'var(--brand)' }}>
                            {lane.count}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div
                    className="rounded-lg p-4"
                    style={{ border: '1px solid var(--border-default)', background: 'var(--surface-2)' }}
                  >
                    <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                      Prompt versioning gaps
                    </h3>
                    <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {agents.slice(0, 8).map((agent) => (
                        <div
                          key={agent.id}
                          className="rounded px-3 py-2"
                          style={{ border: '1px solid var(--border-default)', background: 'var(--surface-raised)' }}
                        >
                          <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{agent.id}</p>
                          <p className="mt-0.5 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                            v{agent.version ?? 'unversioned'} · {agent.prompt_path ?? 'prompt path missing'}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
                {systemGroups.map((group) => (
                  <section
                    key={group.name}
                    className="rounded-lg p-3"
                    style={{
                      border: '1px solid var(--border-default)',
                      background: 'var(--surface-2)',
                    }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {group.name}
                        </h3>
                        <p className="text-xs mt-1 leading-snug" style={{ color: 'var(--text-tertiary)' }}>
                          {systemGroupCopy[group.name]}
                        </p>
                      </div>
                      <span
                        className="text-xs px-2 py-0.5 rounded font-medium"
                        style={{ background: 'var(--brand-subtle)', color: 'var(--brand)' }}
                      >
                        {group.agents.length}
                      </span>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {group.agents.map((agent) => {
                        const involved = involvedIds.has(agent.id);
                        const planned = agent.registry_status === 'planned';
                        const runtime = agentRuntimeState(agent, involvedIds);
                        return (
                          <span
                            key={agent.id}
                            className="text-xs px-2 py-1 rounded font-medium"
                            title={`${agent.role} ${runtime.issue} Prompt: ${agent.prompt_path ?? 'missing'} v${agent.version ?? 'unknown'}`}
                            style={{
                              border: involved
                                ? '1px solid var(--brand)'
                                : '1px solid var(--border-default)',
                              background: involved
                                ? 'var(--brand-subtle)'
                                : planned
                                  ? 'var(--surface-raised)'
                                  : 'var(--surface-1)',
                              color: involved
                                ? 'var(--brand)'
                                : planned
                                  ? 'var(--text-tertiary)'
                                  : 'var(--text-secondary)',
                            }}
                          >
                            {agent.name || agent.id}
                            {agent.is_gate ? ' gate' : ''}
                            <span className="ml-1 px-1 rounded" style={runtime.style}>
                              {runtime.label}
                            </span>
                          </span>
                        );
                      })}
                    </div>
                  </section>
                ))}
                </div>
              </div>
            </details>
          )}
        </>
      )}
      </div>
    </div>
  );
}

// Typed fetch wrappers for Observatory API (spec 028)
// Falls back to demo data when the API is unreachable (e.g. on Vercel deployment)

import type {
  Agent,
  AgentStatus,
  AgentDetail,
  HealthStatus,
  KPIMetrics,
  ModelTier,
  ServiceStatus,
  EvaluationRecord,
  ContentItem,
  ContentDetail,
  ContentResponse,
  CreateContentRequest,
  CreateContentResponse,
  PatchContentRequest,
  KnowledgeFile,
  CostBreakdown,
  GrowthData,
  MemoryContent,
  LessonsResponse,
} from './types';
import { isPublicOrDemoSurface } from './connection';
import {
  demoAgents,
  demoMetrics,
  demoEvaluations,
  demoContent,
  demoKnowledge,
  demoGrowthData,
  demoMemoryContent,
  demoLessons,
  demoDimensionAverages,
} from './demo-data';

// Server-side: use full URL to reach the API directly
// Client-side: use relative URL so Next.js rewrites proxy it through port 3000
const API_BASE_SERVER =
  process.env.NEXT_PUBLIC_OBSERVATORY_URL || 'http://localhost:8003';
const isServer = typeof window === 'undefined';

function inferModelTier(model?: string): ModelTier {
  const normalized = model?.toLowerCase() ?? '';
  if (normalized.includes('opus')) return 'opus';
  if (normalized.includes('sonnet')) return 'sonnet';
  if (normalized.includes('haiku')) return 'haiku';
  return 'unknown';
}

function inferAgentStatus(raw: Record<string, unknown>): AgentStatus {
  const status = String(raw.status ?? raw.last_status ?? '').toLowerCase();
  if (['active', 'idle', 'running', 'error', 'disabled', 'planned'].includes(status)) {
    return status as AgentStatus;
  }
  if (['failed', 'fail', 'failure'].includes(status)) return 'error';
  if (status === 'success') return 'idle';
  return Number(raw.run_count_7d ?? 0) > 0 ? 'active' : 'idle';
}

function normalizeAgent(raw: Partial<Agent> & Record<string, unknown>): Agent {
  const model = String(raw.model ?? '');
  return {
    id: String(raw.id ?? ''),
    name: String(raw.name ?? raw.id ?? 'unknown-agent'),
    role: String(raw.role ?? ''),
    type: String(raw.type ?? 'agent'),
    status: inferAgentStatus(raw),
    model,
    model_tier: (raw.model_tier as ModelTier | undefined) ?? inferModelTier(model),
    category: raw.category as string | undefined,
    registry_status: raw.status as string | undefined,
    is_gate: Boolean(raw.is_gate),
    evaluated_by: Array.isArray(raw.evaluated_by) ? raw.evaluated_by.map(String) : [],
    evaluates_with: Array.isArray(raw.evaluates_with) ? raw.evaluates_with.map(String) : [],
    version: raw.version as string | undefined,
    prompt_path: raw.prompt_path as string | undefined,
    last_run: raw.last_run as string | undefined,
    last_status: raw.last_status as string | undefined,
    run_count_7d: Number(raw.run_count_7d ?? 0),
    description: raw.description as string | undefined,
  };
}

function normalizeHealth(raw: Partial<HealthStatus> & Record<string, unknown>): HealthStatus {
  const timestamp = String(raw.timestamp ?? new Date().toISOString());
  const services: ServiceStatus[] = Array.isArray(raw.services)
    ? (raw.services as ServiceStatus[])
    : [
        {
          name: 'Trajectory Log',
          status: raw.trajectory_file_exists ? 'up' : 'down',
          last_checked: timestamp,
        },
        {
          name: 'Agent Registry',
          status: raw.agents_yaml_exists ? 'up' : 'down',
          last_checked: timestamp,
        },
        {
          name: 'Evaluation History',
          status: raw.eval_history_file_exists ? 'up' : 'degraded',
          last_checked: timestamp,
        },
        {
          name: 'Content Queue',
          status: Number(raw.content_queue_count ?? 0) > 0 ? 'up' : 'degraded',
          last_checked: timestamp,
        },
      ];
  const hasDownService = services.some((service) => service.status === 'down');
  const status =
    raw.status ?? (raw.kill_switch_active || hasDownService ? 'degraded' : 'healthy');

  return {
    status: status as HealthStatus['status'],
    kill_switch_active:
      typeof raw.kill_switch_active === 'boolean' ? raw.kill_switch_active : undefined,
    kill_switch_activated_at: raw.kill_switch_activated_at as string | undefined,
    services,
    timestamp,
  };
}

function normalizeMetrics(raw: Partial<KPIMetrics> & Record<string, unknown>): KPIMetrics {
  return {
    cycles_this_week: Number(raw.cycles_this_week ?? raw.total_cycles ?? 0),
    success_rate: Number(raw.success_rate ?? 0),
    avg_quality_score: Number(raw.avg_quality_score ?? 0),
    total_cost_usd: Number(raw.total_cost_usd ?? 0),
    sparkline: Array.isArray(raw.sparkline) ? raw.sparkline : [],
  };
}

function freshnessFor(modifiedAt: string): KnowledgeFile['freshness'] {
  const ageMs = Date.now() - new Date(modifiedAt).getTime();
  const ageDays = ageMs / 86_400_000;
  if (!Number.isFinite(ageDays) || ageDays < 0) return 'fresh';
  if (ageDays <= 14) return 'fresh';
  if (ageDays <= 45) return 'aging';
  return 'stale';
}

function normalizeKnowledgeFile(raw: Partial<KnowledgeFile> & Record<string, unknown>): KnowledgeFile {
  const name = String(raw.name ?? raw.filename ?? raw.path ?? 'unknown.md');
  const modifiedAt = String(raw.modified_at ?? raw.last_modified ?? new Date(0).toISOString());
  return {
    path: String(raw.path ?? name),
    name,
    modified_at: modifiedAt,
    size_bytes: Number(raw.size_bytes ?? 0),
    freshness: (raw.freshness as KnowledgeFile['freshness'] | undefined) ?? freshnessFor(modifiedAt),
  };
}

async function apiFetch<T>(
  path: string,
  options?: RequestInit & { revalidate?: number }
): Promise<T> {
  const { revalidate, ...fetchOptions } = options ?? {};
  const base = isServer ? API_BASE_SERVER : '';
  const fetchOpts: RequestInit = { ...fetchOptions };
  // next.revalidate only works server-side
  if (isServer) {
    (fetchOpts as Record<string, unknown>).next = { revalidate: revalidate ?? 30 };
  }
  const res = await fetch(`${base}${path}`, fetchOpts);
  if (!res.ok) {
    throw new Error(`API error ${res.status} for ${path}`);
  }
  return res.json() as Promise<T>;
}

async function withFallback<T>(fetcher: () => Promise<T>, fallback: T): Promise<T> {
  if (isPublicOrDemoSurface()) return fallback;
  try {
    return await fetcher();
  } catch {
    return fallback;
  }
}

const DISCONNECTED_HEALTH: HealthStatus = {
  status: 'down',
  services: [
    { name: 'Authenticated Observatory backend', status: 'down', last_checked: '2026-01-01T00:00:00.000Z' },
    { name: 'Generation BFF', status: 'down', last_checked: '2026-01-01T00:00:00.000Z' },
    { name: 'Live event stream', status: 'down', last_checked: '2026-01-01T00:00:00.000Z' },
  ],
  timestamp: '2026-01-01T00:00:00.000Z',
};

// Health
export async function fetchHealth(): Promise<HealthStatus> {
  return withFallback(async () => {
    const raw = await apiFetch<Partial<HealthStatus> & Record<string, unknown>>(
      '/api/v1/health',
      { revalidate: 0 },
    );
    return normalizeHealth(raw);
  }, DISCONNECTED_HEALTH);
}

// Agents list
export async function fetchAgents(): Promise<Agent[]> {
  return withFallback(async () => {
    const raw = await apiFetch<(Partial<Agent> & Record<string, unknown>)[]>('/api/v1/agents', {
      revalidate: 0,
    });
    return raw.map(normalizeAgent);
  }, demoAgents);
}

// Agent detail
export async function fetchAgent(id: string): Promise<AgentDetail> {
  const agent = demoAgents.find((a) => a.id === id);
  const fallback: AgentDetail = {
    ...(agent ?? demoAgents[0]),
    cycles: [],
    recent_scores: [7.2, 8.1, 6.9, 7.8, 8.4],
    dimension_averages: demoDimensionAverages[id] ?? {},
  };
  return withFallback(
    async () => {
      const raw = await apiFetch<Partial<AgentDetail> & Record<string, unknown>>(
        `/api/v1/agents/${id}`,
      );
      return {
        ...normalizeAgent(raw),
        cycles: Array.isArray(raw.cycles) ? raw.cycles : [],
        recent_scores: Array.isArray(raw.recent_scores) ? raw.recent_scores : [],
        dimension_averages:
          (raw.dimension_averages as Record<string, number> | undefined) ?? {},
      };
    },
    fallback,
  );
}

// KPI metrics (dashboard)
export async function fetchMetrics(): Promise<KPIMetrics> {
  return withFallback(async () => {
    const raw = await apiFetch<Partial<KPIMetrics> & Record<string, unknown>>('/api/v1/metrics');
    return normalizeMetrics(raw);
  }, demoMetrics);
}

// Evaluations
export async function fetchEvaluations(params?: {
  agent_id?: string;
  days?: number;
}): Promise<EvaluationRecord[]> {
  const qs = new URLSearchParams();
  if (params?.agent_id) qs.set('agent_id', params.agent_id);
  if (params?.days) qs.set('days', String(params.days));
  const query = qs.toString() ? `?${qs.toString()}` : '';
  let fallback = demoEvaluations;
  if (params?.agent_id) {
    fallback = fallback.filter((e) => e.agent_id === params.agent_id);
  }
  return withFallback(
    async () => {
      const resp = await apiFetch<unknown>(`/api/v1/evaluations${query}`);
      const raw = Array.isArray(resp) ? resp : (resp as Record<string, unknown>).evaluations ?? [];
      // Normalize API shape to EvaluationRecord
      return (raw as Record<string, unknown>[]).map((e, i) => ({
        id: String(e.id ?? `eval-${i}`),
        agent_id: String(e.agent_id ?? 'unknown'),
        agent_name: String(e.agent_name ?? e.agent_id ?? 'unknown'),
        date: String(e.date ?? e.timestamp ?? ''),
        score: Number(e.score ?? 0),
        verdict: (e.passed ? 'pass' : 'fail') as EvaluationRecord['verdict'],
        evaluator: e.evaluator as string | undefined,
        notes: e.notes as string | undefined,
      }));
    },
    fallback,
  );
}

// Content pipeline
export async function fetchContent(): Promise<ContentItem[]> {
  return withFallback(
    async () => {
      const resp = await apiFetch<ContentResponse>('/api/v1/content', { revalidate: 0 });
      return resp.items;
    },
    demoContent,
  );
}

// Create platform drafts from one thought. This only queues drafts for review.
const PUBLIC_MUTATION_BLOCKED =
  'Live drafting requires an authenticated Holus backend. No request was sent.';

function demoContentDetail(id: string): ContentDetail {
  const item = demoContent.find((entry) => entry.id === id) ?? demoContent[0];
  return {
    ...item,
    text: 'Demonstration draft. Labelled demonstration state, not a live generation artifact.',
    agent_trace: [],
  };
}

export async function createContentFromThought(
  body: CreateContentRequest,
): Promise<CreateContentResponse> {
  if (isPublicOrDemoSurface()) {
    throw new Error(PUBLIC_MUTATION_BLOCKED);
  }
  const res = await fetch('/api/v1/content/from-thought', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`POST /content/from-thought → ${res.status}: ${msg}`);
  }
  return res.json() as Promise<CreateContentResponse>;
}

// Content detail (full text + agent trace)
export async function fetchContentDetail(id: string): Promise<ContentDetail> {
  return withFallback(
    () => apiFetch<ContentDetail>(`/api/v1/content/${id}`, { revalidate: 0 }),
    demoContentDetail(id),
  );
}

// Approve / reject / reschedule a content piece (client-side, no cache)
export async function patchContent(
  id: string,
  body: PatchContentRequest,
): Promise<ContentDetail> {
  if (isPublicOrDemoSurface()) {
    throw new Error(PUBLIC_MUTATION_BLOCKED);
  }
  const res = await fetch(`/api/v1/content/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`PATCH /content/${id} → ${res.status}: ${msg}`);
  }
  return res.json() as Promise<ContentDetail>;
}

// Choose A/B visual variant
export async function chooseVisual(
  id: string,
  variant: 'a' | 'b',
): Promise<ContentDetail> {
  if (isPublicOrDemoSurface()) {
    throw new Error(PUBLIC_MUTATION_BLOCKED);
  }
  const res = await fetch(`/api/v1/content/${id}/visual-choice?variant=${variant}`, {
    method: 'PATCH',
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`PATCH visual-choice → ${res.status}: ${msg}`);
  }
  return res.json() as Promise<ContentDetail>;
}

// Image URL helper
export function contentImageUrl(pieceId: string, variant: 'a' | 'b' = 'a'): string {
  return `/api/v1/content/${pieceId}/image${variant === 'b' ? '?variant=b' : ''}`;
}

export function contentPdfUrl(pieceId: string): string {
  return `/api/v1/content/${pieceId}/pdf`;
}

// Knowledge files
export async function fetchKnowledge(): Promise<KnowledgeFile[]> {
  return withFallback(
    async () => {
      const resp = await apiFetch<
        | (Partial<KnowledgeFile> & Record<string, unknown>)[]
        | { files: (Partial<KnowledgeFile> & Record<string, unknown>)[] }
      >('/api/v1/knowledge');
      const files = Array.isArray(resp) ? resp : resp.files ?? [];
      return files.map(normalizeKnowledgeFile);
    },
    demoKnowledge,
  );
}

// Cost breakdown
export async function fetchCosts(): Promise<CostBreakdown[]> {
  return withFallback(
    () => apiFetch<CostBreakdown[]>('/api/v1/costs'),
    [],
  );
}

export { trajectoryStreamUrl } from './connection';

// Is demo / public surface active?
export function isDemoMode(): boolean {
  return isPublicOrDemoSurface();
}

// Results / Growth
export async function fetchResults(): Promise<GrowthData> {
  return withFallback(
    () => apiFetch<GrowthData>('/api/v1/results'),
    demoGrowthData,
  );
}

// Knowledge — MEMORY.md content
export async function fetchMemoryContent(): Promise<MemoryContent | null> {
  return withFallback(
    () => apiFetch<MemoryContent>('/api/v1/knowledge/memory/content'),
    demoMemoryContent,
  );
}

// Knowledge — recent lessons
export async function fetchLessons(limit = 20): Promise<LessonsResponse> {
  return withFallback(
    () => apiFetch<LessonsResponse>(`/api/v1/knowledge/lessons/recent?limit=${limit}`),
    demoLessons,
  );
}

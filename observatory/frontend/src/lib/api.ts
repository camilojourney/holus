// Typed fetch wrappers for Observatory API (spec 028)
// Falls back to demo data when the API is unreachable (e.g. on Vercel deployment)

import type {
  Agent,
  AgentDetail,
  HealthStatus,
  KPIMetrics,
  EvaluationRecord,
  ContentItem,
  ContentDetail,
  ContentResponse,
  PatchContentRequest,
  KnowledgeFile,
  CostBreakdown,
  GrowthData,
  MemoryContent,
  LessonsResponse,
} from './types';
import {
  demoAgents,
  demoHealth,
  demoMetrics,
  demoEvaluations,
  demoContent,
  demoKnowledge,
  demoGrowthData,
  demoMemoryContent,
  demoLessons,
  demoDimensionAverages,
} from './demo-data';

const API_BASE =
  process.env.NEXT_PUBLIC_OBSERVATORY_URL || 'http://localhost:8001';

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === 'true' || !process.env.NEXT_PUBLIC_OBSERVATORY_URL;

async function apiFetch<T>(
  path: string,
  options?: RequestInit & { revalidate?: number }
): Promise<T> {
  const { revalidate, ...fetchOptions } = options ?? {};
  const res = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    next: { revalidate: revalidate ?? 30 },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status} for ${path}`);
  }
  return res.json() as Promise<T>;
}

async function withFallback<T>(fetcher: () => Promise<T>, fallback: T): Promise<T> {
  if (DEMO_MODE) return fallback;
  try {
    return await fetcher();
  } catch {
    return fallback;
  }
}

// Health
export async function fetchHealth(): Promise<HealthStatus> {
  return withFallback(
    () => apiFetch<HealthStatus>('/api/v1/health', { revalidate: 0 }),
    demoHealth,
  );
}

// Agents list
export async function fetchAgents(): Promise<Agent[]> {
  return withFallback(
    () => apiFetch<Agent[]>('/api/v1/agents'),
    demoAgents,
  );
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
    () => apiFetch<AgentDetail>(`/api/v1/agents/${id}`),
    fallback,
  );
}

// KPI metrics (dashboard)
export async function fetchMetrics(): Promise<KPIMetrics> {
  return withFallback(
    () => apiFetch<KPIMetrics>('/api/v1/metrics'),
    demoMetrics,
  );
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
    () => apiFetch<EvaluationRecord[]>(`/api/v1/evaluations${query}`),
    fallback,
  );
}

// Content pipeline
export async function fetchContent(): Promise<ContentItem[]> {
  return withFallback(
    async () => {
      const resp = await apiFetch<ContentResponse>('/api/v1/content');
      return resp.items;
    },
    demoContent,
  );
}

// Content detail (full text + agent trace)
export async function fetchContentDetail(id: string): Promise<ContentDetail> {
  return apiFetch<ContentDetail>(`/api/v1/content/${id}`, { revalidate: 0 });
}

// Approve / reject / reschedule a content piece (client-side, no cache)
export async function patchContent(
  id: string,
  body: PatchContentRequest,
): Promise<ContentDetail> {
  const base = process.env.NEXT_PUBLIC_OBSERVATORY_URL || 'http://localhost:8001';
  const res = await fetch(`${base}/api/v1/content/${id}`, {
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
  const base = process.env.NEXT_PUBLIC_OBSERVATORY_URL || 'http://localhost:8001';
  const res = await fetch(`${base}/api/v1/content/${id}/visual-choice?variant=${variant}`, {
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
  const base = process.env.NEXT_PUBLIC_OBSERVATORY_URL || 'http://localhost:8001';
  return `${base}/api/v1/content/${pieceId}/image${variant === 'b' ? '?variant=b' : ''}`;
}

// Knowledge files
export async function fetchKnowledge(): Promise<KnowledgeFile[]> {
  return withFallback(
    () => apiFetch<KnowledgeFile[]>('/api/v1/knowledge'),
    demoKnowledge,
  );
}

// Cost breakdown
export async function fetchCosts(): Promise<CostBreakdown[]> {
  return withFallback(
    () => apiFetch<CostBreakdown[]>('/api/v1/costs'),
    [
      { agent_id: 'marketing-strategist', agent_name: 'Marketing Strategist', cost_usd: 1.42, percentage: 37.2 },
      { agent_id: 'blog-writer', agent_name: 'Blog Writer', cost_usd: 0.89, percentage: 23.3 },
      { agent_id: 'judge-agent', agent_name: 'Judge Agent', cost_usd: 0.64, percentage: 16.8 },
      { agent_id: 'seo-researcher', agent_name: 'SEO Researcher', cost_usd: 0.52, percentage: 13.6 },
      { agent_id: 'hook-architect', agent_name: 'Hook Architect', cost_usd: 0.35, percentage: 9.1 },
    ],
  );
}

// SSE stream URL (used directly by EventSource)
export function trajectoryStreamUrl(): string {
  return `${API_BASE}/api/v1/trajectory/stream`;
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

// Is demo mode active?
export function isDemoMode(): boolean {
  return DEMO_MODE;
}

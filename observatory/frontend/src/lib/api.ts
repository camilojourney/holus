// Typed fetch wrappers for Observatory API (spec 028)
// All calls go to NEXT_PUBLIC_OBSERVATORY_URL (default: http://localhost:8001)

import type {
  Agent,
  AgentDetail,
  HealthStatus,
  KPIMetrics,
  EvaluationRecord,
  ContentItem,
  KnowledgeFile,
  CostBreakdown,
} from './types';

const API_BASE =
  process.env.NEXT_PUBLIC_OBSERVATORY_URL || 'http://localhost:8001';

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

// Health — no cache (always fresh)
export async function fetchHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>('/api/v1/health', { revalidate: 0 });
}

// Agents list
export async function fetchAgents(): Promise<Agent[]> {
  return apiFetch<Agent[]>('/api/v1/agents');
}

// Agent detail
export async function fetchAgent(id: string): Promise<AgentDetail> {
  return apiFetch<AgentDetail>(`/api/v1/agents/${id}`);
}

// KPI metrics (dashboard)
export async function fetchMetrics(): Promise<KPIMetrics> {
  return apiFetch<KPIMetrics>('/api/v1/metrics');
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
  return apiFetch<EvaluationRecord[]>(`/api/v1/evaluations${query}`);
}

// Content pipeline
export async function fetchContent(): Promise<ContentItem[]> {
  return apiFetch<ContentItem[]>('/api/v1/content');
}

// Knowledge files
export async function fetchKnowledge(): Promise<KnowledgeFile[]> {
  return apiFetch<KnowledgeFile[]>('/api/v1/knowledge');
}

// Cost breakdown
export async function fetchCosts(): Promise<CostBreakdown[]> {
  return apiFetch<CostBreakdown[]>('/api/v1/costs');
}

// SSE stream URL (used directly by EventSource)
export function trajectoryStreamUrl(): string {
  return `${API_BASE}/api/v1/trajectory/stream`;
}

// Shared response types — mirrors Observatory API schema (spec 028)

export type AgentStatus = 'active' | 'idle' | 'running' | 'error' | 'disabled' | 'planned';
export type ModelTier = 'opus' | 'sonnet' | 'haiku' | 'unknown';
export type EvalVerdict = 'pass' | 'review' | 'fail';
export type ContentState = 'DRAFT' | 'REVIEW' | 'PUBLISHED';
export type FreshnessStatus = 'fresh' | 'aging' | 'stale';

export interface Agent {
  id: string;
  name: string;
  role: string;
  type: string;
  status: AgentStatus;
  model: string;
  model_tier: ModelTier;
  version?: string;
  description?: string;
}

export interface AgentDetail extends Agent {
  cycles: CycleRecord[];
  recent_scores: number[];
}

export interface CycleRecord {
  id: string;
  agent_id: string;
  timestamp: string;
  status: 'success' | 'failed' | 'skipped';
  quality_score?: number;
  cost_usd?: number;
  duration_seconds?: number;
  verdict?: EvalVerdict;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'down';
  kill_switch_active: boolean;
  kill_switch_activated_at?: string;
  services: ServiceStatus[];
  timestamp: string;
}

export interface ServiceStatus {
  name: string;
  status: 'up' | 'down' | 'degraded';
  latency_ms?: number;
  last_checked: string;
}

export interface KPIMetrics {
  cycles_this_week: number;
  success_rate: number;
  avg_quality_score: number;
  total_cost_usd: number;
  sparkline: DailyCount[];
}

export interface DailyCount {
  date: string;
  count: number;
}

export interface EvaluationRecord {
  id: string;
  agent_id: string;
  agent_name: string;
  date: string;
  score: number;
  verdict: EvalVerdict;
  evaluator?: string;
  notes?: string;
}

export interface ContentItem {
  id: string;
  title: string;
  platform: string;
  pillar: 'authority' | 'entertainment' | 'education' | 'conversion';
  state: ContentState;
  created_at: string;
  scheduled_at?: string;
  published_at?: string;
}

export interface KnowledgeFile {
  path: string;
  name: string;
  modified_at: string;
  size_bytes: number;
  freshness: FreshnessStatus;
}

export interface TrajectoryEvent {
  id: string;
  timestamp: string;
  agent_name: string;
  event_type: string;
  description: string;
  metadata?: Record<string, unknown>;
}

export interface CostBreakdown {
  agent_id: string;
  agent_name: string;
  cost_usd: number;
  percentage: number;
}

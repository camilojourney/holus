// Shared response types — mirrors Observatory API schema (spec 028)

export type AgentStatus = 'active' | 'idle' | 'running' | 'error' | 'disabled' | 'planned';
export type ModelTier = 'opus' | 'sonnet' | 'haiku' | 'unknown';
export type EvalVerdict = 'pass' | 'review' | 'fail';
export type ContentState = 'DRAFT' | 'REVIEW' | 'PUBLISHED';
export type FreshnessStatus = 'fresh' | 'aging' | 'stale';
export type ContentStatus = 'draft' | 'pending_review' | 'approved' | 'scheduled' | 'published' | 'rejected';

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
  dimension_averages?: Record<string, number>;
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

export interface AgentTraceStep {
  agent_id: string;
  model?: string;
  role?: string;
  at?: string;
  quality_score?: string;
  verdict?: string;
}

export interface ContentQuality {
  hook_score?: string;
  voice_check?: string;
  quality_score?: number;
  violations?: string[];
}

export interface ContentItem {
  id: string;
  title?: string;
  content_type: string;
  platform?: string;
  content_pillar?: string;
  status: string; // 'draft' | 'pending_review' | 'approved' | 'scheduled' | 'published' | 'rejected'
  created_at?: string;
  scheduled_for?: string;
  agent_id?: string;
  idea_source?: string;
  quality?: ContentQuality;
}

export interface ContentDetail extends ContentItem {
  text?: string;
  hashtags?: string[];
  char_count?: number;
  agent_trace?: AgentTraceStep[];
}

export interface ContentStatusCounts {
  draft: number;
  review: number;
  published: number;
  rejected: number;
}

export interface ContentResponse {
  items: ContentItem[];
  counts: ContentStatusCounts;
}

export interface PatchContentRequest {
  status?: string;
  scheduled_at?: string;
}

export interface KnowledgeFile {
  path: string;
  name: string;
  modified_at: string;
  size_bytes: number;
  freshness: FreshnessStatus;
}

export interface MemoryContent {
  content: string;
  last_modified: string;
  size_bytes: number;
}

export interface LessonEntry {
  id: string;
  date?: string;
  lesson?: string;
  source?: string;
  agent_id?: string;
  category?: string;
  context?: string;
}

export interface LessonsResponse {
  lessons: LessonEntry[];
  total: number;
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

// --- Results / Growth types ---

export interface PlatformStats {
  followers: number;
  followers_30d_ago: number;
  posts_30d: number;
  impressions_30d: number;
  engagement_rate: number;
  top_content_type: string;
  profile_url?: string;
}

export interface DailyGrowth {
  date: string;
  total_followers: number;
  posts: number;
  impressions: number;
}

export interface TopPost {
  id: string;
  title: string;
  platform: string;
  published_at: string;
  impressions: number;
  likes: number;
  comments: number;
  shares: number;
  engagement_rate: number;
  content_type: string;
  product: string;
}

export interface PillarStats {
  count: number;
  avg_engagement_rate: number;
  total_impressions: number;
}

export interface ProductStats {
  count: number;
  total_impressions: number;
  avg_engagement_rate: number;
}

export interface GrowthData {
  snapshot_date: string;
  platforms: Record<string, PlatformStats>;
  daily_growth: DailyGrowth[];
  top_posts: TopPost[];
  content_by_pillar: Record<string, PillarStats>;
  content_by_product: Record<string, ProductStats>;
}

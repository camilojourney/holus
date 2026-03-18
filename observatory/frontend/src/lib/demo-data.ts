// Demo data for recruiter-facing deployment (no backend API needed)
// Provides realistic mock data so Observatory looks alive on Vercel

import type {
  Agent,
  HealthStatus,
  KPIMetrics,
  EvaluationRecord,
  ContentItem,
  KnowledgeFile,
  TrajectoryEvent,
  GrowthData,
  MemoryContent,
  LessonsResponse,
} from './types';

// --- Agents ---

export const demoAgents: Agent[] = [
  {
    id: 'marketing-strategist',
    name: 'Marketing Strategist',
    role: 'Strategy & decisions',
    type: 'manager',
    status: 'active',
    model: 'claude-opus-4-6',
    model_tier: 'opus',
    description: 'Primary agent. Observes analytics, decides content strategy, calls silo tools.',
  },
  {
    id: 'hook-architect',
    name: 'Hook Architect',
    role: 'Opening hooks',
    type: 'specialist',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Writes attention-grabbing hooks for posts and videos.',
  },
  {
    id: 'seo-researcher',
    name: 'SEO Researcher',
    role: 'Keyword research',
    type: 'specialist',
    status: 'idle',
    model: 'gemini-2.5-pro',
    model_tier: 'unknown',
    description: 'Researches keywords, competitor content, and search trends.',
  },
  {
    id: 'blog-writer',
    name: 'Blog Writer',
    role: 'Long-form content',
    type: 'specialist',
    status: 'running',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Writes technical blog posts and tutorials.',
  },
  {
    id: 'carousel-architect',
    name: 'Carousel Architect',
    role: 'Visual carousels',
    type: 'specialist',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Designs LinkedIn/Instagram carousel slide sequences.',
  },
  {
    id: 'narrative-specialist',
    name: 'Narrative Specialist',
    role: 'Storytelling',
    type: 'specialist',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Crafts narrative arcs for case studies and founder stories.',
  },
  {
    id: 'tutorial-specialist',
    name: 'Tutorial Specialist',
    role: 'Technical tutorials',
    type: 'specialist',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Creates step-by-step technical tutorials for products.',
  },
  {
    id: 'proof-agent',
    name: 'Proof Agent',
    role: 'Social proof',
    type: 'specialist',
    status: 'idle',
    model: 'claude-haiku-4-5',
    model_tier: 'haiku',
    description: 'Finds and formats testimonials, metrics, and case study evidence.',
  },
  {
    id: 'written-content-judge',
    name: 'Written Content Judge',
    role: 'Quality evaluation',
    type: 'evaluator',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Evaluates text content using domain-specific rubrics.',
  },
  {
    id: 'visual-content-judge',
    name: 'Visual Content Judge',
    role: 'Visual evaluation',
    type: 'evaluator',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Evaluates carousels, images, and visual layouts.',
  },
  {
    id: 'brand-safety-judge',
    name: 'Brand Safety Judge',
    role: 'Safety review',
    type: 'evaluator',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Checks content against brand guidelines and safety rules.',
  },
  {
    id: 'judge-agent',
    name: 'Judge Agent',
    role: 'Evaluation routing',
    type: 'evaluator',
    status: 'active',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Routes content to domain-specific evaluators based on content type.',
  },
  {
    id: 'code-improver',
    name: 'Code Improver',
    role: 'Code quality',
    type: 'ops',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Improves code quality, test coverage, and documentation.',
  },
  {
    id: 'security-sentinel',
    name: 'Security Sentinel',
    role: 'Security audit',
    type: 'ops',
    status: 'idle',
    model: 'claude-sonnet-4-6',
    model_tier: 'sonnet',
    description: 'Scans for credentials, vulnerabilities, and policy violations.',
  },
  {
    id: 'knowledge-keeper',
    name: 'Knowledge Keeper',
    role: 'Learning loop',
    type: 'ops',
    status: 'idle',
    model: 'claude-haiku-4-5',
    model_tier: 'haiku',
    description: 'Maintains system memory, lessons, and knowledge files.',
  },
  {
    id: 'manager',
    name: 'Manager',
    role: 'Self-improvement',
    type: 'manager',
    status: 'active',
    model: 'claude-opus-4-6',
    model_tier: 'opus',
    description: 'Orchestrates self-improvement cycles and coordinates workers.',
  },
];

// --- Health ---

export const demoHealth: HealthStatus = {
  status: 'healthy',
  kill_switch_active: false,
  services: [
    { name: 'Observatory API', status: 'up', latency_ms: 12, last_checked: new Date().toISOString() },
    { name: 'Social Media MCP', status: 'up', latency_ms: 45, last_checked: new Date().toISOString() },
    { name: 'Pilaster MCP', status: 'up', latency_ms: 38, last_checked: new Date().toISOString() },
    { name: 'Genpeli MCP', status: 'up', latency_ms: 52, last_checked: new Date().toISOString() },
    { name: 'Redis Event Bus', status: 'up', latency_ms: 3, last_checked: new Date().toISOString() },
  ],
  timestamp: new Date().toISOString(),
};

// --- KPI Metrics ---

export const demoMetrics: KPIMetrics = {
  cycles_this_week: 14,
  success_rate: 0.857,
  avg_quality_score: 7.4,
  total_cost_usd: 3.82,
  sparkline: Array.from({ length: 7 }, (_, i) => ({
    date: new Date(Date.now() - (6 - i) * 86400000).toISOString().slice(0, 10),
    count: Math.floor(Math.random() * 3) + 1,
  })),
};

// --- Evaluations ---

const evalAgents = ['hook-architect', 'blog-writer', 'carousel-architect', 'narrative-specialist', 'tutorial-specialist'];
const evalNames = ['Hook Architect', 'Blog Writer', 'Carousel Architect', 'Narrative Specialist', 'Tutorial Specialist'];

export const demoEvaluations: EvaluationRecord[] = Array.from({ length: 30 }, (_, i) => {
  const agentIdx = i % evalAgents.length;
  const score = 5 + Math.random() * 4.5;
  return {
    id: `eval-${i}`,
    agent_id: evalAgents[agentIdx],
    agent_name: evalNames[agentIdx],
    date: new Date(Date.now() - i * 86400000 * 0.5).toISOString().slice(0, 10),
    score: Math.round(score * 10) / 10,
    verdict: score >= 7.5 ? 'pass' : score >= 5 ? 'review' : 'fail',
    evaluator: 'written-content-judge',
    notes: score >= 7.5 ? 'Strong hook, clear CTA' : score >= 5 ? 'Needs tighter intro' : 'Off-brand tone',
  };
});

// --- Content Pipeline ---

export const demoContent: ContentItem[] = [
  { id: 'c1', title: 'How I Built a 32-Agent AI Marketing System', platform: 'linkedin', content_type: 'text_post', content_pillar: 'ai_engineering', status: 'published', created_at: '2026-03-10T10:00:00Z', quality: { hook_score: '9', voice_check: 'PASS', quality_score: 88 } },
  { id: 'c2', title: 'ComfyUI Workflow Diffs: Before vs After', platform: 'linkedin', content_type: 'carousel_outline', content_pillar: 'building_in_public', status: 'published', created_at: '2026-03-09T10:00:00Z', quality: { hook_score: '8', voice_check: 'PASS', quality_score: 82 } },
  { id: 'c3', title: 'Pilaster Memory Engine Deep Dive', platform: 'twitter_x', content_type: 'thread', content_pillar: 'ai_engineering', status: 'pending_review', created_at: '2026-03-12T10:00:00Z', scheduled_for: '2026-03-15T14:00:00Z', quality: { hook_score: '7', voice_check: 'PASS', quality_score: 74 } },
  { id: 'c4', title: 'Speech Coaching with 11 Acoustic Dimensions', platform: 'linkedin', content_type: 'text_post', content_pillar: 'ai_engineering', status: 'draft', created_at: '2026-03-13T10:00:00Z', quality: { hook_score: '6', voice_check: 'FAIL', quality_score: 61 } },
  { id: 'c5', title: 'AI Video Editing: Raw to Polished in 60s', platform: 'instagram', content_type: 'instagram_caption', content_pillar: 'bilingual_ai', status: 'published', created_at: '2026-03-07T10:00:00Z', quality: { hook_score: '8', voice_check: 'PASS', quality_score: 79 } },
  { id: 'c6', title: 'MCP vs Skills: Two Paradigms for Extending AI Agents', platform: 'linkedin', content_type: 'text_post', content_pillar: 'systems_thinking', status: 'approved', created_at: '2026-03-13T15:00:00Z', scheduled_for: '2026-03-16T09:00:00Z', quality: { hook_score: '9', voice_check: 'PASS', quality_score: 91 } },
  { id: 'c7', title: 'Building for the Bilingual Market Silicon Valley Ignores', platform: 'twitter_x', content_type: 'thread', content_pillar: 'bilingual_ai', status: 'pending_review', created_at: '2026-03-13T12:00:00Z', quality: { hook_score: '8', voice_check: 'PASS', quality_score: 83 } },
  { id: 'c8', title: 'Why Every AI Stack Needs a Kill Switch', platform: 'linkedin', content_type: 'text_post', content_pillar: 'ai_engineering', status: 'rejected', created_at: '2026-03-11T10:00:00Z', quality: { hook_score: '5', voice_check: 'FAIL', quality_score: 48 } },
];

// --- Knowledge Files ---

export const demoKnowledge: KnowledgeFile[] = [
  { path: '.self-improvement/MEMORY.md', name: 'System Memory', modified_at: '2026-03-13T10:00:00Z', size_bytes: 4200, freshness: 'fresh' },
  { path: '.self-improvement/memory/lessons.json', name: 'Lessons Learned', modified_at: '2026-03-12T18:30:00Z', size_bytes: 8100, freshness: 'fresh' },
  { path: '.self-improvement/memory/trajectory.jsonl', name: 'Decision Trajectory', modified_at: '2026-03-13T09:15:00Z', size_bytes: 32000, freshness: 'fresh' },
  { path: 'config/products.yaml', name: 'Product Definitions', modified_at: '2026-03-10T14:00:00Z', size_bytes: 1200, freshness: 'fresh' },
  { path: 'agents/AGENTS.yaml', name: 'Agent Registry', modified_at: '2026-03-12T20:00:00Z', size_bytes: 6800, freshness: 'fresh' },
  { path: 'config/guardrails.yaml', name: 'Guardrails (safety-critical)', modified_at: '2026-03-01T10:00:00Z', size_bytes: 950, freshness: 'aging' },
];

// --- Trajectory Events ---

export const demoTrajectoryEvents: TrajectoryEvent[] = [
  { id: 't1', timestamp: '2026-03-13T10:30:00Z', agent_name: 'Marketing Strategist', event_type: 'DECISION', description: 'Chose LinkedIn tutorial on Pilaster workflow diffs. Tutorials outperform promo posts 4:1 based on last 30d data.' },
  { id: 't2', timestamp: '2026-03-13T10:25:00Z', agent_name: 'Blog Writer', event_type: 'CONTENT_GENERATED', description: 'Generated 1200-word technical blog post on multi-agent orchestration patterns.' },
  { id: 't3', timestamp: '2026-03-13T10:20:00Z', agent_name: 'Judge Agent', event_type: 'EVALUATION', description: 'Routed blog post to written-content-judge. Score: 8.2/10. Verdict: PASS.' },
  { id: 't4', timestamp: '2026-03-13T09:15:00Z', agent_name: 'SEO Researcher', event_type: 'RESEARCH', description: 'Identified "ComfyUI workflow management" as high-intent keyword (1.2K monthly, low competition).' },
  { id: 't5', timestamp: '2026-03-12T18:00:00Z', agent_name: 'Marketing Strategist', event_type: 'CYCLE_COMPLETE', description: 'Weekly cycle 12 complete. 3 posts published, avg engagement 6.2%, +47 followers across platforms.' },
  { id: 't6', timestamp: '2026-03-12T14:00:00Z', agent_name: 'Hook Architect', event_type: 'CONTENT_GENERATED', description: 'Generated 5 hook variants for Pilaster tutorial post. Top hook: "Your AI generations have no memory. Here is how to fix that."' },
  { id: 't7', timestamp: '2026-03-11T16:30:00Z', agent_name: 'Knowledge Keeper', event_type: 'LEARNING', description: 'Updated MEMORY.md: carousels on LinkedIn get 3x more saves than text posts.' },
  { id: 't8', timestamp: '2026-03-11T10:00:00Z', agent_name: 'Security Sentinel', event_type: 'AUDIT', description: 'Weekly security scan complete. No credentials in code, all MCP calls use env vars.' },
];

// --- Growth / Results ---

function generateDailyGrowth(): GrowthData['daily_growth'] {
  const days: GrowthData['daily_growth'] = [];
  let totalFollowers = 2847;
  for (let i = 29; i >= 0; i--) {
    const date = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    totalFollowers += Math.floor(Math.random() * 18) + 2;
    days.push({
      date,
      total_followers: totalFollowers,
      posts: Math.random() > 0.5 ? 1 : 0,
      impressions: Math.floor(Math.random() * 3000) + 500,
    });
  }
  return days;
}

export const demoGrowthData: GrowthData = {
  snapshot_date: new Date().toISOString().slice(0, 10),
  platforms: {
    linkedin: {
      followers: 1842,
      followers_30d_ago: 1654,
      posts_30d: 12,
      impressions_30d: 28400,
      engagement_rate: 0.062,
      top_content_type: 'tutorial',
      profile_url: 'https://linkedin.com/in/camilomartinez-ai',
    },
    instagram: {
      followers: 743,
      followers_30d_ago: 680,
      posts_30d: 8,
      impressions_30d: 15200,
      engagement_rate: 0.048,
      top_content_type: 'carousel',
      profile_url: 'https://instagram.com/camilojourney',
    },
    twitter: {
      followers: 521,
      followers_30d_ago: 478,
      posts_30d: 15,
      impressions_30d: 12800,
      engagement_rate: 0.035,
      top_content_type: 'thread',
      profile_url: 'https://x.com/camilojourney',
    },
    threads: {
      followers: 234,
      followers_30d_ago: 189,
      posts_30d: 6,
      impressions_30d: 4200,
      engagement_rate: 0.071,
      top_content_type: 'short_post',
    },
    tiktok: {
      followers: 156,
      followers_30d_ago: 112,
      posts_30d: 4,
      impressions_30d: 8900,
      engagement_rate: 0.082,
      top_content_type: 'video',
    },
  },
  daily_growth: generateDailyGrowth(),
  top_posts: [
    {
      id: 'tp1',
      title: 'How I Built a 32-Agent AI Marketing System',
      platform: 'linkedin',
      published_at: '2026-03-11T14:00:00Z',
      impressions: 4820,
      likes: 187,
      comments: 34,
      shares: 28,
      engagement_rate: 0.092,
      content_type: 'authority_post',
      product: 'holus',
    },
    {
      id: 'tp2',
      title: 'ComfyUI Workflow Diffs: Stop Repeating Failed Experiments',
      platform: 'linkedin',
      published_at: '2026-03-10T10:00:00Z',
      impressions: 3640,
      likes: 142,
      comments: 21,
      shares: 19,
      engagement_rate: 0.078,
      content_type: 'tutorial',
      product: 'pilaster',
    },
    {
      id: 'tp3',
      title: 'AI Video Editing: Raw Footage to Polished Reel in 60 Seconds',
      platform: 'instagram',
      published_at: '2026-03-08T16:00:00Z',
      impressions: 6200,
      likes: 312,
      comments: 47,
      shares: 89,
      engagement_rate: 0.105,
      content_type: 'video',
      product: 'genpeli',
    },
    {
      id: 'tp4',
      title: 'Thread: 11 Dimensions of Speech Quality Your English Teacher Never Told You About',
      platform: 'twitter',
      published_at: '2026-03-06T12:00:00Z',
      impressions: 2180,
      likes: 78,
      comments: 15,
      shares: 32,
      engagement_rate: 0.057,
      content_type: 'thread',
      product: 'invoz',
    },
    {
      id: 'tp5',
      title: 'Your AI Generations Have No Memory. Here Is How to Fix That.',
      platform: 'linkedin',
      published_at: '2026-03-07T09:00:00Z',
      impressions: 3100,
      likes: 156,
      comments: 28,
      shares: 22,
      engagement_rate: 0.066,
      content_type: 'conversion',
      product: 'pilaster',
    },
    {
      id: 'tp6',
      title: 'Behind the Scenes: How 7 AI Evaluators Judge Content Quality',
      platform: 'threads',
      published_at: '2026-03-09T11:00:00Z',
      impressions: 1450,
      likes: 89,
      comments: 12,
      shares: 8,
      engagement_rate: 0.075,
      content_type: 'behind_the_scenes',
      product: 'holus',
    },
  ],
  content_by_pillar: {
    authority: { count: 8, avg_engagement_rate: 0.074, total_impressions: 18200 },
    education: { count: 10, avg_engagement_rate: 0.058, total_impressions: 22400 },
    entertainment: { count: 5, avg_engagement_rate: 0.089, total_impressions: 14100 },
    conversion: { count: 4, avg_engagement_rate: 0.051, total_impressions: 8800 },
  },
  content_by_product: {
    pilaster: { count: 12, total_impressions: 28000, avg_engagement_rate: 0.065 },
    genpeli: { count: 6, total_impressions: 16200, avg_engagement_rate: 0.078 },
    invoz: { count: 5, total_impressions: 9400, avg_engagement_rate: 0.048 },
    holus: { count: 4, total_impressions: 10900, avg_engagement_rate: 0.071 },
  },
};

// --- Dimension Averages (per-agent rubric scores) ---

export const demoDimensionAverages: Record<string, Record<string, number>> = {
  'hook-architect': {
    hook_strength: 8.4,
    curiosity_gap: 7.8,
    pattern_interrupt: 7.2,
    emotional_resonance: 6.9,
    clarity: 8.1,
  },
  'blog-writer': {
    hook_strength: 7.6,
    authority_signal: 8.2,
    narrative_arc: 7.9,
    technical_depth: 8.5,
    readability: 7.8,
    cta_strength: 6.8,
  },
  'carousel-architect': {
    visual_flow: 8.1,
    slide_hook: 7.5,
    information_density: 7.8,
    brand_consistency: 8.3,
    cta_strength: 7.2,
  },
  'narrative-specialist': {
    hook_strength: 7.3,
    narrative_arc: 8.6,
    emotional_resonance: 8.2,
    authenticity: 8.4,
    pacing: 7.7,
  },
  'tutorial-specialist': {
    technical_depth: 8.7,
    step_clarity: 8.3,
    code_quality: 8.1,
    readability: 7.9,
    practical_value: 8.5,
  },
  'marketing-strategist': {
    strategic_reasoning: 8.8,
    audience_targeting: 7.9,
    platform_awareness: 8.2,
    data_driven: 8.0,
    creativity: 7.4,
  },
  'seo-researcher': {
    keyword_relevance: 8.3,
    search_intent: 7.8,
    competitive_analysis: 7.5,
    trend_detection: 7.2,
    actionability: 8.0,
  },
};

// --- Memory Content (MEMORY.md) ---

export const demoMemoryContent: MemoryContent = {
  content: `# System Memory

## Content Strategy Patterns

- **Tutorials outperform promo posts 4:1** on LinkedIn (validated across 30+ posts)
- **Carousels get 3x more saves** than text posts on LinkedIn
- **Technical depth correlates with engagement** — shallow tips underperform deep dives
- **Best posting window:** Tuesday-Thursday, 8-10am EST for LinkedIn
- **Instagram Reels** drive more followers than static posts (2.3x growth rate)

## Audience Insights

- Primary audience: AI engineers, content creators, indie hackers
- Pain points: "too many tools, no memory", "AI generations are inconsistent"
- High-resonance topics: multi-agent systems, AI workflow automation, building in public

## Brand Voice

- Direct, technical but accessible
- First person, builder perspective
- Show the work — code snippets, architecture diagrams, real metrics
- Never salesy, never "10 tips" listicles

## What Not to Do

- Avoid generic AI news commentary (low engagement, off-brand)
- Never post about trading/finance (brand confusion risk)
- Do not use corporate buzzwords ("synergy", "leverage", "disrupt")
`,
  last_modified: '2026-03-13T10:00:00Z',
  size_bytes: 1024,
};

// --- Lessons ---

export const demoLessons: LessonsResponse = {
  lessons: [
    { id: '1', date: '2026-03-13', lesson: 'Posts with code snippets get 2.4x more engagement than text-only posts', source: 'analytics_review', agent_id: 'marketing-strategist', category: 'content_format' },
    { id: '2', date: '2026-03-12', lesson: 'LinkedIn algorithm favors posts with exactly 3 line breaks in the hook', source: 'a_b_test', agent_id: 'hook-architect', category: 'platform_optimization' },
    { id: '3', date: '2026-03-12', lesson: 'Thread format on Twitter/X works better for technical content than single tweets', source: 'performance_data', agent_id: 'marketing-strategist', category: 'content_format' },
    { id: '4', date: '2026-03-11', lesson: 'Carousel posts need a strong CTA on the last slide or saves drop by 40%', source: 'analytics_review', agent_id: 'carousel-architect', category: 'content_format' },
    { id: '5', date: '2026-03-11', lesson: 'SEO keywords with "how to" prefix convert 3x better than bare technical terms', source: 'keyword_research', agent_id: 'seo-researcher', category: 'seo' },
    { id: '6', date: '2026-03-10', lesson: 'Brand safety violations most common in automated caption generation — always review', source: 'evaluation_audit', agent_id: 'brand-safety-judge', category: 'safety' },
    { id: '7', date: '2026-03-10', lesson: 'Tutorial posts should include a "before/after" comparison for maximum shareability', source: 'performance_data', agent_id: 'tutorial-specialist', category: 'content_format' },
    { id: '8', date: '2026-03-09', lesson: 'Reposting top content to Threads 48h after LinkedIn gets 60% of original engagement', source: 'cross_post_test', agent_id: 'marketing-strategist', category: 'distribution' },
    { id: '9', date: '2026-03-09', lesson: 'Narrative posts with personal failure stories outperform pure success stories 2:1', source: 'analytics_review', agent_id: 'narrative-specialist', category: 'storytelling' },
    { id: '10', date: '2026-03-08', lesson: 'Instagram caption length sweet spot is 125-150 words for Reels', source: 'performance_data', agent_id: 'marketing-strategist', category: 'platform_optimization' },
  ],
  total: 47,
};

// --- Engagement data (extended for dedicated tracker page) ---

export interface EngagementDataPoint {
  date: string;
  platform: string;
  impressions: number;
  likes: number;
  comments: number;
  shares: number;
  engagement_rate: number;
  posts: number;
}

export function generateEngagementData(): EngagementDataPoint[] {
  const platforms = ['linkedin', 'instagram', 'twitter', 'threads', 'tiktok'];
  const baselines: Record<string, { impressions: number; likes: number; comments: number; shares: number }> = {
    linkedin: { impressions: 900, likes: 35, comments: 6, shares: 5 },
    instagram: { impressions: 500, likes: 25, comments: 4, shares: 8 },
    twitter: { impressions: 400, likes: 12, comments: 3, shares: 6 },
    threads: { impressions: 140, likes: 10, comments: 2, shares: 1 },
    tiktok: { impressions: 300, likes: 18, comments: 3, shares: 5 },
  };

  const data: EngagementDataPoint[] = [];
  for (let i = 29; i >= 0; i--) {
    const date = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    for (const platform of platforms) {
      const b = baselines[platform];
      const variance = () => 0.5 + Math.random();
      const impressions = Math.floor(b.impressions * variance());
      const likes = Math.floor(b.likes * variance());
      const comments = Math.floor(b.comments * variance());
      const shares = Math.floor(b.shares * variance());
      const totalEngagement = likes + comments + shares;
      data.push({
        date,
        platform,
        impressions,
        likes,
        comments,
        shares,
        engagement_rate: impressions > 0 ? totalEngagement / impressions : 0,
        posts: Math.random() > 0.6 ? 1 : 0,
      });
    }
  }
  return data;
}

// --- Follower data (extended for dedicated tracker page) ---

export interface FollowerDataPoint {
  date: string;
  platform: string;
  followers: number;
  new_followers: number;
  unfollows: number;
  net_change: number;
}

export function generateFollowerData(): FollowerDataPoint[] {
  const platforms = ['linkedin', 'instagram', 'twitter', 'threads', 'tiktok'];
  const startFollowers: Record<string, number> = {
    linkedin: 1654,
    instagram: 680,
    twitter: 478,
    threads: 189,
    tiktok: 112,
  };

  const data: FollowerDataPoint[] = [];
  const current = { ...startFollowers };

  for (let i = 29; i >= 0; i--) {
    const date = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    for (const platform of platforms) {
      const newFollowers = Math.floor(Math.random() * 12) + 1;
      const unfollows = Math.floor(Math.random() * 4);
      const netChange = newFollowers - unfollows;
      current[platform] += netChange;
      data.push({
        date,
        platform,
        followers: current[platform],
        new_followers: newFollowers,
        unfollows,
        net_change: netChange,
      });
    }
  }
  return data;
}

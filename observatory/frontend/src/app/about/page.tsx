import Link from 'next/link';
import {
  Brain,
  Eye,
  Zap,
  Shield,
  BarChart3,
  Users,
  ArrowRight,
  Github,
  Linkedin,
  Globe,
} from 'lucide-react';

export const metadata = {
  title: 'Holus Observatory - Architecture',
  description: 'Holus is a multi-agent AI marketing system that coordinates 32 specialized agents to create, evaluate, and publish content across platforms.',
};

const products = [
  {
    name: 'Pilaster',
    tagline: 'AI generation platform with memory',
    url: 'https://pilaster.ai',
  },
  {
    name: 'Invoz',
    tagline: 'Speech coaching with 11 acoustic dimensions',
    url: 'https://invoz.io',
  },
  {
    name: 'Genpeli',
    tagline: 'AI video editing pipeline',
    url: 'https://frontend-six-rho-96.vercel.app',
  },
];

const phases = [
  {
    Icon: Eye,
    title: 'Observe',
    description: 'Reads analytics from social media platforms. What performed well? What audience segments are growing? Which content pillars convert?',
  },
  {
    Icon: Brain,
    title: 'Reason',
    description: 'Claude Opus analyzes patterns across 30 days of data. Decides what content to create, for which product, on which platform.',
  },
  {
    Icon: Zap,
    title: 'Act',
    description: 'Dispatches to specialized agents: hook writers, blog writers, carousel architects, SEO researchers. Each agent has domain-specific expertise.',
  },
  {
    Icon: Shield,
    title: 'Evaluate',
    description: '7 domain-expert judges score every piece. Written content, visual content, and brand safety each have dedicated evaluators with custom rubrics.',
  },
];

const agentCategories = [
  { label: 'Managers', count: 2, description: 'Strategy and self-improvement orchestration' },
  { label: 'Specialists', count: 22, description: '6 content categories: authority, visual, video, growth, research, repurposing' },
  { label: 'Evaluators', count: 7, description: 'Domain-expert quality judges with category-specific rubrics' },
  { label: 'Ops', count: 3, description: 'Code quality, security auditing, knowledge management' },
];

export default function AboutPage() {
  return (
    <div className="px-6 py-8 max-w-4xl mx-auto space-y-12 page-transition">
      {/* Hero */}
      <div className="text-center space-y-4">
        <div
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
          style={{ background: 'var(--brand-subtle)', color: 'var(--brand)' }}
        >
          <span className="status-dot status-dot-active" style={{ background: 'var(--success)' }} />
          32-agent fleet -- live inference
        </div>
        <h1
          className="text-4xl font-bold tracking-tight"
          style={{ color: 'var(--text-primary)' }}
        >
          Holus Observatory
        </h1>
        <p className="text-lg max-w-2xl mx-auto leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          A federated multi-agent system that coordinates 32 specialized agents
          across observe-reason-act-evaluate loops, routing content through domain-expert judges
          and feeding quality signals back into strategy calibration.
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
            style={{ background: 'var(--brand)', color: 'var(--text-inverse)' }}
          >
            Inference Feed <ArrowRight size={16} />
          </Link>
          <Link
            href="/engagement"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
            style={{
              border: '1px solid var(--border-default)',
              color: 'var(--text-secondary)',
            }}
          >
            <BarChart3 size={16} /> Analyze Drift
          </Link>
        </div>
      </div>

      {/* What is this */}
      <section className="card">
        <h2 className="text-lg font-bold mb-3" style={{ color: 'var(--text-primary)' }}>System Architecture</h2>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          This is the Observatory, the real-time monitoring dashboard for Holus.
          Holus is a federated AI system that acts as an autonomous marketing strategist
          for a portfolio of AI products. It does not just generate content. It observes platform analytics,
          reasons about strategy using Claude Opus, dispatches work to specialized agents,
          evaluates every output with domain-expert judges, and feeds results back into
          the next cycle. The Observatory shows this entire loop in real time.
        </p>
        <p className="text-sm leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          The system uses a federated architecture: Holus holds the brain (strategy, decisions, learning)
          while independent silo services handle execution (video editing, image generation, publishing).
          Communication happens via MCP (Model Context Protocol) tool calls, not shared databases.
        </p>
      </section>

      {/* The Agent Loop */}
      <section>
        <h2 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>ReAct Loop (Observe-Reason-Act-Evaluate)</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {phases.map(({ Icon, title, description }, i) => (
            <div key={title} className={`card animate-fade-in stagger-${i + 1}`}>
              <div className="flex items-center gap-2.5 mb-2">
                <div
                  className="p-2 rounded-lg"
                  style={{ background: 'var(--brand-subtle)' }}
                >
                  <Icon size={18} style={{ color: 'var(--brand)' }} />
                </div>
                <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h3>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Agent Architecture */}
      <section>
        <h2 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Agent Fleet -- 32 Agents, 4 Categories</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {agentCategories.map(({ label, count, description }) => (
            <div key={label} className="card">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{label}</h3>
                <span
                  className="text-xs font-medium px-2 py-0.5 rounded-full"
                  style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
                >
                  {count} agents
                </span>
              </div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{description}</p>
            </div>
          ))}
        </div>
        <Link
          href="/agents"
          className="inline-flex items-center gap-1.5 mt-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
          style={{ color: 'var(--brand)' }}
        >
          <Users size={14} /> Inspect full fleet
        </Link>
      </section>

      {/* What it promotes */}
      <section>
        <h2 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Promotion Targets</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {products.map(({ name, tagline, url }) => (
            <a
              key={name}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="card card-interactive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
            >
              <h3 className="font-semibold" style={{ color: 'var(--brand)' }}>{name}</h3>
              <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{tagline}</p>
            </a>
          ))}
        </div>
      </section>

      {/* Technical Stack */}
      <section className="card">
        <h2 className="text-lg font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Technical Stack</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
          {[
            ['Orchestration', 'Python + LangGraph'],
            ['Strategy Model', 'Claude Opus 4.6'],
            ['Content Models', 'Claude Sonnet 4.6'],
            ['Research', 'Gemini 2.5 Pro'],
            ['Event Bus', 'Redis pub/sub'],
            ['Silo Protocol', 'MCP (Model Context Protocol)'],
            ['Observatory', 'Next.js 16 + Tailwind'],
            ['Observatory API', 'FastAPI'],
            ['State', 'JSONL + YAML (no database)'],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
              <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{value}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Explore the demo */}
      <section>
        <h2 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Observatory Panels</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { href: '/', label: 'Inference Feed', desc: 'Live KPIs, fleet status, trajectory stream' },
            { href: '/agents', label: 'Agent Fleet', desc: 'All 32 agents, model tiers, and state' },
            { href: '/content', label: 'Content Pipeline', desc: 'Draft to publish stage gates' },
            { href: '/engagement', label: 'Engagement', desc: 'Signal strength by platform' },
            { href: '/followers', label: 'Audience Growth', desc: 'Acquisition and churn trends' },
            { href: '/evaluations', label: 'Quality Signals', desc: 'Judge scores and drift analysis' },
          ].map(({ href, label, desc }) => (
            <Link
              key={href}
              href={href}
              className="card card-interactive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
            >
              <h3 className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{label}</h3>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{desc}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Built by */}
      <section style={{ borderTop: '1px solid var(--border-default)', paddingTop: '1.5rem' }}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Built by Juan Camilo Martinez
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              AI Engineer. MS Business Analytics, Baruch College.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {[
              { href: 'https://camilomartinez.co', label: 'Personal website', Icon: Globe },
              { href: 'https://linkedin.com/in/camilomartinez-ai', label: 'LinkedIn profile', Icon: Linkedin },
              { href: 'https://github.com/camilojourney', label: 'GitHub profile', Icon: Github },
            ].map(({ href, label, Icon }) => (
              <a
                key={href}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={label}
                className="p-2 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
                style={{ color: 'var(--text-tertiary)' }}
              >
                <Icon size={18} />
              </a>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

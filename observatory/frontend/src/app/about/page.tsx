'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
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
  RotateCcw,
} from 'lucide-react';

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

const loopSteps = [
  {
    Icon: Eye,
    title: 'Observe',
    short: 'Read analytics, detect signals',
    description: 'Reads analytics from social media platforms. What performed well? What audience segments are growing? Which content pillars convert?',
    angle: 0,
  },
  {
    Icon: Brain,
    title: 'Reason',
    short: 'Strategy via Claude Opus',
    description: 'Claude Opus analyzes patterns across 30 days of data. Decides what content to create, for which product, on which platform.',
    angle: 90,
  },
  {
    Icon: Zap,
    title: 'Act',
    short: 'Dispatch to 32 agents',
    description: 'Dispatches to specialized agents: hook writers, blog writers, carousel architects, SEO researchers. Each agent has domain-specific expertise.',
    angle: 180,
  },
  {
    Icon: Shield,
    title: 'Evaluate',
    short: '7 domain-expert judges',
    description: '7 domain-expert judges score every piece. Written content, visual content, and brand safety each have dedicated evaluators with custom rubrics.',
    angle: 270,
  },
];

const agentCategories = [
  { label: 'Managers', count: 2, description: 'Strategy and self-improvement orchestration' },
  { label: 'Specialists', count: 22, description: '6 content categories: authority, visual, video, growth, research, repurposing' },
  { label: 'Evaluators', count: 7, description: 'Domain-expert quality judges with category-specific rubrics' },
  { label: 'Ops', count: 3, description: 'Code quality, security auditing, knowledge management' },
];

function ReactLoopDiagram() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 4);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const radius = 120;
  const center = 160;

  return (
    <div className="relative flex flex-col items-center gap-6 py-8">
      {/* Circular diagram */}
      <div className="relative" style={{ width: 320, height: 320 }}>
        {/* Rotating orbit ring */}
        <svg
          width={320}
          height={320}
          className="absolute inset-0"
          style={{ animation: 'react-loop-spin 10s linear infinite' }}
        >
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="var(--border-default)"
            strokeWidth="1"
            strokeDasharray="8 6"
          />
          {/* Traveling pulse dot */}
          <circle
            cx={center + radius}
            cy={center}
            r="4"
            fill="var(--brand-primary)"
            style={{ filter: 'drop-shadow(0 0 6px var(--brand-primary))' }}
          />
        </svg>

        {/* Static connecting arcs */}
        <svg width={320} height={320} className="absolute inset-0">
          {/* Subtle glow ring */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="var(--brand-primary)"
            strokeWidth="0.5"
            opacity="0.2"
          />
          {/* Arrow arcs between nodes */}
          {[0, 1, 2, 3].map((i) => {
            const startAngle = (i * 90 - 90 + 20) * (Math.PI / 180);
            const endAngle = ((i + 1) * 90 - 90 - 20) * (Math.PI / 180);
            const x1 = center + radius * Math.cos(startAngle);
            const y1 = center + radius * Math.sin(startAngle);
            const x2 = center + radius * Math.cos(endAngle);
            const y2 = center + radius * Math.sin(endAngle);
            return (
              <path
                key={i}
                d={`M ${x1} ${y1} A ${radius} ${radius} 0 0 1 ${x2} ${y2}`}
                fill="none"
                stroke={activeStep === i ? 'var(--brand-primary)' : 'var(--border-strong)'}
                strokeWidth={activeStep === i ? 2 : 1}
                opacity={activeStep === i ? 0.8 : 0.3}
                style={{ transition: 'all 0.5s ease' }}
              />
            );
          })}
        </svg>

        {/* Center label */}
        <div
          className="absolute flex flex-col items-center justify-center"
          style={{
            top: center - 28,
            left: center - 40,
            width: 80,
            height: 56,
          }}
        >
          <RotateCcw
            size={20}
            style={{ color: 'var(--brand-primary)', opacity: 0.6 }}
          />
          <span
            className="text-[10px] font-semibold tracking-widest uppercase mt-1"
            style={{ color: 'var(--text-tertiary)' }}
          >
            ReAct
          </span>
        </div>

        {/* Step nodes positioned around the circle */}
        {loopSteps.map(({ Icon, title, short, angle }, i) => {
          const rad = (angle - 90) * (Math.PI / 180);
          const x = center + radius * Math.cos(rad);
          const y = center + radius * Math.sin(rad);
          const isActive = activeStep === i;

          return (
            <button
              key={title}
              onClick={() => setActiveStep(i)}
              className="absolute flex flex-col items-center gap-1 transition-all duration-500 cursor-pointer"
              style={{
                left: x - 44,
                top: y - 34,
                width: 88,
                transform: isActive ? 'scale(1.15)' : 'scale(1)',
                zIndex: isActive ? 10 : 1,
              }}
              aria-label={`${title}: ${short}`}
            >
              <div
                className="p-2.5 rounded-xl transition-all duration-500"
                style={{
                  background: isActive ? 'var(--brand-primary)' : 'var(--surface-raised)',
                  border: `2px solid ${isActive ? 'var(--brand-primary)' : 'var(--border-default)'}`,
                  boxShadow: isActive
                    ? '0 0 20px rgba(245, 158, 11, 0.3), 0 4px 12px rgba(0,0,0,0.2)'
                    : 'var(--shadow-sm)',
                }}
              >
                <Icon
                  size={20}
                  style={{
                    color: isActive ? 'var(--text-inverse)' : 'var(--brand-primary)',
                  }}
                />
              </div>
              <span
                className="text-xs font-semibold whitespace-nowrap"
                style={{
                  color: isActive ? 'var(--brand-primary)' : 'var(--text-secondary)',
                }}
              >
                {title}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active step detail card */}
      <div
        className="card max-w-md w-full text-center transition-all duration-500"
        style={{
          borderColor: 'var(--brand-primary)',
          borderWidth: '1px',
          opacity: 1,
        }}
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          {(() => {
            const step = loopSteps[activeStep];
            const StepIcon = step.Icon;
            return (
              <>
                <StepIcon size={16} style={{ color: 'var(--brand-primary)' }} />
                <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                  {step.title}
                </span>
              </>
            );
          })()}
        </div>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {loopSteps[activeStep].description}
        </p>
      </div>
    </div>
  );
}

export default function AboutPage() {
  return (
    <div className="px-6 py-8 max-w-4xl mx-auto space-y-12 page-transition">
      {/* Hero with animated ReAct loop */}
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
      </div>

      {/* Animated ReAct Loop Diagram */}
      <section>
        <ReactLoopDiagram />
        <div className="flex justify-center gap-3">
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
      </section>

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

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
  title: 'Holus Observatory - About',
  description: 'Holus is a multi-agent AI marketing system that coordinates 32 specialized agents to create, evaluate, and publish content across platforms.',
};

const products = [
  {
    name: 'Pilaster',
    tagline: 'AI generation platform with memory',
    url: 'https://pilaster.ai',
    color: 'text-indigo-600 dark:text-indigo-400',
  },
  {
    name: 'Invoz',
    tagline: 'Speech coaching with 11 acoustic dimensions',
    url: 'https://invoz.io',
    color: 'text-emerald-600 dark:text-emerald-400',
  },
  {
    name: 'Genpeli',
    tagline: 'AI video editing pipeline',
    url: 'https://frontend-six-rho-96.vercel.app',
    color: 'text-pink-600 dark:text-pink-400',
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
    <div className="px-6 py-8 max-w-4xl mx-auto space-y-12">
      {/* Hero */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          Live system with 32 AI agents
        </div>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
          Holus Observatory
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          A multi-agent AI marketing system that coordinates 32 specialized agents
          to create, evaluate, and publish content across platforms, then learns from what works.
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            View Dashboard <ArrowRight size={16} />
          </Link>
          <Link
            href="/engagement"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <BarChart3 size={16} /> Engagement Tracker
          </Link>
        </div>
      </div>

      {/* What is this */}
      <section className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-6">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-3">What is this?</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          This is the Observatory, the real-time monitoring dashboard for Holus.
          Holus is a federated AI system that acts as an autonomous marketing strategist
          for a portfolio of AI products. It does not just generate content. It observes platform analytics,
          reasons about strategy using Claude Opus, dispatches work to specialized agents,
          evaluates every output with domain-expert judges, and feeds results back into
          the next cycle. The Observatory shows this entire loop in real time.
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mt-3">
          The system uses a federated architecture: Holus holds the brain (strategy, decisions, learning)
          while independent silo services handle execution (video editing, image generation, publishing).
          Communication happens via MCP (Model Context Protocol) tool calls, not shared databases.
        </p>
      </section>

      {/* The Agent Loop */}
      <section>
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">The Agent Loop</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {phases.map(({ Icon, title, description }) => (
            <div key={title} className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950">
                  <Icon size={18} className="text-indigo-600 dark:text-indigo-400" />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Agent Architecture */}
      <section>
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">32 Agents, 4 Categories</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {agentCategories.map(({ label, count, description }) => (
            <div key={label} className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-900 dark:text-white">{label}</h3>
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                  {count} agents
                </span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            </div>
          ))}
        </div>
        <Link
          href="/agents"
          className="inline-flex items-center gap-1.5 mt-3 text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          <Users size={14} /> View all agents
        </Link>
      </section>

      {/* What it promotes */}
      <section>
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Products Holus Promotes</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {products.map(({ name, tagline, url, color }) => (
            <a
              key={name}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5 hover:border-indigo-300 dark:hover:border-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-gray-950 transition-colors"
            >
              <h3 className={`font-semibold ${color}`}>{name}</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{tagline}</p>
            </a>
          ))}
        </div>
      </section>

      {/* Technical Stack */}
      <section className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-6">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-3">Technical Stack</h2>
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
              <p className="text-gray-400 dark:text-gray-600 text-xs">{label}</p>
              <p className="text-gray-700 dark:text-gray-300 font-medium">{value}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Explore the demo */}
      <section>
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Explore the Demo</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { href: '/', label: 'Dashboard', desc: 'KPIs, agent status, live events' },
            { href: '/agents', label: 'Agents', desc: 'All 32 agents and their roles' },
            { href: '/content', label: 'Content Pipeline', desc: 'Drafts, reviews, published' },
            { href: '/engagement', label: 'Engagement', desc: 'Likes, comments, shares by platform' },
            { href: '/followers', label: 'Followers', desc: 'Growth trends by platform' },
            { href: '/evaluations', label: 'Evaluations', desc: 'Quality scores over time' },
          ].map(({ href, label, desc }) => (
            <Link
              key={href}
              href={href}
              className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-4 hover:border-indigo-300 dark:hover:border-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-gray-950 transition-colors"
            >
              <h3 className="font-medium text-sm text-gray-900 dark:text-white">{label}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">{desc}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Built by */}
      <section className="border-t border-gray-200 dark:border-gray-800 pt-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              Built by Juan Camilo Martinez
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">
              AI Engineer. MS Business Analytics, Baruch College.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a href="https://camilomartinez.co" target="_blank" rel="noopener noreferrer" aria-label="Personal website" className="p-2 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <Globe size={18} />
            </a>
            <a href="https://linkedin.com/in/camilomartinez-ai" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn profile" className="p-2 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <Linkedin size={18} />
            </a>
            <a href="https://github.com/camilojourney" target="_blank" rel="noopener noreferrer" aria-label="GitHub profile" className="p-2 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <Github size={18} />
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}

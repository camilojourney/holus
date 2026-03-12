# pilaster Repository

**Repository:** `pilaster`  
**Location:** `/Users/mini/.openclaw/workspace/github/pilaster`  
**Purpose:** Memory layer for ComfyUI — track AI image generation experiments, compare workflow versions, learn from past results  
**Tech Stack:** Next.js 16 (App Router), TypeScript, Supabase (Postgres + Auth + RLS), React Flow, Replicate, Stripe, Cloudflare R2, Radix UI, Tailwind

---

## Architecture Overview

### High-Level System

```
Next.js App (App Router)
        ↓
   API Routes (/api/*)
        ↓
   Supabase Client
        ↓
  PostgreSQL (RLS)
        ↓
   External Services:
   - Replicate (workflow execution)
   - Stripe (credit billing)
   - Cloudflare R2 (image storage)
   - Anthropic (AI suggestions)
```

### Core Features

1. **Workflow Snapshots** — Save ComfyUI workflows with intent notes and outcome labels
2. **Version Diffing** — Compare workflows by parameter values (not node positions)
3. **Memory Engine** — Warns when repeating failed experiments
4. **Replicate Execution** — Run workflows with credit-based billing
5. **AI Suggestions** — Anthropic-powered experiment analysis
6. **R2 Storage** — Store output images with automatic retry

---

## Directory Structure

```
pilaster/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── api/                # API routes
│   │   │   ├── apikeys/        # API key management
│   │   │   ├── gallery/        # Image gallery
│   │   │   ├── health/         # Health check
│   │   │   ├── ingest/         # Workflow ingestion
│   │   │   ├── projects/       # Project CRUD
│   │   │   ├── render/         # Replicate execution
│   │   │   ├── scenes/         # Scene management
│   │   │   ├── settings/       # User settings
│   │   │   └── snapshots/      # Snapshot CRUD
│   │   ├── auth/               # Auth callbacks
│   │   ├── dashboard/          # Main dashboard UI
│   │   ├── gallery/            # Gallery view
│   │   ├── projects/           # Project view
│   │   └── snapshots/          # Snapshot detail
│   ├── components/             # React components (29 files)
│   ├── contexts/               # React contexts
│   ├── hooks/                  # Custom hooks (22 files)
│   ├── lib/                    # Utilities (19 files)
│   └── types/                  # TypeScript types (22 files)
├── supabase/
│   └── migrations/             # SQL migration files (29 migrations)
├── docs/
│   ├── decisions/              # ADRs
│   ├── guides/                 # User guides
│   └── playbooks/              # Development playbooks
├── e2e/                        # Playwright tests
├── public/                     # Static assets
├── docker-compose.yml
├── Dockerfile
└── vercel.json
```

---

## Component Details

### 1. Database Schema (Supabase)

**Key Tables:**

| Table | Description |
|-------|-------------|
| `profiles` | User data (extends auth.users), includes credits |
| `projects` | Workflow collections, unique name per user |
| `snapshots` | Versioned workflows with intent/outcome |
| `runs` | Execution records linked to Replicate |
| `api_keys` | User API keys for external access |
| `settings` | User preferences and config |
| `scenes` | Scene management (new feature) |

**Important Columns:**

```sql
-- profiles
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  username TEXT UNIQUE,
  credits INTEGER DEFAULT 10,  -- Free credits on signup
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- snapshots
CREATE TABLE snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  workflow JSONB NOT NULL,      -- ComfyUI workflow JSON
  intent TEXT,                   -- User's experiment goal
  outcome TEXT,                  -- worked/mixed/failed
  version INTEGER,               -- Auto-incremented per project
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- runs
CREATE TABLE runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  snapshot_id UUID REFERENCES snapshots(id) ON DELETE CASCADE,
  replicate_id TEXT UNIQUE,      -- Replicate prediction ID
  status TEXT,                   -- starting/processing/succeeded/failed
  output_url TEXT,               -- R2 URL of result image
  credits_used INTEGER,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Row Level Security (RLS):**
- All tables have RLS enabled
- Users can only access their own data
- Public share links use special policies

**Migrations:** 29 migrations in `supabase/migrations/` (sequential: 00001 → 00029)

---

### 2. API Routes (Next.js App Router)

**Base Pattern:** `src/app/api/[resource]/route.ts`

**Core Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/ingest | Upload ComfyUI workflow |
| GET | /api/ingest/verify | Verify workflow structure |
| GET | /api/snapshots | List user's snapshots |
| POST | /api/snapshots | Create new snapshot |
| GET | /api/snapshots/[id] | Get snapshot details |
| PUT | /api/snapshots/[id] | Update snapshot |
| DELETE | /api/snapshots/[id] | Soft delete snapshot |
| POST | /api/snapshots/[id]/annotations | Add annotations |
| POST | /api/render | Execute workflow on Replicate |
| GET | /api/render/[id] | Get execution status |
| GET | /api/projects | List projects |
| POST | /api/projects | Create project |
| GET | /api/projects/[id] | Get project details |
| PUT | /api/projects/[id] | Update project |
| DELETE | /api/projects/[id] | Soft delete project |
| GET | /api/gallery | Get image gallery |
| GET | /api/scenes | List scenes |
| POST | /api/scenes | Create scene |
| GET | /api/apikeys | List API keys |
| POST | /api/apikeys | Generate API key |
| POST | /api/apikeys/[id]/revoke | Revoke API key |
| GET | /api/settings | Get user settings |
| PUT | /api/settings | Update settings |
| POST | /api/settings/export | Export user data |
| DELETE | /api/settings/delete-account | Delete account |
| GET | /api/health | Health check |

**Auth Flow:**
- Supabase Auth for user login
- Session-based or API-key-based authentication
- Callbacks: `/auth/callback`, `/auth/confirm`

---

### 3. Workflow Diffing Engine

**Key Files:**
- `src/lib/workflow-diff.ts` — Core diffing logic
- `src/hooks/useWorkflowDiff.ts` — React hook for UI

**Diffing Strategy:**
- Compares workflow parameter values, not node positions
- Tracks added/removed/changed nodes
- Highlights parameter changes (old value → new value)
- Ignores UI metadata (x, y coordinates)

**Diff Output:**

```typescript
interface WorkflowDiff {
  added: Node[];
  removed: Node[];
  changed: {
    nodeId: string;
    nodeName: string;
    parameters: {
      key: string;
      oldValue: any;
      newValue: any;
    }[];
  }[];
}
```

---

### 4. Memory Engine

**Purpose:** Prevent repeating failed experiments

**Logic:**
1. Before running a workflow, check if similar config was tried before
2. If found with outcome = `failed`, show warning to user
3. User can proceed anyway or adjust parameters

**Key Files:**
- `src/lib/memory-engine.ts` — Similarity detection
- `src/hooks/useMemoryWarning.ts` — React hook

**Similarity Matching:**
- Node type match
- Parameter value match (with threshold)
- Previous outcome = `failed`

---

### 5. Replicate Integration

**File:** `src/lib/replicate.ts`

**Workflow Execution:**
1. User clicks "Run" on a snapshot
2. API uploads workflow JSON to Replicate
3. Replicate processes and returns output image
4. Image is downloaded and uploaded to R2
5. Credit is deducted from user's balance

**Credit System:**
- 1 credit = 1 execution
- New users start with 10 free credits
- Purchase credits via Stripe

**Status Polling:**
- Client polls GET `/api/render/[id]` every 2s
- Possible statuses: `starting` → `processing` → `succeeded`/`failed`

---

### 6. Cloudflare R2 Storage

**File:** `src/lib/r2.ts`

**Purpose:** Store output images from Replicate

**URL Pattern:** `{R2_PUBLIC_URL}/outputs/{user_id}/{snapshot_id}/{uuid}.png`

**Features:**
- Automatic retry on failure
- Public URLs for sharing
- Organized by user and snapshot

**Config:**

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_BUCKET_NAME=pilaster-outputs
AWS_ENDPOINT_URL=https://{account_id}.r2.cloudflarestorage.com
```

---

### 7. Stripe Integration

**File:** `src/lib/stripe.ts`

**Credit Purchase:**
1. User selects credit package (10, 50, 100 credits)
2. Stripe Checkout Session created
3. User completes payment
4. Webhook at `/api/webhooks/stripe` receives event
5. Credits added to user's profile

**Webhook Events:**
- `checkout.session.completed` — Add credits
- `payment_intent.succeeded` — Confirm payment

---

### 8. AI Suggestions

**File:** `src/lib/ai-suggestions.ts`

**Provider:** Anthropic Claude

**Workflow:**
1. User requests suggestions on a snapshot
2. System sends experiment history to Claude
3. Claude analyzes patterns and suggests improvements
4. Suggestions displayed in UI

**Rate Limits:**
- 10 requests per day per user (configurable)
- Tracked in database table `ai_suggestion_limits`

---

### 9. UI Components

**Component Library:** Radix UI + Tailwind

**Key Components:**

| Component | Purpose |
|-----------|---------|
| WorkflowViewer | Display ComfyUI workflow graph (React Flow) |
| SnapshotCard | Snapshot preview with intent/outcome |
| DiffViewer | Side-by-side workflow comparison |
| MemoryWarning | Alert when repeating failed experiment |
| CreditBalance | Display user's credits |
| ExecutionStatus | Real-time execution progress |
| GalleryGrid | Image gallery with filters |
| ProjectSidebar | Project navigation |

**Styling:**
- Tailwind CSS for utility classes
- Custom theme in `tailwind.config.js`
- Dark mode support

---

### 10. Auth & Security

**Supabase Auth:**
- Email/password authentication
- OAuth providers (GitHub, Google)
- Magic link login

**Row Level Security (RLS):**
- Users can only access their own data
- Public shares have special policies
- Service role key bypasses RLS (server-side only)

**API Keys:**
- User-generated API keys for external access
- Stored hashed in database
- Revocable

---

## Configuration

**Environment Variables:**

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://....supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# Replicate
REPLICATE_API_TOKEN=...

# Stripe
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_...

# Cloudflare R2
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_BUCKET_NAME=pilaster-outputs
AWS_ENDPOINT_URL=https://...r2.cloudflarestorage.com

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Optional
SENTRY_DSN=...  # Error tracking
```

---

## Development Commands

```bash
# Install dependencies
pnpm install

# Setup environment
cp .env.example .env.local
# Fill in Supabase, Replicate, Stripe, R2 keys

# Start dev server
pnpm dev
# http://localhost:3000

# Run migrations (Supabase CLI)
supabase db push

# Generate TypeScript types from DB
npx supabase gen types typescript --project-id <id> > src/types/supabase.ts

# Run tests
pnpm test       # Watch mode
pnpm test:run   # CI mode

# Run E2E tests
pnpm test:e2e

# Lint
pnpm lint

# Build for production
pnpm build

# Start production server
pnpm start
```

---

## Deployment

### Vercel (Recommended)

**Prerequisites:**
- Vercel account
- Vercel CLI: `pnpm add -g vercel`

**Steps:**

```bash
# Link project
vercel link

# Set environment variables
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
vercel env add SUPABASE_SERVICE_ROLE_KEY
vercel env add REPLICATE_API_TOKEN
vercel env add STRIPE_SECRET_KEY
vercel env add STRIPE_WEBHOOK_SECRET
vercel env add AWS_ACCESS_KEY_ID
vercel env add AWS_SECRET_ACCESS_KEY
vercel env add AWS_BUCKET_NAME

# Deploy
vercel           # Preview
vercel --prod    # Production
```

**GitHub Actions:**
- `.github/workflows/ci.yml` — Lint, test, build on PRs
- `.github/workflows/deploy.yml` — Auto-deploy to Vercel on main push

**Required Secrets:**
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

### Docker

```bash
# Build image
docker build -t pilaster .

# Run
docker run -p 3000:3000 --env-file .env.local pilaster

# Or use Docker Compose
docker-compose up -d
```

**Docker Compose Services:**
- `app` — Next.js (port 3000)
- `postgres` — PostgreSQL (port 5432, dev only)
- `redis` — Redis (port 6379, session management)

---

## Integration Points

**For Holus:** Pilaster is the AI image generation memory layer. Holus can:
1. Query past experiments to inform new generation requests
2. Store ComfyUI workflows for versioning
3. Retrieve successful parameter sets for reuse

**Key Integration Endpoints:**
- POST `/api/ingest` — Upload workflow
- GET `/api/snapshots` — Query past experiments
- POST `/api/render` — Execute workflow
- GET `/api/gallery` — Retrieve generated images

**Authentication:**
- API key authentication for programmatic access
- Generate keys via POST `/api/apikeys`
- Use `Authorization: Bearer <api_key>` header

---

## Key Docs

| Doc | Purpose |
|-----|---------|
| `docs/api-reference.md` | Complete API route reference |
| `docs/guides/api-quickstart.md` | Quick API onboarding |
| `docs/guides/mcp-integration.md` | MCP server integration |
| `docs/guides/versioning.md` | Snapshot versioning workflow |
| `docs/guides/memory-engine.md` | Memory warning behavior |
| `docs/guides/running-workflows.md` | Replicate execution flow |
| `docs/guides/ai-suggestions.md` | AI suggestion workflow |
| `docs/roadmap.md` | Feature plan |
| `docs/decisions/` | Architecture Decision Records |
| `docs/playbooks/` | Phase-based development guides |

---

## Testing

**Unit Tests:** Vitest
- `src/__tests__/` — Test files
- `vitest.config.ts` — Config

**E2E Tests:** Playwright
- `e2e/` — Test specs
- `playwright.config.ts` — Config

**Coverage:** Run `pnpm test:run --coverage`

---

**Last Updated:** 2026-02-27  
**Documented By:** Fruco (Holus Repo Research Task)

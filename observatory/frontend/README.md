# Holus Observatory frontend

The Observatory is the public Holus product experience. It demonstrates
Holus-owned content orchestration, a bounded local generation lifecycle, system
connection state, and the social-content API entry point.

The public/demo surface never calls Genpeli, creates a live generation job,
loads secrets, exposes artifacts, or opens a localhost SSE stream. Live
Observatory data and events require an authenticated backend connection.

## Local development

```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). By default, local
development can use the Observatory API configured by
`NEXT_PUBLIC_OBSERVATORY_URL` (default: `http://localhost:8003`). The public
deployment runs in demo mode and does not apply this local rewrite.

## Public contract

The future authenticated Holus BFF uses the versioned `holus.generation.v1`
contract in `src/lib/generation/`. It permits a constrained create request, a
mapped job status, and a preview reference. It excludes costs, raw traces,
artifacts or artifact URLs, review, rejection, delivery, publishing,
credentials, and operator controls. The local adapter is visibly labelled as
demo data or connection required.

For the architecture and cross-service boundary, see the repository
[architecture document](../../ARCHITECTURE.md).

## Checks

```bash
pnpm lint
```

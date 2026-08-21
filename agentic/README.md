# Holus Agentic Control Plane

Holus owns its marketing-domain behavior, local safety rules, and domain-specific
evaluation data. Fleet may discover the exported manifests and run shared
adapters, but it must not copy Holus runtime state or bypass Holus review gates.

## Company OS

The canonical Company OS sources are in `.agents/skills/`:

- `company-brand-desk`
- `company-content-desk`
- `company-marketing-desk`
- `company-sales-desk`
- `company-evolve`
- `company-supervisor`

`_shared/company_os.py` is a local deterministic helper. It only reads and
writes repo-local evidence and handoff artifacts. It never performs network,
publishing, outreach, spend, CRM, credential, or deployment operations.

- `manifest.yaml` registers the local surface for discovery.
- `permissions.yaml` defines the external-action boundary.
- `memory.yaml` controls what can be exported from the repo-local memory tiers.
- `evals.yaml` declares offline, frozen-input project evaluations for a shared
  adapter.
- `company-os-migration.yaml` records required consumer parity before Fleet can
  remove its retained copies.

The separate `post` skill and the product runtime remain authoritative for
review-before-post and contained external delivery.

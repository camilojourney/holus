# SPEC-001: HOLUS Repository Restructure

> **Prerequisites:** Read SPEC-000 first for architecture overview.
> **Grade from review:** D → Improved with migration script + rollback

## Overview
Reorganize the HOLUS repository from flat agent structure to domain-grouped architecture with subprocess isolation.

## Current State
```
holus/
├── core/
├── agents/
│   ├── job_hunter/
│   ├── youtube_manager/
│   ├── trading_monitor/
│   ├── social_media/
│   ├── inbox_manager/
│   ├── research_scout/
│   └── video_scorer/
├── services/
├── tools/
└── config/
```

## Target State
```
holus/
├── shared/                     # Renamed from core/
│   ├── base_agent.py
│   ├── memory.py
│   ├── llm.py
│   ├── notifier.py
│   ├── utils.py
│   └── types.py
│
├── agents/
│   ├── content-strategy/       # Domain 1
│   │   ├── orchestrator/
│   │   ├── core/
│   │   ├── publishers/
│   │   ├── adapters/
│   │   ├── config.yaml
│   │   ├── content_orchestrator.py
│   │   └── tests/
│   │
│   ├── job-tracker/            # Domain 2
│   │   ├── agents/
│   │   ├── config.yaml
│   │   ├── job_orchestrator.py
│   │   └── tests/
│   │
│   └── trading/                # Domain 3
│       ├── agents/
│       ├── config.yaml
│       ├── trading_orchestrator.py
│       └── tests/
│
├── scripts/
│   ├── test-all.py
│   └── deploy.sh
│
├── main.py                     # Top-level orchestrator
├── docker-compose.yml
└── requirements.txt
```

## Migration Plan

### Phase 1: Create New Structure (No Breaking Changes)
1. Create `shared/` directory
2. Copy (not move) core files to `shared/`
3. Create domain folders under `agents/`
4. Create domain orchestrator stubs

### Phase 2: Migrate Agents
1. Move `youtube_manager/`, `video_scorer/`, `social_media/` → `content-strategy/`
2. Move `job_hunter/` → `job-tracker/`
3. Move `trading_monitor/` → `trading/`
4. Decide on `inbox_manager/`, `research_scout/` (shared utilities?)

### Phase 3: Update Imports
1. Update all imports from `core.` to `shared.`
2. Update orchestrator to use domain orchestrators
3. Add subprocess spawning in `main.py`

### Phase 4: Cleanup
1. Remove old `core/` directory
2. Remove flat agent folders
3. Update README

## Technical Requirements

### Domain Orchestrator Pattern
Each domain has its own orchestrator that:
- Loads domain-specific config.yaml
- Registers only its agents
- Runs as subprocess from main.py
- Has independent crash recovery

```python
# agents/content-strategy/content_orchestrator.py
from shared.base_agent import BaseAgent
from shared.orchestrator import DomainOrchestrator

class ContentOrchestrator(DomainOrchestrator):
    domain = "content-strategy"
    
    def discover_agents(self):
        from .publishers.video_publisher import VideoPublisher
        from .publishers.text_publisher import TextPublisher
        # ...
```

### Main Orchestrator (Subprocess Manager)
```python
# main.py
import subprocess
import sys
from pathlib import Path

DOMAINS = ["content-strategy", "job-tracker", "trading"]

def spawn_domain(domain: str):
    """Spawn domain orchestrator as subprocess."""
    script = Path(f"agents/{domain}/{domain.replace('-', '_')}_orchestrator.py")
    return subprocess.Popen([sys.executable, str(script)])

def main():
    processes = {d: spawn_domain(d) for d in DOMAINS}
    # Monitor, restart on crash, etc.
```

## Acceptance Criteria
- [ ] All agents accessible from new locations
- [ ] Domain orchestrators run independently
- [ ] Crash in one domain doesn't affect others
- [ ] All existing tests pass
- [ ] No functionality regression

## Risks
- Import path changes may break existing code
- Subprocess communication overhead
- Config duplication across domains

## Migration Script

```python
#!/usr/bin/env python3
"""scripts/migrate.py - HOLUS restructure migration"""
import shutil
from pathlib import Path
import subprocess

ROOT = Path(__file__).parent.parent

def backup():
    """Create backup before migration."""
    backup_dir = ROOT / ".backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(ROOT, backup_dir, ignore=shutil.ignore_patterns('.git', '.backup', '__pycache__', '*.pyc'))
    print(f"✅ Backup created at {backup_dir}")

def rollback():
    """Restore from backup."""
    backup_dir = ROOT / ".backup"
    if not backup_dir.exists():
        print("❌ No backup found")
        return
    # Remove current (except .git and .backup)
    for item in ROOT.iterdir():
        if item.name not in ['.git', '.backup']:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    # Restore from backup
    for item in backup_dir.iterdir():
        if item.is_dir():
            shutil.copytree(item, ROOT / item.name)
        else:
            shutil.copy2(item, ROOT / item.name)
    print("✅ Rolled back to backup")

def migrate():
    """Execute migration."""
    backup()
    
    # Phase 1: Create new structure
    (ROOT / "shared").mkdir(exist_ok=True)
    (ROOT / "agents/content-strategy/publishers").mkdir(parents=True, exist_ok=True)
    (ROOT / "agents/content-strategy/adapters").mkdir(exist_ok=True)
    (ROOT / "agents/content-strategy/tests").mkdir(exist_ok=True)
    (ROOT / "agents/job-tracker/tests").mkdir(parents=True, exist_ok=True)
    (ROOT / "agents/trading/tests").mkdir(parents=True, exist_ok=True)
    (ROOT / "scripts").mkdir(exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    
    # Phase 2: Copy core → shared
    core = ROOT / "core"
    shared = ROOT / "shared"
    if core.exists():
        for f in core.glob("*.py"):
            shutil.copy2(f, shared / f.name)
        print("✅ Copied core/ → shared/")
    
    # Phase 3: Move agents to domains
    agents = ROOT / "agents"
    moves = {
        "youtube_manager": "content-strategy/publishers/video_publisher.py",
        "social_media": "content-strategy/publishers/text_publisher.py",
        "video_scorer": "content-strategy/repurposing_engine.py",
        "job_hunter": "job-tracker/job_hunter.py",
        "trading_monitor": "trading/market_monitor.py",
    }
    for old, new in moves.items():
        old_path = agents / old / "agent.py"
        new_path = agents / new
        if old_path.exists():
            shutil.copy2(old_path, new_path)
            print(f"✅ Moved {old} → {new}")
    
    # Phase 4: Update imports (sed-like replacement)
    for py_file in ROOT.rglob("*.py"):
        if ".backup" in str(py_file):
            continue
        content = py_file.read_text()
        updated = content.replace("from core.", "from shared.")
        updated = updated.replace("import core.", "import shared.")
        if content != updated:
            py_file.write_text(updated)
            print(f"✅ Updated imports in {py_file.name}")
    
    print("\n🎉 Migration complete! Run tests to verify.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()
```

## Rollback Strategy

If migration breaks something:
```bash
# Option 1: Use migration script
python scripts/migrate.py rollback

# Option 2: Git reset (if committed incrementally)
git checkout HEAD~1 -- .

# Option 3: Manual restore from .backup/
cp -r .backup/* .
```

## Testing Plan

```bash
# Before migration
pytest tests/ -v > test_results_before.txt

# After migration
pytest tests/ -v > test_results_after.txt

# Compare
diff test_results_before.txt test_results_after.txt

# Verify imports
python -c "from shared.base_agent import BaseAgent; print('OK')"
python -c "from agents.content-strategy.publishers.video_publisher import *; print('OK')"
```

## Timeline (Revised)
- Backup + Phase 1: 1 hour
- Phase 2 (copy core): 30 min
- Phase 3 (move agents): 1 hour
- Phase 4 (update imports): 1 hour
- Testing + fixes: 2 hours
- Documentation: 30 min
- **Total: 6-8 hours**

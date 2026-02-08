#!/usr/bin/env python3
"""HOLUS restructure migration script.

Usage:
    python scripts/migrate.py          # Run migration
    python scripts/migrate.py rollback # Restore from backup
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def backup():
    """Create backup before migration."""
    backup_dir = ROOT / ".backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    
    shutil.copytree(
        ROOT, 
        backup_dir, 
        ignore=shutil.ignore_patterns('.git', '.backup', '__pycache__', '*.pyc', '.venv', 'node_modules')
    )
    print(f"✅ Backup created at {backup_dir}")


def rollback():
    """Restore from backup."""
    backup_dir = ROOT / ".backup"
    if not backup_dir.exists():
        print("❌ No backup found")
        return False
    
    # Remove current (except .git and .backup)
    for item in ROOT.iterdir():
        if item.name not in ['.git', '.backup', '.venv']:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    
    # Restore from backup
    for item in backup_dir.iterdir():
        dest = ROOT / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    
    print("✅ Rolled back to backup")
    return True


def create_directories():
    """Create new directory structure."""
    dirs = [
        "shared",
        "agents/content-strategy/adapters",
        "agents/content-strategy/publishers",
        "agents/content-strategy/tests",
        "agents/job-tracker/tests",
        "agents/trading/tests",
        "scripts",
        "logs",
    ]
    for d in dirs:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    print("✅ Created directory structure")


def copy_core_to_shared():
    """Copy core/ files to shared/."""
    core = ROOT / "core"
    shared = ROOT / "shared"
    
    if not core.exists():
        print("⚠️  core/ not found, skipping copy")
        return
    
    for f in core.glob("*.py"):
        dest = shared / f.name
        if not dest.exists():
            shutil.copy2(f, dest)
            print(f"  Copied {f.name} → shared/")
    
    print("✅ Copied core/ → shared/")


def update_imports():
    """Update imports from core. to shared."""
    count = 0
    for py_file in ROOT.rglob("*.py"):
        # Skip backup, venv, pycache
        if any(x in str(py_file) for x in ['.backup', '.venv', '__pycache__', 'node_modules']):
            continue
        
        try:
            content = py_file.read_text()
            updated = content.replace("from core.", "from shared.")
            updated = updated.replace("import core.", "import shared.")
            
            if content != updated:
                py_file.write_text(updated)
                count += 1
                print(f"  Updated imports in {py_file.relative_to(ROOT)}")
        except Exception as e:
            print(f"  ⚠️  Failed to process {py_file}: {e}")
    
    print(f"✅ Updated imports in {count} files")


def migrate():
    """Execute full migration."""
    print("🚀 Starting HOLUS restructure migration...\n")
    
    # Step 1: Backup
    backup()
    
    # Step 2: Create directories
    create_directories()
    
    # Step 3: Copy core to shared
    copy_core_to_shared()
    
    # Step 4: Update imports
    update_imports()
    
    print("\n🎉 Migration complete!")
    print("\nNext steps:")
    print("  1. Run tests: pytest tests/ -v")
    print("  2. Verify imports: python -c 'from shared.types import ContentItem'")
    print("  3. If issues, rollback: python scripts/migrate.py rollback")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()

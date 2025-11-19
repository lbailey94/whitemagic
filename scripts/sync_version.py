#\!/usr/bin/env python3
"""Version sync - single source of truth."""
import re, json
from pathlib import Path

VERSION_FILE = Path("VERSION")

def get_version():
    return VERSION_FILE.read_text().strip()

def sync_pyproject(v):
    f = Path("pyproject.toml")
    c = f.read_text()
    n = re.sub(r'version\s*=\s*"[\d\.]+"', f'version = "{v}"', c)
    if c \!= n:
        f.write_text(n)
        return True
    return False

def sync_config(v):
    f = Path("whitemagic/config/settings.py")
    if not f.exists():
        return False
    c = f.read_text()
    n = re.sub(r'VERSION\s*=\s*"[\d\.]+"', f'VERSION = "{v}"', c)
    if c \!= n:
        f.write_text(n)
        return True
    return False

def sync_all():
    v = get_version()
    print(f"Syncing to version: {v}")
    
    updated = []
    if sync_pyproject(v):
        updated.append("pyproject.toml")
    if sync_config(v):
        updated.append("config/settings.py")
    
    for u in updated:
        print(f"✓ {u}")
    
    print(f"\n✅ Synced {len(updated)} files")

if __name__ == "__main__":
    sync_all()

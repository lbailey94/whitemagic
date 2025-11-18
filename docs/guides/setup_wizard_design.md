# Setup Wizard Design - v2.2.1

**Created**: Nov 15, 2025 | **Priority**: 0 (Highest)

## Goals
1. Zero to productive in <2 minutes
2. Tier-aware defaults (Personal/Power/Team/Regulated)
3. Beautiful Rich UI
4. Reversible (can re-run anytime)

## 6-Step Flow

### 1. Tier Selection
- Personal (AI companion)
- Power (Dev/freelance)
- Team (Collaboration)
- Regulated (Medical/legal/gov)

### 2. Installation Check
Detect: embeddings installed, config exists, version, size

### 3. Embeddings Choice
- Local AI (+2.5GB, privacy-first)
- OpenAI (lightweight, requires key)
- Skip for now

### 4. Install/Configure
If local: pip install + download model with progress bar
If OpenAI: prompt for API key, save to env

### 5. Tier Configuration
Apply tier-specific defaults:
- Personal: 30d working, no auto-archive, "personal" space
- Power: 90d working, auto-archive, no spaces
- Team: 180d working, auto-archive, "shared" space
- Regulated: manual only, audit required, no spaces

### 6. Complete
Show next steps, saved config path

## CLI Commands
```bash
whitemagic setup        # Full wizard
whitemagic setup --reset
whitemagic setup --show
```

## Implementation
File: `whitemagic/setup/wizard.py`
Classes: `SetupWizard`, `TierConfig`
Dependencies: rich, subprocess

## Tier Configs
```python
TIER_CONFIGS = {
    "personal": {"working_days": 30, "auto_archive": False, "spaces": ["personal"]},
    "power": {"working_days": 90, "auto_archive": True, "spaces": []},
    "team": {"working_days": 180, "auto_archive": True, "spaces": ["shared"], "draft_review": True},
    "regulated": {"working_days": None, "auto_archive": False, "audit": True, "strict_isolation": True},
}
```

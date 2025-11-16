# Setup Wizard Testing Guide

## Run the Wizard

```bash
cd /home/lucas/Desktop/whitemagic
python3 -m whitemagic.cli_app setup
```

## What to Test

### 1. Welcome Screen
- Should see cyan panel with "Welcome to WhiteMagic! 🧠✨"

### 2. Tier Selection
- Table with 4 options (Personal/Power/Team/Regulated)
- Try: Press Enter (default=2, Power tier)
- Should see green confirmation panel

### 3. Embeddings Choice
- Table with 3 options (Local AI/OpenAI/Skip)
- **Recommended: Choose option 3 (Skip)** for quick testing
- If you choose Local AI, it will install ~2.5GB (takes time)
- If you choose OpenAI, it will ask for API key

### 4. Completion
- Should see green "Setup Complete!" panel
- Shows config file location
- Shows next steps

## Verify Config Created

```bash
cat ~/.config/whitemagic/config.yaml
```

Should see your tier and settings!

## Screenshots Needed
1. Welcome screen
2. Tier selection table
3. Tier confirmation panel
4. Embeddings options
5. Completion screen
6. Config file contents

## Quick Test (30 seconds)
1. Run: `python3 -m whitemagic.cli_app setup`
2. Press Enter (Power tier)
3. Type: 3 (Skip embeddings)
4. Done! Check config file.

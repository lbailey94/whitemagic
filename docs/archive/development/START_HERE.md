# 🚀 START HERE - WhiteMagic v2.1.3 Deployment

**Everything is ready. Follow these steps in order.**

---

## ⚡ Quick Deploy (45 minutes)

### Step 1: GitHub (10 min)
```
1. Go to: github.com/lbailey94/whitemagic/settings/secrets/actions
2. Add three secrets:
   - PYPI_API_TOKEN (from pypi.org/manage/account/tokens)
   - DOCKER_USERNAME (lbailey94)  
   - DOCKER_PASSWORD (Docker Hub Access Token - NOT password!)
3. Go to: github.com/lbailey94/whitemagic/settings/pages
4. Set Source to: GitHub Actions
```

### Step 2: Local Setup (2 min)
```bash
cd /home/lucas/Desktop/whitemagic
pip install pre-commit
pre-commit install
```

### Step 3: Release (5 min)
```bash
# Verify version
grep -E 'version\s*=\s*"2\.1\.3"' pyproject.toml

# Tag and push
git tag v2.1.3 -m "Release v2.1.3"
git push origin v2.1.3

# Watch: github.com/lbailey94/whitemagic/actions
```

### Step 4: Production (15 min)
```bash
# On production server
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic && git checkout v2.1.3

# Configure
cp .env.example .env
nano .env
# Set:
#   ALLOWED_ORIGINS=https://yourdomain.com (NO WILDCARDS!)
#   WHOP_API_KEY=your_key
#   WHOP_WEBHOOK_SECRET=your_secret
#   REDIS_URL=redis://... (rate limiting only works when this is set)

# Deploy
docker compose up -d

# Verify
docker compose logs -f api
```

### Step 5: Verify (10 min)
```bash
curl https://yourdomain.com/health
curl https://yourdomain.com/docs
```

---

## 📚 Key Documents

**For Deployment** (pick ONE based on timeline):
- `DEPLOYMENT_GUIDE.md` - 2-hour comprehensive production guide
- `docs/USER_GUIDE.md` - End-to-end product overview (CLI → API → MCP)
- `docs/CHEATSHEET.md` - One-page command reference
- `docs/TROUBLESHOOTING.md` - Common failure modes and fixes
- `DOCUMENTATION_MAP.md` / `docs/INDEX.md` - Navigation aids for everything else

**Status & Release Notes**:
- `CHANGELOG.md` - Version history
- `docs/reviews/v2.1.3/REVIEW_FIXES_APPLIED.md` - Latest fixes shipped
- `docs/reviews/v2.1.3/POST_FIX_COMPREHENSIVE_REVIEW.md` - Most recent audit

**Reference**:
- `README.md` - Project overview
- `.env.example` - Configuration template
- `compose.yaml` - Docker stack
- `docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md` - Current automated test counts

---

## ✅ Pre-flight Check

Before you start, verify:
- [x] You have PyPI API token
- [x] You have Docker Hub credentials
- [x] You have production server access
- [x] You have domain DNS configured
- [x] You have Whop API keys

---

## 🎯 What Gets Deployed

When you push tag v2.1.3:
1. GitHub Actions runs tests
2. Package published to PyPI
3. Docker image built and pushed
4. GitHub release created
5. Docs deployed to GitHub Pages

---

## 📞 Need Help?

- Detailed: Read `DEPLOYMENT_GUIDE.md`
- Issues: github.com/lbailey94/whitemagic/issues
- Status: See `docs/reviews/v2.1.3/REVIEW_FIXES_APPLIED.md`

---

**Ready? Let's deploy! 🚀**

# WhiteMagic v2.1.0 Production Deployment Guide

**Status**: ✅ PRODUCTION READY  
**Difficulty**: Easy (30-45 minutes)  
**For**: Mixed teams (developers + operations)

---

## 🎯 What You'll Deploy

- **REST API** with authentication & rate limiting
- **PostgreSQL database** with auto-migrations
- **Redis** for rate limiting (optional)
- **Automatic HTTPS** via Caddy reverse proxy
- **Monitoring & backups**

---

## 🚀 Part 1: CI/CD Setup (GitHub)

### Step 1: Set Up GitHub Secrets

**Navigate to**: Repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets (**use Access Tokens, not passwords**):

```bash
# PyPI Publishing
PYPI_API_TOKEN=pypi-AgE...  # Get from: https://pypi.org/manage/account/tokens/
# OR use Trusted Publishing (no token needed) - see PyPI docs

# Docker Hub (use Access Token, NOT your login password!)
DOCKER_USERNAME=lbailey94
DOCKER_PASSWORD=dckr_pat_...  # Get from: https://hub.docker.com/settings/security

# Code Coverage (optional)
CODECOV_TOKEN=...  # Only if uploading coverage reports
```

**Important**: 
- Docker Hub: Generate an Access Token at https://hub.docker.com/settings/security
- PyPI: Can use Trusted Publishing instead of tokens (recommended for GitHub Actions)

---

### Step 2: Enable GitHub Pages

1. **Settings** → **Pages**
2. **Source**: GitHub Actions
3. **Save**

**Result**: Live docs at `https://lbailey94.github.io/whitemagic`

---

### Step 3: Install Pre-Commit Hooks

```bash
cd /home/lucas/Desktop/whitemagic
pip install pre-commit
pre-commit install

# Run once to check everything
pre-commit run --all-files

# If it makes changes, commit them
git add -A
git commit -m "chore: apply pre-commit formatting"
```

---

### Step 4: Branch Protection (Optional but Recommended)

**Settings** → **Branches** → Add rule for `main`:
- ✅ Require pull request before merging
- ✅ Require status checks to pass (select "CI" workflow)
- ✅ Require branches to be up to date

---

### Step 5: Tag & Release

**IMPORTANT**: Verify version matches tag to prevent PyPI upload failures

```bash
# Ensure package version == tag
grep -E 'version\s*=\s*"2\.1\.0"' pyproject.toml

# Create release candidate (test run)
git tag v2.1.0-rc1 -m "Release candidate 1"
git push origin v2.1.0-rc1

# Watch GitHub Actions: https://github.com/lbailey94/whitemagic/actions
# Verify: PyPI test upload, Docker image builds

# If successful, create official release
git tag v2.1.0 -m "Release v2.1.0"
git push origin v2.1.0
```

**Result**: 
- ✅ PyPI package published automatically
- ✅ Docker image pushed to Docker Hub
- ✅ GitHub release created with CHANGELOG notes

---

## 🗄️ Part 2: Production Deployment

### Option A: Docker Compose (Recommended ⭐)

**One command brings up everything**: PostgreSQL + Redis + API with auto-migrations

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Edit ALLOWED_ORIGINS (no wildcards), WHOP keys, etc.

# 2. Start the stack
docker compose up -d

# 3. Watch logs
docker compose logs -f api

# 4. Verify health
curl http://localhost:8000/health
```

**What's included**:
- PostgreSQL 16 with health checks
- Redis 7 with persistence
- API with 4 workers
- Automatic database migrations on startup
- Named volumes for data persistence

**To stop**:
```bash
docker compose down  # Keeps data
docker compose down -v  # Removes volumes (data loss!)
```

---

### Option B: Direct Installation

For bare metal or VPS without Docker:

```bash
# 1. Install from PyPI
pip install whitemagic==2.1.0

# 2. Set up database
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/whitemagic
alembic upgrade head

# 3. Configure
cp .env.example .env
nano .env

# 4. Start server
uvicorn whitemagic.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

### Option C: From Source (Development)

```bash
# 1. Clone and checkout tag
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
git checkout v2.1.0

# 2. Install dependencies
pip install -r requirements-api.txt

# 3. Configure
cp .env.example .env
nano .env

# 4. Migrate and run
alembic upgrade head
uvicorn whitemagic.api.app:app --reload
```

---

## 🔐 Part 3: TLS & Reverse Proxy

### Quick HTTPS with Caddy (Easiest)

**Install Caddy** (if not already installed):
```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

**Configure Caddy** (edit `Caddyfile`):
```bash
# Replace yourdomain.com with your actual domain
yourdomain.com {
    reverse_proxy 127.0.0.1:8000
    
    log {
        output file /var/log/caddy/whitemagic-access.log
        format json
    }
}
```

**Start Caddy**:
```bash
sudo caddy run --config Caddyfile
```

**Result**: Automatic HTTPS with Let's Encrypt! 🎉

---

## 🔑 Part 4: Bootstrap Admin API Key

**Problem**: Most teams get stuck here - you need an API key to use the API, but how do you create the first one?

### Solution A: Seed via Environment (Easiest)

Add to `.env` before first startup:
```bash
WM_SEED_ADMIN_KEY=wm_prod_bootstrap_admin_key_secure_random_here
WM_SEED_ADMIN_EMAIL=admin@yourdomain.com
```

### Solution B: CLI Command (If implemented)

```bash
# Create admin key via CLI
docker compose exec api python -m whitemagic.cli create-admin-key \
  --email admin@yourdomain.com \
  --label "Bootstrap Admin"

# Or for non-Docker:
python -m whitemagic.cli create-admin-key \
  --email admin@yourdomain.com \
  --label "Bootstrap Admin"
```

### Solution C: Database Direct (Emergency)

```bash
# Connect to database
docker compose exec db psql -U wmuser -d whitemagic

# Insert user and key manually (use proper hash!)
# See whitemagic/api/auth.py for hash_api_key() function
```

### Test Your Admin Key

```bash
export ADMIN_KEY=wm_prod_your_key_here

# Test stats endpoint
curl -H "Authorization: Bearer $ADMIN_KEY" \
  http://localhost:8000/api/v1/stats

# Should return 200 with memory statistics
```

---

## ✅ Part 5: Verification & Testing

### Health Checks

```bash
# 1. Basic health
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"2.1.0"}

# 2. API docs
open http://localhost:8000/docs

# 3. Readiness (DB check)
curl http://localhost:8000/health/ready
# Expected: 200 if database connected

# 4. Authenticated endpoint
curl -H "Authorization: Bearer $ADMIN_KEY" \
  http://localhost:8000/api/v1/stats
# Expected: Memory statistics JSON
```

### Rate Limit Headers

Check that rate limiting is working:
```bash
curl -I -H "Authorization: Bearer $ADMIN_KEY" \
  http://localhost:8000/api/v1/stats

# Look for headers:
# X-RateLimit-Limit: 10000
# X-RateLimit-Remaining: 9999
# Retry-After: 3600
```

---

## 🔧 Part 6: Essential Production Configuration

### Environment Variables Checklist

Edit `.env` with these **required** values:

```bash
# ============================================================================
# REQUIRED FOR PRODUCTION
# ============================================================================

# Database (auto-configured if using docker compose)
DATABASE_URL=postgresql+asyncpg://wmuser:wmpass@db:5432/whitemagic

# Redis for rate limiting (recommended)
REDIS_URL=redis://redis:6379

# CORS - NEVER use "*" in production!
ALLOWED_ORIGINS=https://yourdomain.com,https://app.whop.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# ============================================================================
# WHOP INTEGRATION (for monetization)
# ============================================================================

WHOP_API_KEY=whop_...your_key_here...
WHOP_WEBHOOK_SECRET=whsec_...your_secret...

# Webhook events to subscribe to:
# - subscription.created
# - subscription.renewed
# - subscription.canceled
# - subscription.upgraded
# - subscription.downgraded

# ============================================================================
# OBSERVABILITY (Optional but recommended)
# ============================================================================

# Sentry error tracking
# SENTRY_DSN=https://...@sentry.io/project-id

# ============================================================================
# ADMIN BOOTSTRAP
# ============================================================================

# Create admin key on first startup
# WM_SEED_ADMIN_KEY=wm_prod_secure_random_key_here
# WM_SEED_ADMIN_EMAIL=admin@yourdomain.com
```

---

## 📦 Part 7: Backups & Data Export

### Automated Daily Backups

Add to crontab on the host machine:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM UTC)
0 2 * * * docker exec -t $(docker ps -qf name=whitemagic-db) pg_dump -U wmuser whitemagic | gzip > /backups/whitemagic_$(date +\%F).sql.gz
```

Create backup directory:
```bash
sudo mkdir -p /backups
sudo chmod 700 /backups
```

### Restore from Backup

```bash
# Stop API to prevent writes
docker compose stop api

# Restore database
gunzip < /backups/whitemagic_2025-11-06.sql.gz | \
  docker exec -i $(docker ps -qf name=whitemagic-db) psql -U wmuser -d whitemagic

# Restart API
docker compose start api
```

### Export User Data via API

```bash
# Export all memories for a user
curl -H "Authorization: Bearer $USER_API_KEY" \
  http://localhost:8000/api/v1/export > user_export.zip
```

---

## 🎯 Part 8: Whop Integration Setup

### Configure Whop Webhooks

1. Go to **Whop Developer Portal**: https://whop.com/developers
2. **Create or select your app**
3. **Webhooks** → **Add Endpoint**
4. **URL**: `https://yourdomain.com/api/v1/webhooks/whop`
5. **Events to subscribe**:
   - `subscription.created`
   - `subscription.renewed` 
   - `subscription.canceled`
   - `subscription.upgraded`
   - `subscription.downgraded`
6. **Copy webhook secret** → Add to `.env` as `WHOP_WEBHOOK_SECRET`

### Flow: New Purchase → API Key Provisioning

```
1. User purchases on Whop
   ↓
2. Whop sends webhook: subscription.created
   ↓
3. WhiteMagic receives webhook
   ↓
4. Validates signature with WHOP_WEBHOOK_SECRET
   ↓
5. Creates user in database (if new)
   ↓
6. Generates API key
   ↓
7. Sets user quota based on plan tier
   ↓
8. Returns API key to user (via Whop or email)
```

### Test Webhook Locally

```bash
# Use Whop's webhook testing tool or curl
curl -X POST http://localhost:8000/api/v1/webhooks/whop \
  -H "Content-Type: application/json" \
  -H "X-Whop-Signature: test_signature" \
  -d '{
    "event": "subscription.created",
    "data": {
      "user_id": "user_test123",
      "plan": "pro",
      "email": "test@example.com"
    }
  }'
```

---

## 📊 Part 9: Monitoring & Observability

### Key Endpoints to Monitor

```bash
# Health check (basic)
GET /health
# Response: {"status":"healthy","version":"2.1.0"}

# Readiness (with DB check)
GET /health/ready
# Response: 200 if DB connected, 503 if not

# Metrics (if implemented)
GET /metrics
# Response: Prometheus-formatted metrics
```

### Log Aggregation

With `LOG_FORMAT=json` in `.env`, logs are structured:

```bash
# View live logs
docker compose logs -f api

# Filter for errors
docker compose logs api | grep '"level":"error"'

# Export logs
docker compose logs api > api_logs_$(date +%F).log
```

### Optional: Error Tracking

By default WhiteMagic emits structured JSON logs; forward them to your favorite collector (CloudWatch, Logtail, etc.). If you'd like richer crash analytics, set `SENTRY_DSN` and install `sentry-sdk`—the FastAPI integration will auto-initialize when the env var is present. Skip this until you need it. More optional add-ons live in [`docs/production/OPTIONAL_INTEGRATIONS.md`](docs/production/OPTIONAL_INTEGRATIONS.md).

---

## 📋 Post-Deployment Checklist

Print this and check off each item:

```
CI/CD & Infrastructure
□ PyPI package exists for tag v2.1.0
□ Docker image exists: lbailey94/whitemagic:2.1.0
□ GitHub Pages live at: lbailey94.github.io/whitemagic
□ Pre-commit hooks installed locally

Production Deployment  
□ docker compose up -d shows all services healthy
□ Database migrations ran: alembic current shows latest
□ Admin API key created and tested
□ /health endpoint returns 200
□ /docs loads with full API documentation

TLS & Security
□ HTTPS active via Caddy (or Nginx)
□ Certificate auto-renewal configured
□ CORS configured (no "*" wildcard)
□ Rate limiting enabled (X-RateLimit-* headers present)

Monitoring & Backups
□ Daily backup cron job scheduled
□ Backup restore tested at least once
□ Sentry DSN configured (optional)
□ Log aggregation working (JSON format)

Whop Integration (if using)
□ WHOP_API_KEY and WHOP_WEBHOOK_SECRET set
□ Webhooks configured in Whop dashboard
□ Test webhook: new purchase → API key issued
□ Cancellation webhook: key revoked after grace period

Performance & Observability
□ Response times < 200ms for simple operations
□ Database pool size appropriate (20 for PostgreSQL)
□ Redis connected (if rate limiting enabled)
□ Worker count set (4 workers recommended)

Documentation
□ Team has access to .env.example
□ Admin knows how to mint new API keys
□ Support knows how to check user quotas
□ Backup/restore procedure documented internally
```

---

## 🚨 Troubleshooting Common Issues

### Issue: "works locally, 403 in prod"

**Cause**: CORS misconfigured  
**Fix**: Check `ALLOWED_ORIGINS` in `.env`:
```bash
# Wrong (only works on localhost)
ALLOWED_ORIGINS=http://localhost:3000

# Right (production domain)
ALLOWED_ORIGINS=https://yourdomain.com,https://app.whop.com
```

### Issue: "Database connection refused"

**Cause**: Database not ready before API starts  
**Fix**: Using docker compose with `depends_on` + `condition: service_healthy` handles this

### Issue: "Rate limit always 0/0"

**Cause**: Redis not connected  
**Fix**: Check `REDIS_URL` in `.env` and verify Redis is running

### Issue: "Whop webhook signature invalid"

**Cause**: `WHOP_WEBHOOK_SECRET` mismatch  
**Fix**: Copy secret exactly from Whop dashboard (starts with `whsec_`)

### Issue: "Can't create first API key"

**Cause**: Chicken-and-egg problem  
**Fix**: Use `WM_SEED_ADMIN_KEY` in `.env` or create via database directly

---

## 🎉 Deployment Complete!

Your WhiteMagic API is now running in production with:

✅ **Automated CI/CD** - Tag pushes trigger releases  
✅ **HTTPS** - Automatic certificate management  
✅ **Database** - PostgreSQL with migrations  
✅ **Rate Limiting** - Per-user quotas enforced  
✅ **Monitoring** - Health checks + structured logging  
✅ **Backups** - Daily automated backups  
✅ **Monetization** - Whop webhooks → API key provisioning  

---

## 📚 Next Steps

1. **Test End-to-End**: Purchase → API key → Make API call
2. **Monitor**: Watch logs for first 24 hours
3. **Optimize**: Adjust worker count based on load
4. **Scale**: Add more API instances behind load balancer if needed
5. **Market**: Start driving traffic to your Whop listing!

---

## 📞 Support

- **Issues**: https://github.com/lbailey94/whitemagic/issues
- **Discussions**: https://github.com/lbailey94/whitemagic/discussions
- **API Docs**: https://lbailey94.github.io/whitemagic

**Deployment time**: 30-45 minutes  
**Confidence level**: VERY HIGH 🚀

---

*Last updated: November 6, 2025*

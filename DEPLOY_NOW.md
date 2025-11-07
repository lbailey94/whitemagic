# 🚀 Deploy WhiteMagic v2.1.0 NOW

**Ready to deploy?** Follow these steps in order.

---

## ⏱️ Quick Timeline

- **GitHub Setup**: 10 minutes
- **Pre-commit**: 2 minutes
- **Release Tag**: 5 minutes
- **Production Deploy**: 15 minutes
- **Verification**: 10 minutes
- **Total**: ~45 minutes

---

## 📋 Step 1: GitHub Secrets (10 min)

You said you have all tokens ready. Add them now:

### Navigate to:
`https://github.com/lbailey94/whitemagic/settings/secrets/actions`

### Add These Secrets:

```
Secret Name: PYPI_API_TOKEN
Value: [Your PyPI token from https://pypi.org/manage/account/tokens/]
```

```
Secret Name: DOCKER_USERNAME
Value: lbailey94
```

```
Secret Name: DOCKER_PASSWORD
Value: [Your Docker Hub Access Token from https://hub.docker.com/settings/security]
NOTE: Use Access Token, NOT your login password!
```

```
Secret Name: CODECOV_TOKEN (optional)
Value: [Your Codecov token if you have one]
```

**✅ Verify**: Go to Actions tab → You should see the secrets listed

---

## 📄 Step 2: Enable GitHub Pages (2 min)

### Navigate to:
`https://github.com/lbailey94/whitemagic/settings/pages`

### Configure:
- **Source**: GitHub Actions (from dropdown)
- **Save**

**✅ Verify**: Page says "GitHub Pages source saved"

---

## 🔨 Step 3: Pre-Commit Hooks (2 min)

```bash
cd /home/lucas/Desktop/whitemagic

# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run once to check
pre-commit run --all-files

# If changes were made, commit them
git add -A
git commit -m "chore: apply pre-commit formatting"
git push origin main
```

**✅ Verify**: Command `pre-commit run --all-files` shows "Passed"

---

## 🏷️ Step 4: Verify Version & Tag (5 min)

```bash
# Check version in pyproject.toml matches what we're tagging
grep -E 'version\s*=\s*"2\.1\.0"' pyproject.toml
# Should output: version = "2.1.0"

# Create release candidate tag (test run)
git tag v2.1.0-rc1 -m "Release candidate 1"
git push origin v2.1.0-rc1

# Watch GitHub Actions
open https://github.com/lbailey94/whitemagic/actions
```

**Monitor the workflows**:
- CI workflow should run and pass
- Release workflow should build package and Docker image
- This usually takes 5-10 minutes

**✅ Verify**: 
- Green checkmark on Actions tab
- Check PyPI Test: `https://test.pypi.org/project/whitemagic/`
- Check Docker Hub: `https://hub.docker.com/r/lbailey94/whitemagic/tags`

### If RC looks good, create official release:

```bash
git tag v2.1.0 -m "Release v2.1.0 - Production ready"
git push origin v2.1.0
```

**✅ Verify**:
- PyPI: `https://pypi.org/project/whitemagic/2.1.0/`
- Docker Hub: Tag `2.1.0` exists
- GitHub: Release created at `https://github.com/lbailey94/whitemagic/releases`

---

## 🐳 Step 5: Production Deployment (15 min)

### On Your Production Server:

```bash
# Clone repo (if not already)
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
git checkout v2.1.0

# Create environment file
cp .env.example .env

# Edit .env with your production values (set ALLOWED_ORIGINS to real domains, no *)
nano .env
```

### Edit `.env` with YOUR values:

```bash
# Database (auto-configured for docker compose)
DATABASE_URL=postgresql+asyncpg://wmuser:wmpass@db:5432/whitemagic

# Redis
REDIS_URL=redis://redis:6379

# CORS - Replace with your domain!
ALLOWED_ORIGINS=https://yourdomain.com,https://app.whop.com

# Whop Integration - ADD YOUR KEYS
WHOP_API_KEY=your_actual_whop_api_key_here
WHOP_WEBHOOK_SECRET=your_actual_webhook_secret_here

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Admin bootstrap (optional - for first run)
# WM_SEED_ADMIN_KEY=wm_prod_<generate_secure_random_string>
# WM_SEED_ADMIN_EMAIL=admin@yourdomain.com

# Sentry (optional - requires requirements-plugins.txt)
# pip install -r requirements-plugins.txt
# SENTRY_DSN=https://your_sentry_dsn@sentry.io/project
```

### Start the stack:

```bash
# Pull latest image
docker pull lbailey94/whitemagic:2.1.0

# Start everything
docker compose up -d

# Watch logs
docker compose logs -f api
```

**✅ Verify**: Logs show:
- "Database migrations complete"
- "Starting server at http://0.0.0.0:8000"
- No error messages
- Dashboard reachable at http://localhost:3000

---

## ✅ Step 6: Verification (10 min)

### Health Check:

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"2.1.0"}
```

### API Docs:

```bash
# Open in browser
open http://localhost:8000/docs
```

### Create Admin Key:

If you set `WM_SEED_ADMIN_KEY` in `.env`, it should already exist.

Otherwise, create one manually (see deployment guide Part 4).

### Test Authenticated Call:

```bash
export ADMIN_KEY=your_admin_key_here

curl -H "Authorization: Bearer $ADMIN_KEY" \
  http://localhost:8000/api/v1/stats
```

**✅ Verify**: Returns JSON with memory statistics

---

## 🔐 Step 7: Set Up HTTPS (10 min)

### Install Caddy:

```bash
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

### Configure Caddy:

```bash
# Edit Caddyfile
nano Caddyfile
```

Replace `yourdomain.com` with your actual domain:

```
yourdomain.com {
    reverse_proxy 127.0.0.1:8000
    
    log {
        output file /var/log/caddy/whitemagic-access.log
        format json
    }
}
```

### Start Caddy:

```bash
sudo caddy run --config Caddyfile
```

**✅ Verify**: 
- Visit `https://yourdomain.com/health`
- Should show green padlock (HTTPS working)
- Certificate automatically obtained from Let's Encrypt

---

## 📦 Step 8: Set Up Backups (5 min)

```bash
# Create backup directory
sudo mkdir -p /backups
sudo chmod 700 /backups

# Add to crontab
crontab -e

# Add this line (daily backup at 2 AM)
0 2 * * * docker exec -t $(docker ps -qf name=whitemagic-db) pg_dump -U wmuser whitemagic | gzip > /backups/whitemagic_$(date +\%F).sql.gz
```

**✅ Verify**: Wait until next day or run manually

---

## 🎯 Step 9: Configure Whop Webhooks

### In Whop Developer Portal:

1. Go to: `https://whop.com/developers`
2. Select your app
3. **Webhooks** → **Add Endpoint**
4. **URL**: `https://yourdomain.com/api/v1/webhooks/whop`
5. **Events**: Select all subscription events:
   - subscription.created
   - subscription.renewed
   - subscription.canceled
   - subscription.upgraded
   - subscription.downgraded
6. **Save** and copy the webhook secret
7. Add secret to `.env` as `WHOP_WEBHOOK_SECRET`

### Test:

```bash
# Make a test purchase on Whop
# Check logs:
docker compose logs -f api | grep webhook
```

**✅ Verify**: Webhook received, user created, API key generated

---

## 🎉 Step 10: Final Verification

### Run Through Post-Deployment Checklist:

Open `POST_DEPLOYMENT_CHECKLIST.md` and verify all items.

### Test End-to-End:

1. Make test purchase on Whop
2. Receive API key
3. Make API call with key
4. Check quota/rate limits
5. Verify logging works

---

## ✅ You're Live!

### What You've Deployed:

- ✅ WhiteMagic API v2.1.0
- ✅ PostgreSQL database with migrations
- ✅ Redis for rate limiting
- ✅ HTTPS with automatic certificates
- ✅ Daily backups
- ✅ Whop integration
- ✅ Monitoring & logging

### Monitoring First 24 Hours:

```bash
# Watch logs
docker compose logs -f api

# Check health every hour
curl https://yourdomain.com/health

# Monitor resource usage
docker stats
```

---

## 🚨 If Something Goes Wrong:

### Quick Rollback:

```bash
# Stop everything
docker compose down

# Check logs
docker compose logs api

# Fix issue in .env or config
nano .env

# Restart
docker compose up -d
```

### Get Help:

- Check logs: `docker compose logs api`
- Check troubleshooting section in `DEPLOYMENT_GUIDE.md`
- Open issue: `https://github.com/lbailey94/whitemagic/issues`

---

## 📞 Ready to Start?

**You have everything you need!**

1. Add GitHub secrets NOW
2. Tag the release
3. Deploy to production
4. Start monetizing!

**Time to go live**: 45 minutes  
**Confidence**: VERY HIGH 🚀

---

**Let's deploy! 🎊**

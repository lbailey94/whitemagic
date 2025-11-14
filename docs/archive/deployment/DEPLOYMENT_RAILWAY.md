# 🚂 Railway Deployment Guide - WhiteMagic API

**Date**: November 13, 2025  
**Purpose**: Deploy WhiteMagic API to Railway with PostgreSQL and Redis  
**Target**: api.whitemagic.dev

---

## 🎯 What We're Deploying

- **FastAPI application** (WhiteMagic API)
- **PostgreSQL database** (user data, API keys, quotas)
- **Redis** (rate limiting)
- **Domain**: api.whitemagic.dev

---

## 📋 Prerequisites

- ✅ Railway account (you have this!)
- ✅ GitHub repository (we'll create/push)
- ✅ Whop API key (you provided: b5xFgUfkCVw3...)
- ✅ Squarespace DNS access (for CNAME)

---

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Code for Production (I'll do this)

**Create production requirements**:
```python
# requirements-prod.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0  # PostgreSQL async driver
aiosqlite==0.19.0
redis==5.0.1
httpx==0.25.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pydantic==2.5.0
pydantic-settings==2.1.0
```

**Create Procfile**:
```
web: uvicorn whitemagic.api.app:app --host 0.0.0.0 --port $PORT
```

**Create railway.json**:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "numReplicas": 1,
    "startCommand": "uvicorn whitemagic.api.app:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Step 2: Push to GitHub

**Do this in your terminal**:
```bash
cd /home/lucas/Desktop/whitemagic

# Initialize git if not already
git init

# Add Railway config files (I'll create these)
git add .
git commit -m "feat: prepare for Railway deployment"

# Create GitHub repo and push
# Option 1: Via GitHub CLI (if installed)
gh repo create lbailey94/whitemagic --private --source=. --push

# Option 2: Manual
# 1. Go to https://github.com/new
# 2. Create private repo "whitemagic"
# 3. Run:
git remote add origin https://github.com/lbailey94/whitemagic.git
git branch -M main
git push -u origin main
```

### Step 3: Create Railway Project

**In Railway Dashboard** (https://railway.app/dashboard):

1. **Click "New Project"**
2. **Select "Deploy from GitHub repo"**
3. **Choose "lbailey94/whitemagic"**
4. Railway will auto-detect Python and start building

### Step 4: Add PostgreSQL Database

**In your Railway project**:

1. **Click "+ New"** in sidebar
2. **Select "Database"**
3. **Choose "PostgreSQL"**
4. Railway automatically creates `DATABASE_URL` variable
5. API will auto-connect (we use `$DATABASE_URL`)

### Step 5: Add Redis

**In your Railway project**:

1. **Click "+ New"** in sidebar
2. **Select "Database"**
3. **Choose "Redis"**
4. Railway automatically creates `REDIS_URL` variable
5. API will auto-connect for rate limiting

### Step 6: Configure Environment Variables

**In Railway → Your API Service → Variables**:

Add these variables:

```bash
# Whop Integration
WHOP_API_KEY=b5xFgUfkCVw3__8wsDQsJ3BLXLXbEx8xKt8SPrmi_U0
WHOP_WEBHOOK_SECRET=<will add after webhook setup>

# CORS (will update after Vercel deploys dashboard)
ALLOWED_ORIGINS=https://app.whitemagic.dev,http://localhost:3000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Database (auto-provided by Railway)
# DATABASE_URL=<auto-populated>
# REDIS_URL=<auto-populated>
```

**Note**: Railway auto-provides `DATABASE_URL`, `REDIS_URL`, and `PORT`. Don't override these.

### Step 7: Deploy!

Railway automatically deploys when you push to GitHub. For first deployment:

1. **Wait for build** (2-3 minutes)
2. **Check logs** for any errors
3. **Test API** at your Railway URL

**Your Railway URL** will be something like:
```
https://whitemagic-production-xxxx.up.railway.app
```

Test it:
```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/health
```

Should return:
```json
{"status":"healthy","version":"2.1.4"}
```

### Step 8: Run Database Migrations

Railway doesn't run migrations automatically. We need to do this once:

**Option A: Railway CLI**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Run migration
railway run python -m whitemagic.api.app migrate
```

**Option B: One-time Deployment Command**

In Railway → Settings → Deploy:
- Set **Health Check Path**: `/health`
- Add **Init Command**: `python -c "from whitemagic.api.database import Database; import asyncio; asyncio.run(Database('$DATABASE_URL').create_tables())"`

### Step 9: Add Custom Domain

**In Railway → Your API Service → Settings → Domains**:

1. **Click "Custom Domain"**
2. **Enter**: `api.whitemagic.dev`
3. Railway gives you a CNAME target (e.g., `whitemagic.up.railway.app`)

**Copy this CNAME target** - you'll need it for DNS!

### Step 10: Configure DNS (Squarespace)

**In Squarespace DNS Settings**:

Add a new record:
```
Type: CNAME
Name: api
Value: <Railway CNAME from step 9>
TTL: 3600 (1 hour)
```

Example:
```
CNAME  api  whitemagic-production.up.railway.app
```

**Wait 5-30 minutes** for DNS propagation.

### Step 11: Verify SSL Certificate

Railway auto-provisions SSL via Let's Encrypt.

**Check SSL**:
```bash
curl https://api.whitemagic.dev/health
```

Should work over HTTPS! 🔒

### Step 12: Test API Endpoints

```bash
# Health check
curl https://api.whitemagic.dev/health

# Create test user (if not exists)
curl -X POST https://api.whitemagic.dev/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@whitemagic.dev", "password": "testpass123"}'

# Test with API key
curl -H "Authorization: Bearer wm_prod_..." \
  https://api.whitemagic.dev/dashboard/account
```

---

## 🔍 Troubleshooting

### Build Fails

**Check Railway logs**:
- Click on your service
- Go to "Deployments"
- Click latest deployment
- Check build logs

**Common issues**:
- Missing dependencies → Check `requirements.txt`
- Python version → Railway uses Python 3.11 by default
- Import errors → Check module paths

### Database Connection Fails

**Verify DATABASE_URL**:
- In Variables, check `DATABASE_URL` exists
- Should be: `postgresql://...`
- Auto-provided by Railway PostgreSQL service

### API Returns 500 Errors

**Check application logs**:
- Railway → Service → Logs
- Look for Python errors
- Common: Missing env vars

### CORS Errors from Dashboard

**Update ALLOWED_ORIGINS**:
```bash
ALLOWED_ORIGINS=https://app.whitemagic.dev
```

Must match exactly (no trailing slash).

### SSL Certificate Not Working

**Wait longer**:
- Railway SSL can take 5-10 minutes
- Check Railway logs for certificate provisioning

**Verify DNS**:
```bash
nslookup api.whitemagic.dev
```

Should point to Railway domain.

---

## 📊 Monitoring & Logs

### View Logs
**Railway Dashboard → Your Service → Logs**

Real-time logs of:
- API requests
- Errors
- Database queries (if LOG_LEVEL=DEBUG)

### Metrics
**Railway Dashboard → Your Service → Metrics**

Shows:
- CPU usage
- Memory usage
- Network traffic
- Request count

### Set Up Alerts

**Railway → Service → Settings → Alerts**:
- CPU > 80%
- Memory > 80%
- Deployment failures

---

## 💰 Cost Estimation

### Railway Pricing

**Starter Plan**: $5 credit/month (free tier)

**Usage-based pricing**:
- **API Service**: ~$5-10/month (estimate)
- **PostgreSQL**: ~$5/month (estimate)
- **Redis**: ~$2/month (estimate)

**Total**: ~$12-17/month

**How to optimize**:
- Use Railway's free $5 credit
- Suspend services during development
- Monitor usage in dashboard

---

## 🔐 Security Checklist

- ✅ **Environment variables**: Stored securely in Railway
- ✅ **API keys**: Never in code (use variables)
- ✅ **Database**: Not publicly accessible
- ✅ **SSL/TLS**: Auto-provisioned by Railway
- ✅ **CORS**: Restricted to app.whitemagic.dev
- ✅ **Logs**: Don't log sensitive data

**Recommendations**:
- Enable Railway's IP allowlist (if needed)
- Rotate Whop API key quarterly
- Monitor access logs
- Set up error alerting

---

## 🔄 Continuous Deployment

Railway auto-deploys on every git push to main:

1. **Push code**: `git push origin main`
2. **Railway builds**: Automatically
3. **Railway deploys**: If build succeeds
4. **Health check**: Railway verifies `/health`
5. **Live**: New version deployed

**To disable auto-deploy**:
- Railway → Service → Settings → Builds
- Toggle "Auto Deploy" off

---

## 📝 Post-Deployment Checklist

After Railway is live:

- [ ] API health check works: `https://api.whitemagic.dev/health`
- [ ] SSL certificate active (HTTPS)
- [ ] Database migrations ran successfully
- [ ] Redis connected (check logs)
- [ ] Whop API key configured
- [ ] CORS allows app.whitemagic.dev
- [ ] Test API key authentication works
- [ ] Set up monitoring alerts
- [ ] Configure webhook URL in Whop dashboard

---

## 🎯 Next Steps

Once Railway is deployed:

1. **Copy Railway URL** → Update Whop webhook
2. **Deploy dashboard to Vercel** → Use api.whitemagic.dev
3. **Test end-to-end flow** → Signup → API calls
4. **Monitor logs** → Check for errors
5. **Set up Whop products** → Using copy I provided

---

**Railway is perfect for WhiteMagic because**:
- ✅ Auto-detects Python/FastAPI
- ✅ Managed PostgreSQL & Redis
- ✅ Auto SSL/TLS
- ✅ GitHub integration (auto-deploy)
- ✅ Reasonable pricing (~$15/mo)
- ✅ Great DX for developers

Ready to deploy! 🚀

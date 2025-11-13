# Day 3: Whop Integration & Domain Setup

**Date**: November 13, 2025  
**Status**: 🚀 Ready to Begin  
**Domain**: whitemagic.dev (acquired!)

---

## 🎯 Objectives

### Part A: Whop Integration
1. ✅ Configure Whop API credentials
2. ✅ Test webhook endpoints
3. ✅ Verify plan synchronization
4. ✅ Add upgrade flow to dashboard
5. ✅ Test subscription lifecycle

### Part B: Domain Setup
1. 🌐 Configure whitemagic.dev DNS
2. 📦 Deploy dashboard to Vercel
3. 🚂 Deploy API to Railway
4. 🔒 Set up SSL/TLS
5. 🔗 Update CORS and API URLs

---

## 📋 What I Need From You

### 1. Whop Credentials 🔑

Please provide:

**Whop API Key**:
- Log in to https://whop.com/settings/developer
- Create or copy your API key
- Format: `whop_xxxxxxxxxxxxxxxxxxxxx`

**Whop Company ID** (optional):
- Found in Whop dashboard URL
- Format: `comp_xxxxx`

**Webhook Secret** (we'll set this up):
- We'll generate this during setup

---

### 2. Domain Access 🌐

For **whitemagic.dev**:

**DNS Provider**:
- Where did you register the domain? (e.g., Namecheap, GoDaddy, Cloudflare)
- Do you have access to DNS settings?

**Proposed Subdomain Structure**:
```
whitemagic.dev              → Marketing site (future)
app.whitemagic.dev          → Dashboard (Vercel)
api.whitemagic.dev          → API Backend (Railway)
docs.whitemagic.dev         → Documentation (future)
status.whitemagic.dev       → Status page (future)
```

Is this structure okay with you?

---

### 3. Deployment Accounts 📦

**Vercel** (for dashboard):
- Do you have a Vercel account?
- If yes, what's your username/org?
- If no, we'll create one

**Railway** (for API):
- Do you have a Railway account?
- If yes, what's your project name?
- If no, we'll create one

---

## 🔧 Whop Integration - What We'll Build

### Step 1: Environment Configuration

We'll add to your `.env` file:
```bash
# Whop Integration
WHOP_API_KEY=whop_xxxxxxxxxxxxxxxxxxxxx
WHOP_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
WHOP_COMPANY_ID=comp_xxxxx

# Production URLs (after domain setup)
ALLOWED_ORIGINS=https://app.whitemagic.dev
FRONTEND_URL=https://app.whitemagic.dev
```

### Step 2: Webhook Setup

We already have webhook handlers in `whitemagic/api/routes/whop.py`:
- ✅ `membership.created` - New subscription
- ✅ `membership.updated` - Plan change
- ✅ `membership.deleted` - Cancellation
- ✅ `membership.went_valid` - Subscription activated
- ✅ `membership.went_invalid` - Subscription expired

**Webhook URL** (after Railway deploy):
```
https://api.whitemagic.dev/webhooks/whop
```

### Step 3: Dashboard Updates

Add upgrade buttons that link to your Whop checkout:
```javascript
// In dashboard/app.js
const WHOP_CHECKOUT_URL = 'https://whop.com/whitemagic/checkout';
```

### Step 4: Testing Checklist

- [ ] Create test subscription
- [ ] Verify user provisioning
- [ ] Test plan tier updates
- [ ] Test subscription cancellation
- [ ] Verify quota limits apply

---

## 🌐 Domain Setup - Step by Step

### Step 1: DNS Configuration

Add these DNS records at your domain provider:

```
Type    Name    Value                           TTL
CNAME   app     cname.vercel-dns.com           3600
CNAME   api     [railway-url].up.railway.app   3600
A       @       [your-IP]                       3600
```

We'll get the exact values after deploying.

### Step 2: Vercel Deployment (Dashboard)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy dashboard
cd dashboard
vercel --prod

# Add custom domain
vercel domains add app.whitemagic.dev
```

**What Vercel needs**:
- Static HTML/CSS/JS files ✅ (we have this)
- No build step needed ✅
- Just serve the files

### Step 3: Railway Deployment (API)

**Option A: GitHub Integration** (Recommended)
1. Push code to GitHub
2. Connect Railway to your repo
3. Railway auto-detects Python + FastAPI
4. Set environment variables in Railway dashboard

**Option B: Railway CLI**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

**Environment Variables to Set in Railway**:
```bash
DATABASE_URL=postgresql://...  # Railway provides this
WHOP_API_KEY=whop_xxxxx
WHOP_WEBHOOK_SECRET=whsec_xxxxx
ALLOWED_ORIGINS=https://app.whitemagic.dev
REDIS_URL=redis://...  # Railway addon
```

### Step 4: SSL/TLS (Automatic)

- ✅ Vercel: Auto SSL via Let's Encrypt
- ✅ Railway: Auto SSL via Let's Encrypt

Both platforms handle this automatically when you add custom domains.

### Step 5: Update Code for Production

**dashboard/app.js**:
```javascript
const API_BASE_URL = window.WHITEMAGIC_API_BASE
    || 'https://api.whitemagic.dev';
```

**whitemagic/api/app.py**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.whitemagic.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 Deployment Checklist

### Pre-Deployment
- [ ] Get Whop API key
- [ ] Get Whop webhook secret
- [ ] Create Vercel account (if needed)
- [ ] Create Railway account (if needed)
- [ ] Access to whitemagic.dev DNS

### Vercel (Dashboard)
- [ ] Deploy to Vercel
- [ ] Add custom domain (app.whitemagic.dev)
- [ ] Verify SSL certificate
- [ ] Test dashboard loads
- [ ] Update API base URL in code

### Railway (API)
- [ ] Create Railway project
- [ ] Add PostgreSQL database
- [ ] Add Redis addon
- [ ] Set environment variables
- [ ] Deploy API
- [ ] Add custom domain (api.whitemagic.dev)
- [ ] Run database migrations
- [ ] Test API endpoints

### Whop Integration
- [ ] Set WHOP_API_KEY in Railway
- [ ] Configure webhook URL in Whop dashboard
- [ ] Test webhook delivery
- [ ] Create test subscription
- [ ] Verify plan synchronization

### DNS Configuration
- [ ] Add CNAME for app.whitemagic.dev → Vercel
- [ ] Add CNAME for api.whitemagic.dev → Railway
- [ ] Wait for DNS propagation (5-30 mins)
- [ ] Verify domains resolve correctly

### Final Testing
- [ ] Login to app.whitemagic.dev
- [ ] API calls work
- [ ] Upgrade button links to Whop
- [ ] Test subscription flow
- [ ] Monitor logs for errors

---

## 🚀 Quick Start: What To Do Now

### Immediate (Next 10 minutes):

1. **Get Whop API Key**:
   - Go to https://whop.com/settings/developer
   - Copy your API key
   - Send it to me (or store securely)

2. **Check Domain DNS Access**:
   - Where is whitemagic.dev registered?
   - Can you access DNS settings?

3. **Deployment Accounts**:
   - Create Vercel account: https://vercel.com/signup
   - Create Railway account: https://railway.app/

### Next (30 minutes):

1. **I'll configure Whop integration locally**
2. **We'll test webhooks**
3. **I'll prepare deployment configs**

### After (1-2 hours):

1. **Deploy to Vercel** (dashboard)
2. **Deploy to Railway** (API)
3. **Configure DNS**
4. **Test production**

---

## 💰 Estimated Costs

### Vercel
- **Free tier**: Likely sufficient for now
- **Pro tier**: $20/mo (if needed for more bandwidth)

### Railway
- **Free tier**: $5 credit/month
- **Estimated**: ~$10-20/month for API + DB + Redis
- **Scales with usage**

### Whop
- **No platform fee** (they take a % of sales)
- **Standard payment processing**: ~2.9% + $0.30

### Domain
- **whitemagic.dev**: ~$15/year (already paid?)

**Total Monthly Estimate**: ~$10-30/month (very affordable!)

---

## 📝 Notes

### Why This Stack?

**Vercel for Dashboard**:
- ✅ Global CDN (fast everywhere)
- ✅ Auto SSL
- ✅ GitHub integration
- ✅ Perfect for static sites

**Railway for API**:
- ✅ Easy Python deployment
- ✅ Managed PostgreSQL
- ✅ Redis addon
- ✅ Environment variables
- ✅ Auto-scaling

**Whop for Payments**:
- ✅ Developer-friendly
- ✅ Already integrated
- ✅ Handles subscriptions
- ✅ Webhooks for automation

### Alternative Options (if needed later)

- **API**: Could move to Fly.io, Render, or AWS
- **Dashboard**: Could use Netlify or Cloudflare Pages
- **Database**: Could use Supabase or Neon
- **Payments**: Could add Stripe alongside Whop

---

## 🎯 Success Criteria

By end of Day 3:

- ✅ Whop API key configured
- ✅ Webhooks tested and working
- ✅ Plan tiers synchronize correctly
- ✅ Dashboard deployed to app.whitemagic.dev
- ✅ API deployed to api.whitemagic.dev
- ✅ SSL working on both
- ✅ Users can sign up via Whop
- ✅ Upgrade flow works end-to-end

---

## 🚦 Ready to Start!

**What I need from you right now**:

1. **Whop API Key** (from https://whop.com/settings/developer)
2. **Domain DNS provider** (Namecheap, GoDaddy, Cloudflare, etc.)
3. **Vercel account** (create at https://vercel.com/signup)
4. **Railway account** (create at https://railway.app/)

**Once you provide these, I'll**:
1. Configure Whop integration
2. Set up environment variables
3. Test webhooks locally
4. Prepare deployment configs
5. Guide you through deploying to production

Let's do this! 🚀

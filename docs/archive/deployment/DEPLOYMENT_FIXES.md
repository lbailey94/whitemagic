# 🔧 Deployment Fixes - Railway & Vercel

**Date**: November 13, 2025  
**Status**: ✅ Fixes Ready - Need to Redeploy  
**Commit**: `b8b0ba0`

---

## ✅ What Was Fixed

### 1. ✅ Whop Product IDs Updated
- **File**: `whitemagic/api/whop.py`
- **What**: Updated plan mapping with your actual Whop product IDs
- **Mapping**:
  ```python
  "prod_Zb6K8XcWXCFZr": "free",       # Free - $0/month
  "prod_nnlWEMbmNWbP3": "starter",    # Plus - $10/month
  "prod_cb3r3jr2rTM18": "pro",        # Pro - $30/month
  "prod_CD0XTEYLhXBws": "enterprise",  # Enterprise - $999/month
  ```

### 2. ✅ Railway Fix - Added `requirements.txt`
- **Problem**: Railway said "no start command was found"
- **Root Cause**: No `requirements.txt` at root → Railway couldn't detect Python project
- **Fix**: Created `/requirements.txt` with all production dependencies
- **What It Does**: Tells Railway this is a Python project and what to install

### 3. ✅ Vercel Fix - Added `.vercelignore`
- **Problem**: Vercel tried to deploy API (FastAPI) instead of dashboard
- **Root Cause**: Vercel detected Python/FastAPI at root
- **Fix**: Created `.vercelignore` to ignore all API files
- **What It Does**: Tells Vercel to only see the `dashboard/` folder

---

## 🚀 How to Fix Railway

### Step 1: Push Changes to GitHub

Your GitHub repo has branch protection, so you need to either:

**Option A: Create a PR** (Recommended)
```bash
cd /home/lucas/Desktop/whitemagic

# Create a new branch
git checkout -b deployment-fixes

# Push to branch
git push origin deployment-fixes

# Then go to GitHub and create a PR from deployment-fixes → main
# Merge the PR
```

**Option B: Temporarily Disable Branch Protection**
1. Go to GitHub → Settings → Branches → Edit main protection
2. Temporarily uncheck "Require a pull request"
3. Push directly:
   ```bash
   git push origin main
   ```
4. Re-enable protection after push

### Step 2: Redeploy on Railway

Once changes are on GitHub:

1. **Go to Railway** → Your project → **whitemagic** service
2. **Click "Deploy"** button (top right)
3. Railway will pull latest code and redeploy
4. **Watch the build logs**:
   - Should see: `pip install -r requirements.txt` ✅
   - Should see: `Installing whitemagic...` ✅
   - Should see: `Starting: uvicorn whitemagic.api.app:app...` ✅
5. **Wait for deploy** (~2-3 minutes)
6. **Check logs** for any errors

### Step 3: Verify Railway Works

```bash
# Replace with your Railway URL (check Railway dashboard)
curl https://whitemagic-production-xxxx.up.railway.app/health
```

Should return:
```json
{"status":"healthy","version":"2.1.4"}
```

✅ **If you see this, Railway is working!**

---

## 🚀 How to Fix Vercel

### Step 1: Delete Current Vercel Deployment

1. **Go to Vercel** → Your project
2. **Settings** → **General** → Scroll down
3. **Click "Delete Project"**
4. Confirm deletion

(We need to start fresh with correct settings)

### Step 2: Redeploy with Correct Settings

Once GitHub has the latest code:

1. **Go to** https://vercel.com/new
2. **Import** `lbailey94/whitemagic` from GitHub
3. **CRITICAL: Configure Project Settings:**

   ```
   Project Name: whitemagic-dashboard
   Framework Preset: Other (NOT FastAPI!)
   Root Directory: dashboard    ← IMPORTANT! Click "Edit" and set this!
   Build Command: (leave empty)
   Output Directory: (leave empty - will use current dir)
   Install Command: (leave empty)
   ```

4. **Click "Deploy"**
5. **Wait ~30 seconds** (it's just static files)
6. **Test the URL** Vercel gives you

### Step 3: Verify Vercel Works

Open the Vercel URL in your browser:
- ✅ Should see beautiful beige dashboard
- ✅ Should see login form
- ✅ Console should say: `API Base URL: http://localhost:8000` (for now)
- ✅ No FastAPI errors!

---

## 🔍 Why These Errors Happened

### Railway Error: "No start command was found"

**The Problem:**
- Railway looks for `requirements.txt` at repo root to detect Python projects
- We had `requirements-api.txt` but not `requirements.txt`
- Without it, Railway didn't know how to run the app

**The Fix:**
- Created `requirements.txt` at root
- Includes `-e .` to install whitemagic package
- Includes all production dependencies
- Railway now knows: "This is Python, install these deps, run the start command"

**Why It Works Now:**
```
requirements.txt exists → Railway detects Python
railway.json has startCommand → Railway knows how to run it
Procfile backup → If railway.json fails, Procfile works
```

### Vercel Error: "No fastapi entrypoint found"

**The Problem:**
- Vercel auto-detected the repo structure
- Saw Python files, FastAPI imports → assumed it's an API
- Tried to deploy the API instead of the dashboard
- Failed because it's not designed to run FastAPI

**The Fix:**
- Added `.vercelignore` to hide all Python/API files
- Set "Root Directory" to `dashboard/` in Vercel UI
- Now Vercel only sees HTML/CSS/JS in dashboard folder
- Deploys as static site (which is what we want!)

**Why It Works Now:**
```
Root Directory = dashboard/ → Vercel looks in dashboard/ only
.vercelignore → Hides API files from Vercel
vercel.json → Configures static site settings
Dashboard is pure HTML/CSS/JS → Deploys instantly
```

---

## 📊 Environment Variables for Railway

After Railway deploys successfully, add these environment variables:

**In Railway → Your Service → Variables:**

```bash
# Database (auto-provided by Railway when you add PostgreSQL)
DATABASE_URL=<auto-filled by Railway>

# Redis (auto-provided by Railway when you add Redis)
REDIS_URL=<auto-filled by Railway>

# CORS (allow your dashboard domain)
ALLOWED_ORIGINS=https://app.whitemagic.dev,http://localhost:3000

# Whop Integration
WHOP_API_KEY=b5xFgUfkCVw3__8wsDQsJ3BLXLXbEx8xKt8SPrmi_U0
WHOP_WEBHOOK_SECRET=<will add after webhook setup>

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Port (auto-provided by Railway)
PORT=<auto-filled by Railway>
```

**Don't override** `DATABASE_URL`, `REDIS_URL`, or `PORT` - Railway provides these automatically!

---

## ✅ Deployment Checklist

### Railway Deployment
- [ ] Changes pushed to GitHub main branch
- [ ] Railway project connected to GitHub repo
- [ ] PostgreSQL database added in Railway
- [ ] Redis added in Railway
- [ ] Environment variables configured
- [ ] Deploy triggered (pulls latest from GitHub)
- [ ] Build succeeds (check logs)
- [ ] `/health` endpoint returns 200 OK
- [ ] No errors in deployment logs

### Vercel Deployment
- [ ] Changes pushed to GitHub main branch
- [ ] Old Vercel project deleted (if needed)
- [ ] New Vercel project created
- [ ] **Root Directory set to `dashboard/`** ← CRITICAL
- [ ] Framework set to "Other" (NOT FastAPI)
- [ ] Deploy succeeds
- [ ] Dashboard loads in browser
- [ ] No FastAPI errors
- [ ] Console shows correct API URL

---

## 🎯 Expected Results

### Railway Should Show:
```
✓ Build: pip install -r requirements.txt
✓ Installing whitemagic package (-e .)
✓ Starting: uvicorn whitemagic.api.app:app
✓ Listening on 0.0.0.0:$PORT
✓ Health check passed: /health returns 200
```

### Vercel Should Show:
```
✓ Root Directory: dashboard
✓ Framework: Other
✓ Deploying static files
✓ Build time: 10-20 seconds
✓ Deployment URL: https://whitemagic-dashboard.vercel.app
✓ Dashboard loads with beige design
```

---

## 🆘 If Still Getting Errors

### Railway: Build Still Failing?

**Check the logs for:**
1. **"ModuleNotFoundError"** → Missing dependency in requirements.txt
2. **"Port already in use"** → Railway port conflict (restart service)
3. **"Database connection failed"** → PostgreSQL not added or wrong URL
4. **"Redis connection failed"** → Redis not added

**Solutions:**
- **Missing deps**: Add to requirements.txt, commit, push, redeploy
- **Port issues**: Railway should set PORT automatically
- **Database**: Add PostgreSQL service in Railway (+ New → Database → PostgreSQL)
- **Redis**: Add Redis service in Railway (+ New → Database → Redis)

### Vercel: Still Detecting FastAPI?

**Double-check:**
1. **Root Directory** in Vercel settings = `dashboard/` (not `.` or `/`)
2. **Framework Preset** = "Other" (not "FastAPI", not "None")
3. **Build Command** = empty (not trying to build anything)
4. **.vercelignore** file exists in repo and is committed

**If still failing:**
- Delete project and start fresh
- When importing, make SURE to set Root Directory BEFORE deploying
- The setting is easy to miss - look for "Edit" button next to Root Directory

---

## 📞 What to Do Next

### 1. Push Changes to GitHub
- Use PR method or temporarily disable branch protection
- Verify changes are on GitHub main branch

### 2. Redeploy Railway
- Trigger redeploy in Railway dashboard
- Watch build logs
- Verify /health endpoint works

### 3. Redeploy Vercel
- Delete old project (if FastAPI error)
- Create new project with Root Directory = dashboard/
- Verify dashboard loads

### 4. Let Me Know Results!
**Reply with:**
- Railway URL (e.g., `whitemagic-production-xxxx.up.railway.app`)
- Vercel URL (e.g., `whitemagic-dashboard.vercel.app`)
- Any error messages still showing
- Screenshots if still having issues

I'll help debug any remaining issues! 🚀

---

## 🎉 Success Criteria

**You'll know it works when:**

✅ **Railway**:
- Build logs show successful pip install
- Service status shows "Active" (green)
- `curl https://your-railway-url.up.railway.app/health` returns JSON
- Logs show "Uvicorn running on 0.0.0.0:PORT"

✅ **Vercel**:
- Build logs show "Deploying static files"
- Dashboard loads in browser
- No FastAPI errors
- Login form appears with beige design

**Then we can:**
- Add custom domains (api.whitemagic.dev, app.whitemagic.dev)
- Configure DNS CNAME records
- Set up Whop webhook
- Test end-to-end!

---

**Ready to deploy!** Push the changes and redeploy both services. Let me know how it goes! 🚀

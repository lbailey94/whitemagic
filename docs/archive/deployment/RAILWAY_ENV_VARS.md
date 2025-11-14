# 🚂 Railway Environment Variables Setup

**Status**: Railway will auto-redeploy with openai package fix  
**Next**: Add these environment variables in Railway

---

## 🔧 Required Environment Variables

Railway should auto-redeploy now that the fix is pushed. Once it's deploying, add these environment variables:

### 1. Go to Railway Dashboard

1. Click on your **whitemagic** service
2. Go to **Variables** tab
3. Add each of these:

---

### Core Variables (Required)

```bash
# Whop Integration
WHOP_API_KEY=b5xFgUfkCVw3__8wsDQsJ3BLXLXbEx8xKt8SPrmi_U0

# CORS - Allow your Vercel dashboard
ALLOWED_ORIGINS=https://whitemagic-one.vercel.app,http://localhost:3000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

### Database Variables (Auto-Provided by Railway)

**DO NOT SET THESE** - Railway provides them automatically when you add services:

- ✅ `DATABASE_URL` - Auto-provided when you add PostgreSQL
- ✅ `REDIS_URL` - Auto-provided when you add Redis
- ✅ `PORT` - Auto-provided by Railway

---

### Optional Variables (For Later)

```bash
# Whop Webhook Secret (add after creating webhook in Whop)
# WHOP_WEBHOOK_SECRET=your_webhook_secret_here

# OpenAI API Key (optional - for semantic search)
# OPENAI_API_KEY=sk-your-key-here
```

---

## 📊 Add PostgreSQL & Redis (If Not Already Added)

### PostgreSQL:
1. In Railway project dashboard
2. Click **"+ New"** → **Database** → **PostgreSQL**
3. Railway will auto-create and link `DATABASE_URL`

### Redis:
1. In Railway project dashboard
2. Click **"+ New"** → **Database** → **Redis**
3. Railway will auto-create and link `REDIS_URL`

---

## ✅ Deployment Status

### Current Fix:
- ✅ Added `openai>=1.3.0` to requirements.txt
- ✅ Fixed `$PORT` interpolation (using Procfile)
- ✅ Code pushed to GitHub
- ⏳ Railway should auto-redeploy now

### Watch For:
```
✓ pip install -r requirements.txt
✓ Successfully installed openai-1.x.x
✓ Starting: uvicorn whitemagic.api.app:app
✓ Health check passed: /health
```

---

## 🎯 Next Steps

### 1. **Wait for Railway to Redeploy** (auto, ~2-3 min)
   - Should start automatically
   - Watch the build logs
   - Look for successful openai install

### 2. **Add Environment Variables** (once deployed)
   - Add `WHOP_API_KEY`
   - Add `ALLOWED_ORIGINS` with Vercel URL
   - Add `LOG_LEVEL` and `LOG_FORMAT`

### 3. **Add PostgreSQL** (if not already)
   - + New → Database → PostgreSQL
   - Wait for `DATABASE_URL` to appear in Variables

### 4. **Add Redis** (if not already)
   - + New → Database → Redis
   - Wait for `REDIS_URL` to appear in Variables

### 5. **Test the API**
   ```bash
   # Replace with your Railway URL
   curl https://your-railway-url.up.railway.app/health
   ```
   
   Should return:
   ```json
   {"status":"healthy","version":"2.1.4"}
   ```

---

## 🌐 Update Vercel Dashboard

Once Railway is live, update the dashboard to point to the API:

### Option 1: Environment Variable in Vercel
1. Vercel → Your project → Settings → Environment Variables
2. Add: `WHITEMAGIC_API_BASE` = `https://your-railway-url.up.railway.app`
3. Redeploy dashboard

### Option 2: Meta Tag in HTML
Edit `dashboard/index.html` and add:
```html
<meta name="whitemagic-api-base" content="https://your-railway-url.up.railway.app">
```

---

## 🎊 Success Criteria

**You'll know it works when:**

✅ **Railway**:
- Build logs show `Successfully installed openai`
- Service status: Active (green)
- Health check passes
- No import errors

✅ **Vercel Dashboard**:
- Loads at https://whitemagic-one.vercel.app
- Login form appears
- Console shows correct API URL

✅ **End-to-End**:
- Create API key in dashboard
- Use API key to call `/health` endpoint
- Returns 200 OK

---

## 🆘 If Still Failing

### Check Railway Logs For:

**"ModuleNotFoundError"** → Missing dependency
- Check requirements.txt has all packages
- Verify `-e .` installs whitemagic package

**"Database connection failed"** → No PostgreSQL
- Add PostgreSQL service in Railway
- Verify `DATABASE_URL` in Variables tab

**"Redis connection failed"** → No Redis
- Add Redis service in Railway
- Verify `REDIS_URL` in Variables tab

**"WHOP_API_KEY not set"** → Missing env var
- Add `WHOP_API_KEY` in Variables tab
- Value: `b5xFgUfkCVw3__8wsDQsJ3BLXLXbEx8xKt8SPrmi_U0`

---

## 📸 What to Send Me

Once Railway redeploys:
1. Screenshot of successful deployment
2. Railway URL (e.g., `whitemagic-production-xxxxx.up.railway.app`)
3. Test result from `/health` endpoint
4. Any errors (if any)

Then we can:
- Add custom domain `api.whitemagic.dev`
- Configure DNS
- Connect dashboard to API
- Test end-to-end! 🚀

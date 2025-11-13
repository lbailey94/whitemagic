# ⚡ Vercel Deployment Guide - WhiteMagic Dashboard

**Date**: November 13, 2025  
**Purpose**: Deploy WhiteMagic Dashboard to Vercel  
**Target**: app.whitemagic.dev

---

## 🎯 What We're Deploying

- **Static dashboard** (HTML, CSS, JavaScript)
- **No build step needed** (vanilla JS)
- **Domain**: app.whitemagic.dev

---

## 📋 Prerequisites

- ✅ Vercel account (you have this!)
- ✅ GitHub repository (same as Railway)
- ✅ Railway API deployed (api.whitemagic.dev)
- ✅ Squarespace DNS access (for CNAME)

---

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Dashboard for Production (I'll do this)

**Create `vercel.json`**:
```json
{
  "buildCommand": null,
  "devCommand": null,
  "installCommand": null,
  "framework": null,
  "outputDirectory": "dashboard",
  "public": true,
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        }
      ]
    }
  ]
}
```

**Update `dashboard/app.js` for production**:

We'll update the API base URL to use the production API:

```javascript
// Before (development)
const API_BASE_URL = isLocal ? 'http://localhost:8000' : 'https://api.whitemagic.dev';

// After (production-ready - already done!)
const API_BASE_URL = window.WHITEMAGIC_API_BASE
    || (metaApiBase && metaApiBase.content.trim())
    || (isLocal ? 'http://localhost:8000' : 'https://api.whitemagic.dev');
```

This is **already configured** ✅ - it will automatically use `https://api.whitemagic.dev` in production!

### Step 2: Push Dashboard Updates to GitHub

```bash
cd /home/lucas/Desktop/whitemagic

# Add vercel.json (I'll create this)
git add vercel.json
git commit -m "feat: add Vercel configuration"
git push origin main
```

### Step 3: Deploy to Vercel

**Option A: Via Vercel Dashboard** (Recommended for first deploy)

1. **Go to**: https://vercel.com/new
2. **Click "Import Project"**
3. **Select "Import Git Repository"**
4. **Choose**: `lbailey94/whitemagic`
5. **Configure Project**:
   - **Project Name**: `whitemagic-dashboard`
   - **Framework Preset**: Other
   - **Root Directory**: `dashboard`
   - **Build Command**: (leave empty)
   - **Output Directory**: `.` (current directory)
   - **Install Command**: (leave empty)
6. **Click "Deploy"**

Vercel will deploy in ~30 seconds!

**Option B: Via Vercel CLI**

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy from dashboard directory
cd dashboard
vercel --prod

# Follow prompts:
# - Link to existing project? No
# - Project name? whitemagic-dashboard
# - Directory? ./ (current)
# - Build command? (leave empty)
```

### Step 4: Test Deployment

Vercel gives you a URL like:
```
https://whitemagic-dashboard.vercel.app
```

**Test it**:
1. Open in browser
2. Should see login form (beautiful beige design!)
3. Open console - should say `API Base URL: https://api.whitemagic.dev`
4. Try logging in with test API key

### Step 5: Add Custom Domain

**In Vercel Dashboard → Your Project → Settings → Domains**:

1. **Click "Add"**
2. **Enter**: `app.whitemagic.dev`
3. **Click "Add"**

Vercel will show you DNS instructions:

```
Type: CNAME
Name: app
Value: cname.vercel-dns.com
```

### Step 6: Configure DNS (Squarespace)

**In Squarespace DNS Settings**:

Add a new record:
```
Type: CNAME
Name: app
Value: cname.vercel-dns.com
TTL: 3600 (1 hour)
```

**Wait 5-30 minutes** for DNS propagation.

### Step 7: Verify SSL Certificate

Vercel auto-provisions SSL via Let's Encrypt.

**Check**:
```bash
curl -I https://app.whitemagic.dev
```

Should return `200 OK` over HTTPS! 🔒

### Step 8: Update Whop Upgrade Links

After deployment, update the upgrade button URL in Whop products to:
```
https://app.whitemagic.dev
```

---

## 🔍 Troubleshooting

### 404 on Dashboard Routes

**Issue**: Vercel returns 404 for /dashboard, /settings, etc.

**Solution**: The `vercel.json` rewrites config handles this. All routes → index.html.

Already configured! ✅

### API Calls Fail (CORS)

**Issue**: Dashboard can't reach api.whitemagic.dev

**Solution**: Update Railway `ALLOWED_ORIGINS`:
```bash
ALLOWED_ORIGINS=https://app.whitemagic.dev
```

### Whitescreen / JavaScript Errors

**Check browser console**:
- Look for JavaScript errors
- Verify API_BASE_URL is correct
- Check network tab for failed requests

**Common fixes**:
- Hard refresh (Ctrl+Shift+R)
- Clear cache
- Check if API is running: https://api.whitemagic.dev/health

### Custom Domain Not Working

**Verify DNS**:
```bash
nslookup app.whitemagic.dev
```

Should return:
```
app.whitemagic.dev  canonical name = cname.vercel-dns.com
```

**If not**:
- Check DNS settings in Squarespace
- Wait longer (DNS can take 30 mins)
- Try `dig app.whitemagic.dev`

---

## 📊 Vercel Features We're Using

### Edge Network
- **Global CDN**: Dashboard served from edge locations worldwide
- **Fast**: <100ms response times globally
- **Reliable**: 99.99% uptime

### Automatic SSL
- **Free certificates**: Let's Encrypt
- **Auto-renewal**: Never expires
- **Force HTTPS**: Automatic redirect

### Git Integration
- **Auto-deploy**: Every push to `main`
- **Preview deployments**: Every PR gets unique URL
- **Rollbacks**: One-click revert to previous version

### Analytics (Optional)
- **Enable in Vercel**: Dashboard → Analytics
- **Shows**: Page views, visitors, performance
- **Free tier**: 100k data points/month

---

## 💰 Cost Estimation

### Vercel Pricing

**Hobby Plan**: FREE! ✅
- Unlimited personal projects
- 100 GB bandwidth/month
- Automatic SSL
- Global CDN

**For WhiteMagic**:
- Dashboard is small (~500 KB)
- Static files (no server)
- Should easily stay in free tier

**If you need more**:
- **Pro Plan**: $20/month
  - More bandwidth
  - Team features
  - Advanced analytics

---

## 🔄 Continuous Deployment

Vercel auto-deploys on every git push:

1. **Push code**: `git push origin main`
2. **Vercel builds**: Automatically (instant for static)
3. **Vercel deploys**: Live in <10 seconds
4. **Preview URL**: Get unique URL per commit

**Preview Deployments**:
- Every branch/PR gets its own URL
- Test before merging to production
- Great for showing clients

---

## 🔐 Security Headers

The `vercel.json` config adds security headers:

```javascript
X-Content-Type-Options: nosniff  // Prevent MIME sniffing
X-Frame-Options: DENY            // Prevent clickjacking
X-XSS-Protection: 1; mode=block  // XSS protection
```

**Already configured!** ✅

---

## 📝 Environment Variables (Optional)

Vercel supports env vars if needed:

**In Vercel Dashboard → Settings → Environment Variables**:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.whitemagic.dev
```

But we don't need this - our JS already detects production! ✅

---

## 🎨 Custom Domain Tips

### Multiple Domains

You can add multiple domains to same project:
- `app.whitemagic.dev` (primary)
- `whitemagic.dev` (redirect to app)
- `www.whitemagic.dev` (redirect to app)

### Email Setup (Future)

Once DNS is configured:
- Add MX records for email
- Use Google Workspace, Zoho, etc.
- Send from `hello@whitemagic.dev`

---

## 📊 Post-Deployment Checklist

After Vercel is live:

- [ ] Dashboard loads: `https://app.whitemagic.dev`
- [ ] SSL certificate active (HTTPS)
- [ ] Login form displays correctly
- [ ] Beige background and lavender accents showing
- [ ] Console shows: `API Base URL: https://api.whitemagic.dev`
- [ ] Test login works with API key
- [ ] Sidebar appears after login
- [ ] Hero section shows usage percentage
- [ ] Chart renders with lavender colors
- [ ] All navigation links work
- [ ] Mobile responsive (test on phone)

---

## 🚀 Performance Optimization (Already Done!)

Our dashboard is already optimized:

**✅ Uses CDN for libraries**:
- Tailwind CSS from cdn.tailwindcss.com
- Lucide icons from unpkg.com
- Chart.js from jsdelivr.net

**✅ Minimal file size**:
- index.html: ~20 KB
- app.js: ~15 KB
- Total: <50 KB (loads instantly)

**✅ No build step**:
- Vanilla JavaScript
- No webpack, Vite, etc.
- Faster deployments

**Future optimizations** (if needed):
- Minify JavaScript
- Combine files
- Service worker for offline
- Image optimization (if we add images)

---

## 🎯 Next Steps

Once Vercel is deployed:

1. **Test end-to-end flow**:
   - Go to app.whitemagic.dev
   - Login with API key
   - Verify all features work

2. **Update Whop products**:
   - Checkout URL → app.whitemagic.dev
   - Upgrade buttons point to Whop

3. **Monitor analytics**:
   - Enable Vercel Analytics
   - Track page views and performance

4. **Share with users**!:
   - app.whitemagic.dev is your official dashboard
   - Professional domain
   - Fast, reliable, secure

---

## 💡 Why Vercel for Dashboard?

**Perfect fit because**:
- ✅ **Static files**: No server needed
- ✅ **Fast**: Global CDN, edge caching
- ✅ **Free**: Hobby plan includes everything
- ✅ **Easy**: Git push to deploy
- ✅ **Reliable**: 99.99% uptime
- ✅ **SSL**: Automatic HTTPS
- ✅ **DX**: Best developer experience

**Alternatives considered**:
- Netlify: Good, but Vercel has better DX
- Cloudflare Pages: Good, but more complex
- GitHub Pages: No custom domains on free tier
- S3 + CloudFront: Too much config

**Vercel wins** for simplicity + features! 🎉

---

Ready to deploy your beautiful dashboard to the world! 🚀

**Estimated deployment time**: 10 minutes

Let me know when you're ready and I'll create the Vercel config files!

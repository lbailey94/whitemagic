# 🌐 DNS Configuration Guide - Squarespace

**Domain**: whitemagic.dev  
**Provider**: Squarespace (Google Domains partnership)  
**Target**: app.whitemagic.dev + api.whitemagic.dev

---

## 📋 DNS Records Needed

### Summary

You'll add **2 CNAME records** in Squarespace:

| Record Type | Name | Value | Purpose |
|-------------|------|-------|---------|
| CNAME | `app` | `cname.vercel-dns.com` | Dashboard (Vercel) |
| CNAME | `api` | `[your-railway-domain].up.railway.app` | API (Railway) |

---

## 🎯 Step-by-Step Instructions

### Step 1: Access Squarespace DNS Settings

1. **Log in to Squarespace**: https://account.squarespace.com
2. **Go to Domains**: Click "Domains" in left sidebar
3. **Select whitemagic.dev**: Click on the domain
4. **Open DNS Settings**: Click "DNS Settings" tab

You should see a page with existing DNS records.

### Step 2: Add Dashboard CNAME (for Vercel)

**Click "Add Record"** and enter:

```
Record Type: CNAME
Host: app
Value: cname.vercel-dns.com
TTL: 3600 (or leave default)
```

**What this does**:
- Maps `app.whitemagic.dev` → Vercel's CDN
- Vercel handles SSL automatically
- Users access dashboard at app.whitemagic.dev

**Click "Save"**

### Step 3: Add API CNAME (for Railway)

First, you need the Railway domain:

1. Deploy API to Railway (follow DEPLOYMENT_RAILWAY.md)
2. In Railway → Service → Settings → Domains → Add Custom Domain
3. Enter: `api.whitemagic.dev`
4. Railway shows you a CNAME target like: `whitemagic-production-abc123.up.railway.app`

**Copy that Railway domain**, then in Squarespace:

**Click "Add Record"** and enter:

```
Record Type: CNAME
Host: api
Value: [your-railway-domain].up.railway.app
TTL: 3600 (or leave default)
```

Example:
```
CNAME  api  whitemagic-production-abc123.up.railway.app
```

**Click "Save"**

### Step 4: Optional - Root Domain Redirect

If you want `whitemagic.dev` (no subdomain) to redirect to `app.whitemagic.dev`:

**Option A: Squarespace Domain Forwarding**
1. In Squarespace → Domains → whitemagic.dev
2. Click "Domain Forwarding"
3. Forward to: `https://app.whitemagic.dev`
4. Enable "Forward with 301"

**Option B: Future Marketing Site**
If you plan to add a marketing site later at root domain:
- Deploy to Vercel (separate project)
- Add CNAME `@` → `cname.vercel-dns.com`
- Or use A record to specific IP

For now, **Option A is simplest**.

---

## ⏱️ DNS Propagation Time

### How Long It Takes

- **Best case**: 5-15 minutes
- **Typical**: 30 minutes to 1 hour
- **Worst case**: Up to 48 hours (rare)

Squarespace DNS is usually fast (15-30 mins).

### Check Propagation Status

**Test your DNS changes**:

```bash
# Check if app.whitemagic.dev resolves
nslookup app.whitemagic.dev

# Check if api.whitemagic.dev resolves
nslookup api.whitemagic.dev

# More detailed check
dig app.whitemagic.dev +short
dig api.whitemagic.dev +short
```

**Expected results**:
```bash
# app.whitemagic.dev should show:
app.whitemagic.dev  canonical name = cname.vercel-dns.com

# api.whitemagic.dev should show:
api.whitemagic.dev  canonical name = whitemagic-production.up.railway.app
```

**Online tool**: https://www.whatsmydns.net/
- Enter your domain
- Check global propagation
- See which DNS servers have updated

---

## ✅ Verification Checklist

After adding DNS records:

### Immediate (5 minutes)
- [ ] Records visible in Squarespace DNS settings
- [ ] No typos in hostnames
- [ ] Correct CNAME values

### After 30 minutes
- [ ] `nslookup app.whitemagic.dev` returns Vercel
- [ ] `nslookup api.whitemagic.dev` returns Railway
- [ ] https://app.whitemagic.dev loads (may show SSL error initially)
- [ ] https://api.whitemagic.dev/health returns JSON

### After 1 hour (full propagation)
- [ ] https://app.whitemagic.dev shows dashboard with SSL ✅
- [ ] https://api.whitemagic.dev/health works with SSL ✅
- [ ] Dashboard can call API (no CORS errors)
- [ ] Login works end-to-end

---

## 🔒 .dev Domain Security (HSTS)

### Why .dev Domains Are Secure

Google owns the `.dev` TLD and enforces HTTPS:

- ✅ **HTTPS only**: Browsers force HTTPS for all .dev domains
- ✅ **HSTS preloaded**: Built into Chrome, Firefox, Safari
- ✅ **Can't be bypassed**: No way to access via HTTP

**This is GOOD** because:
- Forces best practices
- Protects user data
- Better SEO
- Professional appearance

**What it means for you**:
- Must have valid SSL (Vercel & Railway provide free)
- Can't test with HTTP (always use HTTPS)
- More secure by default

**No extra work needed** - Vercel and Railway handle SSL automatically! ✅

---

## 🐛 Troubleshooting

### DNS Record Not Propagating

**Check TTL**:
- Default is usually 3600 (1 hour)
- Lower values propagate faster
- Can't speed up initial propagation

**Check for conflicts**:
- Remove any old A records for app/api
- Only one record per subdomain
- CNAME takes precedence over A

**Flush local DNS cache**:
```bash
# Linux
sudo systemd-resolve --flush-caches

# Mac
sudo dscacheutil -flushcache

# Windows
ipconfig /flushdns
```

### SSL Certificate Errors

**"Your connection is not private"**:
- Normal for first 5-10 minutes
- Vercel/Railway provisioning Let's Encrypt cert
- Wait and refresh

**Persistent SSL errors**:
- Verify DNS resolves correctly
- Check Vercel/Railway logs
- Contact platform support

### Dashboard Can't Reach API

**CORS errors in console**:
```
Access to fetch at 'https://api.whitemagic.dev' from origin 'https://app.whitemagic.dev' has been blocked by CORS policy
```

**Solution**: Update Railway environment variable:
```bash
ALLOWED_ORIGINS=https://app.whitemagic.dev
```

**Restart Railway** after changing env vars.

### Domain Shows "Default Vercel Page"

**Issue**: Domain added to Vercel but not connected to project

**Solution**:
1. Vercel Dashboard → Your Project → Settings → Domains
2. Make sure `app.whitemagic.dev` is listed
3. If not, add it again

---

## 📊 Current DNS Configuration

After completing this guide, your DNS should look like:

```
# Squarespace DNS for whitemagic.dev

CNAME  app  cname.vercel-dns.com                        # Dashboard
CNAME  api  whitemagic-production.up.railway.app       # API

# Future additions (optional)
CNAME  www  cname.vercel-dns.com                        # www redirect
MX     @    mail.google.com (priority 10)               # Email
TXT    @    "v=spf1 include:_spf.google.com ~all"      # SPF
```

---

## 🎯 Quick Reference

### Your Domains

| Domain | Points To | Purpose |
|--------|-----------|---------|
| app.whitemagic.dev | Vercel | Dashboard (users login here) |
| api.whitemagic.dev | Railway | API backend (powers dashboard) |
| whitemagic.dev | (future) | Marketing site or redirect to app |

### Test URLs

```bash
# Dashboard
https://app.whitemagic.dev

# API Health
https://api.whitemagic.dev/health

# API Docs
https://api.whitemagic.dev/docs
```

### Support Contacts

**Squarespace DNS**:
- Help: https://support.squarespace.com/hc/en-us/articles/360002101888-Adding-custom-DNS-records
- Live chat available

**Vercel**:
- Docs: https://vercel.com/docs/concepts/projects/domains
- Support: https://vercel.com/support

**Railway**:
- Docs: https://docs.railway.app/guides/public-networking#custom-domains
- Discord: https://discord.gg/railway

---

## 📝 Save This Configuration

**For your records**, save these values:

```
Domain: whitemagic.dev
Provider: Squarespace
DNS Set Up Date: [DATE]

Records:
- app CNAME → cname.vercel-dns.com
- api CNAME → [railway-domain].up.railway.app

Deployment URLs:
- Dashboard: https://app.whitemagic.dev
- API: https://api.whitemagic.dev

Services:
- Vercel Project: whitemagic-dashboard
- Railway Project: whitemagic-api
```

---

## 🚀 You're All Set!

Once DNS propagates:
- ✅ Professional domain (whitemagic.dev)
- ✅ Secure HTTPS everywhere
- ✅ Fast global delivery (Vercel CDN)
- ✅ Scalable infrastructure (Railway)
- ✅ Ready for customers!

**Next**: Create Whop products and start onboarding users! 🎉

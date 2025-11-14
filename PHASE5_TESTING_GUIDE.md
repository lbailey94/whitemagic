# 🧪 Phase 5: End-to-End Testing Guide

**Date**: November 13, 2025  
**Status**: Ready for Testing  
**Deployments**: Railway + Vercel both live with custom domains

---

## 📋 Pre-Test Checklist

Before starting tests, verify all components are deployed:

- [x] Railway API deployed successfully
- [x] Railway custom domain: `api.whitemagic.dev`
- [x] Vercel dashboard deployed
- [x] Vercel custom domain: `app.whitemagic.dev`
- [x] DNS records configured in Squarespace
- [x] Whop webhook configured
- [x] `WHOP_WEBHOOK_SECRET` added to Railway
- [x] Vercel environment variable `WHITEMAGIC_API_BASE` set

---

## 🎯 Test Suite

### Test 1: Railway API Health Check ✅

**Objective**: Verify Railway API is accessible and healthy

**Command**:
```bash
curl https://api.whitemagic.dev/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "2.1.4"
}
```

**Status Codes**:
- ✅ **200 OK** - API is healthy
- ❌ **502/504** - DNS not propagated yet (wait 5-10 min)
- ❌ **404** - Wrong endpoint
- ❌ **Connection refused** - Service not running

**Alternative Test** (if DNS not ready):
```bash
curl https://whitemagic-production.up.railway.app/health
```

---

### Test 2: Vercel Dashboard Loads ✅

**Objective**: Verify dashboard is accessible with beautiful UI

**Steps**:
1. Open browser to: `https://app.whitemagic.dev`
2. Verify page loads without errors
3. Check browser console (F12) for any errors

**Expected**:
- ✅ Beige/cream colored page loads
- ✅ "WhiteMagic" logo/title visible
- ✅ Login form or "Sign in" button present
- ✅ No console errors

**Alternative Test** (if DNS not ready):
```
https://whitemagic-one.vercel.app
```

---

### Test 3: Dashboard Connects to API ✅

**Objective**: Verify dashboard can communicate with Railway API

**Steps**:
1. Open `https://app.whitemagic.dev`
2. Open browser console (F12)
3. Look for network requests to `api.whitemagic.dev`

**Expected in Console**:
```
GET https://api.whitemagic.dev/health → 200
```

**Or check Network tab**:
- Request to: `api.whitemagic.dev/health`
- Status: 200 OK
- Response: `{"status":"healthy"}`

**Troubleshooting**:
- If you see errors, check `WHITEMAGIC_API_BASE` in Vercel
- Make sure you clicked "Redeploy" after adding env var

---

### Test 4: API CORS Configuration ✅

**Objective**: Verify API accepts requests from dashboard

**Test in Browser Console** (at `app.whitemagic.dev`):
```javascript
fetch('https://api.whitemagic.dev/health')
  .then(r => r.json())
  .then(data => console.log('✅ CORS working!', data))
  .catch(err => console.error('❌ CORS error:', err))
```

**Expected Output**:
```
✅ CORS working! {status: "healthy", version: "2.1.4"}
```

**If CORS Error**:
- Check Railway variable: `ALLOWED_ORIGINS=https://app.whitemagic.dev`
- Make sure there are no typos
- Redeploy Railway if you just added it

---

### Test 5: Whop Product Access ✅

**Objective**: Verify Whop products are accessible and configured

**Steps**:
1. Go to your Whop storefront
2. Verify all 4 products are visible:
   - Free Plan
   - Plus Plan ($9.99/mo)
   - Pro Plan ($24.99/mo)
   - Enterprise Plan ($99.99/mo)
3. Try to purchase/access Free plan

**Expected**:
- ✅ Products load correctly
- ✅ Pricing displayed properly
- ✅ Can click "Get Access" or "Subscribe"

---

### Test 6: Whop Authentication Flow ✅

**Objective**: Verify Whop login redirects to dashboard

**Steps**:
1. Click "Sign in" or "Login" on dashboard
2. Should redirect to Whop authorization
3. Sign in with Whop account
4. Should redirect back to dashboard

**Expected Flow**:
```
Dashboard → Whop Login → User Authorizes → Dashboard (logged in)
```

**Expected in Dashboard After Login**:
- ✅ User email/name displayed
- ✅ Current plan shown
- ✅ API key generated and displayed

**Troubleshooting**:
- If redirect fails, check `WHOP_API_KEY` in Railway
- Verify Whop OAuth redirect URL is set to `https://app.whitemagic.dev`

---

### Test 7: API Key Authentication ✅

**Objective**: Verify generated API keys work

**Prerequisites**: Must be logged in with a Whop account

**Steps**:
1. Log in to dashboard
2. Copy your API key (should start with `wm_`)
3. Test API authentication

**Command**:
```bash
# Replace YOUR_API_KEY with actual key from dashboard
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.whitemagic.dev/api/v1/memories
```

**Expected Response** (if no memories yet):
```json
{
  "memories": [],
  "total": 0
}
```

**Expected Response** (if you have memories):
```json
{
  "memories": [
    {
      "id": "mem_xxx",
      "title": "Test Memory",
      "content": "...",
      "created_at": "2025-11-13T..."
    }
  ],
  "total": 1
}
```

**Status Codes**:
- ✅ **200 OK** - Authenticated successfully
- ❌ **401 Unauthorized** - Invalid API key
- ❌ **403 Forbidden** - API key valid but no permissions

---

### Test 8: Create Memory via Dashboard ✅

**Objective**: Verify full CRUD operations work

**Steps**:
1. Log in to dashboard
2. Click "Create Memory" or "New Memory"
3. Fill in:
   - **Title**: "Test Memory - Deployment Day"
   - **Content**: "WhiteMagic is now live in production!"
   - **Tags**: `deployment`, `production`, `test`
   - **Type**: Short-term
4. Click "Save" or "Create"

**Expected**:
- ✅ Success message appears
- ✅ Memory appears in list
- ✅ No errors in console

**Verify in API**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.whitemagic.dev/api/v1/memories
```

Should show your new memory in the response!

---

### Test 9: Search Memories ✅

**Objective**: Verify search functionality works

**Prerequisites**: Must have at least one memory created

**Test in Dashboard**:
1. Go to search page
2. Enter search query: "deployment"
3. Click "Search"

**Expected**:
- ✅ Search results appear
- ✅ "Test Memory - Deployment Day" is found
- ✅ Search highlights relevant content

**Test via API**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.whitemagic.dev/api/v1/search?q=deployment"
```

**Expected Response**:
```json
{
  "results": [
    {
      "id": "mem_xxx",
      "title": "Test Memory - Deployment Day",
      "content": "WhiteMagic is now live in production!",
      "score": 0.95
    }
  ],
  "total": 1
}
```

---

### Test 10: Whop Webhook Delivery ✅

**Objective**: Verify Whop sends webhooks to Railway API

**This test requires a real Whop transaction. You can:**

**Option A: Use Whop Test Mode** (if available)
1. Go to Whop Developer settings
2. Find "Test Webhooks" or "Send Test Event"
3. Send a test `membership_activated` event

**Option B: Real Subscription**
1. Create a new Whop account (or use a friend's)
2. Subscribe to Free plan
3. Check Railway logs for webhook

**Check Railway Logs**:
1. Railway → whitemagic → Deployments → Latest
2. Click "Deploy Logs" tab
3. Look for:
   ```
   INFO: Received Whop webhook: membership_activated
   INFO: User user_xxx activated on plan free
   ```

**Expected**:
- ✅ Webhook received and logged
- ✅ User's plan updated in database
- ✅ No errors in processing

**If webhook not received**:
- Check webhook URL in Whop: `https://api.whitemagic.dev/api/v1/whop/webhook`
- Verify `WHOP_WEBHOOK_SECRET` matches in Railway
- Check Whop webhook logs for delivery attempts

---

### Test 11: Rate Limiting ✅

**Objective**: Verify rate limiting is working per plan tier

**Test Free Tier** (1000 requests/hour):
```bash
# Make multiple rapid requests
for i in {1..5}; do
  curl -H "Authorization: Bearer YOUR_FREE_TIER_API_KEY" \
       https://api.whitemagic.dev/api/v1/memories
  echo "Request $i"
done
```

**Expected**:
- ✅ First 5 requests succeed (200 OK)
- ✅ After 1000 requests in an hour, get 429 Too Many Requests

**Response Headers to Check**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1699999999
```

---

### Test 12: Database Persistence ✅

**Objective**: Verify data persists across deployments

**Steps**:
1. Create a memory with title "Persistence Test"
2. Note the memory ID
3. Trigger a Railway redeploy:
   - Railway → whitemagic → Deployments
   - Click "Redeploy" on latest deployment
4. Wait for redeploy to complete
5. Fetch memories again

**Command**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.whitemagic.dev/api/v1/memories
```

**Expected**:
- ✅ "Persistence Test" memory still exists
- ✅ Same memory ID
- ✅ All data intact

**This verifies**:
- PostgreSQL is properly configured
- Data is stored in Railway's persistent database
- Not using ephemeral storage

---

### Test 13: Redis Caching ✅

**Objective**: Verify Redis is connected and working

**Test**:
```bash
# Make same request twice
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.whitemagic.dev/api/v1/memories

# Immediately make same request again
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.whitemagic.dev/api/v1/memories
```

**Check Response Headers**:
```
X-Cache-Status: MISS  # First request
X-Cache-Status: HIT   # Second request
```

**Or check Railway logs**:
```
INFO: Cache miss for user_xxx/memories
INFO: Cache hit for user_xxx/memories
```

**Expected**:
- ✅ First request queries database
- ✅ Second request served from Redis cache
- ✅ Response time faster on cached request

---

### Test 14: Error Handling ✅

**Objective**: Verify API handles errors gracefully

**Test Invalid API Key**:
```bash
curl -H "Authorization: Bearer invalid_key_12345" \
     https://api.whitemagic.dev/api/v1/memories
```

**Expected Response**:
```json
{
  "error": "Invalid API key",
  "status": 401
}
```

**Test Missing Auth Header**:
```bash
curl https://api.whitemagic.dev/api/v1/memories
```

**Expected Response**:
```json
{
  "error": "Authorization header required",
  "status": 401
}
```

**Test Invalid Endpoint**:
```bash
curl https://api.whitemagic.dev/api/v1/nonexistent
```

**Expected Response**:
```json
{
  "error": "Not found",
  "status": 404
}
```

---

### Test 15: Production Logging ✅

**Objective**: Verify logging is working properly

**Check Railway Logs**:
1. Railway → whitemagic → Deployments → Latest
2. Click "Deploy Logs" tab
3. Look for structured JSON logs

**Expected Log Format**:
```json
{
  "timestamp": "2025-11-13T22:55:00Z",
  "level": "INFO",
  "message": "Request processed",
  "user_id": "user_xxx",
  "endpoint": "/api/v1/memories",
  "duration_ms": 45
}
```

**Verify**:
- ✅ All requests logged
- ✅ JSON format (not plain text)
- ✅ Sensitive data redacted (no API keys in logs)
- ✅ Error stack traces included for errors

---

## 🎯 Success Criteria

All tests must pass for production approval:

### Critical Tests (Must Pass):
- [ ] Test 1: Health check returns 200 OK
- [ ] Test 2: Dashboard loads without errors
- [ ] Test 3: Dashboard connects to API
- [ ] Test 4: CORS configured correctly
- [ ] Test 7: API key authentication works
- [ ] Test 8: Create memory succeeds
- [ ] Test 12: Database persistence works

### Important Tests (Should Pass):
- [ ] Test 5: Whop products accessible
- [ ] Test 6: Whop auth flow works
- [ ] Test 9: Search returns results
- [ ] Test 11: Rate limiting enforced
- [ ] Test 13: Redis caching works
- [ ] Test 14: Errors handled gracefully

### Nice to Have (Can debug later):
- [ ] Test 10: Whop webhooks deliver
- [ ] Test 15: Production logging

---

## 🐛 Common Issues & Solutions

### Issue: "DNS_PROBE_FINISHED_NXDOMAIN"
**Cause**: DNS not propagated yet  
**Solution**: Wait 5-30 minutes, use Railway/Vercel URLs temporarily

### Issue: "CORS policy blocked"
**Cause**: `ALLOWED_ORIGINS` not set or wrong  
**Solution**: 
```bash
# Railway Variables should have:
ALLOWED_ORIGINS=https://app.whitemagic.dev,https://whitemagic-one.vercel.app
```

### Issue: "401 Unauthorized"
**Cause**: Invalid API key or not logged in  
**Solution**: Log in via Whop, copy fresh API key from dashboard

### Issue: "502 Bad Gateway"
**Cause**: Railway service not responding  
**Solution**: Check Railway deploy logs for startup errors

### Issue: "ModuleNotFoundError"
**Cause**: Missing dependency  
**Solution**: Check pyproject.toml has all deps in core dependencies

### Issue: Webhook not received
**Cause**: Wrong URL or secret mismatch  
**Solution**: 
- Verify webhook URL: `https://api.whitemagic.dev/api/v1/whop/webhook`
- Match `WHOP_WEBHOOK_SECRET` in Railway with Whop dashboard

---

## 📊 Test Results Template

Copy this template and check off as you test:

```markdown
## Test Results - November 13, 2025

### Infrastructure Tests
- [ ] Test 1: Health Check - PASS/FAIL
- [ ] Test 2: Dashboard Loads - PASS/FAIL
- [ ] Test 3: API Connection - PASS/FAIL
- [ ] Test 4: CORS - PASS/FAIL

### Authentication Tests
- [ ] Test 5: Whop Products - PASS/FAIL
- [ ] Test 6: Whop Auth Flow - PASS/FAIL
- [ ] Test 7: API Key Auth - PASS/FAIL

### Functionality Tests
- [ ] Test 8: Create Memory - PASS/FAIL
- [ ] Test 9: Search - PASS/FAIL
- [ ] Test 10: Webhooks - PASS/FAIL

### Performance & Reliability
- [ ] Test 11: Rate Limiting - PASS/FAIL
- [ ] Test 12: Persistence - PASS/FAIL
- [ ] Test 13: Caching - PASS/FAIL
- [ ] Test 14: Error Handling - PASS/FAIL
- [ ] Test 15: Logging - PASS/FAIL

### Overall Status: ✅ APPROVED / ⏳ PENDING / ❌ FAILED

### Notes:
(Add any observations, issues, or improvements needed)
```

---

## 🎊 After All Tests Pass

### You're Live! What's Next?

1. **Announce Launch**
   - Share Whop storefront link
   - Post on social media
   - Email potential users

2. **Monitor First Users**
   - Watch Railway logs
   - Check for errors
   - Respond to user feedback

3. **Set Up Monitoring**
   - Add uptime monitoring (UptimeRobot, Pingdom)
   - Set up error alerting
   - Track API usage metrics

4. **Documentation**
   - Write user guide
   - Create API documentation
   - Make tutorial videos

5. **Iterate**
   - Collect user feedback
   - Fix bugs
   - Add features

---

## 🚀 Launch Checklist

Before announcing to users:

- [ ] All critical tests passing
- [ ] Custom domains working (api + app)
- [ ] Whop integration complete
- [ ] Error handling tested
- [ ] Rate limits verified
- [ ] Logs showing clean operation
- [ ] README updated with production URLs
- [ ] Privacy policy / terms of service added
- [ ] Support email/contact set up
- [ ] Backup strategy in place

---

**Good luck with testing!** 🍀

If any test fails, document the error and we can debug together!

# Dashboard Preview Guide - v2.1.5

**Date**: November 13, 2025  
**Branch**: `v2.1.5-dev`

---

## 🎉 What's New in Phase 1

### ✨ Features Added
1. **Chart.js Usage Trends**
   - Beautiful line chart showing 7/30-day API usage
   - Interactive with hover tooltips
   - Toggle between time periods

2. **Smart Upgrade Banner**
   - Appears automatically for free tier at 70%+ usage
   - Dynamic messaging based on usage level
   - Smooth slide-down animation

3. **Enhanced Progress Bars**
   - Smooth color transitions (green → yellow → red)
   - Animated width changes
   - Better visual feedback

4. **Mobile Responsive**
   - Upgrade banner stacks on mobile
   - Usage stats grid adapts (4 cols → 2 cols)
   - Touch-friendly buttons

---

## 🚀 How to Preview

### Option 1: Local Static Server (Quickest)

```bash
cd /home/lucas/Desktop/whitemagic/dashboard
python3 -m http.server 3000
```

Then open: **http://localhost:3000**

### Option 2: With Full API Backend

```bash
# Terminal 1: Start API
cd /home/lucas/Desktop/whitemagic
python -m whitemagic.api

# Terminal 2: Serve dashboard
cd dashboard
python3 -m http.server 3000
```

Then open: **http://localhost:3000**

### Option 3: Using Node.js

```bash
cd /home/lucas/Desktop/whitemagic/dashboard
npx serve -p 3000
```

Then open: **http://localhost:3000**

---

## 🔑 Getting an API Key for Testing

### If you have the API running:

```bash
# Create a test user and API key
curl -X POST http://localhost:8000/dashboard/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_EXISTING_KEY" \
  -d '{"name": "Test Dashboard Key"}'
```

### If starting fresh:

The dashboard will show a login form. You'll need to:
1. Create a user via Whop webhook or direct DB insert
2. Generate an API key via `/dashboard/api-keys` endpoint
3. Use that key to log in

---

## 📸 What to Test

### 1. Chart Functionality
- [ ] Chart loads and displays data
- [ ] 7-day button is active by default
- [ ] Switching to 30-day works
- [ ] Chart is responsive on mobile
- [ ] Loading spinner shows briefly

### 2. Upgrade Banner
- [ ] Banner appears for free tier users
- [ ] Message changes based on usage %
- [ ] Banner is hidden for paid tiers
- [ ] "Upgrade Now" link works
- [ ] Responsive on mobile (stacks vertically)

### 3. Progress Bars
- [ ] Bars show correct width
- [ ] Colors change at 75% (yellow) and 90% (red)
- [ ] Smooth animation when loading
- [ ] All 4 metrics display properly

### 4. Mobile Responsiveness
- [ ] Navigation collapses properly
- [ ] Usage stats grid becomes 2 columns
- [ ] Upgrade banner stacks vertically
- [ ] Chart is readable on small screens
- [ ] Buttons are touch-friendly

### 5. General UI
- [ ] No console errors
- [ ] Lucide icons render
- [ ] All modals work
- [ ] API key management works
- [ ] Memory browser works

---

## 🐛 Known Limitations

1. **Mock Chart Data**: Chart currently uses randomly generated data
   - Need to connect to real usage history API
   - Should show actual request counts per day

2. **API Endpoint Missing**: No `/dashboard/usage-history` endpoint yet
   - Will be added in Phase 2

3. **Banner Logic**: Upgrade banner logic is client-side only
   - Consider server-side recommendations

---

## 📝 Feedback Checklist

When reviewing, please note:

**Design**:
- [ ] Colors and spacing look good?
- [ ] Chart is easy to read?
- [ ] Banner messaging is clear?

**UX**:
- [ ] Upgrade CTA is compelling?
- [ ] Progress bars are intuitive?
- [ ] Chart navigation is clear?

**Technical**:
- [ ] Performance is smooth?
- [ ] Mobile experience is good?
- [ ] Any console errors?

**Suggestions**:
- What else would you like to see on the dashboard?
- Any confusing elements?
- Missing information?

---

## 🔧 Quick Fixes if Needed

### Chart not showing?
Check browser console - Chart.js might not be loading.

### Upgrade banner not appearing?
Edit `app.js` line 701 - lower the threshold from 70 to 0 for testing.

### Mobile not responsive?
Clear browser cache or try incognito mode.

### API connection issues?
Check `API_BASE_URL` in `app.js` - should match your API server.

---

## 📊 What's Next (Phase 2)

After feedback, we'll tackle:
1. **Feature Toggles**: Plan-based feature access
2. **Usage Alerts**: Email notifications at 80%
3. **Historical Data API**: Real usage trends
4. **Billing Portal Link**: Direct Whop integration

---

## 🎯 Success Metrics

Phase 1 is successful if:
- ✅ Dashboard loads in < 2 seconds
- ✅ Chart renders without errors
- ✅ Mobile experience is smooth
- ✅ No console errors
- ✅ Upgrade CTA is visible and clickable

---

**Ready to preview!** 🚀

Send screenshots once you've tested it. Focus on:
1. Overall dashboard view (desktop)
2. Chart close-up
3. Upgrade banner (if visible)
4. Mobile view
5. Any issues or surprises

Let's make this amazing! ✨

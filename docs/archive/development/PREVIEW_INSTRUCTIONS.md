# 📸 Preview Instructions - Dashboard v2.1.5

**Quick Start**: Follow these steps to preview the enhanced dashboard!

---

## 1️⃣ Start the Dashboard (Choose One)

### Option A: Static Server (Fastest)
```bash
cd /home/lucas/Desktop/whitemagic/dashboard
python3 -m http.server 3000
```

### Option B: With API Backend
```bash
# Terminal 1: Start API
cd /home/lucas/Desktop/whitemagic
python -m whitemagic.api

# Terminal 2: Serve dashboard
cd dashboard
python3 -m http.server 3000
```

---

## 2️⃣ Open Browser

Navigate to: **http://localhost:3000**

---

## 3️⃣ Take Screenshots

### Required Screenshots:

1. **Desktop - Full Dashboard**
   - Entire page view
   - All sections visible

2. **Desktop - Usage Chart**
   - Chart section zoomed in
   - Both 7-day and 30-day views if possible

3. **Desktop - Progress Bars**
   - Close-up of the 4 usage metrics
   - Show different colors if possible

4. **Desktop - Upgrade Banner** (if visible)
   - Full banner with message
   - Button styling

5. **Mobile View** (resize browser or use DevTools)
   - Width: 375px (iPhone SE)
   - Full page scroll
   - Check stacked layout

### Optional Screenshots:

- Console (F12) - any errors?
- Network tab - load times?
- Responsive transitions - animation quality?

---

## 4️⃣ Test These Features

### Chart ✅
- [ ] Chart loads and displays data
- [ ] Can toggle between 7-day and 30-day
- [ ] Hover tooltips work
- [ ] Responsive on mobile

### Upgrade Banner ✅
- [ ] Banner appears (if free tier + high usage)
- [ ] Message is clear
- [ ] Button is clickable
- [ ] Responsive on mobile

### Progress Bars ✅
- [ ] Show correct percentages
- [ ] Colors change (blue → yellow → red)
- [ ] Smooth animations
- [ ] All 4 metrics visible

### Mobile ✅
- [ ] Navigation works
- [ ] Stats grid is 2 columns
- [ ] Banner stacks vertically
- [ ] Chart is readable
- [ ] Buttons are touchable

---

## 5️⃣ Note Any Issues

**Questions to Consider**:

**Design**:
- Does it look professional?
- Are colors pleasing?
- Is text readable?
- Any spacing issues?

**Functionality**:
- Does everything work?
- Any console errors?
- Slow to load?
- Animations smooth?

**Content**:
- Is usage data clear?
- Chart makes sense?
- Banner messaging good?
- Any confusing elements?

**Mobile**:
- Easy to navigate?
- Touch targets big enough?
- Text still readable?
- Any layout breaks?

---

## 6️⃣ Share Feedback

Send screenshots + notes covering:

### What Works Well ✅
- Favorite features
- Good design choices
- Smooth interactions

### What Needs Work 🔧
- Confusing elements
- Design improvements
- Missing information
- Bug reports

### Ideas 💡
- Additional features
- Better messaging
- Layout suggestions
- Enhancement requests

---

## 🎯 What We're Looking For

**Phase 1 Success**:
- Dashboard loads fast
- Chart is beautiful and clear
- Upgrade CTA is compelling
- Mobile experience is smooth
- No critical bugs

**Ready for Phase 2 if**:
- Visual design approved ✅
- All features work ✅
- Mobile responsive ✅
- No blocking issues ✅

---

## 🐛 Troubleshooting

### Chart not showing?
- Check browser console (F12)
- Chart.js CDN might be blocked
- Try different browser

### Upgrade banner not appearing?
- Banner only shows for free tier users
- Must be using 70%+ of quota
- Check `app.js` line 701 to test

### Mobile view not working?
- Use Chrome DevTools (F12)
- Click "Toggle device toolbar"
- Select iPhone or responsive mode

### API connection failed?
- If using Option B, ensure API is running
- Check `http://localhost:8000/docs`
- Verify API key is valid

---

## 📋 Screenshot Naming

Please name screenshots clearly:
- `dashboard-desktop-full.png`
- `dashboard-chart-7day.png`
- `dashboard-chart-30day.png`
- `dashboard-progress-bars.png`
- `dashboard-upgrade-banner.png`
- `dashboard-mobile-375px.png`
- `dashboard-console-errors.png` (if any)

---

## ⏱️ This Should Take

- **Setup**: 2 minutes
- **Testing**: 10 minutes
- **Screenshots**: 5 minutes
- **Feedback**: 5 minutes

**Total**: ~20 minutes

---

## 🚀 After Preview

Once you send screenshots and feedback:
1. We'll iterate on any issues
2. Polish based on your input
3. Move to Phase 2 (Feature Toggles)
4. Continue building v2.1.5!

---

**Ready? Let's see what we built!** 🎉

Remember:
- Take your time
- Be thorough
- Screenshot everything
- Note both good and bad
- Ask questions!

We're excited to see your feedback! 📸✨

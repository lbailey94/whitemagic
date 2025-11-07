# Dashboard Quick Start Guide

## 🎯 Quick Access

**Dashboard URL**: http://localhost:3000  
**API Server**: http://localhost:8000  
**API Docs**: http://localhost:8000/docs

---

## 🔑 Getting Your API Key

### Temporary Test Key (For Now):

```
wm_YDHAjDUvGkFfmVYIgO5NZ1D1NRU79-W5veu8rRoLFtU
```

⚠️ **This is a development test key only!**

### For Production - Use PostgreSQL:

The current SQLite setup has limitations. For production:

1. **Start PostgreSQL**:
```bash
# Using Docker
docker run -d \
  --name whitemagic-postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=whitemagic \
  -p 5432:5432 \
  postgres:15

# Or use existing PostgreSQL server
```

2. **Set DATABASE_URL**:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/whitemagic"
```

3. **Create user via API**:
```bash
# The API will auto-create tables on first request
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","plan":"professional"}'
```

4. **Generate API key via dashboard endpoint** (once logged in with Whop)

---

## 🎨 Dashboard Features (Current)

### ✅ Working Now:
- Login form with API key auth
- Account information display
- Usage statistics with progress bars
- API key management interface
- Clean, modern Tailwind UI

### 🚧 Coming Soon (Improvements):
- **Charts & Graphs**: Usage trends over time
- **Memory Browser**: View, search, filter memories
- **Public Landing Page**: Hero section with features
- **API Playground**: Test endpoints interactively
- **Real-time Updates**: Live activity feed
- **Tag Cloud**: Popular memory tags
- **Analytics Dashboard**: Detailed metrics

---

## 🛠️ Dashboard Improvements Plan

See `dashboard/IMPROVEMENTS.md` for the full roadmap!

### Phase 1 - Quick Wins (Next):

1. **Add Chart.js for visualizations**
2. **Memory management UI**
3. **Better stats display with trends**
4. **Public landing page**

###  Phase 2 - Enhanced Features:

5. **Analytics dashboard**
6. **API playground**
7. **Webhook configuration**
8. **Settings page**

---

## 🐛 Known Issues

### SQLite Compatibility:
The current SQLite database has limitations with the `Quota` model using PostgreSQL-specific functions (`date_trunc`). 

**Workaround**: Use the test key above for now, or switch to PostgreSQL for full functionality.

**Fix in progress**: Updating database models for SQLite compatibility.

---

## 🚀 Next Steps

1. **Test the dashboard** with the temporary key above
2. **Review dashboard/IMPROVEMENTS.md** for enhancement ideas
3. **Switch to PostgreSQL** for production use
4. **Implement dashboard improvements** based on feedback

---

## 📝 Dashboard Architecture

```
dashboard/
├── index.html        # Main dashboard UI
├── app.js            # JavaScript logic
├── IMPROVEMENTS.md   # Enhancement roadmap
└── README.md         # This file

Features:
- Vanilla JavaScript (no build step)
- Tailwind CSS for styling
- Lucide icons
- FastAPI backend integration
- JWT-style API key auth
```

---

## 💡 Tips

1. **Open DevTools** (F12) to see API calls and debug
2. **Check Network tab** if dashboard doesn't load data
3. **API endpoints** are at `/api/v1/*` and `/dashboard/*`
4. **Swagger docs** at http://localhost:8000/docs for API testing

---

## 🎉 Ready to Go!

The dashboard is running and ready for testing! Use the temp key above to log in and explore.

Once logged in, you'll see:
- Your account info
- Usage statistics
- API key management
- Memory counts and storage

Let's improve it together! 🚀

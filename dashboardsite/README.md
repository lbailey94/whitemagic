# WhiteMagic Dashboard Site

## Quick Start
```bash
cd dashboardsite
python3 -m http.server 8080
```

Visit: http://localhost:8080

## Hosting Options

### Best: **Vercel** (Recommended)
- Free tier generous
- Auto-deploy from GitHub
- Edge functions for API
- Custom domains
- Cost: $0-20/month

### Alternative: **Netlify**
- Similar to Vercel
- Serverless functions
- Free tier available

### For Static + API: **Railway**
- Hosts both frontend & backend
- PostgreSQL included
- $5/month base

### Why NOT static-only (like tiiny.host):
Dashboard needs API calls to backend. Static hosts can't run Python/FastAPI.

## Deploy Steps

1. Push to GitHub
2. Connect to Vercel
3. Deploy!

See DEPLOYMENT.md for details.

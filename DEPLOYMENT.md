# WhiteMagic Deployment Guide

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_URL=redis://host:6379
WHOP_API_KEY=whop_xxx
WHOP_WEBHOOK_SECRET=whsec_xxx
ALLOWED_ORIGINS=https://app.whitemagic.dev
```

## Quick Deploy (Railway)

```bash
railway login
railway init
railway add postgresql
railway add redis
railway up
```

Set environment variables in dashboard, configure domain.

## Database Setup

```bash
alembic upgrade head
```

## Whop Webhook

URL: `https://api.whitemagic.dev/webhooks/whop`

Events: membership.created, updated, deleted, went_valid, went_invalid

## Production Checklist

- [ ] Environment variables set
- [ ] Database migrations run
- [ ] Whop webhook configured
- [ ] HTTPS enabled
- [ ] Health check working: /health
- [ ] Dashboard accessible: /
- [ ] API docs accessible: /docs

## Monitoring

- Use /health endpoint for uptime checks
- Check logs for errors
- Monitor database connections
- Track API response times

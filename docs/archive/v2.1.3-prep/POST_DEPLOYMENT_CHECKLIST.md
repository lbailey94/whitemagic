# WhiteMagic v2.1.0 - Post-Deployment Checklist

**Print this page and check off each item after deployment**

---

## ✅ CI/CD & Infrastructure

- [ ] PyPI package exists for tag v2.1.0
- [ ] Docker image exists: `lbailey94/whitemagic:2.1.0`
- [ ] GitHub Pages live at: `lbailey94.github.io/whitemagic`
- [ ] Pre-commit hooks installed locally
- [ ] Branch protection enabled on `main`

---

## ✅ Production Deployment

- [ ] `docker compose up -d` shows all services healthy
- [ ] Database migrations complete: `alembic current` shows latest
- [ ] Admin API key created and working
- [ ] `/health` endpoint returns `200`
- [ ] `/docs` loads with full API documentation
- [ ] `/api/v1/stats` responds (authenticated)

---

## ✅ TLS & Security

- [ ] HTTPS active via Caddy or Nginx
- [ ] Certificate auto-renewal configured
- [ ] CORS configured correctly (no `*` wildcard)
- [ ] Rate limiting enabled
- [ ] `X-RateLimit-*` headers present in responses
- [ ] Environment secrets not committed to git

---

## ✅ Monitoring & Backups

- [ ] Daily backup cron job scheduled (`/backups/whitemagic_*.sql.gz`)
- [ ] Backup restore tested successfully
- [ ] Sentry DSN configured (optional)
- [ ] Log aggregation working (JSON format)
- [ ] Log rotation configured
- [ ] Disk space alerts configured

---

## ✅ Whop Integration

- [ ] `WHOP_API_KEY` set in `.env`
- [ ] `WHOP_WEBHOOK_SECRET` set in `.env`
- [ ] Webhooks configured in Whop dashboard:
  - [ ] `subscription.created`
  - [ ] `subscription.renewed`
  - [ ] `subscription.canceled`
  - [ ] `subscription.upgraded`
  - [ ] `subscription.downgraded`
- [ ] Test purchase → API key issued successfully
- [ ] Test cancellation → key revoked after grace period
- [ ] Webhook signature validation working

---

## ✅ Performance & Observability

- [ ] Response times < 200ms for simple operations
- [ ] Database pool size configured (20 for PostgreSQL)
- [ ] Redis connected (if rate limiting enabled)
- [ ] Worker count set appropriately (4 recommended)
- [ ] Memory usage stable under load
- [ ] No connection leaks observed

---

## ✅ Documentation & Team Readiness

- [ ] Team has access to `.env.example`
- [ ] Admin knows how to mint new API keys
- [ ] Support knows how to check user quotas
- [ ] Support knows how to handle "can't access" tickets
- [ ] Backup/restore procedure documented internally
- [ ] Incident response plan documented
- [ ] Escalation contacts defined

---

## ✅ User Experience

- [ ] New user signup flow tested end-to-end
- [ ] API key delivery working (email or Whop)
- [ ] Dashboard accessible (if applicable)
- [ ] Example API calls in documentation work
- [ ] Error messages helpful and actionable
- [ ] Rate limit messaging clear to users

---

## 🎯 Final Verification Commands

Run these commands and verify all return successfully:

```bash
# Health check
curl https://yourdomain.com/health

# API docs
curl https://yourdomain.com/docs

# Authenticated call
curl -H "Authorization: Bearer $ADMIN_KEY" \
  https://yourdomain.com/api/v1/stats

# Rate limit headers
curl -I -H "Authorization: Bearer $ADMIN_KEY" \
  https://yourdomain.com/api/v1/stats | grep "X-RateLimit"

# Database connection
docker compose exec db psql -U wmuser -d whitemagic -c "SELECT count(*) FROM users;"

# Redis connection (if used)
docker compose exec redis redis-cli ping
```

---

## 📊 Acceptance Criteria

**Ready for production if**:
- All critical checks (✅) complete
- At least 90% of all checks complete
- Test purchase → API key flow works end-to-end
- No error logs for 1 hour of operation
- Response times acceptable under expected load

**Go-live approved by**: ________________  
**Date**: ________________  
**Time**: ________________

---

## 🚨 Emergency Contacts

**Technical Lead**: ________________  
**DevOps**: ________________  
**Support**: ________________

---

## 📝 Post-Launch Monitoring (First 48 Hours)

- [ ] Hour 1: Check logs every 15 minutes
- [ ] Hour 4: First backup completed successfully
- [ ] Hour 12: No memory leaks observed
- [ ] Hour 24: Rate limits functioning as expected
- [ ] Hour 48: No critical errors, ready to scale

---

**Checklist completed by**: ________________  
**Date**: ________________  
**Notes**:

_______________________________________________________________

_______________________________________________________________

_______________________________________________________________

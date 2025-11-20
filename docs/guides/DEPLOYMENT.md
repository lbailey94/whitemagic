# WhiteMagic Deployment Guide - Complete

**Version**: 2.6.5  
**Updated**: 2025-11-20

This guide consolidates all deployment information for WhiteMagic.

---

## Quick Start Deployment

For basic deployment, WhiteMagic can run on any system with Python 3.8+:

```bash
# Install WhiteMagic
pip install whitemagic

# Initialize
whitemagic init

# Run API server (optional)
whitemagic serve --port 8000
```

---

## Production Deployment

### Requirements

- Python 3.8+
- PostgreSQL 12+ (recommended) or SQLite
- Redis (optional, for caching)
- 2GB+ RAM
- SSL certificate (for HTTPS)

### Environment Setup

```bash
# Create .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql://user:pass@localhost/whitemagic
REDIS_URL=redis://localhost:6379
SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
EOF
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  whitemagic:
    image: whitemagic:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/whitemagic
    depends_on:
      - db
      
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: whitemagic
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Cloud Platforms

#### Railway

```bash
# One-click deploy
railway init
railway up
```

#### Vercel (API only)

```bash
# Deploy API endpoints
vercel deploy
```

#### AWS/GCP/Azure

See detailed cloud-specific guides in documentation.

---

## Security Considerations

1. **Environment Variables**: Never commit .env files
2. **API Keys**: Use secret management (Vault, AWS Secrets Manager)
3. **HTTPS**: Always use TLS in production
4. **Rate Limiting**: Configure in production.yaml
5. **Authentication**: Enable JWT or OAuth

---

## Monitoring

### Health Checks

```bash
# Check system health
curl https://your-domain.com/health

# Check metrics
curl https://your-domain.com/metrics
```

### Logging

```python
# Configure logging
LOGGING_LEVEL=INFO
LOG_FORMAT=json
```

---

## Scaling

### Horizontal Scaling

- Use load balancer (Nginx, HAProxy)
- Multiple API instances
- Shared Redis cache
- Centralized database

### Performance Optimization

- Enable caching (Redis)
- Use CDN for static assets
- Connection pooling
- Query optimization

---

## Troubleshooting

### Common Issues

**Database Connection Fails**:
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL
```

**Memory Issues**:
```bash
# Increase worker memory
export WORKER_MEMORY=2GB
```

**Port Already in Use**:
```bash
# Change port
whitemagic serve --port 8001
```

---

## Backup & Recovery

### Database Backups

```bash
# Automated daily backups
pg_dump whitemagic > backup_$(date +%Y%m%d).sql

# Restore
psql whitemagic < backup_20251120.sql
```

### Memory Backups

```bash
# Export memories
whitemagic backup export --output memories_backup.tar.gz

# Restore
whitemagic backup restore memories_backup.tar.gz
```

---

## Updates

### Zero-Downtime Updates

```bash
# Rolling update with Docker
docker-compose up -d --no-deps --build whitemagic

# Health check before switching traffic
curl http://new-instance/health
```

---

For more details, see individual deployment platform guides.

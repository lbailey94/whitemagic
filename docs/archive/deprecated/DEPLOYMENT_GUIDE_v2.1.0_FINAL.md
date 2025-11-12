# 🚀 WhiteMagic v2.1.0 - Complete Deployment Guide

**Last Updated**: November 9, 2025  
**Status**: ✅ **PRODUCTION READY - ALL TESTS PASSING (80/80)**  
**Time Required**: 1-2 hours for full deployment

---

## 📋 **Pre-Deployment Checklist**

### ✅ **What's Ready**
- [x] **80/80 tests passing** (0 failures!)
- [x] **Pydantic V2 migrated** (21 warnings → 5)
- [x] **MCP Server published** to npm (`whitemagic-mcp@2.1.0`)
- [x] **All critical bugs fixed** (date handling, search, auth, quotas)
- [x] **Security hardened** (no wildcards, hashed keys, rate limiting)
- [x] **Documentation complete** (187 files indexed)

### 📌 **What You Need**
- [ ] GitHub account (for CI/CD)
- [ ] Vercel account (for dashboard - free tier OK)
- [ ] Railway account (for API - free tier OK)
- [ ] Domain name (optional but recommended)

---

## 🎯 **Three Deployment Options**

### **Option 1: Quick Launch (Vercel + Railway)** ⭐ **RECOMMENDED**
- **Time**: 45-60 minutes
- **Best for**: Fast deployment, managed infrastructure
- **Cost**: Free tier available
- **Steps**: [Jump to Option 1](#option-1-vercel--railway-deployment)

### **Option 2: Docker Compose (Self-Hosted)**
- **Time**: 30-45 minutes
- **Best for**: On-premise, full control
- **Cost**: Only server costs
- **Steps**: [Jump to Option 2](#option-2-docker-compose-deployment)

### **Option 3: Manual Setup**
- **Time**: 2+ hours
- **Best for**: Custom infrastructure
- **Steps**: [Jump to Option 3](#option-3-manual-deployment)

---

# Option 1: Vercel + Railway Deployment

## Part A: Deploy API to Railway (30 min)

### Step 1: Create Railway Account & Project
```bash
# 1. Go to https://railway.app/new
# 2. Sign in with GitHub
# 3. Click "New Project"
# 4. Select "Deploy from GitHub repo"
# 5. Choose "lbailey94/whitemagic"
```

### Step 2: Add PostgreSQL Database
```bash
# In Railway project:
# 1. Click "New" → "Database" → "PostgreSQL"
# 2. Railway automatically creates DATABASE_URL
# 3. No manual setup needed!
```

### Step 3: Add Redis (Optional - for rate limiting)
```bash
# In Railway project:
# 1. Click "New" → "Database" → "Redis"
# 2. Railway automatically creates REDIS_URL
```

### Step 4: Configure API Service
```bash
# In Railway project:
# 1. Click on the "whitemagic" service
# 2. Go to "Settings" → "Environment Variables"
# 3. Add these variables:
```

**Required Environment Variables:**
```env
# Database (auto-populated by Railway)
DATABASE_URL=${DATABASE_URL}

# Redis (auto-populated by Railway)
REDIS_URL=${REDIS_URL}

# Security - GENERATE NEW KEYS!
SECRET_KEY=<generate-with: openssl rand -hex 32>
JWT_SECRET=<generate-with: openssl rand -hex 32>

# CORS - UPDATE WITH YOUR DOMAIN!
ALLOWED_ORIGINS=https://your-dashboard.vercel.app,https://yourdomain.com

# API Base
WM_BASE_PATH=/app/users

# Optional: Whop Integration
WHOP_API_KEY=your_whop_key_here
WHOP_WEBHOOK_SECRET=your_webhook_secret_here
```

### Step 5: Deploy API
```bash
# Railway will auto-deploy on push to main
# Or manually trigger:
# 1. Go to "Deployments" tab
# 2. Click "Deploy"

# Your API will be live at:
# https://whitemagic-api.up.railway.app
```

### Step 6: Verify API Deployment
```bash
# Test health endpoint
curl https://whitemagic-api.up.railway.app/health

# Expected response:
# {"status": "healthy", "version": "2.1.0"}

# Check API docs
open https://whitemagic-api.up.railway.app/docs
```

---

## Part B: Deploy Dashboard to Vercel (15 min)

### Step 1: Prepare Dashboard
```bash
# Update API URL in dashboard/index.html
cd /home/lucas/Desktop/whitemagic/dashboard

# Option A: Update meta tag (recommended)
# Edit index.html, find:
# <meta name="whitemagic-api-base" content="http://localhost:8000">
# Replace with:
# <meta name="whitemagic-api-base" content="https://whitemagic-api.up.railway.app">

# Option B: Create vercel.json
cat > vercel.json << 'EOF'
{
  "version": 2,
  "env": {
    "NEXT_PUBLIC_API_URL": "https://whitemagic-api.up.railway.app"
  }
}
EOF

git add vercel.json index.html
git commit -m "chore: configure for Vercel deployment"
git push
```

### Step 2: Deploy to Vercel
```bash
# 1. Go to https://vercel.com/new
# 2. Import "lbailey94/whitemagic"
# 3. Configure:
#    - Root Directory: dashboard
#    - Framework Preset: Other
#    - Build Command: (leave empty)
#    - Output Directory: .
# 4. Add environment variable:
#    - NEXT_PUBLIC_API_URL = https://whitemagic-api.up.railway.app
# 5. Click "Deploy"
```

### Step 3: Configure Custom Domain (Optional)
```bash
# In Vercel project:
# 1. Go to Settings → Domains
# 2. Add your domain: app.yourdomain.com
# 3. Follow DNS instructions
# 4. Wait for SSL certificate (automatic)
```

### Step 4: Verify Dashboard
```bash
# Open dashboard
open https://whitemagic-dashboard.vercel.app

# Or your custom domain:
open https://app.yourdomain.com
```

---

## Part C: Update CORS in Railway

### Step 1: Update API Environment Variables
```bash
# In Railway project:
# 1. Go to API service → Variables
# 2. Update ALLOWED_ORIGINS:
ALLOWED_ORIGINS=https://whitemagic-dashboard.vercel.app,https://app.yourdomain.com

# 3. Redeploy (automatic)
```

---

# Option 2: Docker Compose Deployment

## Prerequisites
```bash
# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin
```

## Step 1: Clone & Configure
```bash
# Clone repo
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic

# Checkout release branch
git checkout release/v2.1.0

# Create environment file
cp .env.example .env
nano .env
```

**Update .env:**
```env
# Database
DATABASE_URL=postgresql://whitemagic:changeme@db:5432/whitemagic

# Redis
REDIS_URL=redis://redis:6379/0

# Security - GENERATE NEW KEYS!
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

# CORS - UPDATE WITH YOUR DOMAIN!
ALLOWED_ORIGINS=https://yourdomain.com

# API Base
WM_BASE_PATH=/app/users

# Optional: Whop
WHOP_API_KEY=your_key
WHOP_WEBHOOK_SECRET=your_secret
```

## Step 2: Deploy Stack
```bash
# Start all services
docker compose up -d

# Check logs
docker compose logs -f api

# Verify services
docker compose ps
```

## Step 3: Verify Deployment
```bash
# Test API
curl http://localhost:8000/health

# Test dashboard
open http://localhost:3000

# Check reverse proxy (Caddy)
curl http://localhost
```

## Step 4: Configure Domain (Optional)
```bash
# Update Caddyfile
nano Caddyfile

# Add your domain:
yourdomain.com {
    reverse_proxy dashboard:80
}

api.yourdomain.com {
    reverse_proxy api:8000
}

# Reload Caddy
docker compose restart caddy
```

---

# Option 3: Manual Deployment

## Step 1: Server Setup
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.10+
sudo apt-get install -y python3.10 python3.10-venv python3-pip

# Install PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib

# Install Redis
sudo apt-get install -y redis-server

# Install Nginx
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

## Step 2: Database Setup
```bash
# Create database
sudo -u postgres psql << EOF
CREATE USER whitemagic WITH PASSWORD 'secure_password_here';
CREATE DATABASE whitemagic OWNER whitemagic;
GRANT ALL PRIVILEGES ON DATABASE whitemagic TO whitemagic;
EOF
```

## Step 3: Application Setup
```bash
# Clone repo
cd /opt
sudo git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
sudo git checkout release/v2.1.0

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[api]"

# Configure
cp .env.example .env
nano .env
```

## Step 4: Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/whitemagic-api.service
```

**Service file:**
```ini
[Unit]
Description=WhiteMagic API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/whitemagic
Environment="PATH=/opt/whitemagic/.venv/bin"
EnvironmentFile=/opt/whitemagic/.env
ExecStart=/opt/whitemagic/.venv/bin/uvicorn whitemagic.api.app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable whitemagic-api
sudo systemctl start whitemagic-api
sudo systemctl status whitemagic-api
```

## Step 5: Nginx Configuration
```bash
# Create config
sudo nano /etc/nginx/sites-available/whitemagic
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name app.yourdomain.com;
    root /opt/whitemagic/dashboard;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/whitemagic /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificates
sudo certbot --nginx -d api.yourdomain.com -d app.yourdomain.com
```

---

# Post-Deployment Verification

## Health Checks
```bash
# API health
curl https://api.yourdomain.com/health

# Expected: {"status": "healthy", "version": "2.1.0"}

# API docs
curl https://api.yourdomain.com/docs

# Dashboard
open https://app.yourdomain.com
```

## Create First User
```bash
# Using the API
curl -X POST https://api.yourdomain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "password": "secure_password",
    "plan_tier": "pro"
  }'

# Or use the script
cd /opt/whitemagic
source .venv/bin/activate
python scripts/create_demo_user.py
```

## Test Full Workflow
```bash
# 1. Create memory
curl -X POST https://api.yourdomain.com/api/v1/memories \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Memory",
    "content": "This is a test",
    "type": "short_term",
    "tags": ["test"]
  }'

# 2. Search memories
curl https://api.yourdomain.com/api/v1/memories/search?query=test \
  -H "Authorization: Bearer YOUR_API_KEY"

# 3. Get stats
curl https://api.yourdomain.com/api/v1/stats \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

# Monitoring & Maintenance

## Log Monitoring

### Railway
```bash
# View logs in Railway dashboard:
# 1. Go to your project
# 2. Click "Deployments" tab
# 3. View real-time logs
```

### Docker Compose
```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api
```

### Systemd
```bash
# View service logs
sudo journalctl -u whitemagic-api -f

# Last 100 lines
sudo journalctl -u whitemagic-api -n 100
```

## Database Backups

### Automated Backup Script
```bash
# Create backup script
cat > /opt/whitemagic/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/whitemagic/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U whitemagic whitemagic | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_$DATE.sql.gz"
EOF

chmod +x /opt/whitemagic/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/whitemagic/backup.sh") | crontab -
```

## Performance Monitoring

### Check System Resources
```bash
# CPU & Memory
docker stats

# Or for systemd:
systemctl status whitemagic-api
```

### Check Database
```bash
# Connect to database
docker compose exec db psql -U whitemagic

# Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

# Troubleshooting

## Common Issues

### Issue: "Connection refused" to database
```bash
# Check database is running
docker compose ps db
# Or:
systemctl status postgresql

# Check connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Issue: "CORS error" in dashboard
```bash
# Update ALLOWED_ORIGINS in Railway/env
ALLOWED_ORIGINS=https://your-dashboard.vercel.app

# Verify in API logs
docker compose logs api | grep CORS
```

### Issue: Tests failing
```bash
# Run test suite
cd /home/lucas/Desktop/whitemagic
source .venv/bin/activate
pytest tests/ -v

# If failures, check recent changes:
git log --oneline -10
```

### Issue: "Module not found" errors
```bash
# Reinstall dependencies
pip install -e ".[api,dev]"

# Or in Docker:
docker compose build --no-cache api
docker compose up -d
```

---

# Security Checklist

## Before Going Live

- [ ] Changed all default passwords
- [ ] Generated new SECRET_KEY and JWT_SECRET
- [ ] Updated ALLOWED_ORIGINS (NO WILDCARDS!)
- [ ] Enabled HTTPS/SSL
- [ ] Set up database backups
- [ ] Configured rate limiting
- [ ] Reviewed API key permissions
- [ ] Set up monitoring/alerts
- [ ] Documented recovery procedures

## Security Best Practices

```bash
# 1. Use environment variables (never hardcode secrets)
# 2. Enable rate limiting (already configured)
# 3. Use strong passwords (32+ characters)
# 4. Keep dependencies updated
pip list --outdated

# 5. Monitor logs for suspicious activity
grep "401\|403\|500" /var/log/nginx/access.log

# 6. Regular security audits
pip-audit

# 7. Use HTTPS everywhere (Caddy/Nginx/Vercel handle this)
```

---

# Success! 🎉

Your WhiteMagic instance is now deployed and running!

## Next Steps

1. **Submit to MCP Registry** - See [NEXT_STEPS.md](NEXT_STEPS.md)
2. **Create demo video** - Show off your deployment
3. **Announce launch** - Share on social media
4. **Monitor usage** - Check logs and metrics
5. **Scale as needed** - Upgrade resources when traffic grows

## Support

- **Issues**: https://github.com/lbailey94/whitemagic/issues
- **Docs**: https://lbailey94.github.io/whitemagic
- **Status**: Check `PROJECT_STATUS.md`

---

**Deployed by**: Your Name  
**Deployment Date**: November 9, 2025  
**Version**: 2.1.0  
**Status**: ✅ Production Ready

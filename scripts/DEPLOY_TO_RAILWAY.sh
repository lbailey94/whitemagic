#!/bin/bash
# Quick Deploy to Railway - Interactive Script

echo "======================================================================"
echo "WhiteMagic API - Railway Deployment Helper"
echo "======================================================================"
echo ""

# Check if git repo is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Warning: You have uncommitted changes"
    git status --short
    echo ""
    read -p "Commit changes first? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add -A
        read -p "Commit message: " commit_msg
        git commit -m "$commit_msg"
    fi
fi

echo ""
echo "📋 Pre-Deployment Checklist"
echo "======================================================================"
echo ""
echo "Before deploying, make sure you have:"
echo ""
echo "1. Railway Account"
echo "   → Sign up at https://railway.app"
echo ""
echo "2. GitHub Repository"
echo "   → Your code must be pushed to GitHub"
echo ""
echo "3. Whop Credentials (if using Whop)"
echo "   → WHOP_API_KEY"
echo "   → WHOP_WEBHOOK_SECRET"
echo "   → Plan IDs configured"
echo ""
echo "4. Secret Key Generated"
echo "   → Strong random string (64+ characters)"
echo ""
echo "======================================================================"
echo ""

read -p "Do you have all the above? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Please complete the checklist first"
    exit 1
fi

echo ""
echo "🚀 Deployment Steps"
echo "======================================================================"
echo ""
echo "Step 1: Push to GitHub"
echo "----------------------------------------------------------------------"
echo ""

# Get current remote
REMOTE=$(git remote get-url origin 2>/dev/null)
if [ -z "$REMOTE" ]; then
    echo "❌ No git remote configured"
    echo ""
    echo "Set up GitHub remote:"
    echo "  git remote add origin https://github.com/yourusername/whitemagic.git"
    exit 1
fi

echo "Current remote: $REMOTE"
echo ""
read -p "Push to GitHub now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Pushing to GitHub..."
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo "✅ Pushed to GitHub successfully"
    else
        echo "❌ Push failed. Please fix and try again."
        exit 1
    fi
fi

echo ""
echo "Step 2: Create Railway Project"
echo "----------------------------------------------------------------------"
echo ""
echo "1. Go to: https://railway.app/new"
echo "2. Click 'Deploy from GitHub repo'"
echo "3. Select your whitemagic repository"
echo "4. Railway will detect Python and start deploying"
echo ""
read -p "Press Enter when you've created the Railway project..."
echo ""

echo "Step 3: Add Database Services"
echo "----------------------------------------------------------------------"
echo ""
echo "In your Railway project:"
echo ""
echo "1. Click '+ New' → 'Database' → 'PostgreSQL'"
echo "   ✅ DATABASE_URL will be auto-set"
echo ""
echo "2. Click '+ New' → 'Database' → 'Redis'"  
echo "   ✅ REDIS_URL will be auto-set"
echo ""
read -p "Press Enter when databases are added..."
echo ""

echo "Step 4: Set Environment Variables"
echo "----------------------------------------------------------------------"
echo ""
echo "In Railway project → Variables, add:"
echo ""
echo "Required:"
echo "  SECRET_KEY=<64-character-random-string>"
echo "  ENVIRONMENT=production"
echo ""
echo "For Whop Integration:"
echo "  WHOP_API_KEY=<your-whop-api-key>"
echo "  WHOP_WEBHOOK_SECRET=<your-webhook-secret>"
echo "  WHOP_PLAN_FREE=plan_xxxxx"
echo "  WHOP_PLAN_STARTER=plan_xxxxx"
echo "  WHOP_PLAN_PRO=plan_xxxxx"
echo "  WHOP_PLAN_ENTERPRISE=plan_xxxxx"
echo ""
echo "Optional:"
echo "  ALLOWED_ORIGINS=https://yourdomain.com"
echo "  WM_BASE_PATH=/app/users"
echo ""
echo "Generate SECRET_KEY:"
openssl rand -hex 32
echo ""
read -p "Press Enter when environment variables are set..."
echo ""

echo "Step 5: Run Database Migrations"
echo "----------------------------------------------------------------------"
echo ""
echo "In Railway project → your service → 'Shell' tab:"
echo ""
echo "Run: alembic upgrade head"
echo ""
read -p "Press Enter when migrations are complete..."
echo ""

echo "Step 6: Verify Deployment"
echo "----------------------------------------------------------------------"
echo ""
read -p "Enter your Railway URL (e.g., https://whitemagic-production.up.railway.app): " RAILWAY_URL
echo ""
echo "Testing health endpoint..."
echo ""

HEALTH_CHECK=$(curl -s "$RAILWAY_URL/health")
if [ $? -eq 0 ]; then
    echo "✅ Health check response:"
    echo "$HEALTH_CHECK" | python3 -m json.tool
    echo ""
else
    echo "❌ Health check failed"
    echo "Check Railway logs for errors"
    exit 1
fi

echo ""
echo "Testing API documentation..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "$RAILWAY_URL/docs"
echo ""

echo ""
echo "======================================================================"
echo "🎉 Deployment Complete!"
echo "======================================================================"
echo ""
echo "Your API is now live at:"
echo "  $RAILWAY_URL"
echo ""
echo "Available endpoints:"
echo "  - Health: $RAILWAY_URL/health"
echo "  - Docs: $RAILWAY_URL/docs"
echo "  - API: $RAILWAY_URL/api/v1/"
echo "  - Dashboard: $RAILWAY_URL/dashboard/"
echo ""
echo "Next steps:"
echo "  1. Configure Whop webhook: $RAILWAY_URL/webhooks/whop"
echo "  2. Test with Postman/curl"
echo "  3. Monitor Railway logs"
echo "  4. Set up custom domain (optional)"
echo ""
echo "======================================================================"
echo "Happy deploying! 🚀"
echo "======================================================================"

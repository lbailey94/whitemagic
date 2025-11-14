#!/bin/bash
# Test Whop webhook to create a user and generate API key

# Your Whop webhook secret (from Railway env vars)
WEBHOOK_SECRET="wsk_d38ff04258db3da53bfd2b8e344731b7e042c2eabdf270abbd6db14ccd4f8e"

# Test webhook payload
PAYLOAD='{
  "type": "membership_activated",
  "data": {
    "id": "mem_test123",
    "user_id": "user_test123",
    "plan_id": "plan_mBkVBNKnQDHI",
    "email": "test@whitemagic.dev",
    "status": "active"
  }
}'

# Calculate signature (SHA-256 HMAC)
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -binary | xxd -p)

# Send webhook
echo "Sending test webhook to create user..."
curl -X POST https://api.whitemagic.dev/webhooks/whop \
  -H "Content-Type: application/json" \
  -H "X-Whop-Signature: $SIGNATURE" \
  -d "$PAYLOAD"

echo -e "\n\n✅ Webhook sent! Now check Railway logs for the API key:"
echo "   Railway → whitemagic → Deployments → Latest → Deploy Logs"
echo "   Look for: 'New user provisioned: test@whitemagic.dev (API key generated: wm_prod_...)'"

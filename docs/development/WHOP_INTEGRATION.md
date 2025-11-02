# WhiteMagic Whop Integration Guide

**Version**: 0.2.0  
**Status**: Production Ready  
**Documentation**: Whop API integration for payments and licensing

---

## Overview

WhiteMagic integrates with [Whop](https://whop.com) for:
- 💳 **Payment Processing**: Handle subscriptions and payments
- 🔐 **License Management**: Validate user licenses
- 👤 **User Provisioning**: Auto-create users on purchase
- 📊 **Plan Synchronization**: Keep plan tiers in sync
- 🔔 **Webhook Events**: Real-time subscription updates

---

## Setup

### 1. Create Whop Account

1. Sign up at https://whop.com
2. Create a new product
3. Set up pricing plans matching WhiteMagic tiers

### 2. Get API Credentials

From Whop Dashboard → Settings → Developer:

- **API Key**: For API calls
- **Webhook Secret**: For webhook verification

### 3. Configure Environment

```bash
# Required
WHOP_API_KEY=whop_...
WHOP_WEBHOOK_SECRET=whsec_...

# Optional (for testing)
WHOP_TEST_MODE=true
```

### 4. Configure Webhook Endpoint

In Whop Dashboard → Settings → Webhooks:

**Webhook URL**: `https://api.whitemagic.dev/webhooks/whop`

**Events to Subscribe**:
- `membership.created`
- `membership.updated`
- `membership.deleted`
- `membership.went_valid`
- `membership.went_invalid`

---

## Plan Mapping

Map Whop plan IDs to WhiteMagic tiers in `whitemagic/api/whop.py`:

```python
WHOP_PLAN_MAPPING = {
    'plan_abc123': 'starter',    # Your Starter plan ID
    'plan_def456': 'pro',        # Your Pro plan ID
    'plan_ghi789': 'enterprise', # Your Enterprise plan ID
}
```

### Plan Tiers

| Whop Plan | WhiteMagic Tier | Price | Limits |
|-----------|-----------------|-------|--------|
| Free | `free` | $0 | 10 RPM, 100/day |
| Starter | `starter` | $10/mo | 60 RPM, 5K/day |
| Pro | `pro` | $30/mo | 300 RPM, 50K/day |
| Enterprise | `enterprise` | Custom | 1K RPM, 1M/day |

---

## Webhook Events

### membership.created

**Triggered**: New subscription purchase

**Action**:
1. Create new `User` in database
2. Set `plan_tier` from Whop plan
3. Generate default API key
4. Create initial `Quota`
5. Send welcome email (TODO)

```json
{
  "type": "membership.created",
  "data": {
    "id": "mem_abc123",
    "user": "user_xyz789",
    "email": "customer@example.com",
    "plan": "plan_starter",
    "status": "active",
    "valid": true
  }
}
```

### membership.updated

**Triggered**: Plan change, renewal

**Action**:
1. Find user by `whop_membership_id`
2. Update `plan_tier` if changed
3. Sync any other changes

### membership.deleted

**Triggered**: Subscription cancelled

**Action**:
1. Downgrade user to `free` tier
2. Clear `whop_membership_id`
3. Keep API keys (allow free tier access)
4. Send cancellation email (TODO)

### membership.went_valid

**Triggered**: Payment succeeded after failure

**Action**:
1. Restore `plan_tier` from Whop
2. Reactivate full access

### membership.went_invalid

**Triggered**: Payment failed, subscription expired

**Action**:
1. Downgrade to `free` tier
2. Send payment failure email (TODO)

---

## User Provisioning Flow

### New Purchase

```
1. User purchases on Whop
   ↓
2. Whop sends webhook: membership.created
   ↓
3. WhiteMagic receives webhook
   ↓
4. Verify webhook signature
   ↓
5. Extract user info (email, Whop user ID, plan)
   ↓
6. Create User in database
   ↓
7. Generate API key (wm_prod_xxxxx...)
   ↓
8. Create initial Quota
   ↓
9. Send welcome email with API key
   ↓
10. User starts using WhiteMagic!
```

### API Key Delivery

**Automatic**: Generated on first purchase

**Secure**: Shown once, then hashed in database

**Email Template** (to implement):
```
Subject: Welcome to WhiteMagic! Your API Key

Hello,

Thank you for purchasing WhiteMagic [Plan Name]!

Your API key: wm_prod_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

⚠️  IMPORTANT: Save this key securely. It won't be shown again.

Getting Started:
1. Set up authentication: https://docs.whitemagic.dev/auth
2. Make your first API call: https://docs.whitemagic.dev/quickstart
3. Explore the API: https://api.whitemagic.dev/docs

Questions? Reply to this email or visit our Discord.

Happy memory managing!
- WhiteMagic Team
```

---

## API Endpoints

### Verify Subscription

```http
GET /webhooks/subscription/verify
Authorization: Bearer {api_key}
```

**Response**:
```json
{
  "success": true,
  "active": true,
  "plan_tier": "pro",
  "expires_at": "2025-12-01T00:00:00Z",
  "status": "active"
}
```

### Subscription Status

```http
GET /webhooks/subscription/status
Authorization: Bearer {api_key}
```

**Response**:
```json
{
  "success": true,
  "email": "user@example.com",
  "plan_tier": "pro",
  "whop_user_id": "user_123",
  "whop_membership_id": "mem_456",
  "has_subscription": true
}
```

---

## Testing

### Test Webhook Locally

Use Whop CLI or webhook testing tools:

```bash
# Install Whop CLI
npm install -g @whop-apps/cli

# Forward webhooks to localhost
whop webhooks forward http://localhost:8000/webhooks/whop
```

### Manual Webhook Testing

```bash
# Create test webhook payload
curl -X POST http://localhost:8000/webhooks/whop \
  -H "Content-Type: application/json" \
  -H "X-Whop-Signature: test_signature_for_dev" \
  -d '{
    "type": "membership.created",
    "data": {
      "id": "mem_test123",
      "user": "user_test456",
      "email": "test@example.com",
      "plan": "plan_starter",
      "status": "active",
      "valid": true
    },
    "timestamp": 1699012345,
    "id": "evt_test789"
  }'
```

### Run Tests

```bash
# All Whop tests
pytest tests/test_api_whop.py -v

# Specific test class
pytest tests/test_api_whop.py::TestWhopClient -v
```

---

## Security

### Webhook Signature Verification

All webhooks are verified with HMAC-SHA256:

```python
expected_signature = hmac.new(
    WHOP_WEBHOOK_SECRET.encode(),
    request_body,
    hashlib.sha256,
).hexdigest()

if not hmac.compare_digest(signature, expected_signature):
    raise HTTPException(403, "Invalid signature")
```

**Timing-Attack Resistant**: Uses `hmac.compare_digest()`

### API Key Storage

- ✅ Generated securely with `secrets` module
- ✅ SHA-256 hashed before storage
- ✅ Never logged in plain text
- ✅ Shown once to user, then irretrievable

### Development Mode

Without `WHOP_WEBHOOK_SECRET`:
- ⚠️ Signature verification disabled
- ✅ Allows local testing
- ❌ **Never use in production!**

---

## Production Checklist

- [ ] Set `WHOP_API_KEY` in environment
- [ ] Set `WHOP_WEBHOOK_SECRET` in environment
- [ ] Configure webhook URL in Whop dashboard
- [ ] Map plan IDs in `WHOP_PLAN_MAPPING`
- [ ] Test webhook signature verification
- [ ] Implement welcome email sending
- [ ] Implement payment failure emails
- [ ] Set up error monitoring for webhooks
- [ ] Configure webhook retry logic
- [ ] Test full purchase flow end-to-end

---

## Troubleshooting

### Webhooks Not Received

1. **Check Whop Dashboard**: Webhook delivery logs
2. **Verify URL**: Must be publicly accessible HTTPS
3. **Check Firewall**: Allow Whop IP addresses
4. **Test Endpoint**: `curl` to webhook URL

### Signature Verification Fails

1. **Check Secret**: `WHOP_WEBHOOK_SECRET` matches Whop dashboard
2. **Raw Body**: Verify using raw request body, not parsed JSON
3. **Header Name**: `X-Whop-Signature` (case-sensitive)

### User Not Created

1. **Check Logs**: Look for webhook processing errors
2. **Database**: Verify connection and tables exist
3. **Event Type**: Ensure handling `membership.created`
4. **Email**: Check for duplicate email conflicts

### Plan Tier Not Syncing

1. **Check Mapping**: `WHOP_PLAN_MAPPING` has correct plan IDs
2. **Event Data**: Verify `plan` field in webhook payload
3. **Update Handler**: `membership.updated` event subscribed

---

## Monitoring

### Key Metrics

Monitor these in production:

- **Webhook Success Rate**: Should be >99%
- **Webhook Latency**: Should be <500ms
- **Failed Verifications**: Should be 0 (indicates attack or misconfiguration)
- **New User Provisioning**: Track time from purchase to API key

### Logs to Watch

```python
# Successful provisioning
print(f"New user provisioned: {user.email}")

# Plan changes
print(f"User {user.email} plan changed: {old} → {new}")

# Downgrades
print(f"User {user.email} subscription cancelled, downgrading to free")
```

---

## Future Enhancements

- [ ] **Email Notifications**: Welcome, cancellation, payment failure
- [ ] **Usage Reports**: Send monthly usage emails
- [ ] **Grace Period**: Allow 3-day grace for failed payments
- [ ] **Dunning**: Retry failed payments automatically
- [ ] **Referral Program**: Track referrals via Whop
- [ ] **Annual Plans**: Discounted annual subscriptions
- [ ] **Team Plans**: Multi-seat subscriptions
- [ ] **API Key Limits**: Multiple keys per user

---

## Support

- **Whop Docs**: https://docs.whop.com
- **WhiteMagic Docs**: https://docs.whitemagic.dev
- **Discord**: https://discord.gg/whitemagic (coming soon)
- **Email**: support@whitemagic.dev (coming soon)

---

**Last Updated**: November 2, 2025  
**Version**: 0.2.0

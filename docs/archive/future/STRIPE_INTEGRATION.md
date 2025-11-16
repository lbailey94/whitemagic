# Stripe Integration Guide

**Status**: 🚧 In Progress  
**Version**: v2.2.0  
**Date**: November 14, 2025

## Quick Overview

WhiteMagic uses Stripe for cloud tier payments. Free tier remains 100% free with no limitations.

## Pricing

- **Free**: $0 - Local use, unlimited features
- **Starter**: $10/mo - Cloud sync, 10k requests/month
- **Pro**: $30/mo - Unlimited requests & memories

## Setup Steps

### 1. Stripe Dashboard

1. Create products: "WhiteMagic Starter" ($10/mo) and "WhiteMagic Pro" ($30/mo)
2. Get API keys from Developers → API keys
3. Set up webhook at `https://api.whitemagic.dev/api/v1/stripe/webhook`
4. Listen for: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment.*`

### 2. Environment Variables (Railway)

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_STARTER_PRICE_ID=price_...
STRIPE_PRO_PRICE_ID=price_...
```

### 3. Implementation Tasks

- [ ] Add Stripe SDK: `pip install stripe`
- [ ] Create `/api/v1/stripe/` routes
- [ ] Implement checkout session creation
- [ ] Handle webhook events
- [ ] Update User model with Stripe fields
- [ ] Add "Upgrade" button to dashboard
- [ ] Test end-to-end in test mode

## Database Schema

Add to `User` model:
```python
stripe_customer_id: str | None
stripe_subscription_id: str | None  
subscription_plan: str | None  # "starter" or "pro"
```

## API Endpoints

- `POST /stripe/create-checkout` - Start subscription
- `POST /stripe/webhook` - Handle Stripe events
- `POST /stripe/portal` - Customer portal for plan management

## Testing

Use Stripe test mode with test cards:
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`

---

**Next**: Set up products in Stripe dashboard

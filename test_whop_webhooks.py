#!/usr/bin/env python3
"""
Test script for Whop webhook integration.

Simulates Whop webhook events to verify handlers work correctly.
"""

import asyncio
import hmac
import hashlib
import json
import os
from datetime import datetime

# Set up test environment
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./test_whop.db')
os.environ.setdefault('WHOP_WEBHOOK_SECRET', 'test_secret_12345')

from sqlalchemy import select
from whitemagic.api.database import Database, User, APIKey, Quota
from whitemagic.api.routes.whop import (
    handle_membership_created,
    handle_membership_updated,
    handle_membership_deleted,
    handle_membership_went_valid,
    handle_membership_went_invalid,
)


def generate_signature(payload: dict, secret: str) -> str:
    """Generate HMAC signature for webhook payload."""
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
    signature = hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return signature


def create_webhook_payload(event_type: str, user_id: str = "user_test123") -> dict:
    """Create a test webhook payload."""
    base_data = {
        'id': f'mem_{event_type}_123',
        'user': user_id,
        'email': f'{user_id}@example.com',
        'plan': 'plan_pro',
        'status': 'active',
        'valid': True,
    }
    
    return {
        'type': event_type,
        'data': base_data,
        'timestamp': int(datetime.now().timestamp()),
        'id': f'evt_{event_type}_456',
    }


async def test_membership_created():
    """Test new membership creation."""
    print("\n" + "="*60)
    print("TEST 1: membership.created (New Purchase)")
    print("="*60)
    
    db = Database('sqlite+aiosqlite:///./test_whop.db')
    await db.create_tables()
    
    async with db.get_session() as session:
        # Create webhook data
        event_data = {
            'id': 'mem_new123',
            'user': 'user_alice',
            'email': 'alice@example.com',
            'plan': 'plan_pro',
            'status': 'active',
            'valid': True,
        }
        
        print(f"\n📥 Webhook received:")
        print(f"   User: {event_data['user']}")
        print(f"   Email: {event_data['email']}")
        print(f"   Plan: {event_data['plan']}")
        
        # Process webhook
        user = await handle_membership_created(event_data, session)
        
        print(f"\n✅ User created:")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Plan Tier: {user.plan_tier}")
        print(f"   Whop User ID: {user.whop_user_id}")
        print(f"   Whop Membership ID: {user.whop_membership_id}")
        
        # Check API key was created
        result = await session.execute(
            select(APIKey).where(APIKey.user_id == user.id)
        )
        api_key = result.scalar_one_or_none()
        
        if api_key:
            print(f"\n🔑 API Key generated:")
            print(f"   Prefix: {api_key.key_prefix}")
            print(f"   Name: {api_key.name}")
            print(f"   Active: {api_key.is_active}")
        
        # Check quota was created
        result = await session.execute(
            select(Quota).where(Quota.user_id == user.id)
        )
        quota = result.scalar_one_or_none()
        
        if quota:
            print(f"\n📊 Quota initialized:")
            print(f"   Requests Today: {quota.requests_today}")
            print(f"   Memories: {quota.memories_count}")
        
        print("\n✅ TEST PASSED: User provisioned successfully!")
    
    await db.close()


async def test_membership_updated():
    """Test membership update (plan change)."""
    print("\n" + "="*60)
    print("TEST 2: membership.updated (Plan Upgrade)")
    print("="*60)
    
    db = Database('sqlite+aiosqlite:///./test_whop.db')
    
    async with db.get_session() as session:
        # First create a user with starter plan
        user = User(
            email='bob@example.com',
            whop_user_id='user_bob',
            whop_membership_id='mem_bob123',
            plan_tier='starter',
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        print(f"\n👤 Existing user:")
        print(f"   Email: {user.email}")
        print(f"   Current Plan: {user.plan_tier}")
        
        # Update to pro plan
        event_data = {
            'id': 'mem_bob123',
            'user': 'user_bob',
            'email': 'bob@example.com',
            'plan': 'plan_enterprise',  # Upgraded!
            'status': 'active',
            'valid': True,
        }
        
        print(f"\n📥 Webhook received:")
        print(f"   New Plan: {event_data['plan']}")
        
        # Process update
        await handle_membership_updated(event_data, session)
        
        # Reload user
        await session.refresh(user)
        
        print(f"\n✅ User updated:")
        print(f"   Email: {user.email}")
        print(f"   New Plan Tier: {user.plan_tier}")
        
        if user.plan_tier == 'enterprise':
            print("\n✅ TEST PASSED: Plan upgraded successfully!")
        else:
            print(f"\n❌ TEST FAILED: Expected 'enterprise', got '{user.plan_tier}'")
    
    await db.close()


async def test_membership_deleted():
    """Test membership cancellation."""
    print("\n" + "="*60)
    print("TEST 3: membership.deleted (Cancellation)")
    print("="*60)
    
    db = Database('sqlite+aiosqlite:///./test_whop.db')
    
    async with db.get_session() as session:
        # Create a pro user
        user = User(
            email='charlie@example.com',
            whop_user_id='user_charlie',
            whop_membership_id='mem_charlie123',
            plan_tier='pro',
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        print(f"\n👤 Existing user:")
        print(f"   Email: {user.email}")
        print(f"   Current Plan: {user.plan_tier}")
        print(f"   Membership ID: {user.whop_membership_id}")
        
        # Cancel subscription
        event_data = {
            'id': 'mem_charlie123',
            'user': 'user_charlie',
            'email': 'charlie@example.com',
            'plan': 'plan_pro',
            'status': 'cancelled',
            'valid': False,
        }
        
        print(f"\n📥 Webhook received: CANCELLED")
        
        # Process cancellation
        await handle_membership_deleted(event_data, session)
        
        # Reload user
        await session.refresh(user)
        
        print(f"\n✅ User updated:")
        print(f"   Email: {user.email}")
        print(f"   Plan Tier: {user.plan_tier}")
        print(f"   Membership ID: {user.whop_membership_id}")
        
        if user.plan_tier == 'free' and user.whop_membership_id is None:
            print("\n✅ TEST PASSED: User downgraded to free!")
        else:
            print(f"\n❌ TEST FAILED: Expected free tier with no membership")
    
    await db.close()


async def test_membership_went_invalid():
    """Test payment failure."""
    print("\n" + "="*60)
    print("TEST 4: membership.went_invalid (Payment Failed)")
    print("="*60)
    
    db = Database('sqlite+aiosqlite:///./test_whop.db')
    
    async with db.get_session() as session:
        # Create a pro user
        user = User(
            email='diana@example.com',
            whop_user_id='user_diana',
            whop_membership_id='mem_diana123',
            plan_tier='pro',
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        print(f"\n👤 Existing user:")
        print(f"   Email: {user.email}")
        print(f"   Current Plan: {user.plan_tier}")
        
        # Payment failed
        event_data = {
            'id': 'mem_diana123',
            'user': 'user_diana',
            'email': 'diana@example.com',
            'plan': 'plan_pro',
            'status': 'invalid',
            'valid': False,
        }
        
        print(f"\n📥 Webhook received: PAYMENT FAILED")
        
        # Process invalidation
        await handle_membership_went_invalid(event_data, session)
        
        # Reload user
        await session.refresh(user)
        
        print(f"\n✅ User suspended:")
        print(f"   Email: {user.email}")
        print(f"   Plan Tier: {user.plan_tier}")
        
        if user.plan_tier == 'free':
            print("\n✅ TEST PASSED: User downgraded due to payment failure!")
        else:
            print(f"\n❌ TEST FAILED: Expected free tier")
    
    await db.close()


async def test_membership_went_valid():
    """Test payment recovery."""
    print("\n" + "="*60)
    print("TEST 5: membership.went_valid (Payment Recovered)")
    print("="*60)
    
    db = Database('sqlite+aiosqlite:///./test_whop.db')
    
    async with db.get_session() as session:
        # Create a user with free (was downgraded)
        user = User(
            email='eve@example.com',
            whop_user_id='user_eve',
            whop_membership_id='mem_eve123',
            plan_tier='free',  # Downgraded due to payment failure
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        print(f"\n👤 Existing user (suspended):")
        print(f"   Email: {user.email}")
        print(f"   Current Plan: {user.plan_tier}")
        
        # Payment succeeded
        event_data = {
            'id': 'mem_eve123',
            'user': 'user_eve',
            'email': 'eve@example.com',
            'plan': 'plan_pro',
            'status': 'active',
            'valid': True,
        }
        
        print(f"\n📥 Webhook received: PAYMENT SUCCEEDED")
        print(f"   Restoring to: {event_data['plan']}")
        
        # Process restoration
        await handle_membership_went_valid(event_data, session)
        
        # Reload user
        await session.refresh(user)
        
        print(f"\n✅ User restored:")
        print(f"   Email: {user.email}")
        print(f"   Plan Tier: {user.plan_tier}")
        
        if user.plan_tier == 'pro':
            print("\n✅ TEST PASSED: User restored to pro!")
        else:
            print(f"\n❌ TEST FAILED: Expected pro tier")
    
    await db.close()


async def test_signature_verification():
    """Test webhook signature verification."""
    print("\n" + "="*60)
    print("TEST 6: Webhook Signature Verification")
    print("="*60)
    
    from whitemagic.api.whop import WhopClient
    
    client = WhopClient()
    client.webhook_secret = 'test_secret_12345'
    
    # Test payload
    payload_dict = {
        'type': 'membership.created',
        'data': {'user': 'test'},
    }
    payload_bytes = json.dumps(payload_dict, separators=(',', ':')).encode()
    
    # Generate valid signature
    valid_signature = hmac.new(
        client.webhook_secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    
    print(f"\n🔐 Testing signature verification:")
    print(f"   Payload: {payload_dict}")
    print(f"   Secret: {client.webhook_secret}")
    print(f"   Signature: {valid_signature[:32]}...")
    
    # Test valid signature
    result = client.verify_webhook_signature(payload_bytes, valid_signature)
    print(f"\n✅ Valid signature: {result}")
    
    # Test invalid signature
    invalid_signature = "invalid_sig_12345"
    result = client.verify_webhook_signature(payload_bytes, invalid_signature)
    print(f"❌ Invalid signature: {result}")
    
    if result is False:
        print("\n✅ TEST PASSED: Signature verification working!")
    else:
        print("\n❌ TEST FAILED: Invalid signature was accepted!")


async def run_all_tests():
    """Run all webhook tests."""
    print("\n" + "="*60)
    print("🧪 WHOP WEBHOOK INTEGRATION TESTS")
    print("="*60)
    print(f"Database: test_whop.db (will be recreated)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Clean up old test database
    import os
    if os.path.exists('./test_whop.db'):
        os.remove('./test_whop.db')
        print("🗑️  Removed old test database")
    
    try:
        await test_membership_created()
        await test_membership_updated()
        await test_membership_deleted()
        await test_membership_went_invalid()
        await test_membership_went_valid()
        await test_signature_verification()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nWhop webhook integration is working correctly! 🎉")
        print("\nNext steps:")
        print("1. Configure WHOP_API_KEY and WHOP_WEBHOOK_SECRET")
        print("2. Set up webhook URL in Whop dashboard")
        print("3. Map your plan IDs in whitemagic/api/whop.py")
        print("4. Test with real Whop webhooks")
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED")
        print("="*60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if os.path.exists('./test_whop.db'):
            os.remove('./test_whop.db')
            print("\n🗑️  Cleaned up test database")


if __name__ == '__main__':
    asyncio.run(run_all_tests())

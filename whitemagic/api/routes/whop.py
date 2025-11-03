"""
WhiteMagic API - Whop Routes

Webhook endpoints and subscription management for Whop integration.
"""

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import User, Quota
from ..dependencies import DBSession, CurrentUser
from ..auth import create_api_key
from ..whop import (
    WhopClient,
    WhopEventType,
    parse_webhook_event,
    extract_user_info,
)
from ..models import SuccessResponse, UserResponse, UserInfo, UsageStats


router = APIRouter(prefix="/webhooks", tags=["Whop"])


# Initialize Whop client
whop_client = WhopClient()


async def handle_membership_created(
    event_data: dict,
    session: AsyncSession,
):
    """
    Handle new membership creation.
    
    Provisions new user with API key.
    """
    user_info = extract_user_info(event_data)
    
    # Check if user already exists
    result = await session.execute(
        select(User).where(User.whop_user_id == user_info['whop_user_id'])
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update existing user
        user.whop_membership_id = user_info['whop_membership_id']
        user.plan_tier = whop_client.get_plan_tier(user_info['plan_id'])
    else:
        # Create new user
        user = User(
            email=user_info['email'],
            whop_user_id=user_info['whop_user_id'],
            whop_membership_id=user_info['whop_membership_id'],
            plan_tier=whop_client.get_plan_tier(user_info['plan_id']),
        )
        session.add(user)
        await session.flush()  # Get user.id
        
        # Create initial quota
        quota = Quota(user_id=user.id)
        session.add(quota)
    
    await session.commit()
    await session.refresh(user)
    
    # Generate API key for new user
    result = await session.execute(
        select(User).where(User.id == user.id)
    )
    user = result.scalar_one()
    
    raw_key, api_key = await create_api_key(
        session,
        user.id,
        name="Default API Key (Whop)",
    )
    
    # TODO: Send welcome email with API key
    # SECURITY: Never log the full API key
    print(f"New user provisioned: {user.email} (API key generated: {api_key.key_prefix}...)")
    
    return user


async def handle_membership_updated(
    event_data: dict,
    session: AsyncSession,
):
    """
    Handle membership updates.
    
    Updates plan tier if changed.
    """
    user_info = extract_user_info(event_data)
    
    result = await session.execute(
        select(User).where(User.whop_membership_id == user_info['whop_membership_id'])
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update plan tier
        new_tier = whop_client.get_plan_tier(user_info['plan_id'])
        if user.plan_tier != new_tier:
            print(f"User {user.email} plan changed: {user.plan_tier} → {new_tier}")
            user.plan_tier = new_tier
            await session.commit()


async def handle_membership_deleted(
    event_data: dict,
    session: AsyncSession,
):
    """
    Handle membership cancellation.
    
    Downgrades user to free tier.
    """
    user_info = extract_user_info(event_data)
    
    result = await session.execute(
        select(User).where(User.whop_membership_id == user_info['whop_membership_id'])
    )
    user = result.scalar_one_or_none()
    
    if user:
        print(f"User {user.email} subscription cancelled, downgrading to free")
        user.plan_tier = 'free'
        user.whop_membership_id = None  # Clear membership
        await session.commit()


async def handle_membership_went_valid(
    event_data: dict,
    session: AsyncSession,
):
    """
    Handle membership becoming valid (payment succeeded).
    
    Restores access if previously suspended.
    """
    user_info = extract_user_info(event_data)
    
    result = await session.execute(
        select(User).where(User.whop_membership_id == user_info['whop_membership_id'])
    )
    user = result.scalar_one_or_none()
    
    if user:
        print(f"User {user.email} membership now valid")
        user.plan_tier = whop_client.get_plan_tier(user_info['plan_id'])
        await session.commit()


async def handle_membership_went_invalid(
    event_data: dict,
    session: AsyncSession,
):
    """
    Handle membership becoming invalid (payment failed, expired).
    
    Suspends access by downgrading to free.
    """
    user_info = extract_user_info(event_data)
    
    result = await session.execute(
        select(User).where(User.whop_membership_id == user_info['whop_membership_id'])
    )
    user = result.scalar_one_or_none()
    
    if user:
        print(f"User {user.email} membership now invalid, downgrading to free")
        user.plan_tier = 'free'
        await session.commit()


# Event handler mapping
EVENT_HANDLERS = {
    WhopEventType.MEMBERSHIP_CREATED: handle_membership_created,
    WhopEventType.MEMBERSHIP_UPDATED: handle_membership_updated,
    WhopEventType.MEMBERSHIP_DELETED: handle_membership_deleted,
    WhopEventType.MEMBERSHIP_WENT_VALID: handle_membership_went_valid,
    WhopEventType.MEMBERSHIP_WENT_INVALID: handle_membership_went_invalid,
}


@router.post("/whop")
async def whop_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: DBSession,
):
    """
    Handle Whop webhook events.
    
    Processes subscription lifecycle events:
    - membership.created: Provision new user
    - membership.updated: Update plan tier
    - membership.deleted: Downgrade to free
    - membership.went_valid: Restore access
    - membership.went_invalid: Suspend access
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature
    signature = request.headers.get('X-Whop-Signature', '')
    if not whop_client.verify_webhook_signature(body, signature):
        raise HTTPException(403, "Invalid webhook signature")
    
    # Parse event
    try:
        payload = await request.json()
        event = parse_webhook_event(payload)
    except Exception as e:
        raise HTTPException(400, f"Invalid webhook payload: {e}")
    
    event_type = event['type']
    event_data = event['data']
    
    # Get handler
    handler = EVENT_HANDLERS.get(event_type)
    
    if handler:
        try:
            # Process event
            await handler(event_data, session)
            
            return {
                "status": "ok",
                "event": event_type,
                "processed": True,
            }
        except Exception as e:
            print(f"Error processing webhook {event_type}: {e}")
            raise HTTPException(500, f"Failed to process webhook: {e}")
    else:
        # Unknown event type, acknowledge but don't process
        print(f"Unknown webhook event type: {event_type}")
        return {
            "status": "ok",
            "event": event_type,
            "processed": False,
            "message": "Event type not handled",
        }


@router.get("/subscription/verify")
async def verify_subscription(
    user: CurrentUser,
    session: DBSession,
):
    """
    Verify user's subscription status with Whop.
    
    Returns current subscription info.
    """
    if not user.whop_membership_id:
        return {
            "success": True,
            "active": False,
            "plan_tier": user.plan_tier,
            "message": "No active Whop subscription",
        }
    
    # Verify with Whop API
    license_data = await whop_client.verify_license(user.whop_membership_id)
    
    if license_data and license_data.get('valid'):
        # Sync plan tier if different
        whop_tier = whop_client.get_plan_tier(license_data['plan_id'])
        if user.plan_tier != whop_tier:
            user.plan_tier = whop_tier
            await session.commit()
        
        return {
            "success": True,
            "active": True,
            "plan_tier": user.plan_tier,
            "expires_at": license_data.get('expires_at'),
            "status": license_data.get('status'),
        }
    else:
        # License invalid, downgrade
        if user.plan_tier != 'free':
            user.plan_tier = 'free'
            await session.commit()
        
        return {
            "success": True,
            "active": False,
            "plan_tier": 'free',
            "message": "Subscription not active, downgraded to free",
        }


@router.get("/subscription/status")
async def subscription_status(user: CurrentUser):
    """
    Get subscription status for current user.
    
    Quick check without Whop API call.
    """
    return {
        "success": True,
        "email": user.email,
        "plan_tier": user.plan_tier,
        "whop_user_id": user.whop_user_id,
        "whop_membership_id": user.whop_membership_id,
        "has_subscription": user.whop_membership_id is not None,
    }

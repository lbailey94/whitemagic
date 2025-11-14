"""
WhiteMagic API - API Key Management Routes

Public endpoint for users to retrieve their API key after Whop subscription.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from ..database import User
from ..dependencies import DBSession
from ..auth import create_api_key, list_user_api_keys


router = APIRouter(prefix="/api-keys", tags=["API Keys"])


class RetrieveKeyRequest(BaseModel):
    """Request to retrieve API key by email."""
    email: EmailStr


class RetrieveKeyResponse(BaseModel):
    """Response containing API key."""
    success: bool
    api_key: str
    message: str
    user_email: str
    plan_tier: str


@router.post("/retrieve", response_model=RetrieveKeyResponse)
async def retrieve_api_key(
    request: RetrieveKeyRequest,
    session: DBSession,
):
    """
    Retrieve or generate API key for a user by email.
    
    This endpoint allows users who subscribed via Whop to get their API key.
    
    Flow:
    1. User subscribes on Whop
    2. Webhook creates user account
    3. User visits dashboard and enters email
    4. This endpoint generates a new API key for them
    
    Note: We generate a NEW key each time since existing keys are hashed
    and cannot be retrieved.
    """
    # Look up user by email
    result = await session.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            404,
            detail="No account found with this email. Please subscribe via Whop first: https://whop.com/whitemagic"
        )
    
    # Generate a new API key
    raw_key, api_key = await create_api_key(
        session,
        user_id=user.id,
        name=f"Dashboard Key - {request.email}",
    )
    
    return RetrieveKeyResponse(
        success=True,
        api_key=raw_key,
        message="API key generated successfully! Save this key - it won't be shown again.",
        user_email=user.email,
        plan_tier=user.plan_tier,
    )

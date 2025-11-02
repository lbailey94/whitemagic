"""
WhiteMagic API - Whop Integration

Handles Whop API integration for licensing and payments.
"""

import hmac
import hashlib
import os
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import httpx
except ImportError:
    httpx = None


# Plan ID mapping (configure these in production)
WHOP_PLAN_MAPPING = {
    'plan_starter': 'starter',
    'plan_pro': 'pro',
    'plan_enterprise': 'enterprise',
}


class WhopClient:
    """Client for interacting with Whop API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Whop client.
        
        Args:
            api_key: Whop API key (from environment if not provided)
        """
        self.api_key = api_key or os.getenv('WHOP_API_KEY')
        self.base_url = 'https://api.whop.com/v1'
        self.webhook_secret = os.getenv('WHOP_WEBHOOK_SECRET')
        
        if not self.api_key:
            print("Warning: WHOP_API_KEY not set. Whop integration disabled.")
    
    async def verify_license(
        self,
        membership_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Verify a license with Whop.
        
        Args:
            membership_id: Whop membership ID
        
        Returns:
            License data if valid, None otherwise
        """
        if not self.api_key or not httpx:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/memberships/{membership_id}",
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                    },
                    timeout=10.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if membership is valid
                    if data.get('valid'):
                        return {
                            'membership_id': membership_id,
                            'user_id': data.get('user'),
                            'plan_id': data.get('plan'),
                            'status': data.get('status'),
                            'valid': True,
                            'expires_at': data.get('expires_at'),
                        }
                
                return None
                
        except Exception as e:
            print(f"Error verifying license: {e}")
            return None
    
    async def get_user_memberships(
        self,
        whop_user_id: str,
    ) -> list[Dict[str, Any]]:
        """
        Get all memberships for a user.
        
        Args:
            whop_user_id: Whop user ID
        
        Returns:
            List of membership data
        """
        if not self.api_key or not httpx:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/memberships",
                    params={'user': whop_user_id},
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                    },
                    timeout=10.0,
                )
                
                if response.status_code == 200:
                    return response.json().get('data', [])
                
                return []
                
        except Exception as e:
            print(f"Error fetching memberships: {e}")
            return []
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify Whop webhook signature.
        
        Args:
            payload: Raw request body
            signature: Signature from X-Whop-Signature header
        
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            print("Warning: WHOP_WEBHOOK_SECRET not set. Skipping verification.")
            return True  # Allow in development
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def get_plan_tier(self, whop_plan_id: str) -> str:
        """
        Map Whop plan ID to WhiteMagic plan tier.
        
        Args:
            whop_plan_id: Whop plan ID
        
        Returns:
            WhiteMagic plan tier (free, starter, pro, enterprise)
        """
        return WHOP_PLAN_MAPPING.get(whop_plan_id, 'free')


def parse_webhook_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Whop webhook event.
    
    Args:
        payload: Webhook payload
    
    Returns:
        Parsed event data
    """
    event_type = payload.get('type')
    data = payload.get('data', {})
    
    return {
        'type': event_type,
        'data': data,
        'timestamp': payload.get('timestamp'),
        'id': payload.get('id'),
    }


def extract_user_info(webhook_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract user information from webhook data.
    
    Args:
        webhook_data: Webhook data object
    
    Returns:
        User info dict
    """
    return {
        'whop_user_id': webhook_data.get('user'),
        'whop_membership_id': webhook_data.get('id'),
        'email': webhook_data.get('email') or f"{webhook_data.get('user')}@whop.placeholder",
        'plan_id': webhook_data.get('plan'),
    }


# Webhook event types
class WhopEventType:
    """Whop webhook event types."""
    MEMBERSHIP_CREATED = 'membership.created'
    MEMBERSHIP_UPDATED = 'membership.updated'
    MEMBERSHIP_DELETED = 'membership.deleted'
    MEMBERSHIP_WENT_VALID = 'membership.went_valid'
    MEMBERSHIP_WENT_INVALID = 'membership.went_invalid'
    PAYMENT_SUCCEEDED = 'payment.succeeded'
    PAYMENT_FAILED = 'payment.failed'

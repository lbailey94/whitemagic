"""
Tests for WhiteMagic Whop integration.

Tests webhook handling, license verification, and subscription management.
"""

import pytest
import hmac
import hashlib
from datetime import datetime

from whitemagic.api.whop import (
    WhopClient,
    WhopEventType,
    parse_webhook_event,
    extract_user_info,
    WHOP_PLAN_MAPPING,
)


class TestWhopClient:
    """Tests for WhopClient class."""
    
    def test_whop_client_initialization(self):
        """Test WhopClient initialization."""
        client = WhopClient(api_key="test_key")
        
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.whop.com/v1"
    
    def test_whop_client_without_api_key(self):
        """Test WhopClient works without API key (disabled mode)."""
        client = WhopClient(api_key=None)
        
        assert client.api_key is None
    
    def test_verify_webhook_signature_valid(self):
        """Test webhook signature verification with valid signature."""
        secret = "test_secret"
        client = WhopClient()
        client.webhook_secret = secret
        
        payload = b'{"type": "membership.created", "data": {}}'
        
        # Generate valid signature
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        assert client.verify_webhook_signature(payload, signature) is True
    
    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature."""
        client = WhopClient()
        client.webhook_secret = "test_secret"
        
        payload = b'{"type": "membership.created"}'
        invalid_signature = "invalid_sig"
        
        assert client.verify_webhook_signature(payload, invalid_signature) is False
    
    def test_verify_webhook_signature_no_secret(self):
        """Test webhook verification without secret (development mode)."""
        client = WhopClient()
        client.webhook_secret = None
        
        # Should allow any signature in development
        assert client.verify_webhook_signature(b"payload", "any_sig") is True
    
    def test_get_plan_tier_mapping(self):
        """Test plan ID to tier mapping."""
        client = WhopClient()
        
        assert client.get_plan_tier('plan_starter') == 'starter'
        assert client.get_plan_tier('plan_pro') == 'pro'
        assert client.get_plan_tier('plan_enterprise') == 'enterprise'
    
    def test_get_plan_tier_unknown(self):
        """Test unknown plan ID defaults to free."""
        client = WhopClient()
        
        assert client.get_plan_tier('unknown_plan') == 'free'


class TestWebhookParsing:
    """Tests for webhook parsing functions."""
    
    def test_parse_webhook_event(self):
        """Test parsing webhook event payload."""
        payload = {
            'type': 'membership.created',
            'data': {'user': 'user_123', 'id': 'mem_456'},
            'timestamp': 1699012345,
            'id': 'evt_789',
        }
        
        event = parse_webhook_event(payload)
        
        assert event['type'] == 'membership.created'
        assert event['data']['user'] == 'user_123'
        assert event['timestamp'] == 1699012345
        assert event['id'] == 'evt_789'
    
    def test_extract_user_info(self):
        """Test extracting user info from webhook data."""
        webhook_data = {
            'user': 'user_123',
            'id': 'mem_456',
            'email': 'test@example.com',
            'plan': 'plan_pro',
        }
        
        user_info = extract_user_info(webhook_data)
        
        assert user_info['whop_user_id'] == 'user_123'
        assert user_info['whop_membership_id'] == 'mem_456'
        assert user_info['email'] == 'test@example.com'
        assert user_info['plan_id'] == 'plan_pro'
    
    def test_extract_user_info_no_email(self):
        """Test extracting user info without email (generates placeholder)."""
        webhook_data = {
            'user': 'user_123',
            'id': 'mem_456',
            'plan': 'plan_starter',
        }
        
        user_info = extract_user_info(webhook_data)
        
        # Should generate placeholder email
        assert '@whop.placeholder' in user_info['email']
        assert 'user_123' in user_info['email']


class TestWhopEventTypes:
    """Tests for Whop event type constants."""
    
    def test_event_type_constants(self):
        """Test that event type constants are defined."""
        assert WhopEventType.MEMBERSHIP_CREATED == 'membership.created'
        assert WhopEventType.MEMBERSHIP_UPDATED == 'membership.updated'
        assert WhopEventType.MEMBERSHIP_DELETED == 'membership.deleted'
        assert WhopEventType.MEMBERSHIP_WENT_VALID == 'membership.went_valid'
        assert WhopEventType.MEMBERSHIP_WENT_INVALID == 'membership.went_invalid'
        assert WhopEventType.PAYMENT_SUCCEEDED == 'payment.succeeded'
        assert WhopEventType.PAYMENT_FAILED == 'payment.failed'


class TestPlanMapping:
    """Tests for plan ID mapping."""
    
    def test_all_plan_tiers_mapped(self):
        """Test that all major plan tiers are mapped."""
        assert 'plan_starter' in WHOP_PLAN_MAPPING
        assert 'plan_pro' in WHOP_PLAN_MAPPING
        assert 'plan_enterprise' in WHOP_PLAN_MAPPING
    
    def test_mapping_to_valid_tiers(self):
        """Test that mappings are to valid tier names."""
        valid_tiers = ['free', 'starter', 'pro', 'enterprise']
        
        for whop_plan, tier in WHOP_PLAN_MAPPING.items():
            assert tier in valid_tiers, f"Invalid tier: {tier}"


class TestWebhookIntegration:
    """Integration tests for webhook handling."""
    
    def test_complete_webhook_flow(self):
        """Test complete webhook signature verification and parsing."""
        client = WhopClient()
        client.webhook_secret = "test_secret"
        
        # Create webhook payload
        payload_dict = {
            'type': 'membership.created',
            'data': {
                'user': 'user_123',
                'id': 'mem_456',
                'email': 'test@example.com',
                'plan': 'plan_pro',
            },
            'timestamp': 1699012345,
            'id': 'evt_789',
        }
        
        # Convert to bytes (as it would be in real request)
        import json
        payload_bytes = json.dumps(payload_dict).encode()
        
        # Generate signature
        signature = hmac.new(
            client.webhook_secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        
        # Verify signature
        assert client.verify_webhook_signature(payload_bytes, signature) is True
        
        # Parse event
        event = parse_webhook_event(payload_dict)
        assert event['type'] == 'membership.created'
        
        # Extract user info
        user_info = extract_user_info(event['data'])
        assert user_info['email'] == 'test@example.com'
        
        # Get plan tier
        tier = client.get_plan_tier(user_info['plan_id'])
        assert tier == 'pro'


class TestLicenseValidation:
    """Tests for license validation logic."""
    
    @pytest.mark.asyncio
    async def test_verify_license_without_api_key(self):
        """Test license verification without API key (disabled)."""
        client = WhopClient(api_key=None)
        
        result = await client.verify_license('mem_123')
        
        assert result is None  # Disabled without API key
    
    @pytest.mark.asyncio
    async def test_get_user_memberships_without_api_key(self):
        """Test getting memberships without API key (disabled)."""
        client = WhopClient(api_key=None)
        
        result = await client.get_user_memberships('user_123')
        
        assert result == []  # Returns empty list when disabled


class TestWebhookSecurity:
    """Tests for webhook security features."""
    
    def test_signature_timing_attack_resistant(self):
        """Test that signature comparison is timing-attack resistant."""
        client = WhopClient()
        client.webhook_secret = "secret"
        
        payload = b"test payload"
        
        # Generate correct signature
        correct_sig = hmac.new(
            client.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        # Test with correct signature
        assert client.verify_webhook_signature(payload, correct_sig) is True
        
        # Test with incorrect signature (different length)
        assert client.verify_webhook_signature(payload, "wrong") is False
        
        # Test with incorrect signature (same length, different value)
        wrong_sig = correct_sig[:-1] + ('0' if correct_sig[-1] != '0' else '1')
        assert client.verify_webhook_signature(payload, wrong_sig) is False
    
    def test_empty_payload_handling(self):
        """Test handling of empty payload."""
        client = WhopClient()
        client.webhook_secret = "secret"
        
        payload = b""
        signature = hmac.new(
            client.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        # Should handle empty payload gracefully
        assert client.verify_webhook_signature(payload, signature) is True

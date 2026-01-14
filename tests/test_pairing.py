"""Unit tests for pairing."""

import pytest
import asyncio

from clipberry.security.pairing import PairingManager, PairingToken
from clipberry.utils import generate_device_id


@pytest.mark.asyncio
async def test_generate_token():
    """Test token generation."""
    pm = PairingManager(generate_device_id(), "Test Device")
    
    token = pm.generate_token()
    
    # Should be 8 characters
    assert len(token) == 8
    
    # Should be in active tokens
    assert token in pm._active_tokens


@pytest.mark.asyncio
async def test_validate_token():
    """Test token validation."""
    pm = PairingManager(generate_device_id(), "Test Device")
    
    token = pm.generate_token()
    
    # Should be valid
    assert pm.validate_token(token) is True
    
    # Invalid token should fail
    assert pm.validate_token("INVALID") is False


@pytest.mark.asyncio
async def test_consume_token():
    """Test token consumption."""
    pm = PairingManager(generate_device_id(), "Test Device")
    
    token = pm.generate_token()
    
    # Should be valid
    assert pm.validate_token(token) is True
    
    # Consume token
    consumed = pm.consume_token(token)
    assert consumed is True
    
    # Should no longer be valid
    assert pm.validate_token(token) is False


@pytest.mark.asyncio
async def test_token_expiration():
    """Test token expiration."""
    pm = PairingManager(generate_device_id(), "Test Device")
    
    # Generate token with very short TTL
    token = pm.generate_token(ttl_seconds=1)
    
    # Should be valid initially
    assert pm.validate_token(token) is True
    
    # Wait for expiration
    await asyncio.sleep(2)
    
    # Should be expired
    assert pm.validate_token(token) is False


@pytest.mark.asyncio
async def test_multiple_tokens():
    """Test multiple active tokens."""
    pm = PairingManager(generate_device_id(), "Test Device")
    
    token1 = pm.generate_token()
    token2 = pm.generate_token()
    
    # Should be different
    assert token1 != token2
    
    # Both should be valid
    assert pm.validate_token(token1) is True
    assert pm.validate_token(token2) is True
    
    # Consuming one shouldn't affect the other
    pm.consume_token(token1)
    assert pm.validate_token(token1) is False
    assert pm.validate_token(token2) is True


@pytest.mark.asyncio
async def test_get_active_tokens():
    """Test getting active tokens."""
    pm = PairingManager(generate_device_id(), "Test Device")
    
    token1 = pm.generate_token()
    token2 = pm.generate_token()
    
    active = pm.get_active_tokens()
    
    # Should have 2 active tokens
    assert len(active) == 2
    
    # Consume one
    pm.consume_token(token1)
    
    active = pm.get_active_tokens()
    assert len(active) == 1

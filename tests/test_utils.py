"""Unit tests for utils."""

import pytest
from clibpard.utils import (
    generate_device_id,
    generate_pairing_token,
    compute_content_hash,
    format_size,
    format_timestamp,
)


def test_generate_device_id():
    """Test device ID generation."""
    id1 = generate_device_id()
    id2 = generate_device_id()
    
    # Should be different
    assert id1 != id2
    
    # Should be valid UUIDs (36 chars with hyphens)
    assert len(id1) == 36
    assert id1.count('-') == 4


def test_generate_pairing_token():
    """Test pairing token generation."""
    token1 = generate_pairing_token()
    token2 = generate_pairing_token()
    
    # Should be different
    assert token1 != token2
    
    # Should be 8 characters by default
    assert len(token1) == 8
    
    # Should be uppercase alphanumeric
    assert token1.isalnum()
    assert token1.isupper()
    
    # Custom length
    token3 = generate_pairing_token(length=12)
    assert len(token3) == 12


def test_compute_content_hash():
    """Test content hashing."""
    data1 = b"test data"
    data2 = b"test data"
    data3 = b"different data"
    
    hash1 = compute_content_hash(data1)
    hash2 = compute_content_hash(data2)
    hash3 = compute_content_hash(data3)
    
    # Same data should produce same hash
    assert hash1 == hash2
    
    # Different data should produce different hash
    assert hash1 != hash3
    
    # Should be 64 hex characters (SHA-256)
    assert len(hash1) == 64
    assert all(c in '0123456789abcdef' for c in hash1)


def test_format_size():
    """Test size formatting."""
    assert format_size(100) == "100.0 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1024 * 1024) == "1.0 MB"
    assert format_size(1024 * 1024 * 1024) == "1.0 GB"
    assert format_size(1536) == "1.5 KB"


def test_format_timestamp():
    """Test timestamp formatting."""
    timestamp = 1234567890.0
    formatted = format_timestamp(timestamp)
    
    # Should be in format "YYYY-MM-DD HH:MM:SS"
    assert len(formatted) == 19
    assert formatted[4] == '-'
    assert formatted[7] == '-'
    assert formatted[10] == ' '
    assert formatted[13] == ':'
    assert formatted[16] == ':'

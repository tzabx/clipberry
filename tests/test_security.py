"""Unit tests for security."""

import pytest
import tempfile
from pathlib import Path

from clipberry.security import (
    generate_self_signed_cert,
    load_certificate,
    load_private_key,
    get_certificate_fingerprint,
    sign_data,
    verify_signature,
    SecurityManager,
)
from clipberry.utils import generate_device_id


def test_generate_self_signed_cert():
    """Test certificate generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_path = Path(tmpdir) / "test.crt"
        key_path = Path(tmpdir) / "test.key"
        
        device_id = generate_device_id()
        fingerprint = generate_self_signed_cert(
            device_id,
            "Test Device",
            cert_path,
            key_path,
        )
        
        # Files should be created
        assert cert_path.exists()
        assert key_path.exists()
        
        # Fingerprint should be 64 hex characters
        assert len(fingerprint) == 64
        assert all(c in '0123456789abcdef' for c in fingerprint)


def test_load_certificate():
    """Test loading certificate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_path = Path(tmpdir) / "test.crt"
        key_path = Path(tmpdir) / "test.key"
        
        generate_self_signed_cert(
            generate_device_id(),
            "Test Device",
            cert_path,
            key_path,
        )
        
        cert = load_certificate(cert_path)
        assert cert is not None


def test_get_certificate_fingerprint():
    """Test getting certificate fingerprint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_path = Path(tmpdir) / "test.crt"
        key_path = Path(tmpdir) / "test.key"
        
        fingerprint1 = generate_self_signed_cert(
            generate_device_id(),
            "Test Device",
            cert_path,
            key_path,
        )
        
        cert = load_certificate(cert_path)
        fingerprint2 = get_certificate_fingerprint(cert)
        
        # Should match
        assert fingerprint1 == fingerprint2


def test_sign_and_verify():
    """Test signing and verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_path = Path(tmpdir) / "test.crt"
        key_path = Path(tmpdir) / "test.key"
        
        generate_self_signed_cert(
            generate_device_id(),
            "Test Device",
            cert_path,
            key_path,
        )
        
        cert = load_certificate(cert_path)
        key = load_private_key(key_path)
        
        data = b"test data to sign"
        signature = sign_data(data, key)
        
        # Verification should succeed
        assert verify_signature(data, signature, cert) is True
        
        # Modified data should fail
        assert verify_signature(b"modified data", signature, cert) is False


def test_security_manager_initialize():
    """Test SecurityManager initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_dir = Path(tmpdir)
        device_id = generate_device_id()
        
        sm = SecurityManager(cert_dir, device_id, "Test Device")
        sm.initialize()
        
        # Certificate and key should be created
        assert sm.cert_path.exists()
        assert sm.key_path.exists()
        assert sm.certificate is not None
        assert sm.private_key is not None
        assert sm.fingerprint is not None


def test_security_manager_sign_item():
    """Test SecurityManager item signing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_dir = Path(tmpdir)
        device_id = generate_device_id()
        
        sm = SecurityManager(cert_dir, device_id, "Test Device")
        sm.initialize()
        
        data = b"clipboard item data"
        signature = sm.sign_item(data)
        
        # Should produce a signature
        assert len(signature) > 0
        
        # Should verify with own certificate
        assert sm.verify_item(data, signature, sm.certificate) is True

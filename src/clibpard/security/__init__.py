"""Security: Certificate generation, signing, and pairing."""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509.oid import NameOID


def generate_self_signed_cert(
    device_id: str,
    device_name: str,
    cert_path: Path,
    key_path: Path,
) -> str:
    """
    Generate self-signed certificate for device.
    Returns certificate fingerprint.
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Create certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, device_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Clibpard"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, device_id),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    # Save certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Save private key
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Compute fingerprint
    fingerprint = cert.fingerprint(hashes.SHA256()).hex()
    return fingerprint


def load_certificate(cert_path: Path) -> x509.Certificate:
    """Load certificate from file."""
    with open(cert_path, "rb") as f:
        return x509.load_pem_x509_certificate(f.read(), default_backend())


def load_private_key(key_path: Path):
    """Load private key from file."""
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )


def get_certificate_fingerprint(cert: x509.Certificate) -> str:
    """Get certificate SHA-256 fingerprint."""
    return cert.fingerprint(hashes.SHA256()).hex()


def sign_data(data: bytes, private_key) -> bytes:
    """Sign data with private key."""
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256(),
    )
    return signature


def verify_signature(
    data: bytes, signature: bytes, certificate: x509.Certificate
) -> bool:
    """Verify signature with certificate public key."""
    try:
        public_key = certificate.public_key()

        # Check key type and use appropriate verification method
        from cryptography.hazmat.primitives.asymmetric import rsa, ed25519

        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        elif isinstance(public_key, ed25519.Ed25519PublicKey):
            public_key.verify(signature, data)
        else:
            # Unsupported key type
            return False

        return True
    except Exception:
        return False


class SecurityManager:
    """Manage device certificates and signing."""

    def __init__(self, cert_dir: Path, device_id: str, device_name: str):
        self.cert_dir = cert_dir
        self.device_id = device_id
        self.device_name = device_name

        self.cert_path = cert_dir / "device.crt"
        self.key_path = cert_dir / "device.key"

        self.certificate: Optional[x509.Certificate] = None
        self.private_key = None
        self.fingerprint: Optional[str] = None

    def initialize(self):
        """Initialize or load device certificate."""
        if self.cert_path.exists() and self.key_path.exists():
            # Load existing
            self.certificate = load_certificate(self.cert_path)
            self.private_key = load_private_key(self.key_path)
            self.fingerprint = get_certificate_fingerprint(self.certificate)
        else:
            # Generate new
            self.fingerprint = generate_self_signed_cert(
                self.device_id,
                self.device_name,
                self.cert_path,
                self.key_path,
            )
            self.certificate = load_certificate(self.cert_path)
            self.private_key = load_private_key(self.key_path)

    def sign_item(self, item_data: bytes) -> bytes:
        """Sign clipboard item data."""
        return sign_data(item_data, self.private_key)

    def verify_item(
        self, item_data: bytes, signature: bytes, peer_cert: x509.Certificate
    ) -> bool:
        """Verify clipboard item signature."""
        return verify_signature(item_data, signature, peer_cert)

    def get_ssl_context(self, server: bool = False):
        """Get SSL context for WebSocket connection."""
        import ssl

        if server:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(str(self.cert_path), str(self.key_path))
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # We verify manually via fingerprint
        else:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # We verify manually via fingerprint

        return context

"""Device pairing workflow."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict
from clibpard.utils import generate_pairing_token, utc_now


@dataclass
class PairingToken:
    """Pairing token information."""

    token: str
    created_at: datetime
    expires_at: datetime
    device_id: str
    device_name: str


class PairingManager:
    """Manage device pairing workflow."""

    def __init__(self, device_id: str, device_name: str):
        self.device_id = device_id
        self.device_name = device_name

        self._active_tokens: Dict[str, PairingToken] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def start(self):
        """Start pairing manager."""
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_tokens())

    def stop(self):
        """Stop pairing manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()

    def generate_token(self, ttl_seconds: int = 300) -> str:
        """
        Generate a new pairing token.
        Default TTL is 5 minutes.
        """
        token = generate_pairing_token()
        now = utc_now()

        pairing_token = PairingToken(
            token=token,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            device_id=self.device_id,
            device_name=self.device_name,
        )

        self._active_tokens[token] = pairing_token
        return token

    def validate_token(self, token: str) -> bool:
        """Validate a pairing token."""
        if token not in self._active_tokens:
            return False

        pairing_token = self._active_tokens[token]

        if utc_now() > pairing_token.expires_at:
            del self._active_tokens[token]
            return False

        return True

    def consume_token(self, token: str) -> bool:
        """
        Consume (invalidate) a token after successful pairing.
        Returns True if token was valid.
        """
        if self.validate_token(token):
            del self._active_tokens[token]
            return True
        return False

    def get_active_tokens(self) -> list[PairingToken]:
        """Get list of active tokens."""
        now = utc_now()
        return [
            token for token in self._active_tokens.values() if token.expires_at > now
        ]

    async def _cleanup_expired_tokens(self):
        """Periodically cleanup expired tokens."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                now = utc_now()
                expired = [
                    token
                    for token, info in self._active_tokens.items()
                    if info.expires_at <= now
                ]

                for token in expired:
                    del self._active_tokens[token]

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Token cleanup error: {e}")


class PairingWorkflow:
    """Complete pairing workflow."""

    def __init__(self, pairing_manager: PairingManager, storage, security_manager):
        self.pairing_manager = pairing_manager
        self.storage = storage
        self.security = security_manager

    async def initiate_pairing_as_host(self) -> str:
        """
        Host initiates pairing by generating a token.
        Returns the token to display to user.
        """
        token = self.pairing_manager.generate_token()
        return token

    async def complete_pairing_as_host(
        self,
        token: str,
        peer_device_id: str,
        peer_device_name: str,
        peer_cert_fingerprint: str,
    ) -> bool:
        """
        Host completes pairing after receiving client connection.
        Validates token and stores peer device.
        """
        if not self.pairing_manager.validate_token(token):
            return False

        # Store device
        from clibpard.storage import Device
        from clibpard.utils import utc_timestamp

        device = Device(
            id=peer_device_id,
            name=peer_device_name,
            certificate_fingerprint=peer_cert_fingerprint,
            added_timestamp=utc_timestamp(),
            is_trusted=True,
            capabilities={"sync_text": True, "sync_images": True},
        )

        await self.storage.add_device(device)

        # Consume token
        self.pairing_manager.consume_token(token)

        return True

    async def initiate_pairing_as_client(
        self,
        host_ip: str,
        host_port: int,
        token: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Client initiates pairing by connecting with token.
        Returns (success, error_message).
        """
        # This will be called from the UI
        # The actual connection is handled by WebSocketClient
        return True, None

    async def complete_pairing_as_client(
        self,
        peer_device_id: str,
        peer_device_name: str,
        peer_cert_fingerprint: str,
    ) -> bool:
        """
        Client completes pairing after successful connection.
        Stores peer device.
        """
        from clibpard.storage import Device
        from clibpard.utils import utc_timestamp

        device = Device(
            id=peer_device_id,
            name=peer_device_name,
            certificate_fingerprint=peer_cert_fingerprint,
            added_timestamp=utc_timestamp(),
            is_trusted=True,
            capabilities={"sync_text": True, "sync_images": True},
        )

        await self.storage.add_device(device)
        return True

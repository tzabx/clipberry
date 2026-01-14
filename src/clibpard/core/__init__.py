"""Core service daemon - orchestrates all components."""

import asyncio
from pathlib import Path
from typing import Optional

from clibpard.clipboard import ClipboardMonitor
from clibpard.storage import ClipboardDatabase, ClipboardItem, Device
from clibpard.security import SecurityManager
from clibpard.security.pairing import PairingManager, PairingWorkflow
from clibpard.networking import DiscoveryService, WebSocketServer, WebSocketClient
from clibpard.utils.config import AppConfig
from clibpard.utils import utc_timestamp


class ClipboardSyncService:
    """Main service orchestrating clipboard synchronization."""

    def __init__(self, config: AppConfig):
        self.config = config

        # Initialize components
        self.database = ClipboardDatabase(config.db_path)
        self.security = SecurityManager(
            config.cert_dir,
            config.device_id,
            config.device_name,
        )
        self.clipboard_monitor = ClipboardMonitor(
            config.device_id,
            config.data_dir,
        )
        self.pairing_manager = PairingManager(
            config.device_id,
            config.device_name,
        )
        self.pairing_workflow = PairingWorkflow(
            self.pairing_manager,
            self.database,
            self.security,
        )

        # Network components
        self.discovery: Optional[DiscoveryService] = None
        self.ws_server: Optional[WebSocketServer] = None
        self.ws_client: Optional[WebSocketClient] = None

        # State
        self._running = False
        self._sync_enabled = config.sync_enabled

    async def start(self):
        """Start the service."""
        if self._running:
            return

        print(f"Starting Clibpard service for device: {self.config.device_name}")

        # Initialize security
        self.security.initialize()
        print(f"Device fingerprint: {self.security.fingerprint[:16]}...")

        # Connect to database
        await self.database.connect()
        print("Database connected")

        # Start pairing manager
        self.pairing_manager.start()

        # Start clipboard monitoring
        self.clipboard_monitor.start(self._on_clipboard_captured)
        print("Clipboard monitoring started")

        # Start network components
        if self.config.discovery_enabled:
            self.discovery = DiscoveryService(
                self.config.device_id,
                self.config.device_name,
                self.config.websocket_port,
            )
            await self.discovery.start(self._on_device_discovered)
            print("Device discovery started")

        # Start WebSocket server
        self.ws_server = WebSocketServer(
            self.config.device_id,
            self.config.device_name,
            self.config.websocket_port,
            self.security,
            self._on_item_received,
        )
        await self.ws_server.start()
        print(f"WebSocket server listening on port {self.config.websocket_port}")

        # Initialize client
        self.ws_client = WebSocketClient(
            self.config.device_id,
            self.config.device_name,
            self.security,
            self._on_item_received,
        )

        self._running = True
        print("Service started successfully")

    async def stop(self):
        """Stop the service."""
        if not self._running:
            return

        print("Stopping service...")

        # Stop clipboard monitoring
        self.clipboard_monitor.stop()

        # Stop pairing manager
        self.pairing_manager.stop()

        # Stop network components
        if self.discovery:
            await self.discovery.stop()

        if self.ws_server:
            await self.ws_server.stop()

        # Disconnect database
        await self.database.disconnect()

        self._running = False
        print("Service stopped")

    async def _on_clipboard_captured(self, item: ClipboardItem):
        """Handle locally captured clipboard item."""
        if not self._sync_enabled:
            return

        # Check size limit
        if item.size > self.config.max_item_size:
            print(f"Item too large ({item.size} bytes), skipping")
            return

        # Check type filters
        if item.type == "text" and not self.config.sync_text:
            return
        if item.type == "image" and not self.config.sync_images:
            return

        # Store in database
        added = await self.database.add_item(item)
        if not added:
            # Duplicate, skip
            return

        print(f"Captured {item.type} item: {item.content_hash[:16]}...")

        # Broadcast to connected devices
        if self.ws_server:
            await self.ws_server.broadcast_item(item)

        # Notify UI (will be implemented)
        # self._notify_ui("item_added", item)

    async def _on_item_received(self, item: ClipboardItem, peer_device_id: str):
        """Handle clipboard item received from peer."""
        if not self._sync_enabled:
            return

        # Verify device is trusted
        device = await self.database.get_device(peer_device_id)
        if not device or not device.is_trusted:
            print(f"Ignoring item from untrusted device: {peer_device_id}")
            return

        # Check filters
        if item.type == "text" and not self.config.sync_text:
            return
        if item.type == "image" and not self.config.sync_images:
            return

        # Store in database
        added = await self.database.add_item(item)
        if not added:
            # Duplicate, skip
            return

        print(
            f"Received {item.type} item from {peer_device_id}: {item.content_hash[:16]}..."
        )

        # Update device last seen
        await self.database.update_device_last_seen(peer_device_id, utc_timestamp())

        # Apply to local clipboard if it's the latest
        # (This prevents loops since we set ignore_next)
        if item.type == "text" and item.text_content:
            self.clipboard_monitor.set_clipboard_text(item.text_content)
        elif item.type == "image" and item.blob_path:
            self.clipboard_monitor.set_clipboard_image(Path(item.blob_path))

    async def _on_device_discovered(self, device_info: dict):
        """Handle discovered device."""
        print(f"Discovered device: {device_info['device_name']} at {device_info['ip']}")
        # Notify UI
        # self._notify_ui("device_discovered", device_info)

    # Public API for UI

    async def get_recent_items(self, limit: int = 100):
        """Get recent clipboard items."""
        return await self.database.get_recent_items(limit)

    async def get_devices(self):
        """Get all paired devices."""
        return await self.database.get_all_devices()

    async def connect_to_device(self, host: str, port: int) -> Optional[str]:
        """Connect to a device. Returns device_id if successful."""
        if not self.ws_client:
            return None
        return await self.ws_client.connect_to_device(host, port)

    def generate_pairing_token(self) -> str:
        """Generate a pairing token for this device."""
        return self.pairing_manager.generate_token()

    async def revoke_device(self, device_id: str):
        """Revoke trust for a device."""
        await self.database.revoke_device(device_id)

        # Disconnect if connected
        if self.ws_client:
            await self.ws_client.disconnect(device_id)

    def toggle_sync(self, enabled: bool):
        """Enable or disable sync."""
        self._sync_enabled = enabled
        self.config.sync_enabled = enabled
        # Save config will be called by UI

    def is_sync_enabled(self) -> bool:
        """Check if sync is enabled."""
        return self._sync_enabled

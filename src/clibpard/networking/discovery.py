"""Device discovery using mDNS/Bonjour."""

import asyncio
import socket
from typing import List, Callable, Dict, Any, Optional
from zeroconf import ServiceInfo, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf, AsyncServiceInfo


SERVICE_TYPE = "_clibpard._tcp.local."


class DiscoveryService:
    """mDNS/Bonjour device discovery."""

    def __init__(self, device_id: str, device_name: str, port: int):
        self.device_id = device_id
        self.device_name = device_name
        self.port = port

        self._azc: Optional[AsyncZeroconf] = None
        self._service_info: Optional[ServiceInfo] = None
        self._browser: Optional[AsyncServiceBrowser] = None
        self._discovered_devices: Dict[str, Dict[str, Any]] = {}
        self._callback: Optional[Callable] = None

    async def start(self, on_device_discovered: Optional[Callable] = None):
        """Start discovery service."""
        self._callback = on_device_discovered
        self._azc = AsyncZeroconf()

        # Register our service
        await self._register_service()

        # Start browsing
        self._browser = AsyncServiceBrowser(
            self._azc.zeroconf, SERVICE_TYPE, handlers=[self._on_service_change]
        )

    async def stop(self):
        """Stop discovery service."""
        if self._browser:
            await self._browser.async_cancel()

        if self._service_info:
            await self._azc.async_unregister_service(self._service_info)

        if self._azc:
            await self._azc.async_close()

    async def _register_service(self):
        """Register this device as discoverable."""
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        self._service_info = ServiceInfo(
            SERVICE_TYPE,
            f"{self.device_name}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties={
                "device_id": self.device_id,
                "device_name": self.device_name,
            },
        )

        await self._azc.async_register_service(self._service_info)

    def _on_service_change(
        self, zeroconf: Zeroconf, service_type: str, name: str, state_change
    ):
        """Handle service state change."""
        asyncio.create_task(
            self._handle_service_change(zeroconf, service_type, name, state_change)
        )

    async def _handle_service_change(
        self, zeroconf: Zeroconf, service_type: str, name: str, state_change
    ):
        """Async handler for service change."""
        from zeroconf import ServiceStateChange

        if state_change == ServiceStateChange.Added:
            # Use AsyncServiceInfo for async event loop compatibility
            info = AsyncServiceInfo(service_type, name)
            if self._azc:
                await info.async_request(self._azc.zeroconf, 3000)  # 3 second timeout

                if info and info.addresses:
                    # Parse device info
                    props = {}
                    if info.properties:
                        for key, value in info.properties.items():
                            props[key.decode() if isinstance(key, bytes) else key] = (
                                value.decode() if isinstance(value, bytes) else value
                            )

                    device_id = props.get("device_id")
                    device_name = props.get("device_name", name)

                    # Skip ourselves and missing device_id
                    if not device_id or device_id == self.device_id:
                        return

                    # Get IP address
                    if info.addresses:
                        ip = socket.inet_ntoa(info.addresses[0])
                        port = info.port

                        device_info = {
                            "device_id": device_id,
                            "device_name": device_name,
                            "ip": ip,
                            "port": port,
                        }

                        self._discovered_devices[device_id] = device_info

                        if self._callback:
                            await self._callback(device_info)

        elif state_change == ServiceStateChange.Removed:
            # Device went offline
            pass

    def get_discovered_devices(self) -> List[Dict[str, Any]]:
        """Get list of discovered devices."""
        return list(self._discovered_devices.values())

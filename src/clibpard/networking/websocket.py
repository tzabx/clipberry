"""WebSocket networking for peer-to-peer sync."""

import asyncio
import json
import base64
from typing import Optional, Callable, Dict, Any
from pathlib import Path

import websockets
from websockets.asyncio.server import serve, ServerConnection
from websockets.asyncio.client import connect, ClientConnection

from clibpard.storage import ClipboardItem
from clibpard.security import SecurityManager

# Type aliases for backwards compatibility
WebSocketServerProtocol = ServerConnection


class Message:
    """WebSocket message types."""

    HELLO = "hello"
    CLIPBOARD_ITEM = "clipboard_item"
    REQUEST_ITEM = "request_item"
    ACK = "ack"
    PING = "ping"
    PONG = "pong"


class WebSocketServer:
    """WebSocket server for receiving connections."""

    def __init__(
        self,
        device_id: str,
        device_name: str,
        port: int,
        security_manager: SecurityManager,
        on_item_received: Callable[[ClipboardItem, str], Any],
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.port = port
        self.security = security_manager
        self.on_item_received = on_item_received

        self._server = None
        self._connections: Dict[str, WebSocketServerProtocol] = {}

    async def start(self):
        """Start WebSocket server."""
        ssl_context = self.security.get_ssl_context(server=True)

        self._server = await serve(
            self._handle_connection,
            "0.0.0.0",
            self.port,
            ssl=ssl_context,
        )

    async def stop(self):
        """Stop WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle incoming connection."""
        peer_device_id = None

        try:
            # Send hello
            await websocket.send(
                json.dumps(
                    {
                        "type": Message.HELLO,
                        "device_id": self.device_id,
                        "device_name": self.device_name,
                    }
                )
            )

            # Receive hello
            msg = await websocket.recv()
            data = json.loads(msg)

            if data.get("type") == Message.HELLO:
                peer_device_id = data.get("device_id")
                self._connections[peer_device_id] = websocket

                # Handle messages
                async for message in websocket:
                    # Ensure message is a string
                    msg_str: Optional[str] = None
                    if isinstance(message, bytes):
                        msg_str = message.decode("utf-8")
                    elif isinstance(message, str):
                        msg_str = message

                    if msg_str:
                        await self._handle_message(msg_str, peer_device_id)

        except Exception as e:
            print(f"Connection error: {e}")

        finally:
            if peer_device_id:
                self._connections.pop(peer_device_id, None)

    async def _handle_message(self, message: Optional[str], peer_device_id: str):
        """Handle incoming message."""
        try:
            # Ensure message is a string
            if isinstance(message, bytes):
                message = message.decode("utf-8")

            if not message:
                return

            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == Message.CLIPBOARD_ITEM:
                await self._handle_clipboard_item(data, peer_device_id)

            elif msg_type == Message.PING:
                await self._connections[peer_device_id].send(
                    json.dumps({"type": Message.PONG})
                )

        except Exception as e:
            print(f"Message handling error: {e}")

    async def _handle_clipboard_item(self, data: Dict[str, Any], peer_device_id: str):
        """Handle received clipboard item."""
        # Parse item
        item = ClipboardItem(
            id=data["id"],
            type=data["item_type"],
            content_hash=data["content_hash"],
            origin_device_id=data["origin_device_id"],
            timestamp=data["timestamp"],
            size=data["size"],
            metadata=data.get("metadata", {}),
            text_content=data.get("text_content"),
        )

        # Handle blob if present
        if data.get("blob_data"):
            blob_data = base64.b64decode(data["blob_data"])
            # Will be saved by storage layer

        # Notify handler
        if self.on_item_received is not None:
            await self.on_item_received(item, peer_device_id)

        # Send ACK
        await self._connections[peer_device_id].send(
            json.dumps(
                {
                    "type": Message.ACK,
                    "item_id": item.id,
                }
            )
        )

    async def broadcast_item(self, item: ClipboardItem):
        """Broadcast clipboard item to all connected devices."""
        msg = {
            "type": Message.CLIPBOARD_ITEM,
            "id": item.id,
            "item_type": item.type,
            "content_hash": item.content_hash,
            "origin_device_id": item.origin_device_id,
            "timestamp": item.timestamp,
            "size": item.size,
            "metadata": item.metadata,
        }

        if item.text_content:
            msg["text_content"] = item.text_content

        if item.blob_path:
            # Load and encode blob
            with open(item.blob_path, "rb") as f:
                blob_data = f.read()
            msg["blob_data"] = base64.b64encode(blob_data).decode()

        # Send to all connections
        for device_id, ws in list(self._connections.items()):
            try:
                await ws.send(json.dumps(msg))
            except Exception as e:
                print(f"Broadcast error to {device_id}: {e}")


class WebSocketClient:
    """WebSocket client for connecting to peers."""

    def __init__(
        self,
        device_id: str,
        device_name: str,
        security_manager: SecurityManager,
        on_item_received: Callable[[ClipboardItem, str], Any],
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.security = security_manager
        self.on_item_received = on_item_received

        self._connections: Dict[str, ClientConnection] = {}

    async def connect_to_device(self, host: str, port: int) -> Optional[str]:
        """Connect to a device. Returns peer device_id if successful."""
        try:
            ssl_context = self.security.get_ssl_context(server=False)

            uri = f"wss://{host}:{port}"
            websocket = await connect(uri, ssl=ssl_context)

            # Receive hello
            msg = await websocket.recv()
            data = json.loads(msg)

            if data.get("type") == Message.HELLO:
                peer_device_id = data.get("device_id")

                # Send our hello
                await websocket.send(
                    json.dumps(
                        {
                            "type": Message.HELLO,
                            "device_id": self.device_id,
                            "device_name": self.device_name,
                        }
                    )
                )
                self._connections[peer_device_id] = websocket

                # Start message handler
                asyncio.create_task(self._handle_messages(websocket, peer_device_id))

                return peer_device_id

            return None

        except Exception as e:
            print(f"Connection error: {e}")
            return None

    async def _handle_messages(self, websocket, peer_device_id: str):
        """Handle messages from peer."""
        try:
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == Message.CLIPBOARD_ITEM:
                    await self._handle_clipboard_item(data, peer_device_id)

                elif msg_type == Message.PING:
                    await websocket.send(json.dumps({"type": Message.PONG}))

        except Exception as e:
            print(f"Message handling error: {e}")

        finally:
            self._connections.pop(peer_device_id, None)

    async def _handle_clipboard_item(self, data: Dict[str, Any], peer_device_id: str):
        """Handle received clipboard item."""
        item = ClipboardItem(
            id=data["id"],
            type=data["item_type"],
            content_hash=data["content_hash"],
            origin_device_id=data["origin_device_id"],
            timestamp=data["timestamp"],
            size=data["size"],
            metadata=data.get("metadata", {}),
            text_content=data.get("text_content"),
        )

        if self.on_item_received is not None:
            await self.on_item_received(item, peer_device_id)

    async def send_item(self, device_id: str, item: ClipboardItem):
        """Send clipboard item to specific device."""
        if device_id not in self._connections:
            return

        msg = {
            "type": Message.CLIPBOARD_ITEM,
            "id": item.id,
            "item_type": item.type,
            "content_hash": item.content_hash,
            "origin_device_id": item.origin_device_id,
            "timestamp": item.timestamp,
            "size": item.size,
            "metadata": item.metadata,
        }

        if item.text_content:
            msg["text_content"] = item.text_content

        if item.blob_path:
            with open(item.blob_path, "rb") as f:
                blob_data = f.read()
            msg["blob_data"] = base64.b64encode(blob_data).decode()

        await self._connections[device_id].send(json.dumps(msg))

    def is_connected(self, device_id: str) -> bool:
        """Check if connected to device."""
        return device_id in self._connections

    async def disconnect(self, device_id: str):
        """Disconnect from device."""
        if device_id in self._connections:
            await self._connections[device_id].close()
            del self._connections[device_id]

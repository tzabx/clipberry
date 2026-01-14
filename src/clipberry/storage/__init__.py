"""Storage layer for clipboard items and devices."""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel


class ClipboardItem(BaseModel):
    """Clipboard item model."""

    id: str
    type: str  # "text", "image", "file"
    content_hash: str
    origin_device_id: str
    timestamp: float
    size: int
    metadata: Dict[str, Any] = {}

    # Content storage
    text_content: Optional[str] = None
    blob_path: Optional[str] = None


class Device(BaseModel):
    """Trusted device model."""

    id: str
    name: str
    certificate_fingerprint: str
    added_timestamp: float
    last_seen_timestamp: Optional[float] = None
    is_trusted: bool = True
    capabilities: Dict[str, Any] = {}


class ClipboardDatabase:
    """SQLite database for clipboard items and devices."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to database."""
        self._conn = await aiosqlite.connect(
            str(self.db_path), isolation_level=None  # Autocommit mode
        )
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._initialize_schema()

    async def disconnect(self):
        """Disconnect from database."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _initialize_schema(self):
        """Initialize database schema."""
        await self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clipboard_items (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                origin_device_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                size INTEGER NOT NULL,
                metadata TEXT NOT NULL,
                text_content TEXT,
                blob_path TEXT,
                created_at REAL NOT NULL,
                UNIQUE(content_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_timestamp ON clipboard_items(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_content_hash ON clipboard_items(content_hash);
            CREATE INDEX IF NOT EXISTS idx_origin_device ON clipboard_items(origin_device_id);

            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                certificate_fingerprint TEXT NOT NULL,
                added_timestamp REAL NOT NULL,
                last_seen_timestamp REAL,
                is_trusted INTEGER NOT NULL,
                capabilities TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_trusted ON devices(is_trusted);
        """
        )

    async def add_item(self, item: ClipboardItem) -> bool:
        """Add clipboard item. Returns False if duplicate."""
        try:
            from clipberry.utils import utc_timestamp

            if not self._conn:
                return False
            await self._conn.execute(
                """
                INSERT INTO clipboard_items
                (id, type, content_hash, origin_device_id, timestamp, size,
                 metadata, text_content, blob_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.type,
                    item.content_hash,
                    item.origin_device_id,
                    item.timestamp,
                    item.size,
                    json.dumps(item.metadata),
                    item.text_content,
                    item.blob_path,
                    utc_timestamp(),
                ),
            )
            return True
        except aiosqlite.IntegrityError:
            # Duplicate content_hash
            return False

    async def get_item_by_hash(self, content_hash: str) -> Optional[ClipboardItem]:
        """Get item by content hash."""
        if not self._conn:
            return None
        cursor = await self._conn.execute(
            """
            SELECT id, type, content_hash, origin_device_id, timestamp, size,
                   metadata, text_content, blob_path
            FROM clipboard_items
            WHERE content_hash = ?
            """,
            (content_hash,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return ClipboardItem(
            id=row[0],
            type=row[1],
            content_hash=row[2],
            origin_device_id=row[3],
            timestamp=row[4],
            size=row[5],
            metadata=json.loads(row[6]),
            text_content=row[7],
            blob_path=row[8],
        )

    async def get_recent_items(self, limit: int = 100) -> List[ClipboardItem]:
        """Get recent clipboard items."""
        if not self._conn:
            return []
        cursor = await self._conn.execute(
            """
            SELECT id, type, content_hash, origin_device_id, timestamp, size,
                   metadata, text_content, blob_path
            FROM clipboard_items
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()

        return [
            ClipboardItem(
                id=row[0],
                type=row[1],
                content_hash=row[2],
                origin_device_id=row[3],
                timestamp=row[4],
                size=row[5],
                metadata=json.loads(row[6]),
                text_content=row[7],
                blob_path=row[8],
            )
            for row in rows
        ]

    async def add_device(self, device: Device) -> None:
        """Add or update trusted device."""
        if not self._conn:
            return
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO devices
            (id, name, certificate_fingerprint, added_timestamp,
             last_seen_timestamp, is_trusted, capabilities)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device.id,
                device.name,
                device.certificate_fingerprint,
                device.added_timestamp,
                device.last_seen_timestamp,
                1 if device.is_trusted else 0,
                json.dumps(device.capabilities),
            ),
        )

    async def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID."""
        if not self._conn:
            return None
        cursor = await self._conn.execute(
            """
            SELECT id, name, certificate_fingerprint, added_timestamp,
                   last_seen_timestamp, is_trusted, capabilities
            FROM devices
            WHERE id = ?
            """,
            (device_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return Device(
            id=row[0],
            name=row[1],
            certificate_fingerprint=row[2],
            added_timestamp=row[3],
            last_seen_timestamp=row[4],
            is_trusted=bool(row[5]),
            capabilities=json.loads(row[6]),
        )

    async def get_all_devices(self) -> List[Device]:
        """Get all devices."""
        if not self._conn:
            return []
        cursor = await self._conn.execute(
            """
            SELECT id, name, certificate_fingerprint, added_timestamp,
                   last_seen_timestamp, is_trusted, capabilities
            FROM devices
            ORDER BY added_timestamp DESC
            """
        )
        rows = await cursor.fetchall()

        return [
            Device(
                id=row[0],
                name=row[1],
                certificate_fingerprint=row[2],
                added_timestamp=row[3],
                last_seen_timestamp=row[4],
                is_trusted=bool(row[5]),
                capabilities=json.loads(row[6]),
            )
            for row in rows
        ]

    async def update_device_last_seen(self, device_id: str, timestamp: float):
        """Update device last seen timestamp."""
        if not self._conn:
            return
        await self._conn.execute(
            "UPDATE devices SET last_seen_timestamp = ? WHERE id = ?",
            (timestamp, device_id),
        )

    async def revoke_device(self, device_id: str):
        """Revoke trust for a device."""
        if not self._conn:
            return
        await self._conn.execute(
            "UPDATE devices SET is_trusted = 0 WHERE id = ?", (device_id,)
        )

    async def clear_clipboard_history(self):
        """Clear all clipboard items from database."""
        if not self._conn:
            return
        await self._conn.execute("DELETE FROM clipboard_items")

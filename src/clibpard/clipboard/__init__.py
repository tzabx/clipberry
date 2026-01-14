"""Clipboard monitoring and integration."""

import asyncio
import io
from pathlib import Path
from typing import Optional, Callable, Awaitable
from PySide6.QtGui import QClipboard, QImage
from PySide6.QtWidgets import QApplication

from clibpard.utils import compute_content_hash, generate_device_id, utc_timestamp
from clibpard.storage import ClipboardItem


class ClipboardMonitor:
    """Monitor clipboard changes and capture items."""

    def __init__(self, device_id: str, data_dir: Path):
        self.device_id = device_id
        self.data_dir = data_dir
        self.blobs_dir = data_dir / "blobs"
        self.blobs_dir.mkdir(exist_ok=True)

        self._clipboard: Optional[QClipboard] = None
        self._last_hash: Optional[str] = None
        self._ignore_next = False
        self._callback: Optional[Callable[[ClipboardItem], Awaitable[None]]] = None
        self._timer_task: Optional[asyncio.Task] = None

    def start(self, callback: Callable[[ClipboardItem], Awaitable[None]]):
        """Start monitoring clipboard."""
        app = QApplication.instance()
        if not app:
            raise RuntimeError("QApplication must be created first")

        self._clipboard = app.clipboard()
        self._callback = callback

        # Connect to clipboard changed signal
        self._clipboard.dataChanged.connect(self._on_clipboard_changed)

        # Also poll periodically as backup
        self._timer_task = asyncio.create_task(self._poll_clipboard())

    def stop(self):
        """Stop monitoring clipboard."""
        if self._clipboard:
            try:
                self._clipboard.dataChanged.disconnect(self._on_clipboard_changed)
            except Exception:
                pass

        if self._timer_task:
            self._timer_task.cancel()

    def _on_clipboard_changed(self):
        """Handle clipboard changed signal."""
        # Schedule async processing
        asyncio.create_task(self._process_clipboard())

    async def _poll_clipboard(self):
        """Poll clipboard periodically as backup."""
        while True:
            try:
                await asyncio.sleep(1.0)
                await self._process_clipboard()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Clipboard poll error: {e}")

    async def _process_clipboard(self):
        """Process current clipboard content."""
        if self._ignore_next:
            self._ignore_next = False
            return

        if not self._clipboard:
            return

        mime_data = self._clipboard.mimeData()
        if not mime_data:
            return

        # Try text first
        if mime_data.hasText():
            text = mime_data.text()
            if text and text.strip():
                await self._capture_text(text)
                return

        # Try image
        if mime_data.hasImage():
            image = self._clipboard.image()
            if not image.isNull():
                await self._capture_image(image)
                return

    async def _capture_text(self, text: str):
        """Capture text from clipboard."""
        content = text.encode("utf-8")
        content_hash = compute_content_hash(content)

        # Check if duplicate
        if content_hash == self._last_hash:
            return

        self._last_hash = content_hash

        item = ClipboardItem(
            id=generate_device_id(),  # Use as item ID
            type="text",
            content_hash=content_hash,
            origin_device_id=self.device_id,
            timestamp=utc_timestamp(),
            size=len(content),
            metadata={"length": len(text)},
            text_content=text,
        )

        if self._callback:
            await self._callback(item)

    async def _capture_image(self, image: QImage):
        """Capture image from clipboard."""
        # Convert to PNG bytes
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        content = buffer.getvalue()
        content_hash = compute_content_hash(content)

        # Check if duplicate
        if content_hash == self._last_hash:
            return

        self._last_hash = content_hash

        # Save to blob file
        blob_path = self.blobs_dir / f"{content_hash}.png"
        with open(blob_path, "wb") as f:
            f.write(content)

        item = ClipboardItem(
            id=generate_device_id(),
            type="image",
            content_hash=content_hash,
            origin_device_id=self.device_id,
            timestamp=utc_timestamp(),
            size=len(content),
            metadata={
                "width": image.width(),
                "height": image.height(),
                "format": "PNG",
            },
            blob_path=str(blob_path),
        )

        if self._callback:
            await self._callback(item)

    def set_clipboard_text(self, text: str):
        """Set clipboard text (prevents loop)."""
        self._ignore_next = True
        if self._clipboard:
            self._clipboard.setText(text)

    def set_clipboard_image(self, image_path: Path):
        """Set clipboard image (prevents loop)."""
        self._ignore_next = True
        if self._clipboard:
            image = QImage(str(image_path))
            self._clipboard.setImage(image)

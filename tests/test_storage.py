"""Unit tests for storage layer."""

import pytest
import pytest_asyncio
import tempfile
from pathlib import Path

from clibpard.storage import ClipboardDatabase, ClipboardItem, Device
from clibpard.utils import generate_device_id, compute_content_hash, utc_timestamp


@pytest_asyncio.fixture
async def db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    database = ClipboardDatabase(db_path)
    await database.connect()
    yield database
    await database.disconnect()
    db_path.unlink()


@pytest.mark.asyncio
async def test_add_item(db):
    """Test adding clipboard item."""
    item = ClipboardItem(
        id=generate_device_id(),
        type="text",
        content_hash=compute_content_hash(b"test"),
        origin_device_id=generate_device_id(),
        timestamp=utc_timestamp(),
        size=4,
        text_content="test",
    )
    
    added = await db.add_item(item)
    assert added is True


@pytest.mark.asyncio
async def test_add_duplicate_item(db):
    """Test adding duplicate item (same content_hash)."""
    content_hash = compute_content_hash(b"test")
    
    item1 = ClipboardItem(
        id=generate_device_id(),
        type="text",
        content_hash=content_hash,
        origin_device_id=generate_device_id(),
        timestamp=utc_timestamp(),
        size=4,
        text_content="test",
    )
    
    item2 = ClipboardItem(
        id=generate_device_id(),
        type="text",
        content_hash=content_hash,  # Same hash
        origin_device_id=generate_device_id(),
        timestamp=utc_timestamp(),
        size=4,
        text_content="test",
    )
    
    added1 = await db.add_item(item1)
    added2 = await db.add_item(item2)
    
    assert added1 is True
    assert added2 is False  # Duplicate rejected


@pytest.mark.asyncio
async def test_get_item_by_hash(db):
    """Test retrieving item by content hash."""
    content_hash = compute_content_hash(b"test")
    
    item = ClipboardItem(
        id=generate_device_id(),
        type="text",
        content_hash=content_hash,
        origin_device_id=generate_device_id(),
        timestamp=utc_timestamp(),
        size=4,
        text_content="test",
    )
    
    await db.add_item(item)
    
    retrieved = await db.get_item_by_hash(content_hash)
    assert retrieved is not None
    assert retrieved.content_hash == content_hash
    assert retrieved.text_content == "test"


@pytest.mark.asyncio
async def test_get_recent_items(db):
    """Test getting recent items."""
    device_id = generate_device_id()
    
    # Add multiple items
    for i in range(5):
        item = ClipboardItem(
            id=generate_device_id(),
            type="text",
            content_hash=compute_content_hash(f"test{i}".encode()),
            origin_device_id=device_id,
            timestamp=utc_timestamp(),
            size=5,
            text_content=f"test{i}",
        )
        await db.add_item(item)
    
    items = await db.get_recent_items(limit=10)
    assert len(items) == 5


@pytest.mark.asyncio
async def test_add_device(db):
    """Test adding device."""
    device = Device(
        id=generate_device_id(),
        name="Test Device",
        certificate_fingerprint="abc123",
        added_timestamp=utc_timestamp(),
        is_trusted=True,
        capabilities={"sync_text": True},
    )
    
    await db.add_device(device)
    
    retrieved = await db.get_device(device.id)
    assert retrieved is not None
    assert retrieved.name == "Test Device"
    assert retrieved.is_trusted is True


@pytest.mark.asyncio
async def test_revoke_device(db):
    """Test revoking device."""
    device = Device(
        id=generate_device_id(),
        name="Test Device",
        certificate_fingerprint="abc123",
        added_timestamp=utc_timestamp(),
        is_trusted=True,
        capabilities={},
    )
    
    await db.add_device(device)
    await db.revoke_device(device.id)
    
    retrieved = await db.get_device(device.id)
    assert retrieved is not None
    assert retrieved.is_trusted is False


@pytest.mark.asyncio
async def test_update_device_last_seen(db):
    """Test updating device last seen timestamp."""
    device = Device(
        id=generate_device_id(),
        name="Test Device",
        certificate_fingerprint="abc123",
        added_timestamp=utc_timestamp(),
        is_trusted=True,
        capabilities={},
    )
    
    await db.add_device(device)
    
    new_timestamp = utc_timestamp()
    await db.update_device_last_seen(device.id, new_timestamp)
    
    retrieved = await db.get_device(device.id)
    assert retrieved.last_seen_timestamp == new_timestamp

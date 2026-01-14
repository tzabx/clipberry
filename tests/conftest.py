"""Test configuration."""

import pytest


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def event_loop():
    """Create event loop for tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

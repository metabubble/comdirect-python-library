"""Pytest configuration for Comdirect API client tests."""

import pytest

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure async backend for pytest-asyncio."""
    return "asyncio"


@pytest.fixture
def log_capture(caplog):
    """Fixture to capture and configure logging."""
    caplog.set_level("DEBUG")
    return caplog

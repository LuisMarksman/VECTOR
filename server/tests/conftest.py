"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """A TestClient that runs the app's lifespan (bus degrades gracefully)."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

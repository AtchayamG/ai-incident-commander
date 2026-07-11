from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TEST_SETTINGS = Settings(demo_mode=True, demo_admin_key="test-admin-key")


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app = create_app(TEST_SETTINGS)
    with TestClient(app) as test_client:
        yield test_client

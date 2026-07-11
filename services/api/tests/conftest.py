import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.store.models import Base
from sqlalchemy import create_engine

@pytest.fixture(scope="function")
def test_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass

@pytest.fixture()
def client(test_db_path) -> Iterator[TestClient]:
    settings = Settings(
        demo_mode=True, 
        demo_admin_key="test-admin-key",
        database_url=f"sqlite:///{test_db_path}"
    )
    # Ensure fresh db schema for each test run or just let reset do it
    engine = create_engine(settings.database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client

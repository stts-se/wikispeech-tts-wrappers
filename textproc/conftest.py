import pytest
from dotenv import load_dotenv
load_dotenv("pytest_config.env")

from fastapi.testclient import TestClient
from textproc_server import app

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

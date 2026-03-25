# uv pip install httpx
# uv pip install pytest

# Run using the pytest command:
# pytest test_textproc_server.py

from dotenv import load_dotenv
load_dotenv("testing.env") 

from fastapi.testclient import TestClient

from textproc_server import app

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 404

def test_read_docs():
    response = client.get("/docs")
    assert response.status_code == 200
    


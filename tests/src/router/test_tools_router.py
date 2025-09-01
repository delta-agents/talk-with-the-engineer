from fastapi.testclient import TestClient
from src.main import app
from tests.utils_tests import setup_dot_env


def test_get_database_schema():
    setup_dot_env()
    client = TestClient(app)
    response = client.post("/tools.Prerequisites/example2", json={"factor": 0})
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    assert response.status_code == 200
    assert "data" in response.json()
    assert "description" in response.json()

import pytest
from fastapi.testclient import TestClient

import main as app_module


@pytest.fixture
def client():
    client = TestClient(app_module.app)
    return client


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "status" in r.json()


def test_features_route(client):
    # call with sample team names; endpoint should return JSON with keys
    r = client.get("/api/features/CSK/MI/Wankhede")
    # if dataset missing, server may return 503; accept either 200 or 503
    assert r.status_code in (200, 503)
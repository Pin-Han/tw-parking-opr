from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_realtime_returns_200():
    with patch("api.routes.realtime.fetch_taipei", return_value=[]):
        with patch("api.routes.realtime.fetch_ntpc", return_value=[]):
            res = client.get("/api/realtime")
    assert res.status_code == 200
    data = res.json()
    assert "records" in data
    assert "count" in data
    assert "fetched_at" in data


def test_realtime_returns_records():
    mock_tp = [{"source": "taipei", "road_id": "1", "road_name": "test",
                "district": "中山區", "total_spots": 10, "available_spots": 3,
                "usage_rate": 0.7, "latitude": None, "longitude": None}]
    with patch("api.routes.realtime.fetch_taipei", return_value=mock_tp):
        with patch("api.routes.realtime.fetch_ntpc", return_value=[]):
            res = client.get("/api/realtime")
    data = res.json()
    assert data["count"] == 1
    assert data["records"][0]["road_name"] == "test"

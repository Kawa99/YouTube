import io

import pytest
from openpyxl import load_workbook

from app import create_app
from models import Channel, db


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.drop_all()
        db.create_all()
        with app.test_client() as test_client:
            yield test_client
        db.session.remove()
        db.drop_all()


def test_api_data_empty(client):
    response = client.get("/api/data")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["counts"]["total_videos"] == 0


def test_api_data_pagination_limits(client):
    with client.application.app_context():
        channels = [
            Channel(channel_username=f"@channel_{idx}", subscribers=idx)
            for idx in range(30)
        ]
        db.session.add_all(channels)
        db.session.commit()

    response = client.get("/api/data?page=1&limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["channels"]["items"]) == 10

    pagination = payload["channels"]["pagination"]
    assert pagination["total_items"] == 30
    assert pagination["total_pages"] == 3
    assert pagination["current_page"] == 1
    assert pagination["has_next"] is True


def test_api_data_invalid_parameters_fallback(client):
    response = client.get("/api/data?page=-5&limit=invalid_string")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["query"]["page"] == 1
    assert payload["query"]["limit"] == 25


def test_export_csv_success(client):
    response = client.get("/export?format=csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    body = response.get_data(as_text=True)
    assert "=== VIDEOS ===" in body
    assert "=== CHANNELS ===" in body
    assert "=== CHANNEL_VIDEOS ===" in body
    assert "=== CHANNEL_HISTORY ===" in body


def test_export_xlsx_success(client):
    response = client.get("/export?format=xlsx")

    assert response.status_code == 200
    assert (
        response.mimetype
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    workbook = load_workbook(io.BytesIO(response.data), read_only=True)
    try:
        assert set(workbook.sheetnames) == {
            "videos",
            "channels",
            "channel_videos",
            "channel_history",
        }
    finally:
        workbook.close()

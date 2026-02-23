import pytest

import app as app_module
from app import create_app
from models import Channel, db


@pytest.fixture
def client(monkeypatch):
    original_join = app_module.os.path.join

    def join_with_in_memory_db(path, *paths):
        if paths and paths[-1] == "videos.db":
            return ":memory:"
        return original_join(path, *paths)

    monkeypatch.setattr(app_module.os.path, "join", join_with_in_memory_db)

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
        channels = [Channel(channel_username=f"@channel_{idx}", subscribers=idx) for idx in range(30)]
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

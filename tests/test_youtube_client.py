import pytest

from services.youtube.client import YouTubeClient
from services.youtube.errors import (
    YouTubeAuthError,
    YouTubeBadRequestError,
    YouTubeRetryableError,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.responses.pop(0)


def test_client_raises_structured_error_for_invalid_key():
    session = FakeSession(
        [
            FakeResponse(
                {
                    "error": {
                        "errors": [{"reason": "keyInvalid"}],
                        "status": "PERMISSION_DENIED",
                    }
                },
                status_code=403,
            )
        ]
    )
    client = YouTubeClient(api_key="bad-key", session=session, max_retries=1)

    with pytest.raises(YouTubeAuthError) as error:
        client.get("videos", {"part": "snippet", "id": "video"})

    assert error.value.status_code == 403
    assert error.value.reason == "keyInvalid"


def test_client_retries_retryable_statuses_without_retrying_bad_request(monkeypatch):
    session = FakeSession(
        [
            FakeResponse({"error": {"errors": [{"reason": "backendError"}]}}, 500),
            FakeResponse({"items": []}, 200),
        ]
    )
    client = YouTubeClient(api_key="test-key", session=session, max_retries=2)
    monkeypatch.setattr(
        client, "_sleep_with_backoff", lambda attempt, max_delay=8.0: None
    )

    assert client.get("videos", {"part": "snippet", "id": "video"}) == {"items": []}
    assert len(session.calls) == 2

    bad_request_session = FakeSession(
        [FakeResponse({"error": {"errors": [{"reason": "invalidParameter"}]}}, 400)]
    )
    client = YouTubeClient(
        api_key="test-key", session=bad_request_session, max_retries=3
    )

    with pytest.raises(YouTubeBadRequestError):
        client.get("videos", {"part": "snippet", "id": "video"})

    assert len(bad_request_session.calls) == 1


def test_client_requires_api_key():
    client = YouTubeClient(api_key="", session=FakeSession([]), max_retries=1)

    with pytest.raises(YouTubeAuthError):
        client.get("videos", {"part": "snippet", "id": "video"})


def test_client_raises_retryable_after_exhausting_retries(monkeypatch):
    session = FakeSession(
        [
            FakeResponse({"error": {"errors": [{"reason": "backendError"}]}}, 500),
            FakeResponse({"error": {"errors": [{"reason": "backendError"}]}}, 500),
        ]
    )
    client = YouTubeClient(api_key="test-key", session=session, max_retries=2)
    monkeypatch.setattr(
        client, "_sleep_with_backoff", lambda attempt, max_delay=8.0: None
    )

    with pytest.raises(YouTubeRetryableError):
        client.get("videos", {"part": "snippet", "id": "video"})

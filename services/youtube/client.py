import logging
import os
import secrets
import time
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.youtube.errors import (
    YouTubeAuthError,
    YouTubeBadRequestError,
    YouTubeNotFoundError,
    YouTubeQuotaExceededError,
    YouTubeRetryableError,
)
from services.youtube.quota import DEFAULT_DAILY_QUOTA_BUDGET, QuotaTracker

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
REQUEST_TIMEOUT = (3.05, 15)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
AUTH_STATUS_CODES = {401, 403}
NOT_FOUND_STATUS_CODES = {404}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404}


def chunked(values: Iterable[str], size: int):
    batch = []
    for value in values:
        if value in batch:
            continue
        batch.append(value)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def create_retry_session(max_retries: int, backoff_base_seconds: float):
    session = requests.Session()
    retries = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        status=max_retries,
        backoff_factor=backoff_base_seconds,
        status_forcelist=sorted(RETRYABLE_STATUS_CODES),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


class YouTubeClient:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        session=None,
        max_retries: Optional[int] = None,
        backoff_base_seconds: Optional[float] = None,
        timeout: Tuple[float, float] = REQUEST_TIMEOUT,
        daily_quota_budget: int = DEFAULT_DAILY_QUOTA_BUDGET,
    ):
        self.api_key = (
            api_key if api_key is not None else os.environ.get("YOUTUBE_API_KEY")
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else int(os.environ.get("API_MAX_RETRIES", "5"))
        )
        self.backoff_base_seconds = (
            backoff_base_seconds
            if backoff_base_seconds is not None
            else float(os.environ.get("API_BACKOFF_BASE_SECONDS", "0.5"))
        )
        self.timeout = timeout
        self.quota = QuotaTracker(daily_quota_budget)
        self.session = session or create_retry_session(
            self.max_retries, self.backoff_base_seconds
        )

    def get(self, endpoint: str, params: Mapping[str, Any]) -> Dict[str, Any]:
        payload = dict(params)
        payload["key"] = self.api_key
        self.quota.add(endpoint)
        return self.request_json(endpoint, payload)

    def request_json(self, endpoint: str, params: Mapping[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise YouTubeAuthError("YouTube API key is not configured.")

        url = f"{YOUTUBE_API_BASE_URL}/{endpoint}"
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries - 1:
                    raise YouTubeRetryableError(
                        f"Request to YouTube {endpoint} failed: {exc}"
                    ) from exc
                self._sleep_with_backoff(attempt)
                continue

            if response.status_code < 400:
                try:
                    return response.json()
                except ValueError as exc:
                    raise YouTubeBadRequestError(
                        f"YouTube {endpoint} returned invalid JSON."
                    ) from exc

            error_reason = self._error_reason(response)
            error_message = (
                f"YouTube {endpoint} failed with HTTP {response.status_code}"
                f" ({error_reason or 'unknown'})."
            )

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt >= self.max_retries - 1:
                    if error_reason == "quotaExceeded":
                        raise YouTubeQuotaExceededError(
                            error_message,
                            status_code=response.status_code,
                            reason=error_reason,
                        )
                    raise YouTubeRetryableError(
                        error_message,
                        status_code=response.status_code,
                        reason=error_reason,
                    )
                logger.warning(
                    "Retrying YouTube %s request after HTTP %s (%s), attempt %s/%s.",
                    endpoint,
                    response.status_code,
                    error_reason,
                    attempt + 1,
                    self.max_retries,
                )
                self._sleep_with_backoff(attempt)
                continue

            if response.status_code in AUTH_STATUS_CODES:
                if error_reason in {"quotaExceeded", "dailyLimitExceeded"}:
                    raise YouTubeQuotaExceededError(
                        error_message,
                        status_code=response.status_code,
                        reason=error_reason,
                    )
                raise YouTubeAuthError(
                    error_message,
                    status_code=response.status_code,
                    reason=error_reason,
                )

            if response.status_code in NOT_FOUND_STATUS_CODES:
                raise YouTubeNotFoundError(
                    error_message,
                    status_code=response.status_code,
                    reason=error_reason,
                )

            raise YouTubeBadRequestError(
                error_message,
                status_code=response.status_code,
                reason=error_reason,
            )

        raise YouTubeRetryableError(
            f"Request to YouTube {endpoint} failed: {last_error}"
        )

    def list_videos(self, video_ids, part="snippet,statistics,contentDetails"):
        payloads = []
        for batch in chunked(video_ids, 50):
            payloads.append(self.get("videos", {"part": part, "id": ",".join(batch)}))
        return payloads

    def list_channels(self, channel_ids, part="snippet,statistics,contentDetails"):
        payloads = []
        for batch in chunked(channel_ids, 50):
            payloads.append(self.get("channels", {"part": part, "id": ",".join(batch)}))
        return payloads

    @staticmethod
    def _error_reason(response) -> Optional[str]:
        try:
            payload = response.json()
        except ValueError:
            return None

        errors = payload.get("error", {}).get("errors", [])
        if errors:
            return errors[0].get("reason")
        return payload.get("error", {}).get("status")

    def _sleep_with_backoff(self, attempt: int, max_delay: float = 8.0) -> None:
        delay = min(max_delay, self.backoff_base_seconds * (2**attempt))
        jitter = (secrets.randbelow(1000) / 1000) * (delay * 0.2 if delay > 0 else 0)
        time.sleep(delay + jitter)


_default_client = None


def get_default_client() -> YouTubeClient:
    global _default_client
    if _default_client is None:
        _default_client = YouTubeClient()
    return _default_client


def reset_default_client() -> None:
    global _default_client
    _default_client = None

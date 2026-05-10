class YouTubeAPIError(Exception):
    """Base error for YouTube API collection failures."""

    def __init__(self, message, *, status_code=None, reason=None, retryable=False):
        super().__init__(message)
        self.status_code = status_code
        self.reason = reason
        self.retryable = retryable


class YouTubeRetryableError(YouTubeAPIError):
    """Transient API failure that can be retried."""

    def __init__(self, message, *, status_code=None, reason=None):
        super().__init__(
            message, status_code=status_code, reason=reason, retryable=True
        )


class YouTubeAuthError(YouTubeAPIError):
    """Invalid, missing, or unauthorized API credentials."""


class YouTubeQuotaExceededError(YouTubeAPIError):
    """The API quota or configured local quota budget was exceeded."""


class YouTubeNotFoundError(YouTubeAPIError):
    """Requested YouTube entity was not found."""


class YouTubeBadRequestError(YouTubeAPIError):
    """Request is invalid and should not be retried without changes."""

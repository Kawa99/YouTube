import os

DEFAULT_DAILY_QUOTA_BUDGET = int(os.environ.get("YOUTUBE_DAILY_QUOTA_BUDGET", "10000"))

ENDPOINT_QUOTA_COSTS = {
    "videos": 1,
    "channels": 1,
    "playlistItems": 1,
    "search": 100,
}


def estimate_endpoint_cost(endpoint: str, calls: int = 1) -> int:
    return ENDPOINT_QUOTA_COSTS.get(endpoint, 1) * max(0, int(calls or 0))


def estimate_video_batch_cost(video_count: int) -> int:
    calls = (max(0, int(video_count or 0)) + 49) // 50
    return estimate_endpoint_cost("videos", calls)


def estimate_channel_batch_cost(channel_count: int) -> int:
    calls = (max(0, int(channel_count or 0)) + 49) // 50
    return estimate_endpoint_cost("channels", calls)


def estimate_channel_uploads_cost(video_limit: int) -> int:
    playlist_calls = (max(0, int(video_limit or 0)) + 49) // 50
    return estimate_endpoint_cost("channels") + estimate_endpoint_cost(
        "playlistItems", playlist_calls
    )


def estimate_search_cost(pages: int = 1) -> int:
    return estimate_endpoint_cost("search", pages)


class QuotaTracker:
    def __init__(self, daily_budget: int = DEFAULT_DAILY_QUOTA_BUDGET):
        self.daily_budget = daily_budget
        self.estimated_used = 0

    def add(self, endpoint: str, calls: int = 1) -> int:
        cost = estimate_endpoint_cost(endpoint, calls)
        self.estimated_used += cost
        return cost

    @property
    def remaining(self) -> int:
        return max(0, self.daily_budget - self.estimated_used)

    def would_exceed(self, additional_cost: int) -> bool:
        return (
            self.estimated_used + max(0, int(additional_cost or 0)) > self.daily_budget
        )

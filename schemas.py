from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class VideoCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    youtube_video_id: str
    channel_username: str
    subscribers: int = 0
    title: str = ""
    description: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    posted: Optional[str] = None
    video_length: str = ""
    transcript: str = ""

    @field_validator("subscribers", "views", "likes", "comments", mode="before")
    @classmethod
    def normalize_numeric_fields(cls, value):
        if value is None:
            return 0
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned == "":
                return 0
            return int(cleaned.replace(",", ""))
        return value

    @field_validator("youtube_video_id", "channel_username")
    @classmethod
    def require_non_empty_strings(cls, value):
        if value == "":
            raise ValueError("Field must not be empty.")
        return value

    @field_validator("posted", mode="before")
    @classmethod
    def normalize_posted(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

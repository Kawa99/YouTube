from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Channel(db.Model):
    __tablename__ = "channels"

    id = db.Column(db.Integer, primary_key=True)
    channel_username = db.Column(db.String, unique=True, nullable=False)
    subscribers = db.Column(db.Integer, nullable=False, default=0)

    videos = db.relationship("Video", back_populates="channel", lazy=True)
    history_records = db.relationship(
        "ChannelHistory", back_populates="channel", lazy=True
    )
    linked_videos = db.relationship("ChannelVideo", back_populates="channel", lazy=True)


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    youtube_video_id = db.Column(db.String, unique=True)
    title = db.Column(db.String)
    description = db.Column(db.Text)
    views = db.Column(db.Integer)
    likes = db.Column(db.Integer)
    comments = db.Column(db.Integer)
    posted = db.Column(db.String)
    video_length = db.Column(db.String)
    transcript = db.Column(db.Text)
    saved_at = db.Column(db.Text, server_default=db.text("CURRENT_TIMESTAMP"))
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"))

    channel = db.relationship("Channel", back_populates="videos")
    linked_channels = db.relationship("ChannelVideo", back_populates="video", lazy=True)

    def _safe_percentage_rate(self, numerator):
        """Return a 2-decimal percentage, suppressing invalid math states."""
        try:
            return round((numerator / self.views) * 100, 2)
        except (ZeroDivisionError, TypeError):
            return 0.0

    @property
    def like_rate(self):
        """Likes as a percentage of views."""
        return self._safe_percentage_rate(self.likes)

    @property
    def comment_rate(self):
        """Comments as a percentage of views."""
        return self._safe_percentage_rate(self.comments)

    @property
    def engagement_rate(self):
        """Combined likes + comments as a percentage of views."""
        try:
            engagement_total = (self.likes or 0) + (self.comments or 0)
        except TypeError:
            engagement_total = 0
        return self._safe_percentage_rate(engagement_total)


class ChannelHistory(db.Model):
    __tablename__ = "channel_history"

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"), nullable=False)
    previous_subscribers = db.Column(db.Integer, nullable=False, default=0)
    recorded_at = db.Column(db.Text, server_default=db.text("CURRENT_TIMESTAMP"))

    channel = db.relationship("Channel", back_populates="history_records")


class ChannelVideo(db.Model):
    __tablename__ = "channel_videos"

    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"), primary_key=True)

    video = db.relationship("Video", back_populates="linked_channels")
    channel = db.relationship("Channel", back_populates="linked_videos")

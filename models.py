from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Channel(db.Model):
    __tablename__ = "channels"

    id = db.Column(db.Integer, primary_key=True)
    channel_username = db.Column(db.String, unique=True, nullable=False)
    subscribers = db.Column(db.Integer, nullable=False, default=0)

    videos = db.relationship("Video", back_populates="channel", lazy=True)
    history_records = db.relationship("ChannelHistory", back_populates="channel", lazy=True)
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

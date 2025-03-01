-- Table for storing channels (now storing @username)
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_username TEXT UNIQUE,  -- @handle instead of name
    subscribers INTEGER
);

-- Table for storing videos
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    posted TEXT,
    video_length TEXT,
    transcript TEXT,
    saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
    channel_id INTEGER,
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- Linking table between channels and videos
CREATE TABLE IF NOT EXISTS channel_videos (
    video_id INTEGER,
    channel_id INTEGER,
    FOREIGN KEY (video_id) REFERENCES videos(id),
    FOREIGN KEY (channel_id) REFERENCES channels(id),
    PRIMARY KEY (video_id, channel_id)
);

-- Table for tracking subscriber count history
CREATE TABLE IF NOT EXISTS channel_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    previous_subscribers INTEGER,
    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

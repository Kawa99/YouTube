-- Table for storing channels (now storing @username)
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_username TEXT UNIQUE  -- @handle instead of name
);

-- Table for storing videos
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_url TEXT UNIQUE,  -- Ensures the same video isn't saved twice
    title TEXT,
    description TEXT,
    posted DATETIME,
    video_length INTEGER,
    transcript TEXT,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    channel_id INTEGER NOT NULL,  -- Links to the channel that uploaded the video
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- Table for tracking subscriber count history
CREATE TABLE IF NOT EXISTS channel_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    subscribers INTEGER,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- Table for tracking video performance
CREATE TABLE IF NOT EXISTS video_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    views INTEGER,
    likes INTEGER,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);

-- Table for keeping track of comments under a video
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    comment_text TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);

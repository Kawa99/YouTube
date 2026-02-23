import sqlite3

DB_PATH = "videos.db"


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _table_sql(cursor, table_name):
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?", (table_name,))
    row = cursor.fetchone()
    return row[0] if row else ""


def _videos_table_needs_unique_constraint(cursor):
    videos_sql = " ".join((_table_sql(cursor, "videos") or "").lower().split())
    if "youtube_video_id text unique" in videos_sql:
        return False
    return _column_exists(cursor, "videos", "youtube_video_id")


def _migrate_videos_table(cursor):
    cursor.execute("DROP TABLE IF EXISTS videos_new")
    cursor.execute("DROP TABLE IF EXISTS channel_videos_new")
    cursor.execute("DROP TABLE IF EXISTS video_id_map")

    cursor.execute(
        """
        CREATE TEMP TABLE video_id_map AS
        SELECT
            v.id AS old_id,
            COALESCE(keep_rows.keep_id, v.id) AS new_id
        FROM videos v
        LEFT JOIN (
            SELECT youtube_video_id, MAX(id) AS keep_id
            FROM videos
            WHERE youtube_video_id IS NOT NULL
            GROUP BY youtube_video_id
        ) keep_rows
        ON v.youtube_video_id = keep_rows.youtube_video_id
        """
    )

    cursor.execute(
        """
        CREATE TABLE videos_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            youtube_video_id TEXT UNIQUE,
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
        )
        """
    )

    cursor.execute(
        """
        INSERT INTO videos_new (
            id, youtube_video_id, title, description, views, likes, comments,
            posted, video_length, transcript, saved_at, channel_id
        )
        SELECT
            id, youtube_video_id, title, description, views, likes, comments,
            posted, video_length, transcript, saved_at, channel_id
        FROM videos v
        JOIN video_id_map m ON m.old_id = v.id
        WHERE m.new_id = v.id
        ORDER BY v.id
        """
    )

    cursor.execute(
        """
        CREATE TABLE channel_videos_new (
            video_id INTEGER,
            channel_id INTEGER,
            FOREIGN KEY (video_id) REFERENCES videos(id),
            FOREIGN KEY (channel_id) REFERENCES channels(id),
            PRIMARY KEY (video_id, channel_id)
        )
        """
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO channel_videos_new (video_id, channel_id)
        SELECT COALESCE(m.new_id, cv.video_id), cv.channel_id
        FROM channel_videos cv
        LEFT JOIN video_id_map m ON m.old_id = cv.video_id
        """
    )

    cursor.execute("DROP TABLE channel_videos")
    cursor.execute("DROP TABLE videos")
    cursor.execute("ALTER TABLE videos_new RENAME TO videos")
    cursor.execute("ALTER TABLE channel_videos_new RENAME TO channel_videos")
    cursor.execute("DROP TABLE video_id_map")


def _create_indexes(cursor):
    cursor.execute("DROP INDEX IF EXISTS idx_videos_youtube_video_id")
    cursor.execute("DROP INDEX IF EXISTS idx_videos_channel_id")
    cursor.execute("DROP INDEX IF EXISTS idx_channel_history_channel_id")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_channel ON videos(channel_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel_videos_channel_id ON channel_videos(channel_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel_videos_video_id ON channel_videos(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_channel ON channel_history(channel_id)")


def init_db():
    """Create database tables and apply schema migrations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE,
            subscribers INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            youtube_video_id TEXT,
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
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_videos (
            video_id INTEGER,
            channel_id INTEGER,
            FOREIGN KEY (video_id) REFERENCES videos(id),
            FOREIGN KEY (channel_id) REFERENCES channels(id),
            PRIMARY KEY (video_id, channel_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            previous_subscribers INTEGER,
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(id)
        )
    """)

    if not _column_exists(cursor, "videos", "youtube_video_id"):
        cursor.execute("ALTER TABLE videos ADD COLUMN youtube_video_id TEXT")

    if _videos_table_needs_unique_constraint(cursor):
        _migrate_videos_table(cursor)

    _create_indexes(cursor)

    conn.commit()
    conn.close()

def save_video(data):
    """Idempotently insert/update video data and manage channel subscriber history."""
    youtube_video_id = data.get("youtube_video_id")
    if not youtube_video_id:
        raise ValueError("youtube_video_id is required to save video data.")

    channel_username = data.get("channel_username")
    if not channel_username:
        raise ValueError("channel_username is required to save video data.")

    subscribers = _safe_int(data.get("subscribers"), 0)

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, subscribers FROM channels WHERE channel_username = ?",
            (channel_username,),
        )
        channel_result = cursor.fetchone()

        if channel_result:
            channel_id, previous_subscribers = channel_result

            if previous_subscribers != subscribers:
                cursor.execute(
                    "INSERT INTO channel_history (channel_id, previous_subscribers) VALUES (?, ?)",
                    (channel_id, previous_subscribers),
                )
                cursor.execute(
                    "UPDATE channels SET subscribers = ? WHERE id = ?",
                    (subscribers, channel_id),
                )
        else:
            cursor.execute(
                "INSERT INTO channels (channel_username, subscribers) VALUES (?, ?)",
                (channel_username, subscribers),
            )
            channel_id = cursor.lastrowid

        video_fields = (
            data.get("title", ""),
            data.get("description", ""),
            _safe_int(data.get("views"), 0),
            _safe_int(data.get("likes"), 0),
            _safe_int(data.get("comments"), 0),
            data.get("posted", ""),
            data.get("video_length", ""),
            data.get("transcript", ""),
            channel_id,
            youtube_video_id,
        )

        cursor.execute(
            "SELECT id FROM videos WHERE youtube_video_id = ?",
            (youtube_video_id,),
        )
        existing_video = cursor.fetchone()

        if existing_video:
            video_id = existing_video[0]
            cursor.execute(
                """
                UPDATE videos
                SET title = ?, description = ?, views = ?, likes = ?, comments = ?,
                    posted = ?, video_length = ?, transcript = ?, channel_id = ?
                WHERE id = ?
                """,
                video_fields[:-1] + (video_id,),
            )
            created = False
        else:
            cursor.execute(
                """
                INSERT INTO videos (
                    title, description, views, likes, comments, posted,
                    video_length, transcript, channel_id, youtube_video_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                video_fields,
            )
            video_id = cursor.lastrowid
            created = True

        cursor.execute(
            "INSERT OR IGNORE INTO channel_videos (video_id, channel_id) VALUES (?, ?)",
            (video_id, channel_id),
        )

        conn.commit()
        return {"video_id": video_id, "created": created}
    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise e
    finally:
        if conn is not None:
            conn.close()

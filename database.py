import sqlite3

def init_db():
    """Create database tables"""
    conn = sqlite3.connect("videos.db")
    cursor = conn.cursor()

    # Table for storing channels (now storing @username)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE,  -- @handle instead of name
            subscribers INTEGER
        )
    """)

    # Table for storing videos - ADD UNIQUE CONSTRAINT
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE,  -- Add video_id field with unique constraint
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

    # Linking table between channels and videos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_videos (
            video_id INTEGER,
            channel_id INTEGER,
            FOREIGN KEY (video_id) REFERENCES videos(id),
            FOREIGN KEY (channel_id) REFERENCES channels(id),
            PRIMARY KEY (video_id, channel_id)
        )
    """)

    # Table for tracking subscriber count history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            previous_subscribers INTEGER,
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(id)
        )
    """)

    conn.commit()
    conn.close()

def save_video(data):
    """Insert video data and manage channel updates using @username - with duplicate prevention"""
    try:
        conn = sqlite3.connect("videos.db")
        cursor = conn.cursor()

        print("Saving video data:", data)  # Debugging print

        # Extract video_id from the data (you'll need to pass this from app.py)
        video_id = data.get("video_id")
        if not video_id:
            raise ValueError("video_id is required to prevent duplicates")

        # Check if video already exists
        cursor.execute("SELECT id FROM videos WHERE video_id = ?", (video_id,))
        existing_video = cursor.fetchone()
        
        if existing_video:
            print(f"Video {video_id} already exists in database. Skipping save.")
            conn.close()
            return {"status": "duplicate", "message": f"Video {video_id} already exists in database"}

        # Check if channel exists
        cursor.execute("SELECT id, subscribers FROM channels WHERE channel_username = ?", (data["channel_username"],))
        channel_result = cursor.fetchone()

        if channel_result:
            channel_id, previous_subscribers = channel_result
            print(f"Channel exists: ID {channel_id}, Previous Subscribers {previous_subscribers}")

            # Update subscriber count if changed
            if previous_subscribers != int(data["subscribers"]):
                cursor.execute("INSERT INTO channel_history (channel_id, previous_subscribers) VALUES (?, ?)", 
                               (channel_id, previous_subscribers))
                cursor.execute("UPDATE channels SET subscribers = ? WHERE id = ?", 
                               (data["subscribers"], channel_id))
        else:
            print("New channel detected. Inserting into database.")
            cursor.execute("INSERT INTO channels (channel_username, subscribers) VALUES (?, ?)", 
                           (data["channel_username"], data["subscribers"]))
            channel_id = cursor.lastrowid  # Get new channel ID

        # Insert the video with video_id
        cursor.execute("""
            INSERT INTO videos (video_id, title, description, views, likes, comments, posted, video_length, transcript, channel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video_id, data["title"], data["description"], data["views"], data["likes"], 
            data["comments"], data["posted"], data["video_length"], data["transcript"], channel_id
        ))
        video_db_id = cursor.lastrowid

        # Link video and channel
        cursor.execute("INSERT INTO channel_videos (video_id, channel_id) VALUES (?, ?)", 
                       (video_db_id, channel_id))

        conn.commit()
        conn.close()
        print("Video saved successfully!")  # Debugging print
        return {"status": "success", "message": "Video saved successfully"}
        
    except sqlite3.IntegrityError as e:
        print("Integrity error (likely duplicate):", str(e))
        conn.close()
        return {"status": "duplicate", "message": "Video already exists in database"}
    except Exception as e:
        print("Error saving video:", str(e))  # Debugging print
        if 'conn' in locals():
            conn.close()
        raise e  # Ensure the error is visible

def check_video_exists(video_id):
    """Check if a video already exists in the database"""
    try:
        conn = sqlite3.connect("videos.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM videos WHERE video_id = ?", (video_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    except Exception as e:
        print(f"Error checking video existence: {str(e)}")
        return False

def get_duplicate_videos():
    """Get statistics about duplicate videos (for debugging/cleanup)"""
    try:
        conn = sqlite3.connect("videos.db")
        cursor = conn.cursor()
        
        # Find duplicate video_ids (if any exist due to old data)
        cursor.execute("""
            SELECT video_id, COUNT(*) as count 
            FROM videos 
            WHERE video_id IS NOT NULL
            GROUP BY video_id 
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        conn.close()
        
        return duplicates
    except Exception as e:
        print(f"Error checking for duplicates: {str(e)}")
        return []
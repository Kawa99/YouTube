import sqlite3

def init_db():
    """Initialize database using SQL script from schema.sql"""
    conn = sqlite3.connect("videos.db")
    cursor = conn.cursor()

    # Read and execute SQL file
    with open("static/database/schema.sql", "r") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()


def save_video(data):
    """Insert video data and manage channel updates using @username"""
    try:
        conn = sqlite3.connect("videos.db")
        cursor = conn.cursor()

        print("Received data:", data)  # Debugging print

        # Ensure video_url is present
        if "video_url" not in data or not data["video_url"]:
            print("❌ Error: Missing 'video_url'")
            return  # Exit function if video_url is missing

        # Check if channel exists
        cursor.execute("SELECT id FROM channels WHERE channel_username = ?", (data["channel_username"],))
        channel_result = cursor.fetchone()

        if channel_result:
            channel_id = channel_result[0]
            print(f"✅ Channel exists: ID {channel_id}")
        else:
            print("🆕 New channel detected. Inserting into database.")
            cursor.execute("INSERT INTO channels (channel_username) VALUES (?)", 
                           (data["channel_username"],))
            channel_id = cursor.lastrowid  # Get new channel ID

        # Check if video already exists
        cursor.execute("SELECT id FROM videos WHERE video_url = ?", (data["video_url"],))
        video_result = cursor.fetchone()

        if video_result:
            print("⚠️ Duplicate video detected. Skipping insertion.")
            conn.close()
            return  # Video already exists, exit the function

        # Insert video details
        cursor.execute("""
            INSERT INTO videos (video_url, title, description, posted, video_length, transcript, saved_at, channel_id)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, (
            data["video_url"], data["title"], data["description"], data["posted"], 
            data["video_length"], data["transcript"], channel_id
        ))
        video_id = cursor.lastrowid

        # Insert video performance metrics
        cursor.execute("""
            INSERT INTO video_performance (video_id, views, likes, recorded_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            video_id, data["views"], data["likes"]
        ))

        # Insert comment count (not individual comments)
        cursor.execute("""
            INSERT INTO comments (video_id, comment_text, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (
            video_id, f"Total comments: {data['comments']}"
        ))

        conn.commit()
        conn.close()
        print("✅ Video saved successfully!")  # Debugging print
    except Exception as e:
        print("❌ Error saving video:", str(e))  # Debugging print
        raise e  # Ensure the error is visible

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

        print("Saving video data:", data)  # Debugging print

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

        # Insert the video
        cursor.execute("""
            INSERT INTO videos (title, description, views, likes, comments, posted, video_length, transcript, channel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["title"], data["description"], data["views"], data["likes"], 
            data["comments"], data["posted"], data["video_length"], data["transcript"], channel_id
        ))
        video_id = cursor.lastrowid

        # Link video and channel
        cursor.execute("INSERT INTO channel_videos (video_id, channel_id) VALUES (?, ?)", 
                       (video_id, channel_id))

        conn.commit()
        conn.close()
        print("Video saved successfully!")  # Debugging print
    except Exception as e:
        print("Error saving video:", str(e))  # Debugging print
        raise e  # Ensure the error is visible


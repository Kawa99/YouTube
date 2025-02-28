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

    # Table for storing videos
    cursor.execute("""
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

# def save_video(data):
#     """Insert video data and manage channel updates using @username"""
#     conn = sqlite3.connect("videos.db")
#     cursor = conn.cursor()

#     # Check if the channel exists by @username
#     cursor.execute("SELECT id, subscribers FROM channels WHERE channel_username = ?", (data["channel_username"],))
#     channel_result = cursor.fetchone()

#     if channel_result:
#         channel_id, previous_subscribers = channel_result

#         # If the subscriber count has changed, add to history table
#         if previous_subscribers != data["subscribers"]:
#             cursor.execute("INSERT INTO channel_history (channel_id, previous_subscribers) VALUES (?, ?)", 
#                            (channel_id, previous_subscribers))
            
#             # Update the current subscriber count
#             cursor.execute("UPDATE channels SET subscribers = ? WHERE id = ?", 
#                            (data["subscribers"], channel_id))
#     else:
#         # Insert new channel if it does not exist
#         cursor.execute("INSERT INTO channels (channel_username, subscribers) VALUES (?, ?)", 
#                        (data["channel_username"], data["subscribers"]))
#         channel_id = cursor.lastrowid  # Get the new channel ID

#     # Insert the video
#     cursor.execute("""
#         INSERT INTO videos (title, description, views, likes, comments, posted, video_length, transcript, channel_id)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#     """, (
#         data["title"], data["description"], data["views"], data["likes"], 
#         data["comments"], data["posted"], data["video_length"], data["transcript"], channel_id
#     ))

#     # Link video and channel
#     video_id = cursor.lastrowid  # Get new video ID
#     cursor.execute("INSERT INTO channel_videos (video_id, channel_id) VALUES (?, ?)", 
#                    (video_id, channel_id))

#     conn.commit()
#     conn.close()

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


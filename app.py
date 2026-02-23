import csv
from database import save_video, init_db
from flask import Flask, request, render_template, redirect, flash, url_for, Response, jsonify
import isodate
import os
import pandas as pd
import requests
import sqlite3
from youtube_transcript_api import YouTubeTranscriptApi
import time
from urllib.parse import urlparse

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-secret-key-change-me")

# Initialize the database when app starts
init_db()

# Load API key from environment (empty string fallback for local setup)
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
REQUEST_TIMEOUT = 10

def extract_video_id(video_url):
    """Extracts video ID from different YouTube URL formats."""
    if "watch?v=" in video_url:
        return video_url.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in video_url:
        return video_url.split("youtu.be/")[1].split("?")[0]
    elif "embed/" in video_url:
        return video_url.split("embed/")[1].split("?")[0]
    elif "shorts/" in video_url:
        return video_url.split("shorts/")[1].split("?")[0]
    return None

def extract_channel_info(channel_url):
    """Extract (identifier_type, identifier) from common YouTube channel URL formats."""
    if not channel_url:
        return None, None

    parsed = urlparse(channel_url if "://" in channel_url else f"https://{channel_url}")
    host = parsed.netloc.lower().replace("www.", "")
    if host not in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        return None, None

    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return None, None

    first = path_parts[0]
    if first == "channel" and len(path_parts) > 1:
        return "channel_id", path_parts[1]
    if first == "user" and len(path_parts) > 1:
        return "username", path_parts[1]
    if first == "c" and len(path_parts) > 1:
        return "custom", path_parts[1]
    if first.startswith("@"):
        return "handle", first

    # Fallback for legacy custom URLs like youtube.com/somechannel
    reserved = {"watch", "shorts", "embed", "playlist", "feed", "results", "live"}
    if first not in reserved:
        return "custom", first

    return None, None

def get_channel_id_from_url(channel_url):
    """Resolve a canonical YouTube channel ID (UC...) from various URL formats."""
    identifier_type, identifier = extract_channel_info(channel_url)
    if not identifier:
        return None

    base_url = "https://www.googleapis.com/youtube/v3"
    handle_no_at = identifier[1:] if identifier.startswith("@") else identifier

    # Prefer exact resolvers for known URL types, then fallback to search.
    call_plan = []
    if identifier_type == "channel_id":
        call_plan.append(("channels", {"part": "id", "id": identifier}))
    elif identifier_type == "username":
        call_plan.append(("channels", {"part": "id", "forUsername": identifier}))
    elif identifier_type == "handle":
        call_plan.append(("channels", {"part": "id", "forHandle": identifier}))
        call_plan.append(("channels", {"part": "id", "forHandle": handle_no_at}))
    else:
        call_plan.append(("search", {"part": "snippet", "type": "channel", "q": identifier, "maxResults": 1}))

    # Broad fallback sequence to improve resilience for unusual URLs.
    call_plan.extend(
        [
            ("channels", {"part": "id", "id": identifier}),
            ("channels", {"part": "id", "forUsername": identifier}),
            ("channels", {"part": "id", "forHandle": identifier}),
            ("channels", {"part": "id", "forHandle": handle_no_at}),
            ("search", {"part": "snippet", "type": "channel", "q": identifier, "maxResults": 1}),
        ]
    )

    for endpoint, params in call_plan:
        try:
            params["key"] = YOUTUBE_API_KEY
            response = requests.get(f"{base_url}/{endpoint}", params=params, timeout=REQUEST_TIMEOUT).json()
            if "items" in response and response["items"]:
                if endpoint == "channels":
                    return response["items"][0]["id"]
                item = response["items"][0]
                item_id = item.get("id")
                search_id = item_id.get("channelId") if isinstance(item_id, dict) else None
                search_id = search_id or item.get("snippet", {}).get("channelId")
                if search_id:
                    return search_id
        except Exception:
            continue

    return None

def get_channel_videos_from_search(channel_id, max_results=50):
    """Fallback: fetch channel videos using search endpoint ordered by date."""
    videos = []
    next_page_token = None

    while len(videos) < max_results:
        params = {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": min(50, max_results - len(videos)),
            "key": YOUTUBE_API_KEY,
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params,
            timeout=REQUEST_TIMEOUT,
        ).json()

        items = response.get("items", [])
        if not items:
            break

        for item in items:
            item_id = item.get("id")
            video_id = item_id.get("videoId") if isinstance(item_id, dict) else None
            if video_id:
                videos.append(video_id)
                if len(videos) >= max_results:
                    break

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

        time.sleep(0.1)

    return videos

def get_channel_videos(channel_id, max_results=50):
    """Get up to max_results recent video IDs from a channel uploads playlist."""
    videos = []
    next_page_token = None

    # Fetch uploads playlist once.
    channel_api_url = "https://www.googleapis.com/youtube/v3/channels"
    channel_response = requests.get(
        channel_api_url,
        params={"part": "contentDetails", "id": channel_id, "key": YOUTUBE_API_KEY},
        timeout=REQUEST_TIMEOUT,
    ).json()

    if not ("items" in channel_response and channel_response["items"]):
        return videos

    uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"].get("uploads")
    if not uploads_playlist_id:
        return get_channel_videos_from_search(channel_id, max_results)

    while len(videos) < max_results:
        # Get videos from uploads playlist
        playlist_params = {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,
            "key": YOUTUBE_API_KEY,
        }
        if next_page_token:
            playlist_params["pageToken"] = next_page_token

        playlist_response = requests.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params=playlist_params,
            timeout=REQUEST_TIMEOUT,
        ).json()

        if not ("items" in playlist_response and playlist_response["items"]):
            break

        for item in playlist_response["items"]:
            if len(videos) >= max_results:
                break
            videos.append(item["contentDetails"]["videoId"])

        next_page_token = playlist_response.get("nextPageToken")
        if not next_page_token:
            break

        # Add delay to respect API rate limits
        time.sleep(0.1)

    if not videos:
        return get_channel_videos_from_search(channel_id, max_results)

    return videos

def parse_duration(duration):
    """Converts YouTube ISO 8601 duration format to HH:MM:SS"""
    parsed_duration = isodate.parse_duration(duration)
    return str(parsed_duration)  # Formats to HH:MM:SS

def get_transcript(video_id):
    """Fetches transcript if available, otherwise returns a default message"""
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)
        return " ".join([line.text for line in transcript])
    except Exception:
        return "Transcript unavailable or disabled by the uploader."

def get_video_data(video_id):
    """Fetch video details including channel @username and subscribers"""
    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(api_url).json()

    if "items" in response and response["items"]:
        data = response["items"][0]
        channel_id = data["snippet"]["channelId"]

        # Fetch channel details (including @username and subscribers)
        channel_api_url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&id={channel_id}&key={YOUTUBE_API_KEY}"
        channel_response = requests.get(channel_api_url).json()
        
        if "items" in channel_response and channel_response["items"]:
            channel_data = channel_response["items"][0]["snippet"]
            statistics_data = channel_response["items"][0]["statistics"]

            channel_username = channel_data.get("customUrl", f"@{channel_id}")  # Fallback to ID if username unavailable
            subscribers = statistics_data.get("subscriberCount", "0")  # Ensure it exists, fallback to "0"
        else:
            channel_username = f"@{channel_id}"
            subscribers = "0"  # Default if API call fails

        return {
            "title": data["snippet"]["title"],
            "description": data["snippet"]["description"],
            "views": data["statistics"].get("viewCount", "N/A"),
            "likes": data["statistics"].get("likeCount", "N/A"),
            "comments": data["statistics"].get("commentCount", "N/A"),
            "posted": data["snippet"]["publishedAt"].split("T")[0],
            "channel_username": channel_username,
            "subscribers": subscribers,  # Ensure this exists
            "video_length": parse_duration(data["contentDetails"]["duration"]),
            "transcript": get_transcript(video_id),
        }
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    video_data = None
    if request.method == "POST":
        if not YOUTUBE_API_KEY:
            flash("YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.", "danger")
            return render_template("index.html", data=None)

        video_url = request.form["video_url"]
        video_id = extract_video_id(video_url)
        if not video_id:
            flash("Invalid YouTube URL. Please paste a valid video link.", "warning")
            return render_template("index.html", data=None)

        video_data = get_video_data(video_id)
        if not video_data:
            flash("Could not fetch video data. Check your API key/quota and try again.", "warning")

    return render_template("index.html", data=video_data)

@app.route("/channel", methods=["GET", "POST"])
def channel_scraper():
    if request.method == "POST":
        if not YOUTUBE_API_KEY:
            flash("YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.", "danger")
            return render_template("channel.html")

        channel_url = request.form["channel_url"]
        max_videos = int(request.form.get("max_videos", 50))
        
        channel_id = get_channel_id_from_url(channel_url)
        if not channel_id:
            flash("Could not extract channel ID from URL. Please check the URL format.", "danger")
            return render_template("channel.html")
        
        # Start background processing
        flash(f"Started processing channel. This may take a while for {max_videos} videos...", "info")
        return redirect(url_for('process_channel', channel_id=channel_id, max_videos=max_videos))
    
    return render_template("channel.html")

@app.route("/process_channel/<channel_id>/<int:max_videos>")
def process_channel(channel_id, max_videos):
    try:
        if not YOUTUBE_API_KEY:
            flash("YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.", "danger")
            return redirect(url_for('channel_scraper'))

        video_ids = get_channel_videos(channel_id, max_videos)
        
        if not video_ids:
            flash("No videos found for this channel.", "warning")
            return redirect(url_for('channel_scraper'))
        
        processed_count = 0
        failed_count = 0
        
        for video_id in video_ids:
            try:
                video_data = get_video_data(video_id)
                if video_data:
                    save_video(video_data)
                    processed_count += 1
                else:
                    failed_count += 1
                
                # Add delay to respect API rate limits
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing video {video_id}: {str(e)}")
                failed_count += 1
                continue
        
        flash(f"Channel processing complete! Processed: {processed_count} videos, Failed: {failed_count} videos", "success")
        
    except Exception as e:
        flash(f"Error processing channel: {str(e)}", "danger")
    
    return redirect(url_for('channel_scraper'))

@app.route("/save", methods=["POST"])
def save():
    try:
        video_data = request.form.to_dict()
        print("Received video data:", video_data)  # Debugging print
        save_video(video_data)  # Call database function
        flash("Video data saved successfully!", "success")
        print("Flash success message set.")  # Debugging print
    except Exception as e:
        flash(f"Error saving video: {str(e)}", "danger")
        print("Flash error message set:", str(e))  # Debugging print

    return redirect(url_for("index"))

@app.route("/data")
def data_viewer():
    """Display all data in tables."""
    return render_template("data_viewer.html")

@app.route("/api/data")
def get_data_api():
    """API endpoint to fetch all data as JSON."""
    conn = sqlite3.connect("videos.db")

    # Get data with joins for better readability.
    videos_query = """
    SELECT
        v.id,
        v.title,
        c.channel_username,
        v.views,
        v.likes,
        v.comments,
        v.posted,
        v.video_length,
        v.saved_at,
        c.subscribers
    FROM videos v
    JOIN channels c ON v.channel_id = c.id
    ORDER BY v.saved_at DESC
    """

    channels_query = "SELECT * FROM channels ORDER BY subscribers DESC"
    history_query = """
    SELECT
        ch.id,
        c.channel_username,
        ch.previous_subscribers,
        ch.recorded_at
    FROM channel_history ch
    JOIN channels c ON ch.channel_id = c.id
    ORDER BY ch.recorded_at DESC
    """

    videos_df = pd.read_sql_query(videos_query, conn)
    channels_df = pd.read_sql_query(channels_query, conn)
    history_df = pd.read_sql_query(history_query, conn)

    conn.close()

    data = {
        "videos": videos_df.to_dict("records"),
        "channels": channels_df.to_dict("records"),
        "history": history_df.to_dict("records"),
        "counts": {
            "total_videos": len(videos_df),
            "total_channels": len(channels_df),
            "total_history_records": len(history_df),
        },
    }

    return jsonify(data)

@app.route("/export", methods=["GET"])
def export_data_route():
    """Retrieve all data and export as CSV or Excel"""
    format = request.args.get("format", "csv")  # Default to CSV if no format is specified

    conn = sqlite3.connect("videos.db")

    # Load all tables into separate Pandas DataFrames
    tables = {
        "videos": pd.read_sql_query("SELECT * FROM videos", conn),
        "channels": pd.read_sql_query("SELECT * FROM channels", conn),
        "channel_videos": pd.read_sql_query("SELECT * FROM channel_videos", conn),
        "channel_history": pd.read_sql_query("SELECT * FROM channel_history", conn)
    }
    
    conn.close()

    # Export to CSV (Combine All Tables)
    if format == "csv":
        from io import StringIO
        output = StringIO()

        # Write all tables to a single CSV file
        for sheet_name, df in tables.items():
            output.write(f"\n=== {sheet_name.upper()} ===\n")  # Add table name as a separator
            df.to_csv(output, index=False)
            output.write("\n")  # Space between tables

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=exported_data.csv"}
        )

    # Export to Excel (Each Table in a Separate Sheet)
    elif format == "xlsx":
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sheet_name, df in tables.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=exported_data.xlsx"}
        )

    # If an invalid format is provided, return an error
    else:
        return "Invalid format! Please choose 'csv' or 'xlsx'.", 400

if __name__ == "__main__":
    app.run(debug=True)

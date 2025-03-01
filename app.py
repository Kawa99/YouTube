import csv
from database import save_video, init_db
from flask import Flask, request, render_template, redirect, flash, url_for, Response
import isodate
import os
import requests
import sqlite3
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

app.secret_key = "1234"

# Initialize the database when app starts
init_db()

# Load API Key securely
YOUTUBE_API_KEY = "AIzaSyA9Z2aPRDrJdYt1OjQKRiEIaXjkzyQJakg"  # Set in your environment variables

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

def parse_duration(duration):
    """Converts YouTube ISO 8601 duration format to HH:MM:SS"""
    parsed_duration = isodate.parse_duration(duration)
    return str(parsed_duration)  # Formats to HH:MM:SS

def get_transcript(video_id):
    """Fetches transcript if available, otherwise returns a default message"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([line["text"] for line in transcript])
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
        video_url = request.form["video_url"]
        video_id = extract_video_id(video_url)
        if video_id:
            video_data = get_video_data(video_id)

    return render_template("index.html", data=video_data)


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


@app.route("/export", methods=["GET"])
def export_data():
    """Retrieve all data from the database and export as CSV"""
    conn = sqlite3.connect("videos.db")
    cursor = conn.cursor()

    # SQL Query to Join All Tables
    query = """
        SELECT 
            v.id AS video_id,
            v.title,
            v.description,
            v.views,
            v.likes,
            v.comments,
            v.posted,
            v.video_length,
            v.transcript,
            v.saved_at,
            c.channel_username,
            c.subscribers,
            ch.previous_subscribers,
            ch.recorded_at AS sub_history_timestamp
        FROM videos v
        LEFT JOIN channels c ON v.channel_id = c.id
        LEFT JOIN channel_videos cv ON v.id = cv.video_id
        LEFT JOIN channel_history ch ON c.id = ch.channel_id
    """

    cursor.execute(query)
    data = cursor.fetchall()
    conn.close()

    # Define CSV File Column Headers
    column_headers = [
        "video_id", "title", "description", "views", "likes", "comments", "posted",
        "video_length", "transcript", "saved_at", "channel_username", "subscribers",
        "previous_subscribers", "sub_history_timestamp"
    ]

    # Create CSV File in Memory
    def generate():
        yield ",".join(column_headers) + "\n"  # CSV Header Row
        for row in data:
            yield ",".join(str(value) if value is not None else "" for value in row) + "\n"

    # Serve CSV File for Download
    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=exported_data.csv"})


if __name__ == "__main__":
    app.run(debug=True)

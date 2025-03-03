import csv
from database import save_video, init_db
from flask import Flask, request, render_template, redirect, flash, url_for, Response
import isodate
import os
import pandas as pd
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
    """Converts YouTube ISO 8601 duration format to total seconds (INTEGER)."""
    parsed_duration = isodate.parse_duration(duration)  # Converts to timedelta
    return int(parsed_duration.total_seconds())  # Convert to integer (seconds)

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

        # Construct the full video URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"  # ✅ Ensure video URL is included

        # Fetch channel details
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
            "video_url": video_url,  # ✅ Ensure this is included
            "title": data["snippet"]["title"],
            "description": data["snippet"]["description"],
            "views": data["statistics"].get("viewCount", "N/A"),
            "likes": data["statistics"].get("likeCount", "N/A"),
            "comments": data["statistics"].get("commentCount", "N/A"),
            "posted": data["snippet"]["publishedAt"].split("T")[0],
            "channel_username": channel_username,
            "subscribers": subscribers,
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
def export_data_route():
    """Retrieve all data and export as CSV or Excel"""
    format = request.args.get("format", "csv")  # Default to CSV if no format is specified

    conn = sqlite3.connect("videos.db")

    # Load all tables that exist in the database
    tables = {
        "videos": pd.read_sql_query("SELECT * FROM videos", conn),
        "channels": pd.read_sql_query("SELECT * FROM channels", conn),
        "channel_history": pd.read_sql_query("SELECT * FROM channel_history", conn),
        "video_performance": pd.read_sql_query("SELECT * FROM video_performance", conn),
        "comments": pd.read_sql_query("SELECT * FROM comments", conn)
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

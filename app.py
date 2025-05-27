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
import re

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

def extract_channel_info(channel_url):
    """Extract channel ID or username from various YouTube channel URL formats"""
    patterns = [
        r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        r'youtube\.com/c/([a-zA-Z0-9_-]+)',
        r'youtube\.com/user/([a-zA-Z0-9_-]+)',
        r'youtube\.com/@([a-zA-Z0-9_.-]+)',
        r'youtube\.com/([a-zA-Z0-9_-]+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, channel_url)
        if match:
            return match.group(1)
    
    return None

def get_channel_id_from_url(channel_url):
    """Get channel ID from various channel URL formats"""
    channel_identifier = extract_channel_info(channel_url)
    if not channel_identifier:
        return None
    
    # Try different API calls based on the identifier type
    api_calls = [
        f"https://www.googleapis.com/youtube/v3/channels?part=id&id={channel_identifier}&key={YOUTUBE_API_KEY}",
        f"https://www.googleapis.com/youtube/v3/channels?part=id&forUsername={channel_identifier}&key={YOUTUBE_API_KEY}",
        f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=channel&q={channel_identifier}&key={YOUTUBE_API_KEY}"
    ]
    
    for api_url in api_calls:
        try:
            response = requests.get(api_url).json()
            if "items" in response and response["items"]:
                if "search" in api_url:
                    return response["items"][0]["snippet"]["channelId"]
                else:
                    return response["items"][0]["id"]
        except:
            continue
    
    return None

def get_channel_videos(channel_id, max_results=50):
    """Get all video IDs from a channel"""
    videos = []
    next_page_token = None
    
    while len(videos) < max_results:
        # Get uploads playlist ID
        channel_api_url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channel_id}&key={YOUTUBE_API_KEY}"
        channel_response = requests.get(channel_api_url).json()
        
        if not ("items" in channel_response and channel_response["items"]):
            break
            
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Get videos from uploads playlist
        playlist_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_playlist_id}&maxResults=50&key={YOUTUBE_API_KEY}"
        
        if next_page_token:
            playlist_url += f"&pageToken={next_page_token}"
            
        playlist_response = requests.get(playlist_url).json()
        
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
    
    return videos

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

@app.route("/channel", methods=["GET", "POST"])
def channel_scraper():
    if request.method == "POST":
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
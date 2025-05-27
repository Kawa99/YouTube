#!/usr/bin/env python3
"""
Test script for debugging transcript issues with specific video IDs
"""

from youtube_transcript_api import YouTubeTranscriptApi

def test_transcript(video_id):
    """Test transcript fetching for a specific video ID"""
    print(f"\n{'='*50}")
    print(f"Testing video ID: {video_id}")
    print(f"{'='*50}")
    
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        print("Available transcripts:")
        for i, transcript_info in enumerate(transcript_list):
            print(f"  {i+1}. {transcript_info.language_code}: "
                  f"{'Auto' if transcript_info.is_generated else 'Manual'}, "
                  f"Translatable: {transcript_info.is_translatable}")
        
        # Test each transcript individually
        for i, transcript_info in enumerate(transcript_list):
            print(f"\nTesting transcript {i+1} ({transcript_info.language_code}):")
            try:
                transcript = transcript_info.fetch()
                if transcript and len(transcript) > 0:
                    sample = " ".join([line["text"] for line in transcript[:3]])  # First 3 lines
                    print(f"  ✅ SUCCESS: {len(transcript)} segments")
                    print(f"  Sample: {sample[:100]}...")
                else:
                    print(f"  ❌ EMPTY: Transcript returned but empty")
            except Exception as e:
                print(f"  ❌ FAILED: {e}")
        
    except Exception as e:
        print(f"❌ MAJOR ERROR: {e}")

if __name__ == "__main__":
    # Test the failing video IDs from your log
    failing_videos = [
        "s3q_SI831QQ",  # Man Dies Playing VR Game
        "gMVs1bZUh0I",  # How To Survive A Waterfall Drop
        "zpCkH9yPuHY",  # How Whiplash Injuries Happen
        "41Rv1qMmfdQ",  # Dragged To Death By A Stag
        "XOzGOwRS1ME",  # How Choking Works
    ]
    
    for video_id in failing_videos:
        test_transcript(video_id)
        input("\nPress Enter to test next video...")
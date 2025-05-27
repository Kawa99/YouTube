#!/usr/bin/env python3
"""
Test retry logic for transcript fetching
"""

from youtube_transcript_api import YouTubeTranscriptApi
import time

def get_transcript_with_retry(video_id, max_retries=2):
    """Test transcript fetching with retry logic"""
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"  🔄 Retry attempt {attempt} for video {video_id}")
                time.sleep(1)  # Brief delay between retries
                
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get auto-generated English transcript
            for transcript_info in transcript_list:
                if transcript_info.is_generated and transcript_info.language_code == 'en':
                    try:
                        transcript = transcript_info.fetch()
                        if transcript and len(transcript) > 0:
                            if attempt > 0:
                                print(f"  ✅ SUCCESS on retry {attempt}!")
                            else:
                                print(f"  ✅ SUCCESS on first attempt!")
                            sample = " ".join([line["text"] for line in transcript[:3]])
                            return f"SUCCESS: {sample[:100]}..."
                    except Exception as e:
                        if "no element found" in str(e).lower():
                            print(f"  ❌ XML parsing error on attempt {attempt + 1}")
                            if attempt < max_retries:
                                break  # Break to retry
                            else:
                                return f"FAILED after {max_retries + 1} attempts: {e}"
                        else:
                            return f"DIFFERENT ERROR: {e}"
                            
        except Exception as e:
            return f"API ERROR: {e}"
    
    return f"FAILED after all retries"

def test_problematic_video():
    """Test the video that consistently has issues"""
    problem_video = "s3q_SI831QQ"  # This one fails often based on your tests
    
    print(f"Testing retry logic on problematic video: {problem_video}")
    print("=" * 60)
    
    for test_run in range(3):
        print(f"\nTest run {test_run + 1}:")
        result = get_transcript_with_retry(problem_video, max_retries=2)
        print(f"  Result: {result}")
        
        # Brief pause between test runs
        time.sleep(2)

if __name__ == "__main__":
    test_problematic_video()
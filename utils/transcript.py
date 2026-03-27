"""
utils/transcript.py
YouTube transcript fetch karo — 429 error ke liye retry logic ke saath
"""

import time
import logging
import re

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> str | None:
    """YouTube URL se video ID nikalo"""
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_transcript(url: str, retries: int = 3, delay: int = 5):
    """
    YouTube video ka transcript fetch karo.
    
    Returns:
        tuple: (transcript_text: str, video_title: str)
    """
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    import yt_dlp

    video_id = extract_video_id(url)
    if not video_id:
        logger.error("Invalid YouTube URL")
        return "", "Unknown Video"

    # ── Video title fetch ──────────────────────────────────
    video_title = "YouTube Video"
    try:
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get("title", "YouTube Video")
    except Exception as e:
        logger.warning(f"Title fetch failed: {e}")

    # ── Transcript fetch with retry ────────────────────────
    transcript_text = ""

    for attempt in range(retries):
        try:
            # Pehle Hindi try karo, phir English
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id, languages=["hi", "en", "hi-IN", "en-IN"]
                )
            except Exception:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

            transcript_text = " ".join([entry["text"] for entry in transcript_list])
            logger.info(f"Transcript fetched: {len(transcript_text)} chars")
            break  # Success!

        except TranscriptsDisabled:
            logger.warning("Transcripts disabled for this video")
            break  # Retry se kuch nahi hoga

        except NoTranscriptFound:
            logger.warning("No transcript found for this video")
            break  # Retry se kuch nahi hoga

        except Exception as e:
            error_str = str(e)

            if "429" in error_str:
                # Rate limit — wait karke retry karo
                wait_time = delay * (attempt + 1)
                logger.warning(
                    f"Transcript error (429 - Rate Limited). "
                    f"Attempt {attempt + 1}/{retries}. "
                    f"{wait_time}s baad retry karenge..."
                )
                if attempt < retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached for transcript (429)")
            else:
                logger.error(f"Transcript error: {e}")
                break  # Unknown error — retry nahi karenge

    return transcript_text, video_title

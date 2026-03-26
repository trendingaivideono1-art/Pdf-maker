"""
YouTube transcript fetcher
Supports: regular videos, live streams, shorts
"""

import re
import json
import logging
import urllib.request
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
)

logger = logging.getLogger(__name__)
LANG_PRIORITY = ["en", "hi", "en-IN", "hi-IN", "a.en", "a.hi"]


def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:/live/)([A-Za-z0-9_-]{11})",
        r"(?:shorts/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_title(video_id: str) -> str:
    try:
        url = f"https://www.youtube.com/oembed?url=https://youtu.be/{video_id}&format=json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("title", "YouTube Video")
    except Exception:
        return "YouTube Video"


def get_transcript(url: str) -> tuple[str | None, str]:
    """Returns (transcript_text, video_title)"""
    video_id = extract_video_id(url)
    if not video_id:
        return None, "Unknown Video"

    title = get_video_title(video_id)

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None

        try:
            transcript = transcript_list.find_manually_created_transcript(LANG_PRIORITY)
        except Exception:
            pass

        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(LANG_PRIORITY)
            except Exception:
                for t in transcript_list:
                    transcript = t
                    break

        if not transcript:
            return None, title

        segments = transcript.fetch()
        full_text = " ".join(seg["text"] for seg in segments)
        full_text = re.sub(r"\[.*?\]", "", full_text)
        full_text = re.sub(r"\s+", " ", full_text).strip()

        logger.info(f"Transcript: {len(full_text)} chars for '{title}'")
        return full_text, title

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        logger.warning(f"Transcript unavailable: {e}")
        return None, title
    except Exception as e:
        logger.error(f"Transcript error: {e}")
        return None, title

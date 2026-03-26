"""
Video downloader using yt-dlp
Downloads only what's needed for frame extraction
"""

import os
import tempfile
import logging
import subprocess

logger = logging.getLogger(__name__)


def download_video(url: str, max_height: int = 480) -> str | None:
    """
    Download YouTube video using yt-dlp.
    Uses low resolution (480p) to save time and space.
    Returns path to downloaded video file, or None on failure.
    """
    try:
        tmp_dir = tempfile.mkdtemp(prefix="ytbot_")
        output_path = os.path.join(tmp_dir, "video.mp4")

        cmd = [
            "yt-dlp",
            "--format", f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_height}][ext=mp4]/best[ext=mp4]/best",
            "--output", output_path,
            "--no-playlist",
            "--no-warnings",
            "--quiet",
            "--merge-output-format", "mp4",
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if result.returncode != 0:
            logger.error(f"yt-dlp error: {result.stderr}")
            return None

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Video downloaded: {size_mb:.1f} MB at {output_path}")
            return output_path

        # yt-dlp sometimes adds extension
        for f in os.listdir(tmp_dir):
            if f.startswith("video"):
                full = os.path.join(tmp_dir, f)
                logger.info(f"Found video: {full}")
                return full

        logger.warning("Video file not found after download")
        return None

    except subprocess.TimeoutExpired:
        logger.error("Video download timed out (180s)")
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not installed! Run: pip install yt-dlp")
        return None
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None


def cleanup(video_path: str):
    """Remove downloaded video and its temp directory."""
    try:
        if video_path and os.path.exists(video_path):
            os.unlink(video_path)
            tmp_dir = os.path.dirname(video_path)
            if tmp_dir.startswith(tempfile.gettempdir()):
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.info(f"Cleaned up: {video_path}")
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")

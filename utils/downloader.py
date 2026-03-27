"""
utils/downloader.py
YouTube video download karo (yt-dlp)
Railway deployment ke liye — COOKIES_CONTENT env variable support
"""

import os
import logging
import tempfile

logger = logging.getLogger(__name__)


def _get_cookies_file() -> str | None:
    """
    Cookies file path return karo.
    Railway pe COOKIES_CONTENT env variable se temporary file banao.
    """

    # ── Option 1: COOKIES_CONTENT env variable (Railway ke liye best) ──
    cookies_content = os.getenv("COOKIES_CONTENT")
    if cookies_content:
        try:
            tmp_cookies = tempfile.mktemp(suffix=".txt")
            with open(tmp_cookies, "w") as f:
                f.write(cookies_content)
            logger.info("Cookies file created from COOKIES_CONTENT env variable")
            return tmp_cookies
        except Exception as e:
            logger.warning(f"Cookies file banana fail hua: {e}")

    # ── Option 2: COOKIES_FILE path (agar koi file path diya ho) ────────
    cookies_file = os.getenv("COOKIES_FILE")
    if cookies_file and os.path.exists(cookies_file):
        logger.info(f"Using cookies file: {cookies_file}")
        return cookies_file

    logger.warning("Koi cookies nahi mili — age-restricted videos fail ho sakti hain")
    return None


def download_video(url: str) -> str | None:
    """
    YouTube video download karo OCR ke liye.

    Args:
        url: YouTube video URL

    Returns:
        str: Downloaded video file path, ya None if failed
    """
    import yt_dlp

    output_path = tempfile.mktemp(suffix=".mp4")
    cookies_file = _get_cookies_file()
    tmp_cookies_created = False

    # ── yt-dlp options ─────────────────────────────────────
    ydl_opts = {
        "format": "worst[ext=mp4]/worst",  # Sabse chhoti quality (OCR ke liye kaafi)
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file
        # Agar COOKIES_CONTENT se banaya tha to baad mein delete karenge
        if cookies_file.endswith(".txt") and "tmp" in cookies_file:
            tmp_cookies_created = True

    # ── Download ───────────────────────────────────────────
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists(output_path):
            logger.info(f"Video downloaded: {output_path}")
            return output_path
        else:
            logger.error("Download failed: File not found after download")
            return None

    except yt_dlp.utils.DownloadError as e:
        error_str = str(e)

        if "Sign in" in error_str or "sign in" in error_str:
            logger.error(
                "yt-dlp error: Sign-in required!\n"
                "Railway Fix:\n"
                "  1. Chrome me 'Get cookies.txt Locally' extension install karein\n"
                "  2. YouTube pe login karein\n"
                "  3. Extension se cookies.txt export karein\n"
                "  4. Railway Dashboard → Variables mein add karein:\n"
                "     COOKIES_CONTENT = <cookies.txt ka poora content>"
            )
        elif "Private video" in error_str:
            logger.error("yt-dlp error: Private video — download nahi ho sakta")
        elif "unavailable" in error_str.lower():
            logger.error("yt-dlp error: Video is region locked / unavailable")
        else:
            logger.error(f"yt-dlp error: {e}")

        return None

    except Exception as e:
        logger.error(f"Unexpected download error: {e}")
        return None

    finally:
        # Temporary cookies file delete karo
        if tmp_cookies_created and cookies_file and os.path.exists(cookies_file):
            try:
                os.unlink(cookies_file)
            except Exception:
                pass


def cleanup(video_path: str):
    """Downloaded video file delete karo"""
    try:
        if video_path and os.path.exists(video_path):
            os.unlink(video_path)
            logger.info(f"Cleaned up: {video_path}")
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")

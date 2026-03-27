"""
Board Text Extractor using OpenCV + EasyOCR
============================================
- Extracts frames from video at smart intervals
- Detects frames where board content changed
- Runs OCR on unique frames (whiteboard + digital board)
- Returns cleaned, deduplicated board text
"""

import os
import logging
import hashlib
from collections import Counter

logger = logging.getLogger(__name__)

# How many frames to sample per minute of video
FRAMES_PER_MINUTE = 4
# Max frames to OCR (to limit processing time)
MAX_FRAMES_TO_OCR = 40


def extract_board_text(video_path: str) -> str:
    """
    Main function: Extract all readable text from video frames.
    Returns combined deduplicated text from board/screen.
    """
    try:
        import cv2
        import easyocr
        import numpy as np
    except ImportError as e:
        logger.error(f"Missing library: {e}. Run: pip install opencv-python-headless easyocr")
        return ""

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return ""

        fps          = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps
        duration_min = duration_sec / 60

        logger.info(f"Video: {duration_min:.1f} min, {total_frames} frames @ {fps:.1f} fps")

        # Calculate frame interval
        sample_count = max(10, min(MAX_FRAMES_TO_OCR, int(duration_min * FRAMES_PER_MINUTE)))
        interval     = max(1, total_frames // sample_count)

        logger.info(f"Sampling {sample_count} frames every {interval} frames")

        # ── Extract candidate frames ───────────────────────
        frames    = []
        prev_hash = None

        for i in range(0, total_frames, interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Duplicate frame skip
            frame_hash = hashlib.md5(gray.tobytes()[::100]).hexdigest()
            if frame_hash == prev_hash:
                continue
            prev_hash = frame_hash

            # Board/screen detect karo
            if has_board_region(gray):
                frames.append(frame)

            if len(frames) >= MAX_FRAMES_TO_OCR:
                break

        cap.release()
        logger.info(f"Selected {len(frames)} frames with board content")

        if not frames:
            logger.info("No board frames detected")
            return ""

        # ── Run EasyOCR ────────────────────────────────────
        reader = easyocr.Reader(
            ['en', 'hi'],
            gpu=False,
            verbose=False
        )

        all_texts  = []
        seen_lines = set()

        for idx, frame in enumerate(frames):
            try:
                # Preprocess for better OCR
                processed = preprocess_frame(frame)

                results = reader.readtext(processed, detail=0, paragraph=True)
                for text in results:
                    cleaned = clean_text(text)
                    if cleaned and cleaned not in seen_lines:
                        seen_lines.add(cleaned)
                        all_texts.append(cleaned)

                logger.info(f"Frame {idx+1}/{len(frames)}: {len(results)} text blocks")
            except Exception as e:
                logger.warning(f"OCR error on frame {idx}: {e}")
                continue

        final_text = "\n".join(all_texts)
        logger.info(f"Total board text extracted: {len(final_text)} chars")
        return final_text

    except Exception as e:
        logger.error(f"Board extraction failed: {e}", exc_info=True)
        return ""


def has_board_region(gray_frame) -> bool:
    """
    Whiteboard, Blackboard aur Digital Board (projector/screen) detect karo.
    """
    try:
        import numpy as np
        import cv2

        small  = cv2.resize(gray_frame, (160, 90))
        center = small[20:70, 40:120]

        # Whiteboard: bahut bright
        white_ratio   = np.sum(small > 200) / small.size
        # Blackboard: center dark
        dark_ratio    = np.sum(center < 80) / center.size
        # ✅ Digital board: medium brightness (projector screen)
        digital_ratio = np.sum((small > 80) & (small < 220)) / small.size

        # Text edges
        edges      = cv2.Canny(small, 50, 150)
        edge_ratio = np.sum(edges > 0) / edges.size

        has_background = (
            white_ratio   > 0.3 or
            dark_ratio    > 0.3 or
            digital_ratio > 0.5   # Digital board ke liye
        )
        has_text = edge_ratio > 0.01

        return has_background and has_text

    except Exception:
        return True  # Default: OCR try karo


def preprocess_frame(frame):
    """
    Frame ko OCR ke liye better banao.
    Whiteboard + Digital board dono ke liye kaam karta hai.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Sharpen
    kernel    = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)

    # Contrast enhance (CLAHE)
    clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(sharpened)

    # Scale up 1.5x — OCR accuracy badhti hai
    scaled = cv2.resize(enhanced, None, fx=1.5, fy=1.5,
                        interpolation=cv2.INTER_CUBIC)
    return scaled


def clean_text(text: str) -> str:
    """Clean and normalize extracted OCR text."""
    if not text:
        return ""

    text = text.strip()

    if len(text) < 3:
        return ""

    # Mostly symbols → skip
    alpha_count = sum(1 for c in text if c.isalpha())
    if len(text) > 3 and alpha_count < len(text) * 0.3:
        return ""

    return text

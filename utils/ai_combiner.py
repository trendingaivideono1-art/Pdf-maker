"""
AI Notes Combiner using Claude API
====================================
Intelligently merges audio transcript + board OCR text
into structured, comprehensive study notes
"""

import os
import logging
import anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_TRANSCRIPT_CHARS = 5000
MAX_BOARD_CHARS      = 3000


def combine_and_create_notes(
    transcript: str,
    board_text: str,
    video_title: str,
    style: str = "study",
    has_transcript: bool = True
) -> str | None:
    """
    Combine transcript + board text using Claude AI.
    Returns formatted notes string or None on failure.
    """

    # Trim to fit context window
    transcript_trimmed = transcript[:MAX_TRANSCRIPT_CHARS] if transcript else ""
    board_trimmed      = board_text[:MAX_BOARD_CHARS] if board_text else ""

    # Build input for Claude
    input_parts = []
    if transcript_trimmed:
        input_parts.append(f"=== AUDIO TRANSCRIPT (Teacher ki awaaz) ===\n{transcript_trimmed}")
    if board_trimmed:
        input_parts.append(f"=== BOARD TEXT (OCR se nikala gaya) ===\n{board_trimmed}")

    combined_input = f"Video Title: {video_title}\n\n" + "\n\n".join(input_parts)

    system_prompt = get_system_prompt(style, has_transcript, bool(board_text))

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2800,
            system=system_prompt,
            messages=[{"role": "user", "content": combined_input}]
        )
        notes = message.content[0].text
        logger.info(f"Combined notes generated: {len(notes)} chars, style={style}")
        return notes
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return None


def get_system_prompt(style: str, has_transcript: bool, has_board: bool) -> str:
    """Build the right system prompt based on available sources and style."""

    source_note = ""
    if has_transcript and has_board:
        source_note = (
            "You have TWO sources:\n"
            "1. AUDIO TRANSCRIPT — what the teacher said (may have speech-to-text errors)\n"
            "2. BOARD TEXT — text extracted via OCR from the board/screen (may have OCR errors)\n\n"
            "IMPORTANT: Cross-reference both. Board text = most accurate facts/formulas/keywords. "
            "Transcript = context and explanations. Fix obvious OCR/speech errors using context."
        )
    elif has_board:
        source_note = (
            "You only have BOARD TEXT (OCR extracted). "
            "Use it to reconstruct what was likely taught. Fill gaps with your knowledge."
        )
    else:
        source_note = (
            "You only have AUDIO TRANSCRIPT. "
            "Create notes from what the teacher explained verbally."
        )

    base = f"""You are an expert teacher and study note creator.

{source_note}

Language: If content is in Hindi, respond in Hinglish (Hindi + English mix). Otherwise use English.
Always fix obvious OCR errors (e.g. '0' vs 'O', '1' vs 'l', broken words).
Preserve all formulas, equations, dates, and numbers EXACTLY as they appear on board.
"""

    FORMATS = {
        "study": base + """
Create comprehensive STUDY NOTES in this EXACT format:

# [Topic Name]

## 📋 Overview
[2-3 line summary]

## 🎯 Main Topics Covered
[bullet list of topics]

## 📚 Detailed Notes

### [Sub-topic 1]
- Key point
- Key point
  - Sub-detail

### [Sub-topic 2]
[continue...]

## 🔢 Formulas & Definitions
[All formulas/equations/definitions from board]
- **Term**: meaning
- **Formula**: equation

## 💡 Important Points
[What teacher emphasized]

## 🔑 Key Takeaways
[5-7 points to remember]

## ❓ Practice Questions
[5 questions based on this content]
1. ?
2. ?
""",

        "summary": base + """
Create a SHORT SUMMARY in this EXACT format:

# [Topic Name — Summary]

## 🎯 What Was Taught
[1 paragraph]

## 📌 Key Points
1. Point
2. Point
[8-10 numbered points]

## 🔢 Important Formulas / Facts
[Only critical formulas/facts]

## ✅ In One Line
[Single sentence takeaway]
""",

        "mindmap": base + """
Create a MIND MAP style notes in this EXACT format:

# [Topic Name — Mind Map]

## 🌐 Core Concept
[The central idea]

## 🌿 [Branch 1: Name]
  → Main point
    → Detail
    → Detail
  → Main point
    → Detail

## 🌿 [Branch 2: Name]
  → Main point
    → Detail

[Continue for all major branches]

## 🔗 Key Connections
[How concepts link together]

## ⭐ Must Remember
[Top 5 things]
""",

        "qa": base + """
Create a Q&A STUDY GUIDE in this EXACT format:

# [Topic Name — Q&A Guide]

## 📖 Introduction
[Brief overview]

## ❓ Questions & Answers

**Q1: [Basic question]**
A: [Clear answer]

**Q2: [Conceptual question]**
A: [Answer]

[Continue for 12-15 Q&A pairs, from basic to advanced]

## 🧪 Self-Test Questions
[5 harder questions — NO answers, for self-testing]
1. ?
2. ?
"""
    }

    return FORMATS.get(style, FORMATS["study"])

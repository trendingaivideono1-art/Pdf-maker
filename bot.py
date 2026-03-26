"""
🤖 YouTube Smart PDF Bot
=========================
Audio Transcript + Board Text (OCR) → Beautiful Study PDF

Flow:
1. User sends YouTube link
2. Bot downloads video (yt-dlp)
3. Extracts audio transcript (youtube-transcript-api)
4. Extracts video frames & runs OCR (OpenCV + EasyOCR)
5. AI combines both into smart notes (Claude)
6. Generates beautiful PDF
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from utils.transcript import get_transcript
from utils.ocr_extractor import extract_board_text
from utils.ai_combiner import combine_and_create_notes
from utils.pdf_maker import generate_pdf
from utils.downloader import download_video, cleanup
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─── /start ────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *YouTube Smart PDF Bot!*\n\n"
        "Main do tareekon se notes banata hoon:\n\n"
        "🎙️ *Audio Transcript* — Teacher jo bolte hain\n"
        "📋 *Board Text (OCR)* — Board pe jo likha hai\n\n"
        "Dono combine karke ek complete PDF!\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📤 Bas YouTube link bhejo!\n"
        "⚙️ /style — PDF format choose karo\n"
        "ℹ️ /help — Help",
        parse_mode="Markdown"
    )


# ─── /help ─────────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Kaise Use Karein?*\n\n"
        "1️⃣ YouTube video link copy karein\n"
        "2️⃣ Is chat mein bhejo\n"
        "3️⃣ Bot automatically:\n"
        "   • Audio transcript lega\n"
        "   • Board/screen text padega\n"
        "   • AI se notes banayega\n"
        "   • PDF bhejega\n\n"
        "⏱️ *Time:* 1-3 minute (video length pe depend)\n\n"
        "⚠️ *Note:*\n"
        "• Board OCR ke liye video download hogi\n"
        "• Clear board wale videos best results dete hain\n"
        "• Hindi + English dono support hai",
        parse_mode="Markdown"
    )


# ─── /style ────────────────────────────────────────────────
async def style_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📚 Study Notes",  callback_data="style_study"),
            InlineKeyboardButton("📋 Summary",      callback_data="style_summary"),
        ],
        [
            InlineKeyboardButton("🧠 Mind Map",     callback_data="style_mindmap"),
            InlineKeyboardButton("❓ Q&A Format",   callback_data="style_qa"),
        ],
    ]
    await update.message.reply_text(
        "🎨 *PDF Style choose karein:*\n\n"
        "📚 *Study Notes* — Full detailed notes\n"
        "📋 *Summary* — Short & crisp\n"
        "🧠 *Mind Map* — Visual tree structure\n"
        "❓ *Q&A* — Question-answer format",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ─── Callback ──────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    style_map = {
        "style_study":   ("📚 Study Notes", "study"),
        "style_summary": ("📋 Summary",     "summary"),
        "style_mindmap": ("🧠 Mind Map",    "mindmap"),
        "style_qa":      ("❓ Q&A Format",  "qa"),
    }

    if query.data in style_map:
        label, key = style_map[query.data]
        context.user_data["pdf_style"] = key
        await query.edit_message_text(
            f"✅ Style set: *{label}*\n\nAb YouTube link bhejiye!",
            parse_mode="Markdown"
        )


# ─── Main message handler ──────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not any(x in text for x in ["youtube.com", "youtu.be"]):
        await update.message.reply_text(
            "⚠️ Valid YouTube link nahi mila.\n"
            "Example: `https://www.youtube.com/watch?v=...`",
            parse_mode="Markdown"
        )
        return

    style = context.user_data.get("pdf_style", "study")
    video_path = None

    try:
        # ── Step 1: Transcript ─────────────────────────
        msg = await update.message.reply_text(
            "🔄 *Processing...*\n\n"
            "⏳ Step 1/5: Audio transcript fetch ho raha hai...",
            parse_mode="Markdown"
        )

        transcript, video_title = get_transcript(text)
        has_transcript = bool(transcript)

        if not has_transcript:
            transcript = ""
            logger.info("No transcript found, will rely on OCR only")

        # ── Step 2: Download video ─────────────────────
        await msg.edit_text(
            "🔄 *Processing...*\n\n"
            "✅ Step 1/5: Transcript ready\n"
            "⏳ Step 2/5: Video download ho rahi hai (OCR ke liye)...",
            parse_mode="Markdown"
        )

        video_path = download_video(text)

        # ── Step 3: OCR ───────────────────────────────
        await msg.edit_text(
            "🔄 *Processing...*\n\n"
            "✅ Step 1/5: Transcript ready\n"
            "✅ Step 2/5: Video downloaded\n"
            "⏳ Step 3/5: Board text extract ho raha hai (OCR)...",
            parse_mode="Markdown"
        )

        board_text = ""
        if video_path:
            board_text = extract_board_text(video_path)
            logger.info(f"OCR extracted: {len(board_text)} chars")

        if not has_transcript and not board_text:
            await msg.edit_text(
                "❌ *Kuch bhi extract nahi hua!*\n\n"
                "• Transcript: Not available\n"
                "• Board OCR: No text found\n\n"
                "💡 Clear board wali video try karein.",
                parse_mode="Markdown"
            )
            return

        # ── Step 4: AI combines both ───────────────────
        await msg.edit_text(
            "🔄 *Processing...*\n\n"
            "✅ Step 1/5: Transcript ready\n"
            "✅ Step 2/5: Video downloaded\n"
            "✅ Step 3/5: Board text extracted\n"
            "⏳ Step 4/5: AI notes bana raha hai...",
            parse_mode="Markdown"
        )

        notes = combine_and_create_notes(
            transcript=transcript,
            board_text=board_text,
            video_title=video_title,
            style=style,
            has_transcript=has_transcript
        )

        if not notes:
            await msg.edit_text("❌ Notes generate nahi ho sake. Dobara try karein.")
            return

        # ── Step 5: Generate PDF ───────────────────────
        await msg.edit_text(
            "🔄 *Processing...*\n\n"
            "✅ Step 1/5: Transcript ready\n"
            "✅ Step 2/5: Video downloaded\n"
            "✅ Step 3/5: Board text extracted\n"
            "✅ Step 4/5: AI notes ready\n"
            "⏳ Step 5/5: PDF ban raha hai...",
            parse_mode="Markdown"
        )

        sources_used = []
        if has_transcript: sources_used.append("🎙️ Audio")
        if board_text:      sources_used.append("📋 Board OCR")
        sources_str = " + ".join(sources_used)

        pdf_path = generate_pdf(notes, video_title, style, sources_str)

        # ── Send PDF ───────────────────────────────────
        with open(pdf_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"{video_title[:40]}_notes.pdf",
                caption=(
                    f"✅ *PDF Ready!*\n\n"
                    f"📹 *{video_title[:60]}*\n\n"
                    f"📊 Sources: {sources_str}\n"
                    f"🎨 Style: {style.title()}\n\n"
                    f"💡 /style se format badlein"
                ),
                parse_mode="Markdown"
            )

        await msg.delete()
        os.unlink(pdf_path)

    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Kuch error aaya:\n`{str(e)[:200]}`\n\nDobara try karein.",
            parse_mode="Markdown"
        )
    finally:
        if video_path:
            cleanup(video_path)


# ─── Main ──────────────────────────────────────────────────
async def main():
    print("🤖 Smart PDF Bot starting...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(CommandHandler("style", style_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot running! Press Ctrl+C to stop.")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await app.updater.idle()
        await app.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

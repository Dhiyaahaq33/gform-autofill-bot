import os
import re
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext
)

from form_parser import GoogleFormParser
from response_generator import ResponseGenerator
from form_submitter import FormSubmitter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User state storage in-memory
# user_id -> { "form_data": {...}, "awaiting_custom_count": bool, "active_task": bool }
USER_SESSIONS = {}

def build_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Builds a visual text progress bar like [████░░░░░░]"""
    if total <= 0:
        return "[░░░░░░░░░░] 0%"
    fraction = min(1.0, current / total)
    filled = int(fraction * length)
    bar = "█" * filled + "░" * (length - filled)
    percent = int(fraction * 100)
    return f"[{bar}] {percent}%"

def start_command(update: Update, context: CallbackContext):
    """Handles /start command"""
    welcome_text = (
        "👋 *Halo! Selamat Datang di Google Form Auto-Filler Bot.*\n\n"
        "Bot ini dapat mengisi Google Form secara otomatis dengan variasi jawaban organik "
        "layaknya responden manusia sungguhan.\n\n"
        "✨ *Keunggulan Fitur:*\n"
        "• Ekstraksi otomatis pertanyaan, pilihan, skala, dan esai.\n"
        "• Variasi jawaban manusia (nama Indonesia, feedback unik, distribusi wajar).\n"
        "• Rotasi User-Agent & jeda waktu acak agar aman dari deteksi.\n"
        "• Live progress bar langsung di chat.\n\n"
        "👉 *Cara Pakai:*\n"
        "Cukup *kirimkan link Google Form* kamu ke chat ini."
    )
    update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

def handle_url_or_message(update: Update, context: CallbackContext):
    """Detects Google Form link or custom count input from user"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    session = USER_SESSIONS.get(user_id, {})

    # Check if user is currently replying with a custom number of respondents
    if session.get("awaiting_custom_count"):
        try:
            count = int(text)
            if count <= 0:
                update.message.reply_text("⚠️ Jumlah responden minimal 1. Silakan masukkan angka yang valid:")
                return
            if count > 300:
                update.message.reply_text("⚠️ Demi keamanan dari rate limit Google, maksimal sekali jalan 300 responden. Masukkan angka <= 300:")
                return
            session["awaiting_custom_count"] = False
            start_filling_process(update, context, user_id, count)
            return
        except ValueError:
            update.message.reply_text("⚠️ Mohon masukkan angka bilangan bulat saja (contoh: 15):")
            return

    # Check for Google Form URL
    gform_match = re.search(r"https?://(?:docs\.google\.com/forms/d/|forms\.gle/)[^\s]+", text)
    if not gform_match:
        update.message.reply_text(
            "ℹ️ Silakan kirimkan link Google Form yang valid (contoh: `https://forms.gle/...` atau `https://docs.google.com/forms/d/e/.../viewform`)",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    form_url = gform_match.group(0)
    msg = update.message.reply_text("🔍 *Menganalisis Google Form...*", parse_mode=ParseMode.MARKDOWN)

    try:
        parser = GoogleFormParser(form_url)
        form_data = parser.fetch_and_parse()
        
        if not form_data["questions"]:
            msg.edit_text("❌ Form berhasil diakses, namun tidak ditemukan kolom pertanyaan atau form memerlukan login Google.")
            return

        USER_SESSIONS[user_id] = {
            "form_data": form_data,
            "awaiting_custom_count": False,
            "active_task": False
        }

        # Build summary of questions
        q_summary = []
        for i, q in enumerate(form_data["questions"][:6], 1):
            q_summary.append(f"{i}. *{q['title']}* (`{q['type']}`)")
        if len(form_data["questions"]) > 6:
            q_summary.append(f"_...dan {len(form_data['questions']) - 6} pertanyaan lainnya_")

        summary_text = (
            f"📋 *Form Ditemukan!*\n"
            f"📌 *Judul:* {form_data['title'] or 'Tanpa Judul'}\n"
            f"📝 *Total Pertanyaan:* {len(form_data['questions'])}\n\n"
            f"*Daftar Pertanyaan:*\n" + "\n".join(q_summary) + "\n\n"
            f"👉 *Pilih jumlah responden yang ingin diisi:*"
        )

        keyboard = [
            [
                InlineKeyboardButton("5 Orang", callback_data="count_5"),
                InlineKeyboardButton("10 Orang", callback_data="count_10"),
                InlineKeyboardButton("25 Orang", callback_data="count_25"),
            ],
            [
                InlineKeyboardButton("50 Orang", callback_data="count_50"),
                InlineKeyboardButton("100 Orang", callback_data="count_100"),
                InlineKeyboardButton("✏️ Kustom Angka", callback_data="count_custom"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg.edit_text(summary_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error parsing form: {e}")
        msg.edit_text(
            f"❌ *Gagal memuat form:* {str(e)}\n\n"
            f"Pastikan opsi *'Batasi ke 1 tanggapan'* (perlu login Google) di form tersebut sudah dinonaktifkan oleh pembuat form.",
            parse_mode=ParseMode.MARKDOWN
        )

def handle_callback_query(update: Update, context: CallbackContext):
    """Handles inline buttons click"""
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = update.effective_user.id
    session = USER_SESSIONS.get(user_id)

    if not session or not session.get("form_data"):
        query.edit_message_text("⚠️ Sesi kedaluwarsa. Silakan kirimkan kembali link Google Form.")
        return

    if data.startswith("count_"):
        val = data.replace("count_", "")
        if val == "custom":
            session["awaiting_custom_count"] = True
            query.edit_message_text(
                "✍️ *Ketik jumlah responden yang diinginkan:*\n(Contoh: `15` atau `75`)",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            count = int(val)
            query.edit_message_text(f"⏳ Menyiapkan pengisian untuk *{count} responden*...", parse_mode=ParseMode.MARKDOWN)
            start_filling_process(update, context, user_id, count, message_id=query.message.message_id)

def start_filling_process(update: Update, context: CallbackContext, user_id: int, count: int, message_id: int = None):
    """Spawns background worker thread to generate and submit responses"""
    session = USER_SESSIONS.get(user_id)
    if not session or session.get("active_task"):
        text = "⚠️ Sedang ada proses pengisian yang berjalan. Mohon tunggu hingga selesai."
        if update.message:
            update.message.reply_text(text)
        elif update.callback_query:
            update.callback_query.message.reply_text(text)
        return

    session["active_task"] = True
    chat_id = update.effective_chat.id
    form_data = session["form_data"]

    # Send initial status message if not already editing existing
    if not message_id:
        status_msg = context.bot.send_message(
            chat_id=chat_id,
            text=f"🧠 *Menyiapkan data variasi {count} responden dengan AI/Heuristik...*",
            parse_mode=ParseMode.MARKDOWN
        )
        message_id = status_msg.message_id

    # Run in background thread
    def worker():
        start_time = time.time()
        try:
            # 1. Generate human-like responses
            generator = ResponseGenerator()
            batch_answers = generator.generate_batch(form_data["questions"], count)

            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=(
                    f"🚀 *Memulai Pengiriman Respon!*\n"
                    f"📋 *Form:* {form_data['title']}\n"
                    f"👥 *Target:* {count} responden\n"
                    f"{build_progress_bar(0, count)}\n"
                    f"Status: Menghubungi server Google..."
                ),
                parse_mode=ParseMode.MARKDOWN
            )

            # 2. Submit responses with live progress update
            submitter = FormSubmitter(form_data["response_url"])
            last_update_time = [0.0]

            def on_progress(current: int, total: int, is_success: bool):
                # Throttle Telegram message updates to avoid hitting Telegram rate limits (max 1 edit per 1.5s)
                now = time.time()
                if now - last_update_time[0] >= 1.5 or current == total:
                    last_update_time[0] = now
                    try:
                        bar = build_progress_bar(current, total)
                        context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=(
                                f"⏳ *Sedang Mengisi Form...*\n"
                                f"📋 *Form:* {form_data['title']}\n"
                                f"👥 *Progres:* {current}/{total} responden\n"
                                f"{bar}\n"
                                f"⏱️ _Jeda acak aktif untuk menyerupai manusia asli..._"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as edit_err:
                        logger.debug(f"Progress edit notice: {edit_err}")

            result = submitter.submit_batch(
                batch_answers,
                min_delay=1.0,
                max_delay=2.5,
                progress_callback=on_progress
            )

            elapsed = int(time.time() - start_time)

            # Final success message
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=(
                    f"🎉 *Pengisian Form Selesai!*\n\n"
                    f"📋 *Form:* {form_data['title']}\n"
                    f"👥 *Total Target:* {result['total']}\n"
                    f"✅ *Berhasil Dikirim:* {result['success']}\n"
                    f"❌ *Gagal:* {result['failed']}\n"
                    f"⏱️ *Total Durasi:* {elapsed} detik\n\n"
                    f"Jawaban bervariasi secara acak & natural layaknya orang-orang asli."
                ),
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error(f"Worker execution failed: {e}")
            try:
                context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"❌ *Terjadi Kesalahan saat Pengiriman:*\n`{str(e)}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass
        finally:
            session["active_task"] = False

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler to satisfy cloud health checks (Render, Koyeb, Railway)"""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - Google Form Auto-Filler Telegram Bot is running 24/7.")

    def log_message(self, format, *args):
        # Silence standard HTTP access logs to keep terminal/console clean
        pass

def run_health_server(port: int):
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger.info(f"Health check HTTP server listening on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Could not start HTTP health server on port {port}: {e}")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("="*60)
        print("ERROR: TELEGRAM_BOT_TOKEN belum diatur!")
        print("Silakan masukkan token bot dari @BotFather ke dalam file .env")
        print("="*60)
        return

    # Start background HTTP server if PORT environment variable is set (Render/Koyeb/Railway)
    port_env = os.getenv("PORT")
    if port_env:
        try:
            port = int(port_env)
            http_thread = threading.Thread(target=run_health_server, args=(port,), daemon=True)
            http_thread.start()
        except ValueError:
            logger.warning(f"Invalid PORT value: {port_env}")

    updater = Updater(token=token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CallbackQueryHandler(handle_callback_query))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_url_or_message))

    print("🤖 Google Form Auto-Filler Telegram Bot sedang berjalan...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

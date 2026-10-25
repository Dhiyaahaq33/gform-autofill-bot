import os
import re
import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

# Import our modular core
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from form_parser import GoogleFormParser
from response_generator import ResponseGenerator
from form_submitter import FormSubmitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def call_tg(method: str, payload: dict) -> dict:
    """Helper to call Telegram Bot API with automatic Markdown entity fallback"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not configured.")
        return {}
    try:
        r = requests.post(f"{TELEGRAM_API_BASE}/{method}", json=payload, timeout=12)
        res = r.json()
        if not res.get("ok") and "can't parse entities" in res.get("description", "").lower():
            # If Telegram rejects markdown formatting, retry cleanly as plain text
            payload_plain = dict(payload)
            payload_plain.pop("parse_mode", None)
            r_fallback = requests.post(f"{TELEGRAM_API_BASE}/{method}", json=payload_plain, timeout=12)
            return r_fallback.json()
        return res
    except Exception as e:
        logger.error(f"Telegram API call error ({method}): {e}")
        return {}

class handler(BaseHTTPRequestHandler):
    """
    Vercel Serverless Function Handler
    Supports Webhook POST from Telegram and GET health-check / webhook setup.
    """

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        # Convenience endpoint to link Telegram Webhook:
        # GET /api/index?setup=true&url=https://your-app.vercel.app/api/index
        if "setup" in qs and "url" in qs:
            target_url = qs["url"][0]
            tg_res = call_tg("setWebhook", {"url": target_url})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "message": f"Webhook setup requested for {target_url}",
                "telegram_response": tg_res
            }, indent=2).encode("utf-8"))
            return

        # Default Health Check response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response_body = {
            "status": "online",
            "service": "gform-autofill-bot",
            "platform": "Vercel Serverless",
            "info": "Kirimkan POST dari Telegram Webhook atau pasang webhook via /api/index?setup=true&url=YOUR_URL"
        }
        self.wfile.write(json.dumps(response_body, indent=2).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            update = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Invalid JSON payload: {e}")
            self.send_response(400)
            self.end_headers()
            return

        # Acknowledge Telegram immediately with 200 OK
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

        # Process update
        try:
            self.process_telegram_update(update)
        except Exception as proc_err:
            logger.error(f"Error processing telegram update: {proc_err}")

    def process_telegram_update(self, update: dict):
        # 1. Handle incoming text message
        if "message" in update:
            msg = update["message"]
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "").strip()

            if not chat_id or not text:
                return

            if text.startswith("/start"):
                welcome = (
                    "👋 *Halo! Selamat Datang di Google Form Auto-Filler Bot (Serverless Vercel).* 🚀\n\n"
                    "Bot ini aktif 24/7 di cloud tanpa perlu server VPS atau laptop nyala.\n\n"
                    "📌 *Perintah Tersedia:*\n"
                    "• `/status` - Cek kesehatan sistem, server Vercel, dan engine AI\n\n"
                    "👉 *Cara Pakai:*\n"
                    "Cukup *kirimkan link Google Form* kamu ke chat ini."
                )
                call_tg("sendMessage", {
                    "chat_id": chat_id,
                    "text": welcome,
                    "parse_mode": "Markdown"
                })
                return

            if text.startswith("/status"):
                status_msg = (
                    "📊 *STATUS SISTEM & BOT GOOGLE FORM AUTO-FILLER*\n"
                    "───────────────────────\n"
                    "🟢 *Status Server:* Online 24/7 (Vercel Serverless Edge)\n"
                    "🤖 *Bot Identity:* `@JohannesHaq7bot`\n"
                    "🌐 *Platform Cloud:* Vercel Python Runtime (`gform-autofill-bot.vercel.app`)\n"
                    "🧠 *AI & Response Engine:* Dual Mode (Universal Context-Adaptive Heuristics + Gemini Flash)\n"
                    "📝 *Tipe Soal Didukung:* Pilihan Ganda, Dropdown, Skala 1–5, Matriks Grid, Checklist, Isian Singkat, Esai/Paragraf, Tanggal & Waktu\n"
                    "🚨 *File Upload Sentinel:* Aktif (Deteksi Otomatis Soal Berkas/Dokumen Penting)\n"
                    "📑 *Multi-Section Engine:* Aktif (`pageHistory` Dynamic Chain Resolver)\n"
                    "🛡️ *Anti-Detection System:* Rotasi User-Agent (Chrome, Firefox, Safari iOS, Android) & Randomized Jitter\n"
                    "⚡ *Metode Pengiriman:* Multi-threaded Concurrent Engine (~0.3s per respon)\n"
                    "⏱️ *Koneksi Webhook:* Terhubung & Aktif\n"
                    "───────────────────────\n"
                    "Status: *Ready!* Silakan kirimkan link Google Form kamu untuk mulai pengisian otomatis."
                )
                call_tg("sendMessage", {
                    "chat_id": chat_id,
                    "text": status_msg,
                    "parse_mode": "Markdown"
                })
                return

            # Check for Google Form link
            gform_match = re.search(r"https?://(?:docs\.google\.com/forms/d/|forms\.gle/)[^\s]+", text)
            if not gform_match:
                call_tg("sendMessage", {
                    "chat_id": chat_id,
                    "text": "ℹ️ Kirimkan link Google Form yang valid (contoh: `https://forms.gle/...` atau `https://docs.google.com/forms/d/e/.../viewform`)",
                    "parse_mode": "Markdown"
                })
                return

            form_url = gform_match.group(0)
            loading_res = call_tg("sendMessage", {
                "chat_id": chat_id,
                "text": "🔍 *Menganalisis Google Form di Cloud...*",
                "parse_mode": "Markdown"
            })
            loading_msg_id = loading_res.get("result", {}).get("message_id")

            try:
                parser = GoogleFormParser(form_url)
                form_data = parser.fetch_and_parse()

                if not form_data["questions"]:
                    call_tg("editMessageText", {
                        "chat_id": chat_id,
                        "message_id": loading_msg_id,
                        "text": "❌ Form tidak memiliki pertanyaan publik atau membutuhkan login akun Google."
                    })
                    return

                q_summary = []
                for i, q in enumerate(form_data["questions"][:5], 1):
                    q_summary.append(f"{i}. *{q['title']}* (`{q['type']}`)")
                if len(form_data["questions"]) > 5:
                    q_summary.append(f"_...dan {len(form_data['questions']) - 5} pertanyaan lainnya_")

                # Detect File Upload warning
                file_alert = ""
                if form_data.get("has_file_upload"):
                    items_desc = []
                    for it in form_data.get("file_upload_items", []):
                        req_str = "*(Wajib)*" if it.get("required") else "*(Opsional)*"
                        items_desc.append(f"  • 📁 *{it['title']}* {req_str}")
                    file_alert = (
                        "⚠️ *PERINGATAN: MEMERLUKAN INPUT/UPLOAD FILE!* ⚠️\n"
                        "Formulir ini memiliki bagian penting yang meminta unggahan berkas/file:\n"
                        + "\n".join(items_desc) + "\n\n"
                        "ℹ️ _Pemberitahuan: Bagian upload berkas biasanya wajib Anda lakukan sendiri secara manual karena memerlukan file fisik/login Google Drive._\n\n"
                    )

                summary_text = (
                    f"{file_alert}"
                    f"📋 *Form Ditemukan!*\n"
                    f"📌 *Judul:* {form_data['title'] or 'Tanpa Judul'}\n"
                    f"📝 *Pertanyaan:* {len(form_data['questions'])} item\n\n"
                    f"*Daftar Pertanyaan:*\n" + "\n".join(q_summary) + "\n\n"
                    f"👉 *Pilih jumlah responden yang ingin diisi:*"
                )

                fid = form_data["form_id"]
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "5 Orang", "callback_data": f"f:{fid}|c:5"},
                            {"text": "10 Orang", "callback_data": f"f:{fid}|c:10"},
                            {"text": "25 Orang", "callback_data": f"f:{fid}|c:25"}
                        ],
                        [
                            {"text": "50 Orang", "callback_data": f"f:{fid}|c:50"},
                            {"text": "100 Orang", "callback_data": f"f:{fid}|c:100"}
                        ]
                    ]
                }

                call_tg("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": loading_msg_id,
                    "text": summary_text,
                    "reply_markup": keyboard,
                    "parse_mode": "Markdown"
                })

            except Exception as parse_err:
                logger.error(f"Parse error: {parse_err}")
                err_str = str(parse_err)
                if "401" in err_str or "unauthorized" in err_str.lower():
                    err_msg = (
                        "🔒 *FORM MEMERLUKAN LOGIN GOOGLE / TERKUNCI!*\n\n"
                        "Google Form ini tidak dapat diakses publik oleh bot karena:\n"
                        "1. Opsi *'Batasi ke 1 tanggapan'* (perlu login Google) aktif, atau\n"
                        "2. Form dibatasi hanya untuk email organisasi internal tertentu, atau\n"
                        "3. Memiliki pertanyaan Upload File yang mewajibkan login Drive.\n\n"
                        "💡 *Solusi untuk Pemilik Form:*\n"
                        "Buka Google Form ➔ *Setelan (Settings)* ➔ Bagian *Tanggapan (Responses)* ➔ Matikan centang *'Batasi ke 1 tanggapan'* (*Limit to 1 response*)."
                    )
                else:
                    err_msg = (
                        f"❌ *Gagal Membaca Form:*\n`{err_str}`\n\n"
                        "Pastikan link Google Form benar dan dapat diakses secara publik tanpa login."
                    )
                call_tg("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": loading_msg_id,
                    "text": err_msg,
                    "parse_mode": "Markdown"
                })

        # 2. Handle callback query (button clicks)
        elif "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb.get("id")
            chat_id = cb.get("message", {}).get("chat", {}).get("id")
            msg_id = cb.get("message", {}).get("message_id")
            data = cb.get("data", "")

            # Acknowledge click immediately
            call_tg("answerCallbackQuery", {"callback_query_id": cb_id})

            # Format data: f:<form_id>|c:<count>
            if data.startswith("f:") and "|c:" in data:
                parts = data.split("|c:")
                form_id = parts[0].replace("f:", "")
                count = int(parts[1])

                call_tg("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "text": f"⏳ *Menyiapkan & Mengirim {count} respon di Cloud Vercel...*\nMohon tunggu beberapa detik.",
                    "parse_mode": "Markdown"
                })

                try:
                    # Re-fetch form structure
                    view_url = f"https://docs.google.com/forms/d/e/{form_id}/viewform"
                    parser = GoogleFormParser(view_url)
                    form_data = parser.fetch_and_parse()

                    # Generate human-like responses
                    generator = ResponseGenerator()
                    batch_answers = generator.generate_batch(form_data["questions"], count)

                    # Submit fast concurrently
                    page_history = form_data.get("page_history", "0")
                    submitter = FormSubmitter(form_data["response_url"], page_history=page_history)
                    result = submitter.submit_concurrent(batch_answers, max_workers=6)

                    # Update message with completion result
                    call_tg("editMessageText", {
                        "chat_id": chat_id,
                        "message_id": msg_id,
                        "text": (
                            f"🎉 *Pengisian Form Selesai!*\n\n"
                            f"📋 *Form:* {form_data['title']}\n"
                            f"👥 *Total Target:* {result['total']}\n"
                            f"✅ *Berhasil Dikirim:* {result['success']}\n"
                            f"❌ *Gagal:* {result['failed']}\n\n"
                            f"Jawaban berhasil masuk dengan variasi persona & opini alami! 🚀"
                        ),
                        "parse_mode": "Markdown"
                    })

                except Exception as run_err:
                    logger.error(f"Execution error: {run_err}")
                    call_tg("editMessageText", {
                        "chat_id": chat_id,
                        "message_id": msg_id,
                        "text": f"❌ *Terjadi kesalahan saat pengiriman:* {str(run_err)}",
                        "parse_mode": "Markdown"
                    })

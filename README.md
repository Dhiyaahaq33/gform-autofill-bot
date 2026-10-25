# 🤖 Google Form Auto-Filler Telegram Bot

Bot Telegram untuk mengisi Google Form secara otomatis dengan variasi jawaban organik menyerupai respon manusia sungguhan.

## ✨ Fitur Utama
1. **Ekstraksi Otomatis Soal:**
   - Mendukung Pilihan Ganda (Radio Button), Kotak Centang (Checkboxes), Skala Linear (1-5 / 1-10), Dropdown, Isian Singkat, dan Paragraf/Esai.
2. **Variasi Jawaban Alami (Human-like):**
   - Menggunakan distribusi probabilitas wajar untuk pilihan ganda & skala rating.
   - Nama-nama responden Indonesia, email acak yang realistis, domisili, dan nomor telepon.
   - Variasi teks esai/saran (positif, netral, rekomendasi konstruktif).
   - Terintegrasi dengan **Gemini AI** (opsional) untuk hasil narasi yang sangat kaya dan bervariasi.
3. **Aman & Anti-Deteksi:**
   - Rotasi User-Agent (Desktop Chrome, Firefox, Safari iOS, Android).
   - Jeda acak (random delay) antar pengiriman.
4. **Live Progress Bar:**
   - Menampilkan progres pengiriman waktu nyata langsung di chat Telegram.

---

## 🚀 Panduan Setup & Menjalankan Bot

### 1. Dapatkan Token Telegram Bot
1. Buka Telegram, cari akun `@BotFather`.
2. Kirim perintah `/newbot`, lalu ikuti instruksi (beri nama dan username bot).
3. Salin **HTTP API Token** yang diberikan.

### 2. Konfigurasi Token di `.env`
Buka file `.env` di folder proyek ini:
```env
TELEGRAM_BOT_TOKEN=masukkan_token_botfather_disini
GEMINI_API_KEY=masukkan_gemini_api_key_disini_jika_ada
```

### 3. Jalankan Bot
Cukup klik ganda (double click) file:
```
run.bat
```
Atau jalankan via terminal:
```powershell
python bot.py
```

### 4. Penggunaan di Telegram
1. Buka bot kamu di Telegram, lalu ketik `/start`.
2. Kirimkan link Google Form (misal: `https://forms.gle/...` atau `https://docs.google.com/forms/d/e/.../viewform`).
3. Bot akan membaca form dan menampilkan tombol pilihan jumlah responden (`5`, `10`, `25`, `50`, atau ketik kustom).
4. Klik tombol, dan bot akan langsung bekerja mengisi form dengan progress bar real-time!

---

## 🧪 Pengujian Cepat Tanpa Telegram (CLI)
Jika ingin menguji pengisian form langsung dari terminal tanpa membuka Telegram:
```powershell
python test_form.py
```

"""
Skrip pengujian langsung Google Form Auto-Filler via CLI / Terminal.
Bisa dipakai untuk tes tanpa harus buka Telegram.
"""
import sys
from form_parser import GoogleFormParser
from response_generator import ResponseGenerator
from form_submitter import FormSubmitter

def main():
    print("=" * 60)
    print("🧪 GOOGLE FORM AUTO-FILLER (CLI TESTER)")
    print("=" * 60)

    url = input("Masukkan Link Google Form: ").strip()
    if not url:
        print("Link tidak boleh kosong!")
        return

    count_str = input("Mau berapa responden? (default 3): ").strip()
    count = int(count_str) if count_str.isdigit() else 3

    print("\n🔍 Membaca struktur pertanyaan form...")
    parser = GoogleFormParser(url)
    try:
        data = parser.fetch_and_parse()
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    print(f"\n📋 Judul Form : {data['title']}")
    print(f"📝 Pertanyaan : {len(data['questions'])} item")
    for i, q in enumerate(data['questions'], 1):
        choices_info = f" -> {len(q['choices'])} opsi" if q.get('choices') else ""
        print(f"  {i}. {q['title']} [{q['type']}]{choices_info}")

    confirm = input(f"\nLanjutkan mengisi {count} respon? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Dibatalkan.")
        return

    print("\n🧠 Menghasilkan jawaban bervariasi...")
    generator = ResponseGenerator()
    batch = generator.generate_batch(data["questions"], count)

    print("\n🚀 Mulai mengirimkan jawaban...")
    submitter = FormSubmitter(data["response_url"])

    def on_progress(curr, total, ok):
        status = "✅ Sukses" if ok else "❌ Gagal"
        print(f"[{curr}/{total}] {status}")

    result = submitter.submit_batch(batch, min_delay=1.0, max_delay=2.5, progress_callback=on_progress)

    print("\n" + "=" * 60)
    print(f"🎉 Selesai! Berhasil: {result['success']} | Gagal: {result['failed']}")
    print("=" * 60)

if __name__ == "__main__":
    main()

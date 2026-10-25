import os
import random
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

FIRST_NAMES = [
    "Ahmad", "Muhammad", "Rizky", "Dimas", "Budi", "Fajar", "Aditya", "Bayu", "Arif", "Hendra",
    "Siti", "Nur", "Putri", "Dian", "Anisa", "Dewi", "Indah", "Rina", "Tri", "Lestari",
    "Kevin", "Jonathan", "Michael", "Grace", "Jessica", "Vania", "Nadia", "Fikri", "Ilham", "Zul"
]

LAST_NAMES = [
    "Pratama", "Saputra", "Wijaya", "Kusuma", "Santoso", "Hidayat", "Setiawan", "Utomo", "Nugroho",
    "Wibowo", "Ramadhan", "Siregar", "Nasution", "Lubis", "Simanjuntak", "Pangestu", "Gunawan"
]

CITIES = ["Jakarta", "Bogor", "Depok", "Tangerang", "Bekasi", "Bandung", "Surabaya", "Semarang", "Yogyakarta", "Malang"]

# Multi-tone text pools: Casual, Semi-Formal, Baku/Akademik
TEXT_CASUAL = [
    "Wifi sekolah tolong bgt dipercepat min, pas jam istirahat suka ngelag parah.",
    "Colokan di kelas ditambahin dong, laptop suka kehabisan batre pas presentasi.",
    "AC kelas kalo siang kurang dingin euy, tolong diservis ya.",
    "Kantin kursinya tambahin lagi kak, sering bgt ga kebagian tempat duduk.",
    "Toilet cowok tolong airnya diperlancar sama wanginya dijaga biar ga bau.",
    "Udah oke bgt sih fasilitasnya, tinggal perpus aja tambahin novel-novel baru.",
    "Mantep bgt lab komputernya, cuma mouse ada bbrp yg kliknya keras.",
    "Garis lapangan basket dicat ulang dong biar pas main lebih seru.",
    "Bagus kok secara keseluruhan, pertahankan terus yaa!"
]

TEXT_SEMI_FORMAL = [
    "Mohon untuk fasilitas Wi-Fi di area kelas diperkuat jangkauannya agar lancar untuk belajar.",
    "Perlu penambahan stopkontak di setiap sudut ruang kelas demi menunjang pembelajaran digital.",
    "Kondisi pendingin ruangan (AC) di beberapa kelas mohon dicek dan dibersihkan secara berkala.",
    "Area kantin sebaiknya diperluas dan ditambah tempat sampahnya agar lebih higienis.",
    "Kebersihan toilet dan ketersediaan sabun cuci tangan mohon selalu dipantau oleh petugas.",
    "Koleksi buku di perpustakaan sudah cukup lengkap, mungkin bisa ditambah referensi terbitan terbaru.",
    "Fasilitas laboratorium komputer dan IPA sudah baik, mohon pemeliharaan alat tetap konsisten.",
    "Secara umum fasilitas sekolah sudah sangat menunjang kegiatan civitas sekolah, terima kasih."
]

TEXT_BAKU_FORMAL = [
    "Diharapkan pihak sekolah melakukan pemeliharaan rutin terhadap sistem sirkulasi udara dan proyektor di ruang kelas.",
    "Peningkatan kapasitas bandwidth internet sangat penting guna mendukung efektivitas kegiatan belajar mengajar berbasis teknologi.",
    "Penyediaan fasilitas sanitasi yang prima serta pemilahan sampah di area publik sekolah hendaknya terus ditingkatkan.",
    "Manajemen ketertiban area parkir dan sistem keamanan lingkungan sekolah patut diapresiasi, mohon dipertahankan.",
    "Sarana penunjang seperti laboratorium dan perpustakaan telah memenuhi standar memadai untuk menunjang prestasi akademis civitas sekolah."
]

class ResponseGenerator:
    """
    Generates diverse, realistic survey answers for multiple respondents.
    Supports both Gemini Flash AI and intelligent multi-tone heuristic mode.
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.ai_client = None
        if self.api_key:
            try:
                from google import genai
                self.ai_client = genai.Client(api_key=self.api_key)
                logger.info("Gemini AI Client initialized successfully.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client: {e}")

    def generate_batch(self, questions: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Generate answers for `count` respondents.
        """
        if self.ai_client and count <= 30:
            try:
                ai_results = self._generate_with_gemini(questions, count)
                if ai_results and len(ai_results) == count:
                    return ai_results
            except Exception as e:
                logger.warning(f"AI generation failed, falling back to smart heuristics: {e}")

        # Smart Heuristic Generation
        return [self._generate_single_heuristic(questions, i) for i in range(count)]

    def _generate_with_gemini(self, questions: List[Dict[str, Any]], count: int) -> Optional[List[Dict[str, Any]]]:
        prompt = (
            f"Kamu adalah AI yang bertugas menyimulasikan data survei Google Form dari {count} orang responden yang berbeda-beda di Indonesia.\n"
            "Karakteristik responden harus beraneka ragam (siswa santai, guru formal, staf, orang tua murid).\n"
            "Jawabannya harus tampak alami layaknya manusia asli yang mengisi form:\n"
            "- Ada yang menjawab santai (ga, bgt, klo, min, kak), ada yang sopan umum, ada yang memakai bahasa baku formal.\n"
            "- Untuk pilihan ganda/skala/grid matriks, variasikan pilihannya sesuai distribusi umum (jangan seragam!).\n\n"
            "Berikut daftar pertanyaan form:\n"
        )

        for q in questions:
            prompt += f"- ID: {q['entry_id']} | Tipe: {q['type']} | Pertanyaan: \"{q['title']}\""
            if q.get('choices'):
                prompt += f" | Pilihan: {json.dumps(q['choices'], ensure_ascii=False)}"
            prompt += "\n"

        prompt += (
            f"\nBerikan output HANYA dalam format JSON valid (array of {count} objects). "
            "Setiap object berisi key ID entry (contoh: \"entry.123456\") dan value berupa array string jawabannya.\n"
        )

        response = self.ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )

        content = response.text.strip()
        data = json.loads(content)
        if isinstance(data, list):
            return data
        return None

    def _generate_single_heuristic(self, questions: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
        persona_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        persona_age = random.randint(16, 45)
        persona_city = random.choice(CITIES)

        # Tone distribution: 40% casual, 40% semi-formal, 20% baku
        tone = random.choices(["casual", "semi", "baku"], weights=[0.4, 0.4, 0.2])[0]
        if tone == "casual":
            text_pool = TEXT_CASUAL
        elif tone == "semi":
            text_pool = TEXT_SEMI_FORMAL
        else:
            text_pool = TEXT_BAKU_FORMAL

        submission_data = {}

        for q in questions:
            entry_id = q["entry_id"]
            q_type = q["type"]
            choices = q.get("choices", [])
            title_lower = q["title"].lower()

            # Multiple choice, Dropdown, Grid, or Linear Scale
            if q_type in ["multiple_choice", "dropdown", "grid", "linear_scale"]:
                if choices:
                    # Bell-curve style weighting towards positive/middle
                    n = len(choices)
                    if n == 5: # e.g. 1 to 5 scale
                        weights = [0.05, 0.12, 0.35, 0.33, 0.15]
                    elif n == 4:
                        weights = [0.15, 0.35, 0.35, 0.15]
                    elif n == 3:
                        weights = [0.25, 0.50, 0.25]
                    else:
                        weights = [1.0] * n
                    
                    choice = random.choices(choices, weights=weights[:n])[0]
                    submission_data[entry_id] = [choice]
                else:
                    submission_data[entry_id] = ["Pilihan 1"]

            elif q_type == "checkboxes":
                if choices:
                    # Realistic multi-select: pick 2 to 3 choices
                    k = min(len(choices), random.choices([2, 3, 1], weights=[0.5, 0.4, 0.1])[0])
                    submission_data[entry_id] = random.sample(choices, k)
                else:
                    submission_data[entry_id] = ["Pilihan 1"]

            elif q_type in ["short_answer", "paragraph"]:
                if any(w in title_lower for w in ["nama", "name"]):
                    submission_data[entry_id] = [persona_name]
                elif any(w in title_lower for w in ["email", "e-mail"]):
                    clean_name = persona_name.lower().replace(" ", ".")
                    submission_data[entry_id] = [f"{clean_name}{random.randint(10, 99)}@gmail.com"]
                elif any(w in title_lower for w in ["umur", "usia", "age"]):
                    submission_data[entry_id] = [str(persona_age)]
                elif any(w in title_lower for w in ["kota", "asal", "domisili", "alamat"]):
                    submission_data[entry_id] = [persona_city]
                elif any(w in title_lower for w in ["hp", "telepon", "wa", "whatsapp", "phone", "no"]):
                    submission_data[entry_id] = [f"08{random.choice(['12', '13', '21', '57', '78'])}{random.randint(10000000, 99999999)}"]
                elif any(w in title_lower for w in ["saran", "kritik", "usulan", "aspirasi", "masukan", "evaluasi"]):
                    # 85% give feedback, 15% skip or very brief
                    if random.random() < 0.85:
                        submission_data[entry_id] = [random.choice(text_pool)]
                    else:
                        submission_data[entry_id] = ["Sudah cukup baik."]
                elif any(w in title_lower for w in ["alasan", "pendapat", "kesan", "pesan"]):
                    submission_data[entry_id] = [random.choice(text_pool)]
                else:
                    # General open-ended input
                    submission_data[entry_id] = [random.choice(text_pool)]

            else:
                submission_data[entry_id] = ["Sesuai"]

        return submission_data

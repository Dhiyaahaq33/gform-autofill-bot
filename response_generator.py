import os
import random
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

FIRST_NAMES = [
    "Ahmad", "Muhammad", "Rizky", "Dimas", "Budi", "Fajar", "Aditya", "Bayu", "Arif", "Hendra",
    "Siti", "Nur", "Putri", "Dian", "Anisa", "Dewi", "Indah", "Rina", "Tri", "Lestari",
    "Kevin", "Jonathan", "Michael", "Grace", "Jessica", "Vania", "Nadia", "Fikri", "Ilham", "Zul",
    "Wahyu", "Bambang", "Agus", "Danang", "Taufik", "Citra", "Mega", "Sari", "Tiara", "Farhan"
]

LAST_NAMES = [
    "Pratama", "Saputra", "Wijaya", "Kusuma", "Santoso", "Hidayat", "Setiawan", "Utomo", "Nugroho",
    "Wibowo", "Ramadhan", "Siregar", "Nasution", "Lubis", "Simanjuntak", "Pangestu", "Gunawan",
    "Firmansyah", "Permana", "Kurniawan", "Suryono", "Handayani", "Maulana", "Arifin"
]

CITIES = [
    "Jakarta Selatan", "Jakarta Pusat", "Jakarta Barat", "Bogor", "Depok", "Tangerang", "Bekasi",
    "Bandung", "Surabaya", "Semarang", "Yogyakarta", "Malang", "Surakarta (Solo)", "Medan",
    "Palembang", "Makassar", "Denpasar", "Bandar Lampung", "Padang", "Pekanbaru"
]

INSTITUTIONS = [
    "Universitas Indonesia", "Institut Pertanian Bogor (IPB)", "Institut Teknologi Bandung (ITB)",
    "Universitas Gadjah Mada (UGM)", "Universitas Padjadjaran (Unpad)", "Universitas Diponegoro (Undip)",
    "Universitas Brawijaya (UB)", "Universitas Airlangga (Unair)", "PT Swasta Nasional",
    "Instansi Pemerintah", "Perusahaan Ritel", "Startup Teknologi", "Karyawan Swasta", "Wirausaha Mandiri"
]

# Universal feedback pools across multiple domains & tones
FEEDBACK_CASUAL = [
    "Secara keseluruhan udah mantap bgt min, paling kedepannya koneksi/aksesnya bisa lebih distabilin lagi ya.",
    "Bagus kok acaranya/layanannya, materinya dapet bgt. Cuma waktunya agak mepet aja tadi pas sesi akhir.",
    "Udah oke bgt sih, puas pkknya. Tingkatkan terus yaa!",
    "Bagus bgt, penjelasannya gampang dipahami. Semoga sering-sering diadain lagi yang kayak gini.",
    "Pelayanannya ramah dan cepet, ga ribet sama sekali. Pertahankan ya!",
    "Overall oke, cuma sound/mic pas penjelasan tadi sempet agak mendem sedikit.",
    "Keren bgt, sangat membantu buat nambah wawasan dan skill baru.",
    "Udah cukup baik, ga ada keluhan yg berarti kok. Sukses selalu tim panitia/pengelola!",
    "Materi dan fasilitasnya oke, paling kapasitas ruangan/tempatnya aja yg diperluas biar ga terlalu padet."
]

FEEDBACK_SEMI_FORMAL = [
    "Kegiatan dan pelayanannya sudah sangat baik serta informatif. Semoga ke depan dapat diselenggarakan secara berkala.",
    "Secara umum sudah memenuhi ekspektasi. Mohon koordinasi waktu pelaksanaan lebih diperhatikan agar tidak molor.",
    "Materi yang disampaikan sangat aplikatif dan bermanfaat. Fasilitas pendukung juga sudah cukup memadai.",
    "Proses registrasi dan layanannya sangat responsif. Terima kasih kepada seluruh tim yang bertugas.",
    "Fasilitas dan penyampaian sudah baik, mungkin ke depan sesi tanya jawab atau diskusi interaktif bisa ditambah durasinya.",
    "Sudah sangat memuaskan, semoga evaluasi ini bisa menjadi bahan perbaikan untuk program selanjutnya.",
    "Pelayanan ramah dan tempat cukup nyaman. Tingkatkan terus kualitas layanannya."
]

FEEDBACK_BAKU_FORMAL = [
    "Secara komprehensif, pelaksanaan program dan penyediaan sarana telah berjalan dengan optimal dan tertib.",
    "Diharapkan pihak penyelenggara/pengelola senantiasa menjaga konsistensi mutu pelayanan serta meningkatkan aspek teknis pendukung.",
    "Materi serta substansi yang disajikan memiliki relevansi tinggi dan sangat menunjang pengembangan kompetensi peserta.",
    "Manajemen operasional serta alur kegiatan telah terlaksana secara sistematis dan patut diapresiasi.",
    "Rekomendasi dari kami adalah optimalisasi fasilitas penunjang dan penyesuaian alokasi waktu guna mencapai hasil yang lebih maksimal."
]

REASONS_CASUAL = [
    "Pengen nambah ilmu baru dan memperluas relasi sama temen-temen baru.",
    "Tertarik bgt sama topik bahasannya karena relevan sama apa yg lagi saya pelajari sekarang.",
    "Rekomendasi dari temen, dan pas dicoba ternyata emang seru dan bermanfaat bgt.",
    "Buat ngisi waktu luang dengan hal positif sekaligus ningkatin skill diri.",
    "Suka sama programnya yang terstruktur dan ga bertele-tele."
]

REASONS_SEMI_FORMAL = [
    "Untuk memperdalam pemahaman di bidang ini guna menunjang perkuliahan dan karier ke depan.",
    "Karena materi dan program yang ditawarkan sangat relevan dengan kebutuhan praktis saat ini.",
    "Mencari pengalaman baru serta memperluas jejaring profesional dengan sesama praktisi/peserta.",
    "Ingin mendapatkan sertifikasi serta bimbingan langsung dari pemateri yang berpengalaman."
]

REASONS_BAKU_FORMAL = [
    "Guna meningkatkan kapabilitas akademis serta profesionalisme dalam bidang yang ditekuni.",
    "Substansi yang ditawarkan memiliki korelasi signifikan dengan rencana riset dan pengembangan karier jangka panjang.",
    "Sebagai sarana pengembangan kompetensi terstandar yang diakui secara institusional."
]

class ResponseGenerator:
    """
    Universal AI & Smart-Heuristic Survey Response Generator.
    Works dynamically for ANY topic (Academic, Customer Service, HR/Job, Event, Health, etc.)
    and ANY question type (Multiple choice, Dropdown, Linear scale, Grid, Checkboxes, Text, Dates).
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.ai_client = None
        if self.api_key:
            try:
                from google import genai
                self.ai_client = genai.Client(api_key=self.api_key)
                logger.info("Gemini AI Client initialized.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client: {e}")

    def generate_batch(self, questions: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Generate answers for `count` respondents.
        """
        if self.ai_client and count <= 35:
            try:
                ai_results = self._generate_with_gemini(questions, count)
                if ai_results and len(ai_results) == count:
                    return ai_results
            except Exception as e:
                logger.warning(f"AI generation fallback to universal heuristics: {e}")

        # Universal Intelligent Heuristic
        return [self._generate_single_heuristic(questions, i) for i in range(count)]

    def _generate_with_gemini(self, questions: List[Dict[str, Any]], count: int) -> Optional[List[Dict[str, Any]]]:
        """
        Universal Gemini prompt that adapts dynamically to the form's actual subject matter.
        """
        prompt = (
            f"Kamu adalah AI simulator tanggapan survei Google Form dari {count} orang responden unik di Indonesia.\n"
            "TUGAS KAMU:\n"
            "1. Analisis konteks dan topik dari daftar pertanyaan berikut (apakah survei sekolah, evaluasi acara, riset skripsi, kepuasan pelanggan, formulir pendaftaran, dll).\n"
            "2. Hasilkan profil dan sudut pandang responden yang beragam, logis, dan masuk akal sesuai konteks topik form tersebut.\n"
            "3. Jawaban esai/teks harus beragam variasinya: sebagian santai berbahasa percakapan (singkatan wajar: yg, bgt, ga, oke), sebagian sopan umum, dan sebagian berbahasa baku formal.\n"
            "4. Untuk pilihan ganda, skala 1-5, dan kisi matriks (grid), berikan variasi distribusi yang wajar layaknya kurva normal statistik (jangan seragam atau selalu memilih opsi pertama).\n"
            "5. Untuk checkboxes, pilih 1 hingga 3 opsi yang logis.\n\n"
            "Daftar pertanyaan form:\n"
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
        """
        Universal Intelligent Heuristic Generator: detects semantic intent from question title
        and maps choices dynamically from the form's options.
        """
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        clean_name = f"{first_name.lower()}.{last_name.lower()}"
        age = random.randint(18, 48)
        city = random.choice(CITIES)
        institution = random.choice(INSTITUTIONS)
        phone = f"08{random.choice(['12', '13', '21', '57', '78', '96'])}{random.randint(10000000, 99999999)}"
        email_domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "mail.ugm.ac.id", "apps.ipb.ac.id"])
        email = f"{clean_name}{random.randint(10, 99)}@{email_domain}"

        # Personality tone for this respondent (40% casual, 40% semi-formal, 20% baku)
        tone = random.choices(["casual", "semi", "baku"], weights=[0.4, 0.4, 0.2])[0]
        if tone == "casual":
            feedback_pool = FEEDBACK_CASUAL
            reason_pool = REASONS_CASUAL
        elif tone == "semi":
            feedback_pool = FEEDBACK_SEMI_FORMAL
            reason_pool = REASONS_SEMI_FORMAL
        else:
            feedback_pool = FEEDBACK_BAKU_FORMAL
            reason_pool = REASONS_BAKU_FORMAL

        submission = {}

        for q in questions:
            entry_id = q["entry_id"]
            q_type = q["type"]
            choices = q.get("choices", [])
            title_lower = q["title"].lower()

            # 1. Pilihan Ganda, Dropdown, Skala Linier, & Kisi Matriks (Grid)
            if q_type in ["multiple_choice", "dropdown", "linear_scale", "grid"]:
                if choices:
                    n = len(choices)
                    # Natural bell-curve statistical weighting
                    if n == 5:
                        weights = [0.04, 0.12, 0.36, 0.34, 0.14]
                    elif n == 4:
                        weights = [0.12, 0.38, 0.38, 0.12]
                    elif n == 3:
                        weights = [0.20, 0.55, 0.25]
                    elif n == 2: # Yes/No or Gender
                        weights = [0.52, 0.48]
                    else:
                        weights = [1.0] * n
                    
                    choice = random.choices(choices, weights=weights[:n])[0]
                    submission[entry_id] = [choice]
                else:
                    submission[entry_id] = ["Sesuai"]

            # 2. Kotak Centang / Checkboxes (Multi-select)
            elif q_type == "checkboxes":
                if choices:
                    # Pick 1, 2, or 3 options naturally
                    k = min(len(choices), random.choices([2, 3, 1], weights=[0.45, 0.40, 0.15])[0])
                    submission[entry_id] = random.sample(choices, k)
                else:
                    submission[entry_id] = ["Pilihan 1"]

            # 3. Tanggal (Date)
            elif q_type == "date" or any(w in title_lower for w in ["tanggal", "tgl", "date", "lahir"]):
                if "lahir" in title_lower or "birth" in title_lower:
                    birth_year = 2024 - age
                    submission[entry_id] = [f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"]
                else:
                    # Recent event date
                    submission[entry_id] = [f"2024-{random.randint(5,11):02d}-{random.randint(1,28):02d}"]

            # 4. Waktu (Time)
            elif q_type == "time" or any(w in title_lower for w in ["jam", "waktu", "time"]):
                submission[entry_id] = [f"{random.randint(8,16):02d}:{random.choice(['00', '15', '30', '45'])}"]

            # 5. Isian Singkat & Paragraf / Esai (Semantic Intent Matching)
            elif q_type in ["short_answer", "paragraph"]:
                # Identity & Contact fields
                if any(w in title_lower for w in ["nama", "name", "lengkap"]):
                    submission[entry_id] = [full_name]
                elif any(w in title_lower for w in ["email", "e-mail", "surel"]):
                    submission[entry_id] = [email]
                elif any(w in title_lower for w in ["hp", "telepon", "wa", "whatsapp", "phone", "no.", "kontak"]):
                    submission[entry_id] = [phone]
                elif any(w in title_lower for w in ["umur", "usia", "age"]):
                    submission[entry_id] = [str(age)]
                elif any(w in title_lower for w in ["kota", "asal", "domisili", "alamat", "kabupaten"]):
                    submission[entry_id] = [city]
                elif any(w in title_lower for w in ["institusi", "instansi", "kampus", "universitas", "sekolah", "organisasi", "perusahaan", "kantor"]):
                    submission[entry_id] = [institution]
                elif any(w in title_lower for w in ["nim", "npm", "nrp", "nis", "nisn", "student id"]):
                    submission[entry_id] = [f"G{random.randint(1,9)}{random.randint(4000000, 4999999)}"]
                elif any(w in title_lower for w in ["pekerjaan", "profesi", "jabatan"]):
                    submission[entry_id] = [random.choice(["Mahasiswa", "Karyawan Swasta", "Wirausaha", "Guru / Pendidik", "Staf Administrasi"])]

                # Narrative & Open feedback fields
                elif any(w in title_lower for w in ["saran", "kritik", "masukan", "usulan", "evaluasi", "rekomendasi", "perbaikan", "aspirasi"]):
                    # 85% provide insightful feedback, 15% concise
                    if random.random() < 0.85:
                        submission[entry_id] = [random.choice(feedback_pool)]
                    else:
                        submission[entry_id] = ["Sudah sangat baik dan memuaskan."]
                elif any(w in title_lower for w in ["alasan", "motivasi", "tujuan", "harapan", "ekspektasi"]):
                    submission[entry_id] = [random.choice(reason_pool)]
                elif any(w in title_lower for w in ["kendala", "masalah", "hambatan", "kesulitan"]):
                    submission[entry_id] = [random.choice([
                        "Koneksi jaringan internet yang terkadang kurang stabil.",
                        "Waktu pengerjaan atau durasi yang dirasa cukup padat.",
                        "Secara umum tidak ada kendala yang berarti, semua berjalan lancar."
                    ])]
                else:
                    # General open-ended input
                    if q_type == "paragraph":
                        submission[entry_id] = [random.choice(feedback_pool)]
                    else:
                        submission[entry_id] = [random.choice(["Sangat memuaskan", "Sesuai kebutuhan", "Cukup jelas", "Bagus dan terstruktur", "Sangat informatif"])]

            else:
                submission[entry_id] = ["Sesuai"]

        return submission

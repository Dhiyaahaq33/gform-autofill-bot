import os
import random
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Common Indonesian names & mock pools for heuristic generation
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

FEEDBACK_TEMPLATES_POSITIVE = [
    "Sudah sangat bagus dan informatif.",
    "Bagus banget, sangat membantu saya memahami materinya.",
    "Secara keseluruhan sudah oke bgt, pertahankan yaa.",
    "Pelayanan dan materinya memuaskan sekali.",
    "Keren, materi tersampaikan dengan jelas.",
    "Mantap, semoga ke depannya bisa lebih banyak event/program seperti ini.",
    "Udah oke bgt, ga ada keluhan.",
    "Sangat memuaskan dan aplikatif di kehidupan sehari-hari."
]

FEEDBACK_TEMPLATES_NEUTRAL = [
    "Cukup baik, sudah sesuai ekspektasi.",
    "Lumayan oke, tapi mungkin durasinya bisa diperpanjang.",
    "Bagus, hanya saja penyampaiannya agak terlalu cepat.",
    "Sudah cukup memadai.",
    "Biasa saja sih, overall standar dan aman.",
    "Oke kok, tinggal ditingkatkan lagi ke depannya."
]

FEEDBACK_TEMPLATES_SUGGESTION = [
    "Mohon untuk audio/sound diperbaiki lagi agar lebih jernih.",
    "Mungkin bisa ditambah sesi tanya jawab atau praktiknya.",
    "Bahan presentasinya semoga bisa dibagikan setelah acara selesai.",
    "Waktunya kalau bisa jangan terlalu mepet ya.",
    "Tolong materi studi kasusnya diperbanyak lagi biar lebih paham.",
    "Ditingkatkan lagi komunikasi dan koordinasi panitianya."
]

class ResponseGenerator:
    """
    Generates diverse, realistic survey answers for multiple respondents.
    Supports both Gemini Flash AI and intelligent heuristic mode.
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
        Returns a list of dicts, each mapping `entry_id` -> list of selected/written values.
        """
        if self.ai_client and count <= 30:
            # Try AI generation for rich context if respondent count is reasonable
            try:
                ai_results = self._generate_with_gemini(questions, count)
                if ai_results and len(ai_results) == count:
                    return ai_results
            except Exception as e:
                logger.warning(f"AI generation failed, falling back to smart heuristics: {e}")

        # Smart Heuristic Generation
        return [self._generate_single_heuristic(questions, i) for i in range(count)]

    def _generate_with_gemini(self, questions: List[Dict[str, Any]], count: int) -> Optional[List[Dict[str, Any]]]:
        """
        Use Gemini Flash to produce realistic, varied human responses.
        """
        prompt = (
            f"Kamu adalah AI yang bertugas menyimulasikan data survei Google Form dari {count} orang responden yang berbeda-beda di Indonesia.\n"
            "Karakteristik responden harus beraneka ragam (mahasiswa, pekerja, bapak-bapak, anak muda santai, formal).\n"
            "Jawabannya harus tampak alami layaknya manusia asli yang mengisi form:\n"
            "- Ada yang menjawab singkat padat, ada yang santai memakai singkatan umum (yg, bgt, ga, oke), ada yang formal dan lengkap.\n"
            "- Untuk pilihan ganda/skala, variasikan pilihannya sesuai distribusi umum (jangan semuanya memilih opsi pertama/tertinggi).\n\n"
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
            "Contoh struktur JSON:\n"
            "[\n"
            "  {\n"
            "    \"entry.12345\": [\"Pilihan A\"],\n"
            "    \"entry.67890\": [\"Saran saya durasinya ditambah\"]\n"
            "  }\n"
            "]"
        )

        response = self.ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        content = response.text.strip()
        data = json.loads(content)
        if isinstance(data, list):
            return data
        return None

    def _generate_single_heuristic(self, questions: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
        """
        Smart Heuristic generator when AI is unavailable or for large bulk batches.
        """
        persona_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        persona_age = random.randint(19, 35)
        persona_city = random.choice(CITIES)

        submission_data = {}

        for q in questions:
            entry_id = q["entry_id"]
            q_type = q["type"]
            choices = q.get("choices", [])
            title_lower = q["title"].lower()

            if q_type == "multiple_choice" or q_type == "dropdown":
                if choices:
                    # Realistic weighted distribution: slight preference to middle/positive, but naturally scattered
                    weights = [1.0] * len(choices)
                    if len(choices) >= 3:
                        # give higher weight to first 2-3 options
                        weights[0] = 1.8
                        weights[1] = 2.2
                    choice = random.choices(choices, weights=weights[:len(choices)])[0]
                    submission_data[entry_id] = [choice]
                else:
                    submission_data[entry_id] = ["Ya"]

            elif q_type == "checkboxes":
                if choices:
                    # Pick 1 to 2 random choices
                    k = min(len(choices), random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0])
                    submission_data[entry_id] = random.sample(choices, k)
                else:
                    submission_data[entry_id] = ["Pilihan 1"]

            elif q_type == "linear_scale":
                if choices:
                    # Linear scale usually 1 to 5: realistic human distribution skewed to 4 & 5
                    scale_weights = []
                    for i, _ in enumerate(choices):
                        pos = i + 1
                        if pos in [4, 5]:
                            scale_weights.append(3.5)
                        elif pos == 3:
                            scale_weights.append(2.0)
                        else:
                            scale_weights.append(0.8)
                    choice = random.choices(choices, weights=scale_weights[:len(choices)])[0]
                    submission_data[entry_id] = [choice]
                else:
                    submission_data[entry_id] = ["4"]

            elif q_type in ["short_answer", "paragraph"]:
                # Match title intent
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
                elif any(w in title_lower for w in ["nim", "npm", "nrp", "student id"]):
                    submission_data[entry_id] = [f"G{random.randint(1, 9)}{random.randint(4000000, 4999999)}"]
                elif any(w in title_lower for w in ["saran", "masukan", "evaluasi", "kritik"]):
                    pool = random.choices([FEEDBACK_TEMPLATES_POSITIVE, FEEDBACK_TEMPLATES_SUGGESTION], weights=[0.4, 0.6])[0]
                    submission_data[entry_id] = [random.choice(pool)]
                elif any(w in title_lower for w in ["alasan", "pendapat", "kesan", "pesan"]):
                    pool = random.choices([FEEDBACK_TEMPLATES_POSITIVE, FEEDBACK_TEMPLATES_NEUTRAL], weights=[0.7, 0.3])[0]
                    submission_data[entry_id] = [random.choice(pool)]
                else:
                    # General open-ended answer
                    if q_type == "paragraph":
                        submission_data[entry_id] = [random.choice(FEEDBACK_TEMPLATES_POSITIVE + FEEDBACK_TEMPLATES_NEUTRAL)]
                    else:
                        submission_data[entry_id] = [random.choice(["Sudah baik", "Sesuai kebutuhan", "Memuaskan", "Cukup jelas", "Bagus"])]

            else:
                # Fallback for generic inputs
                submission_data[entry_id] = ["Sesuai"]

        return submission_data

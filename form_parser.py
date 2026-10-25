import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class GoogleFormParser:
    """
    Parses Google Forms to extract form metadata, question titles, entry IDs,
    question types, and available options.
    """
    
    QUESTION_TYPES = {
        0: "short_answer",
        1: "paragraph",
        2: "multiple_choice",
        3: "dropdown",
        4: "checkboxes",
        5: "linear_scale",
        7: "grid",
        9: "date",
        10: "time"
    }

    def __init__(self, form_url: str):
        self.raw_url = form_url.strip()
        self.form_id = self._extract_form_id(self.raw_url)
        self.view_url = f"https://docs.google.com/forms/d/e/{self.form_id}/viewform" if self.form_id else self.raw_url
        self.response_url = f"https://docs.google.com/forms/d/e/{self.form_id}/formResponse" if self.form_id else ""
        self.title = ""
        self.description = ""
        self.questions: List[Dict[str, Any]] = []

    def _extract_form_id(self, url: str) -> Optional[str]:
        # Formats:
        # https://docs.google.com/forms/d/e/1FAIpQLSc.../viewform
        # https://docs.google.com/forms/d/1FAIpQLSc.../viewform
        # https://forms.gle/...
        match = re.search(r"/forms/d/(?:e/)?([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
        return None

    def fetch_and_parse(self, session: Optional[requests.Session] = None) -> Dict[str, Any]:
        s = session or requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Follow redirects in case it's forms.gle
        resp = s.get(self.raw_url, headers=headers, allow_redirects=True, timeout=15)
        resp.raise_for_status()

        final_url = resp.url
        form_id_match = re.search(r"/forms/d/(?:e/)?([a-zA-Z0-9_-]+)", final_url)
        if form_id_match:
            self.form_id = form_id_match.group(1)
            self.view_url = f"https://docs.google.com/forms/d/e/{self.form_id}/viewform"
            self.response_url = f"https://docs.google.com/forms/d/e/{self.form_id}/formResponse"

        html_content = resp.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract Form Title & Description from meta or title tag
        page_title = soup.find("title")
        if page_title and page_title.text:
            self.title = page_title.text.replace(" - Google Forms", "").strip()

        # Extract FB_PUBLIC_LOAD_DATA_
        # Pattern: var FB_PUBLIC_LOAD_DATA_ = [...];
        match = re.search(r"var FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);\s*</script>", html_content, re.DOTALL)
        if not match:
            # Alternate search pattern
            match = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);\s*;", html_content, re.DOTALL)
            
        if not match:
            raise ValueError("Gagal membaca struktur Google Form. Pastikan link dapat diakses publik tanpa login.")

        try:
            data = json.loads(match.group(1))
        except Exception as e:
            raise ValueError(f"Gagal mem-parsing metadata JSON dari Google Form: {e}")

        # Extract form title & description from data array if available
        if len(data) > 1 and data[1]:
            if len(data[1]) > 8 and data[1][8]:
                self.title = data[1][8] or self.title
            if len(data[1]) > 0 and isinstance(data[1][0], str) and data[1][0]:
                self.description = data[1][0]

        # Questions array is usually at data[1][1]
        raw_items = []
        if len(data) > 1 and len(data[1]) > 1 and isinstance(data[1][1], list):
            raw_items = data[1][1]

        self.questions = []
        page_count = 0
        for item in raw_items:
            if not isinstance(item, list) or len(item) < 4:
                continue

            q_title = item[1]
            q_desc = item[2] if len(item) > 2 else ""
            q_type_code = item[3] if len(item) > 3 else 0
            q_type_name = self.QUESTION_TYPES.get(q_type_code, "other")

            # Check if this item is a Page Break (Section header)
            if q_type_code == 8:
                page_count += 1
                continue

            # Check for entry details in item[4]
            if len(item) > 4 and isinstance(item[4], list) and len(item[4]) > 0:
                for entry_info in item[4]:
                    if not isinstance(entry_info, list) or len(entry_info) == 0:
                        continue
                    entry_id = entry_info[0]
                    choices = []
                    # Choices in entry_info[1]
                    if len(entry_info) > 1 and isinstance(entry_info[1], list):
                        for c in entry_info[1]:
                            if isinstance(c, list) and len(c) > 0 and c[0] is not None:
                                choices.append(str(c[0]))
                    
                    is_required = bool(entry_info[2]) if len(entry_info) > 2 else False

                    # For grid questions (type 7), include specific row label if present
                    row_title = q_title
                    if q_type_code == 7 and len(entry_info) > 3 and isinstance(entry_info[3], list) and entry_info[3]:
                        row_title = f"{q_title} [{entry_info[3][0]}]"

                    self.questions.append({
                        "entry_id": f"entry.{entry_id}",
                        "title": row_title,
                        "description": q_desc,
                        "type": q_type_name,
                        "type_code": q_type_code,
                        "choices": choices,
                        "required": is_required
                    })

        # Calculate pageHistory string: e.g. "0,1,2,3,4,5" if 5 page breaks exist
        page_history = ",".join(str(p) for p in range(page_count + 1))

        return {
            "form_id": self.form_id,
            "title": self.title,
            "description": self.description,
            "view_url": self.view_url,
            "response_url": self.response_url,
            "page_history": page_history,
            "questions": self.questions
        }

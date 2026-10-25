import time
import random
import logging
import requests
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0 Safari/537.36"
]

class FormSubmitter:
    """
    Submits generated answers to Google Form response endpoint
    with human-like headers, randomized delays, and status callbacks.
    """

    def __init__(self, response_url: str):
        self.response_url = response_url

    def submit_single(self, submission_dict: Dict[str, List[str]], session: Optional[requests.Session] = None) -> bool:
        """
        Submits one respondent data.
        submission_dict is { "entry.XXXX": ["val1", "val2"] }
        """
        s = session or requests.Session()
        ua = random.choice(USER_AGENTS)

        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": self.response_url.replace("formResponse", "viewform"),
            "Origin": "https://docs.google.com",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Convert dictionary to list of tuples to support repeated keys (e.g. checkboxes)
        payload = []
        for entry_id, values in submission_dict.items():
            for val in values:
                payload.append((entry_id, val))

        # Standard Google Form hidden tokens
        payload.append(("fvv", "1"))
        payload.append(("draftResponse", "[]"))
        payload.append(("pageHistory", "0"))
        payload.append(("fbzx", str(random.randint(1000000000000000000, 9999999999999999999))))

        try:
            resp = s.post(self.response_url, data=payload, headers=headers, timeout=15)
            # Google Form returns 200 on successful submission
            if resp.status_code == 200:
                return True
            else:
                logger.warning(f"Submission returned status {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error submitting form: {e}")
            return False

    def submit_batch(
        self,
        batch_data: List[Dict[str, List[str]]],
        min_delay: float = 1.2,
        max_delay: float = 3.0,
        progress_callback: Optional[Callable[[int, int, bool], None]] = None
    ) -> Dict[str, int]:
        """
        Submits batch of respondents sequentially with human delay.
        Calls progress_callback(current_index, total_count, is_success) after each submission.
        """
        total = len(batch_data)
        success_count = 0
        fail_count = 0

        session = requests.Session()

        for idx, submission in enumerate(batch_data, 1):
            is_success = self.submit_single(submission, session=session)
            if is_success:
                success_count += 1
            else:
                fail_count += 1

            if progress_callback:
                try:
                    progress_callback(idx, total, is_success)
                except Exception as cb_err:
                    logger.warning(f"Callback error: {cb_err}")

            # Realistic human delay between answers
            if idx < total:
                delay = random.uniform(min_delay, max_delay)
                time.sleep(delay)

        return {
            "total": total,
            "success": success_count,
            "failed": fail_count
        }

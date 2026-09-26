from __future__ import annotations

from typing import List, Tuple


def validate_body(body: str, taboo_words: List[str]) -> Tuple[bool, str]:
    if not body or not body.strip():
        return False, "empty_body"
    if "http://" in body.lower() or "https://" in body.lower():
        return False, "url_in_body"
    lowered = body.lower()
    for word in taboo_words:
        if word.lower() in lowered:
            return False, f"taboo_word:{word}"
    if len(body) > 700:
        return False, "body_too_long"
    return True, "ok"
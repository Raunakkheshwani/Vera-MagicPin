"""
In-memory tracking for Attention/Fatigue, Trigger Arbitration,
Message Evolution, and the reply/auto-reply engine.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional, Set, Tuple


class EngagementStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._send_times: Dict[str, List[float]] = {}
        self._used_suppression_keys: Set[str] = set()
        self._conversation_history: Dict[str, List[str]] = {}
        self._auto_reply_count: Dict[str, int] = {}
        self._ended_conversations: Set[str] = set()
        self._open_session: Set[str] = set()
        self._last_opportunity: Dict[str, Dict] = {}                  # conversation_id -> context
        self._attempt_count: Dict[Tuple[str, str], int] = {}          # (merchant_id, family) -> count

    # --- suppression / dedupe -------------------------------------------------
    def already_sent(self, suppression_key: str) -> bool:
        with self._lock:
            return suppression_key in self._used_suppression_keys

    def mark_sent(self, suppression_key: str) -> None:
        with self._lock:
            self._used_suppression_keys.add(suppression_key)

    # --- fatigue ----------------------------------------------------------------
    def record_send(self, merchant_id: str) -> None:
        with self._lock:
            self._send_times.setdefault(merchant_id, []).append(time.time())

    def fatigue_for(self, merchant_id: str, window_seconds: int = 86400, cap: int = 3) -> float:
        with self._lock:
            now = time.time()
            recent = [t for t in self._send_times.get(merchant_id, []) if now - t <= window_seconds]
            self._send_times[merchant_id] = recent
            return min(1.0, len(recent) / cap)

    # --- conversation / repeat / auto-reply -------------------------------------
    def record_outbound(self, conversation_id: str, body: str) -> None:
        with self._lock:
            self._conversation_history.setdefault(conversation_id, []).append(body)
            self._open_session.add(conversation_id)

    def has_repeated_body(self, conversation_id: str, body: str) -> bool:
        with self._lock:
            return body in self._conversation_history.get(conversation_id, [])

    def has_open_session(self, conversation_id: str) -> bool:
        with self._lock:
            return conversation_id in self._open_session

    def bump_auto_reply(self, conversation_id: str) -> int:
        with self._lock:
            self._auto_reply_count[conversation_id] = self._auto_reply_count.get(conversation_id, 0) + 1
            return self._auto_reply_count[conversation_id]

    def end_conversation(self, conversation_id: str) -> None:
        with self._lock:
            self._ended_conversations.add(conversation_id)

    def is_ended(self, conversation_id: str) -> bool:
        with self._lock:
            return conversation_id in self._ended_conversations

    # --- opportunity memory (grounds /v1/reply's default case) -----------------
    def remember_opportunity(self, conversation_id: str, family: str, why_now: List[str], evidence: List[dict]) -> None:
        with self._lock:
            self._last_opportunity[conversation_id] = {"family": family, "why_now": why_now, "evidence": evidence}

    def get_last_opportunity(self, conversation_id: str) -> Optional[Dict]:
        with self._lock:
            return self._last_opportunity.get(conversation_id)

    # --- message evolution: attempt tracking per (merchant, family) ------------
    def bump_attempt(self, merchant_id: str, family: str) -> int:
        with self._lock:
            key = (merchant_id, family)
            self._attempt_count[key] = self._attempt_count.get(key, 0) + 1
            return self._attempt_count[key]

    def reset_attempts(self, merchant_id: str, family: str) -> None:
        with self._lock:
            self._attempt_count.pop((merchant_id, family), None)

    def clear(self) -> None:
        with self._lock:
            self._send_times.clear()
            self._used_suppression_keys.clear()
            self._conversation_history.clear()
            self._auto_reply_count.clear()
            self._ended_conversations.clear()
            self._open_session.clear()
            self._last_opportunity.clear()
            self._attempt_count.clear()
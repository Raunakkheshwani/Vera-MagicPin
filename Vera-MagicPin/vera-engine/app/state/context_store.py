import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.models.api import ContextPushAccepted, ContextPushRejected, ContextScope


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class ContextStore:
    """
    In-memory, versioned store keyed by (scope, context_id).

    Behavior matches challenge-testing-brief.md's reference skeleton and
    api-call-examples.md Examples 1.5/1.6:
      - same or lower version than what's stored -> rejected, stale_version
      - strictly higher version -> accepted, replaces atomically
    A lock guards this because uvicorn serves requests concurrently, and
    adaptive-injection pushes can arrive while /v1/tick or /v1/reply are
    reading the same data.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def push(self, scope: ContextScope, context_id: str, version: int, payload: Dict[str, Any]):
        key = (scope, context_id)
        with self._lock:
            current = self._data.get(key)
            if current is not None and version <= current["version"]:
                return ContextPushRejected(reason="stale_version", current_version=current["version"])
            self._data[key] = {"version": version, "payload": payload}
            return ContextPushAccepted(ack_id=f"ack_{context_id}_v{version}", stored_at=_now_iso())

    def get(self, scope: ContextScope, context_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._data.get((scope, context_id))
            return None if entry is None else entry["payload"]

    def all_of_scope(self, scope: ContextScope) -> Dict[str, Any]:
        with self._lock:
            return {cid: e["payload"] for (s, cid), e in self._data.items() if s == scope}

    def counts_loaded(self) -> Dict[str, int]:
        with self._lock:
            counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
            for scope, _cid in self._data:
                if scope in counts:
                    counts[scope] += 1
            return counts

    def clear(self) -> None:
        """Test-only: reset all state between test cases."""
        with self._lock:
            self._data.clear()
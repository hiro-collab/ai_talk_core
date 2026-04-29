"""Process-local turn events with JSONL projection."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import queue
import threading
import time
from typing import Any, Iterator
from uuid import uuid4


MAX_SUBSCRIBER_QUEUE_SIZE = 200
MAX_EVENT_LOG_BYTES = 5 * 1024 * 1024
MAX_EVENT_LABEL_LENGTH = 80
MAX_EVENT_SOURCE_LENGTH = 64
MAX_EVENT_TURN_ID_LENGTH = 128
MAX_EVENT_PAYLOAD_KEYS = 32
MAX_EVENT_PAYLOAD_DEPTH = 4
MAX_EVENT_STRING_LENGTH = 512
MAX_EVENT_LIST_ITEMS = 16


@dataclass(frozen=True)
class TurnEvent:
    """One latency or state event for a voice turn."""

    turn_id: str
    event: str
    timestamp_wall: str
    timestamp_monotonic: float
    source: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Return a stable JSON projection."""
        return {
            "turn_id": self.turn_id,
            "event": self.event,
            "timestamp_wall": self.timestamp_wall,
            "timestamp_monotonic": self.timestamp_monotonic,
            "source": self.source,
            "payload": self.payload,
        }


class TurnEventBus:
    """Small in-process pub/sub bus that also appends events to JSONL."""

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path or get_event_log_path()
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue[TurnEvent]] = []

    def emit(
        self,
        event: str,
        *,
        turn_id: str,
        source: str = "core",
        payload: dict[str, Any] | None = None,
    ) -> TurnEvent:
        """Emit one event to subscribers and the JSONL projection."""
        turn_event = TurnEvent(
            turn_id=normalize_event_turn_id(turn_id),
            event=normalize_event_name(event),
            timestamp_wall=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            timestamp_monotonic=time.perf_counter(),
            source=normalize_event_source(source),
            payload=sanitize_event_payload(payload or {}),
        )
        line = json.dumps(turn_event.to_payload(), ensure_ascii=False, sort_keys=True)
        with self._lock:
            self._append_event_line(line)
            for subscriber in list(self._subscribers):
                try:
                    subscriber.put_nowait(turn_event)
                except queue.Full:
                    try:
                        subscriber.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        subscriber.put_nowait(turn_event)
                    except queue.Full:
                        pass
        return turn_event

    def _append_event_line(self, line: str) -> None:
        """Append one JSONL record while bounding local log growth."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_log_if_needed()
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _rotate_log_if_needed(self) -> None:
        """Keep the process-local projection from growing without bound."""
        if MAX_EVENT_LOG_BYTES <= 0:
            return
        try:
            if (
                not self.log_path.exists()
                or self.log_path.stat().st_size < MAX_EVENT_LOG_BYTES
            ):
                return
            archive_path = Path(f"{self.log_path}.1")
            if archive_path.exists():
                archive_path.unlink()
            self.log_path.replace(archive_path)
        except OSError:
            try:
                self.log_path.write_text("", encoding="utf-8")
            except OSError:
                pass

    @contextmanager
    def subscribe(self) -> Iterator[queue.Queue[TurnEvent]]:
        """Subscribe to future events until the context exits."""
        subscriber: queue.Queue[TurnEvent] = queue.Queue(
            maxsize=MAX_SUBSCRIBER_QUEUE_SIZE
        )
        with self._lock:
            self._subscribers.append(subscriber)
        try:
            yield subscriber
        finally:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)


def get_project_root() -> Path:
    """Return the project root."""
    return Path(__file__).resolve().parents[2]


def get_event_log_path() -> Path:
    """Return the default events.jsonl projection path."""
    return get_project_root() / ".cache" / "events.jsonl"


def new_turn_id(prefix: str = "turn") -> str:
    """Return a compact opaque turn id."""
    safe_prefix = _normalize_label(
        prefix,
        default="turn",
        max_length=24,
    )
    return f"{safe_prefix or 'turn'}_{uuid4().hex}"


def text_payload_facts(text: str) -> dict[str, Any]:
    """Return redacted facts for text-bearing events."""
    normalized = text or ""
    return {
        "text_length": len(normalized),
        "text_present": bool(normalized),
    }


def sanitize_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce payload values into JSON-safe debug data."""
    if not isinstance(payload, dict):
        return {}
    return _sanitize_mapping(payload, depth=0)


def normalize_event_name(value: object, *, default: str = "event") -> str:
    """Return a compact event name safe for JSONL and SSE event fields."""
    return _normalize_label(
        value,
        default=default,
        max_length=MAX_EVENT_LABEL_LENGTH,
        allow_hyphen=False,
    )


def normalize_event_source(value: object, *, default: str = "core") -> str:
    """Return a compact event source label."""
    return _normalize_label(
        value,
        default=default,
        max_length=MAX_EVENT_SOURCE_LENGTH,
    )


def normalize_event_turn_id(value: object, *, default: str = "turn_unknown") -> str:
    """Return a compact turn id for event projections."""
    return _normalize_label(
        value,
        default=default,
        max_length=MAX_EVENT_TURN_ID_LENGTH,
    )


def _normalize_label(
    value: object,
    *,
    default: str,
    max_length: int,
    allow_hyphen: bool = True,
) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return default
    allowed_extra = "_-" if allow_hyphen else "_"
    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        f"{allowed_extra}"
    )
    safe = "".join(character for character in normalized if character in allowed)
    safe = safe[:max_length]
    return safe or default


def _sanitize_mapping(value: dict[Any, Any], *, depth: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    items = list(value.items())
    for key, child_value in items[:MAX_EVENT_PAYLOAD_KEYS]:
        if child_value is None:
            continue
        safe_key = _truncate_string(str(key), max_length=MAX_EVENT_LABEL_LENGTH)
        if safe_key:
            result[safe_key] = _sanitize_value(child_value, depth=depth + 1)
    if len(items) > MAX_EVENT_PAYLOAD_KEYS:
        result["_truncated_keys"] = len(items) - MAX_EVENT_PAYLOAD_KEYS
    return result


def _sanitize_value(value: Any, *, depth: int) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, str):
        return _truncate_string(value, max_length=MAX_EVENT_STRING_LENGTH)
    if isinstance(value, Path):
        return value.name
    if depth >= MAX_EVENT_PAYLOAD_DEPTH:
        return _truncate_string(str(value), max_length=MAX_EVENT_STRING_LENGTH)
    if isinstance(value, dict):
        return _sanitize_mapping(value, depth=depth)
    if isinstance(value, list | tuple):
        result = [
            _sanitize_value(child_value, depth=depth + 1)
            for child_value in value[:MAX_EVENT_LIST_ITEMS]
        ]
        if len(value) > MAX_EVENT_LIST_ITEMS:
            result.append(f"...{len(value) - MAX_EVENT_LIST_ITEMS} more")
        return result
    return _truncate_string(str(value), max_length=MAX_EVENT_STRING_LENGTH)


def _truncate_string(value: str, *, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}...[truncated]"


_DEFAULT_EVENT_BUS = TurnEventBus()


def get_event_bus() -> TurnEventBus:
    """Return the process-wide event bus."""
    return _DEFAULT_EVENT_BUS


def emit_event(
    event: str,
    *,
    turn_id: str,
    source: str = "core",
    payload: dict[str, Any] | None = None,
) -> TurnEvent:
    """Emit one event on the default bus."""
    return get_event_bus().emit(
        event,
        turn_id=turn_id,
        source=source,
        payload=payload,
    )

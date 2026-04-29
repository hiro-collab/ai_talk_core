"""Process-local turn events with JSONL projection."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import queue
import threading
import time
from typing import Any, Iterator
from uuid import uuid4


MAX_SUBSCRIBER_QUEUE_SIZE = 200


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
            turn_id=turn_id,
            event=event,
            timestamp_wall=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            timestamp_monotonic=time.perf_counter(),
            source=source,
            payload=sanitize_event_payload(payload or {}),
        )
        line = json.dumps(turn_event.to_payload(), ensure_ascii=False, sort_keys=True)
        with self._lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
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
    safe_prefix = "".join(
        character for character in prefix.strip().lower() if character.isalnum() or character == "_"
    )
    return f"{safe_prefix or 'turn'}_{uuid4().hex}"


def text_payload_facts(text: str) -> dict[str, Any]:
    """Return redacted facts for text-bearing events."""
    normalized = text or ""
    return {
        "text_length": len(normalized),
        "text_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if normalized
        else "",
    }


def sanitize_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce payload values into JSON-safe debug data."""
    return {
        str(key): _sanitize_value(value)
        for key, value in payload.items()
        if value is not None
    }


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _sanitize_value(child_value)
            for key, child_value in value.items()
            if child_value is not None
        }
    if isinstance(value, list | tuple):
        return [_sanitize_value(child_value) for child_value in value]
    return str(value)


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

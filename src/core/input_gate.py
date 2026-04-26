"""Backend-neutral input gating for voice capture sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class InputGateError(ValueError):
    """Raised when an input-gate update payload is invalid."""


@dataclass(frozen=True)
class InputGateState:
    """Current decision for whether voice input should be accepted."""

    enabled: bool = True
    reason: str = "default"
    source: str = "local"
    timestamp: float | None = None

    def to_payload(self) -> dict[str, bool | float | str | None]:
        """Return a stable protocol payload for app or adapter boundaries."""
        return {
            "type": "input_gate_state",
            "input_enabled": self.enabled,
            "reason": self.reason,
            "source": self.source,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class InputGateEvent:
    """One external or local request to update the input gate."""

    input_enabled: bool
    reason: str = "external"
    source: str = "external"
    timestamp: float | None = None


class InputGate:
    """Track whether voice capture should currently accept microphone input."""

    def __init__(
        self,
        initially_enabled: bool = True,
        *,
        reason: str = "default",
        source: str = "local",
        timestamp: float | None = None,
    ) -> None:
        self._state = InputGateState(
            enabled=_expect_bool(initially_enabled, "initially_enabled"),
            reason=_normalize_text(reason, "default", "reason"),
            source=_normalize_text(source, "local", "source"),
            timestamp=_normalize_timestamp(timestamp),
        )

    @property
    def state(self) -> InputGateState:
        """Return the current immutable state snapshot."""
        return self._state

    def is_enabled(self) -> bool:
        """Return whether input should currently be accepted."""
        return self._state.enabled

    def set_input_enabled(
        self,
        enabled: bool,
        *,
        reason: str = "manual",
        source: str = "local",
        timestamp: float | None = None,
    ) -> InputGateState:
        """Set the gate directly and return the resulting state."""
        self._state = InputGateState(
            enabled=_expect_bool(enabled, "enabled"),
            reason=_normalize_text(reason, "manual", "reason"),
            source=_normalize_text(source, "local", "source"),
            timestamp=_normalize_timestamp(timestamp),
        )
        return self._state

    def update(self, event: InputGateEvent) -> InputGateState:
        """Apply an input-gate event and return the resulting state."""
        return self.set_input_enabled(
            event.input_enabled,
            reason=event.reason,
            source=event.source,
            timestamp=event.timestamp,
        )

    def update_from_payload(self, payload: Mapping[str, Any]) -> InputGateState:
        """Parse and apply a backend-neutral input-gate payload."""
        return self.update(parse_input_gate_payload(payload))


def parse_input_gate_payload(payload: Mapping[str, Any]) -> InputGateEvent:
    """Parse an input-gate control payload.

    The accepted control keys are intentionally generic so an integration app can
    map gesture, keyboard, network, or UI state into this protocol without this
    project importing any gesture-specific package.
    """
    if not isinstance(payload, Mapping):
        raise InputGateError("input gate payload must be a mapping")

    enabled_field = _find_enabled_field(payload)
    if enabled_field is None:
        raise InputGateError(
            "input gate payload must include input_enabled, mic_enabled, or enabled"
        )
    enabled_key, enabled_value = enabled_field
    reason = _normalize_text(payload.get("reason"), "external", "reason")
    source = _normalize_text(payload.get("source"), "external", "source")
    timestamp = _normalize_timestamp(payload.get("timestamp"))
    return InputGateEvent(
        input_enabled=_expect_bool(enabled_value, enabled_key),
        reason=reason,
        source=source,
        timestamp=timestamp,
    )


def _find_enabled_field(payload: Mapping[str, Any]) -> tuple[str, Any] | None:
    for key in ("input_enabled", "mic_enabled", "enabled"):
        if key in payload:
            return key, payload[key]
    return None


def _expect_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise InputGateError(f"{field_name} must be a boolean")


def _normalize_text(value: Any, fallback: str, field_name: str) -> str:
    if value is None:
        return fallback
    if not isinstance(value, str):
        raise InputGateError(f"{field_name} must be a string")
    normalized = value.strip()
    return normalized or fallback


def _normalize_timestamp(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputGateError("timestamp must be a number")
    return float(value)

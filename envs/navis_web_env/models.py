"""Compatibility wrapper that re-exports package models."""

try:
    from navis_web_env.models import LinkOption, NavisWebAction, NavisWebObservation, NavisWebState
except ImportError:  # pragma: no cover - repo import path
    from .navis_web_env.models import LinkOption, NavisWebAction, NavisWebObservation, NavisWebState

__all__ = [
    "LinkOption",
    "NavisWebAction",
    "NavisWebObservation",
    "NavisWebState",
]

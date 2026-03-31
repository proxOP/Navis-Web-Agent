"""Compatibility wrapper that re-exports the packaged client."""

try:
    from navis_web_env.client import NavisWebEnv
except ImportError:  # pragma: no cover - repo import path
    from .navis_web_env.client import NavisWebEnv

__all__ = ["NavisWebEnv"]

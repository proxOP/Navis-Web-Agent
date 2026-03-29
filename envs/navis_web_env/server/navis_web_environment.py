"""Compatibility wrapper for the packaged environment class."""

try:
    from navis_web_env.server.navis_web_environment import NavisWebEnvironment
except ImportError:  # pragma: no cover - repo import path
    from ..navis_web_env.server.navis_web_environment import NavisWebEnvironment

__all__ = ["NavisWebEnvironment"]

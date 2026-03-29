"""Compatibility wrapper for the package server app."""

try:
    from navis_web_env.server.app import app, main
except ImportError:  # pragma: no cover - repo import path
    from ..navis_web_env.server.app import app, main

__all__ = ["app", "main"]

"""Compatibility wrapper for the package server app."""

try:
    from navis_web_env.server.app import app as package_app, main as package_main
except ImportError:  # pragma: no cover - repo import path
    from ..navis_web_env.server.app import app as package_app, main as package_main

app = package_app


def main() -> None:
    package_main()


if __name__ == "__main__":  # pragma: no cover
    main()

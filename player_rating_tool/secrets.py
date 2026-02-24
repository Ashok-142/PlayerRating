from __future__ import annotations

import os
from pathlib import Path


def load_env_files() -> None:
    """Load `.env` when available; ignore if python-dotenv is not installed."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


def get_secret(name: str, default: str | None = None) -> str | None:
    """Read secrets from environment first, then Streamlit secrets if available."""
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st
    except Exception:
        return default

    try:
        secret_value = st.secrets.get(name)
    except Exception:
        return default

    if secret_value is None:
        return default
    return str(secret_value)


def require_secret(name: str) -> str:
    value = get_secret(name)
    if not value:
        raise ValueError(
            f"Missing required secret: {name}. Set it via environment variables, "
            "a local .env file, or Streamlit secrets."
        )
    return value

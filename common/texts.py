"""
Centralized UI texts loader and formatter for AITU Gaming Hub.
Loads text strings from texts.json with dot-notation lookup and safe formatting.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TEXTS_CACHE: dict[str, Any] = {}
_LAST_MTIME: float = 0.0


def get_texts_file_path() -> Path:
    """Finds texts.json either in common/ or in project root."""
    common_dir = Path(__file__).resolve().parent
    common_file = common_dir / "texts.json"
    root_file = common_dir.parent / "texts.json"

    if common_file.exists():
        return common_file
    if root_file.exists():
        return root_file
    return common_file


def load_texts(force: bool = False) -> dict[str, Any]:
    """Loads texts dictionary from texts.json with caching and hot-reload on file modification."""
    global _TEXTS_CACHE, _LAST_MTIME

    file_path = get_texts_file_path()
    if not file_path.exists():
        logger.warning(f"Texts file not found at {file_path}")
        return _TEXTS_CACHE

    try:
        current_mtime = file_path.stat().st_mtime
        if force or current_mtime != _LAST_MTIME or not _TEXTS_CACHE:
            with open(file_path, "r", encoding="utf-8") as f:
                _TEXTS_CACHE = json.load(f)
            _LAST_MTIME = current_mtime
    except Exception as e:
        logger.error(f"Error loading texts from {file_path}: {e}")

    return _TEXTS_CACHE


def reload_texts() -> dict[str, Any]:
    """Explicitly reloads texts from file."""
    return load_texts(force=True)


def get_text(key: str, default: str | None = None, **kwargs: Any) -> str:
    """
    Retrieves a string from texts.json using dot-separated keys and formats it.

    Example:
        get_text("auth.club_info.text")
        get_text("auth.phone.text", full_name="John Doe")
    """
    texts = load_texts()
    parts = key.split(".")
    val: Any = texts

    for part in parts:
        if isinstance(val, dict) and part in val:
            val = val[part]
        else:
            val = None
            break

    if val is None or not isinstance(val, str):
        if default is not None:
            val = default
        else:
            val = f"[{key}]"

    result = str(val)
    if kwargs:
        try:
            result = result.format(**kwargs)
        except (KeyError, ValueError, IndexError) as err:
            logger.debug(f"Formatting failed for key '{key}' ({err}), using manual replacement")
            for k, v in kwargs.items():
                result = result.replace(f"{{{k}}}", str(v))

    return result

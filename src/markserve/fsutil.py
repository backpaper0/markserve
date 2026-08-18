"""ファイル種別判定まわりのユーティリティ。"""

from __future__ import annotations

import mimetypes
from pathlib import Path

MARKDOWN_SUFFIXES = {".md", ".markdown"}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico"}

_SNIFF_BYTES = 8192


def is_markdown(path: Path) -> bool:
    return path.suffix.lower() in MARKDOWN_SUFFIXES


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def guess_mime_type(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type or "application/octet-stream"


def is_probably_text(data: bytes) -> bool:
    """先頭バイト列を見てテキストらしいかどうかを簡易判定する。"""
    if b"\0" in data[:_SNIFF_BYTES]:
        return False
    try:
        data[:_SNIFF_BYTES].decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True

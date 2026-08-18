"""URLパスをルートディレクトリ配下のファイルパスへ安全に解決する。"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote


class PathTraversalError(Exception):
    """URLパスがルートディレクトリの外を指している場合に送出される。"""


def safe_resolve(root: Path, url_path: str) -> Path:
    """URLパスをrootディレクトリ配下の実ファイルパスへ解決する。

    rootの外を指す場合（`..`によるものやシンボリックリンク経由のものを含む）は
    PathTraversalErrorを送出する。
    """
    decoded = unquote(url_path)
    if "\0" in decoded:
        raise PathTraversalError(f"NUL byte in path: {url_path!r}")

    rel_parts = [part for part in decoded.split("/") if part not in ("", ".")]
    if any(part == ".." for part in rel_parts):
        raise PathTraversalError(f"path escapes root: {url_path!r}")

    candidate = root.joinpath(*rel_parts)
    resolved = candidate.resolve()

    if not (resolved == root or resolved.is_relative_to(root)):
        raise PathTraversalError(f"resolved path escapes root: {url_path!r}")

    return resolved

"""markserveコマンドのエントリポイント。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .server import serve


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markserve",
        description="ローカルディレクトリのMarkdownファイルをブラウザでプレビューする。",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="プレビュー対象のルートディレクトリ（既定: カレントディレクトリ）",
    )
    parser.add_argument("-p", "--port", type=int, default=8000, help="待ち受けポート（既定: 8000）")
    parser.add_argument(
        "-H", "--host", default="127.0.0.1", help="待ち受けホスト（既定: 127.0.0.1）"
    )
    parser.add_argument(
        "-o", "--open", action="store_true", dest="open_browser", help="起動後にブラウザを自動で開く"
    )
    parser.add_argument("--version", action="version", version=f"markserve {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    root = Path(args.directory)
    if not root.exists():
        print(f"markserve: ディレクトリが見つかりません: {root}", file=sys.stderr)
        return 1
    if not root.is_dir():
        print(f"markserve: ディレクトリではありません: {root}", file=sys.stderr)
        return 1

    serve(root.resolve(strict=True), args.host, args.port, open_browser=args.open_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
    parser.add_argument(
        "-f",
        "--pretty-font",
        action="store_true",
        dest="pretty_font",
        help="読みやすさ重視のフォント（Windows: UD デジタル教科書体 / macOS: 游教科書体・Osaka）を使用する",
    )
    parser.add_argument(
        "--css",
        dest="custom_css",
        metavar="PATH",
        default=None,
        help="指定したCSSファイルでデザイン（フォントなど）を上書きする",
    )
    parser.add_argument(
        "--show-hidden",
        dest="show_hidden",
        action="append",
        metavar="NAME",
        default=None,
        help="ドット始まりでも表示対象に含める名前（階層を問わず一致。複数指定可）",
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

    custom_css_path: Path | None = None
    if args.custom_css:
        custom_css_path = Path(args.custom_css)
        if not custom_css_path.is_file():
            print(f"markserve: CSSファイルが見つかりません: {custom_css_path}", file=sys.stderr)
            return 1
        custom_css_path = custom_css_path.resolve(strict=True)

    serve(
        root.resolve(strict=True),
        args.host,
        args.port,
        open_browser=args.open_browser,
        pretty_font=args.pretty_font,
        custom_css_path=custom_css_path,
        show_hidden=frozenset(args.show_hidden or ()),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

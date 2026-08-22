"""markserveのHTTPサーバー本体。"""

from __future__ import annotations

import html
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import fsutil, render
from .security import PathTraversalError, safe_resolve
from .tree import TreeNode, build_tree

STATIC_PREFIX = "/__markserve_static__/"

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _rel_path(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return "" if rel == "." else rel


def _breadcrumbs(rel_path: str) -> list[dict]:
    parts = [p for p in rel_path.split("/") if p]
    crumbs = []
    acc: list[str] = []
    for part in parts:
        acc.append(part)
        crumbs.append({"name": part, "href": "/".join(acc)})
    return crumbs


def _render_error(status: HTTPStatus, message: str, base_url: str = "") -> bytes:
    template = _env.get_template("error.html")
    out = template.render(status_code=int(status), message=message, base_url=base_url)
    return out.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    root: Path
    pretty_font: bool = False
    custom_css_path: Path | None = None
    show_hidden: frozenset[str] = frozenset()
    base_url: str = ""
    server_version = "markserve/0.1"

    def _render_page(
        self,
        *,
        title: str,
        breadcrumbs: list[dict],
        tree_root: TreeNode,
        tree_truncated: bool,
        content: str,
        is_markdown: bool = False,
        raw_mode: bool = False,
    ) -> bytes:
        template = _env.get_template("layout.html")
        out = template.render(
            title=title,
            breadcrumbs=breadcrumbs,
            tree_root=tree_root,
            tree_truncated=tree_truncated,
            content=content,
            is_markdown=is_markdown,
            raw_mode=raw_mode,
            pretty_font=self.pretty_font,
            custom_css=self.custom_css_path is not None,
            base_url=self.base_url,
        )
        return out.encode("utf-8")

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        split = urlsplit(self.path)
        url_path = split.path
        query_params = parse_qs(split.query)
        raw_mode = query_params.get("raw", ["0"])[0] == "1"

        if url_path.startswith(STATIC_PREFIX):
            self._serve_static(url_path[len(STATIC_PREFIX) :])
            return

        try:
            resolved = safe_resolve(self.root, url_path)
        except PathTraversalError:
            self._send_error_page(HTTPStatus.FORBIDDEN, "このパスにはアクセスできません。")
            return

        if resolved.is_dir():
            if not url_path.endswith("/"):
                location = url_path + "/"
                if split.query:
                    location += "?" + split.query
                self._redirect(location)
                return
            self._serve_directory(resolved, raw_mode=raw_mode)
            return

        if not resolved.exists():
            self._send_error_page(HTTPStatus.NOT_FOUND, "ファイルが見つかりません。")
            return

        if fsutil.is_markdown(resolved):
            self._serve_markdown(resolved, raw_mode=raw_mode)
        elif fsutil.is_image(resolved):
            self._serve_binary(resolved)
        else:
            self._serve_text_or_binary(resolved)

    def _serve_directory(self, dir_path: Path, *, raw_mode: bool = False) -> None:
        for name in ("index.md", "README.md"):
            candidate = dir_path / name
            if candidate.is_file():
                self._serve_markdown(candidate, raw_mode=raw_mode)
                return
        self._serve_dir_listing(dir_path)

    def _serve_dir_listing(self, dir_path: Path) -> None:
        rel_path = _rel_path(self.root, dir_path)
        tree_result = build_tree(self.root, current_rel_path=rel_path, show_hidden=self.show_hidden)

        try:
            entries = sorted(
                (
                    e
                    for e in dir_path.iterdir()
                    if not e.name.startswith(".") or e.name in self.show_hidden
                ),
                key=lambda e: (not e.is_dir(), e.name.lower()),
            )
        except OSError:
            entries = []

        items = []
        for entry in entries:
            suffix = "/" if entry.is_dir() else ""
            label = entry.name + suffix
            items.append(
                f'<li><a href="{html.escape(entry.name)}{suffix}">{html.escape(label)}</a></li>'
            )
        listing = "".join(items) or "<li>(空のディレクトリです)</li>"
        content = f'<div class="text-body"><ul class="dir-listing">{listing}</ul></div>'

        body = self._render_page(
            title=rel_path or "/",
            breadcrumbs=_breadcrumbs(rel_path),
            tree_root=tree_result.root,
            tree_truncated=tree_result.truncated,
            content=content,
        )
        self._send_html(HTTPStatus.OK, body)

    def _serve_markdown(self, file_path: Path, *, raw_mode: bool) -> None:
        rel_path = _rel_path(self.root, file_path)
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree_result = build_tree(self.root, current_rel_path=rel_path, show_hidden=self.show_hidden)

        if raw_mode:
            content = f'<div class="text-body"><pre>{html.escape(source)}</pre></div>'
        else:
            front_matter, body_source = render.split_front_matter(source)
            html_parts = []
            if front_matter:
                html_parts.append(
                    '<details class="front-matter-wrapper">'
                    "<summary>Front matter</summary>"
                    f"{render.render_front_matter_table(front_matter)}"
                    "</details>"
                )
            html_parts.append(render.render_markdown(body_source))
            content = f'<div class="markdown-body">{"".join(html_parts)}</div>'

        body = self._render_page(
            title=file_path.name,
            breadcrumbs=_breadcrumbs(rel_path),
            tree_root=tree_result.root,
            tree_truncated=tree_result.truncated,
            content=content,
            is_markdown=True,
            raw_mode=raw_mode,
        )
        self._send_html(HTTPStatus.OK, body)

    def _serve_text_or_binary(self, file_path: Path) -> None:
        data = file_path.read_bytes()
        if not fsutil.is_probably_text(data):
            self._send_bytes(HTTPStatus.OK, data, fsutil.guess_mime_type(file_path))
            return

        rel_path = _rel_path(self.root, file_path)
        tree_result = build_tree(self.root, current_rel_path=rel_path, show_hidden=self.show_hidden)
        text = data.decode("utf-8", errors="replace")
        content = f'<div class="text-body"><pre>{html.escape(text)}</pre></div>'

        body = self._render_page(
            title=file_path.name,
            breadcrumbs=_breadcrumbs(rel_path),
            tree_root=tree_result.root,
            tree_truncated=tree_result.truncated,
            content=content,
        )
        self._send_html(HTTPStatus.OK, body)

    def _serve_binary(self, file_path: Path) -> None:
        data = file_path.read_bytes()
        self._send_bytes(HTTPStatus.OK, data, fsutil.guess_mime_type(file_path))

    def _serve_static(self, name: str) -> None:
        if name == "style.css":
            css = (_STATIC_DIR / "style.css").read_text(encoding="utf-8")
            css += "\n" + render.pygments_css() + "\n"
            self._send_bytes(HTTPStatus.OK, css.encode("utf-8"), "text/css; charset=utf-8")
        elif name == "pretty-font.css":
            css = (_STATIC_DIR / "pretty-font.css").read_text(encoding="utf-8")
            self._send_bytes(HTTPStatus.OK, css.encode("utf-8"), "text/css; charset=utf-8")
        elif name == "custom.css" and self.custom_css_path is not None:
            css = self.custom_css_path.read_text(encoding="utf-8")
            self._send_bytes(HTTPStatus.OK, css.encode("utf-8"), "text/css; charset=utf-8")
        else:
            self._send_error_page(HTTPStatus.NOT_FOUND, "ファイルが見つかりません。")

    def _send_html(self, status: HTTPStatus, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status: HTTPStatus, data: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error_page(self, status: HTTPStatus, message: str) -> None:
        self._send_html(status, _render_error(status, message, base_url=self.base_url))

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.MOVED_PERMANENTLY)
        self.send_header("Location", self.base_url + location)
        self.send_header("Content-Length", "0")
        self.end_headers()


def _make_handler_class(
    root: Path,
    *,
    pretty_font: bool = False,
    custom_css_path: Path | None = None,
    show_hidden: frozenset[str] = frozenset(),
    base_url: str = "",
) -> type[Handler]:
    return type(
        "BoundHandler",
        (Handler,),
        {
            "root": root,
            "pretty_font": pretty_font,
            "custom_css_path": custom_css_path,
            "show_hidden": show_hidden,
            "base_url": base_url,
        },
    )


def serve(
    root: Path,
    host: str,
    port: int,
    open_browser: bool = False,
    pretty_font: bool = False,
    custom_css_path: Path | None = None,
    show_hidden: frozenset[str] = frozenset(),
    base_url: str = "",
) -> None:
    handler_class = _make_handler_class(
        root,
        pretty_font=pretty_font,
        custom_css_path=custom_css_path,
        show_hidden=show_hidden,
        base_url=base_url,
    )
    httpd = ThreadingHTTPServer((host, port), handler_class)

    if open_browser:
        url = f"http://{host}:{port}{base_url}/"
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()

    print(f"markserve: serving {root} at http://{host}:{port}{base_url}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

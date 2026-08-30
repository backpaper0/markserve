"""MarkdownをHTMLへ変換する。Mermaidブロックとシンタックスハイライトに対応する。"""

from __future__ import annotations

import html
import re

import yaml
from markdown_it import MarkdownIt
from pygments import highlight as pygments_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

PYGMENTS_STYLE = "friendly"

_FRONT_MATTER_RE = re.compile(r"\A---\r?\n(.*?\r?\n)---\r?\n?", re.DOTALL)

_formatter = HtmlFormatter(style=PYGMENTS_STYLE, nowrap=True)


def _get_lexer(lang: str, code: str):
    if lang:
        try:
            return get_lexer_by_name(lang)
        except ClassNotFound:
            pass
    try:
        return guess_lexer(code)
    except ClassNotFound:
        return TextLexer()


def _highlight(code: str, lang: str, _attrs: str) -> str:
    lexer = _get_lexer(lang, code)
    body = pygments_highlight(code, lexer, _formatter)
    lang_class = f" language-{html.escape(lang)}" if lang else ""
    return f'<pre class="highlight"><code class="highlight{lang_class}">{body}</code></pre>\n'


def _build_markdown_it() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "highlight": _highlight})
    md.enable("table")

    default_fence = md.renderer.rules.get("fence") or md.renderer.fence

    def fence_with_mermaid(tokens, idx, options, env):
        token = tokens[idx]
        info = token.info.strip() if token.info else ""
        lang = info.split(maxsplit=1)[0] if info else ""
        if lang == "mermaid":
            escaped = html.escape(token.content)
            return (
                '<div class="mermaid-wrapper">'
                f'<a class="mermaid-popout" href="#" data-mermaid-source="{escaped}">'
                "⛶ 別ウィンドウで開く</a>"
                f'<pre class="mermaid">{escaped}</pre>'
                "</div>\n"
            )
        return default_fence(tokens, idx, options, env)

    md.renderer.rules["fence"] = fence_with_mermaid
    return md


_md = _build_markdown_it()


def split_front_matter(source: str) -> tuple[dict | None, str]:
    """先頭のYAML front matterを取り出す。無い、または辞書として解釈できない場合は(None, source)を返す。"""
    match = _FRONT_MATTER_RE.match(source)
    if not match:
        return None, source
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None, source
    if not isinstance(data, dict):
        return None, source
    return data, source[match.end() :]


def _front_matter_value_html(value: object) -> str:
    if isinstance(value, list):
        if not value:
            return ""
        items = "".join(f"<li>{_front_matter_value_html(v)}</li>" for v in value)
        return f"<ul>{items}</ul>"
    if isinstance(value, dict):
        if not value:
            return ""
        rows = "".join(
            f"<tr><th>{html.escape(str(k))}</th><td>{_front_matter_value_html(v)}</td></tr>"
            for k, v in value.items()
        )
        return f'<table class="front-matter-nested"><tbody>{rows}</tbody></table>'
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return html.escape(str(value))


def render_front_matter_table(data: dict) -> str:
    """front matterの辞書をHTMLテーブルへ変換する。"""
    rows = "".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{_front_matter_value_html(value)}</td></tr>"
        for key, value in data.items()
    )
    return f'<table class="front-matter"><tbody>{rows}</tbody></table>'


def render_markdown(source: str) -> str:
    """Markdown文字列をHTML文字列へ変換する。"""
    return _md.render(source)


def pygments_css() -> str:
    """シンタックスハイライト用のCSSを生成する。"""
    return _formatter.get_style_defs(".highlight")

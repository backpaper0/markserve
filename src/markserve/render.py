"""MarkdownをHTMLへ変換する。Mermaidブロックとシンタックスハイライトに対応する。"""

from __future__ import annotations

import html

from markdown_it import MarkdownIt
from pygments import highlight as pygments_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

PYGMENTS_STYLE = "friendly"

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
            return f'<pre class="mermaid">{escaped}</pre>\n'
        return default_fence(tokens, idx, options, env)

    md.renderer.rules["fence"] = fence_with_mermaid
    return md


_md = _build_markdown_it()


def render_markdown(source: str) -> str:
    """Markdown文字列をHTML文字列へ変換する。"""
    return _md.render(source)


def pygments_css() -> str:
    """シンタックスハイライト用のCSSを生成する。"""
    return _formatter.get_style_defs(".highlight")

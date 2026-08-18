from markserve.render import render_markdown


def test_headings_and_emphasis():
    html_out = render_markdown("# Title\n\n**bold** and *italic*\n")
    assert "<h1>Title</h1>" in html_out
    assert "<strong>bold</strong>" in html_out
    assert "<em>italic</em>" in html_out


def test_table():
    html_out = render_markdown("| a | b |\n| --- | --- |\n| 1 | 2 |\n")
    assert "<table>" in html_out


def test_code_block_is_highlighted():
    html_out = render_markdown("```python\nprint('hi')\n```\n")
    assert 'class="highlight' in html_out
    assert "<span" in html_out


def test_mermaid_fence_bypasses_highlight():
    html_out = render_markdown("```mermaid\ngraph TD; A-->B;\n```\n")
    assert '<pre class="mermaid">' in html_out
    assert "highlight" not in html_out

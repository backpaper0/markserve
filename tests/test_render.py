from markserve.render import render_front_matter_table, render_markdown, split_front_matter


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


def test_mermaid_fence_includes_popout_link_with_source():
    html_out = render_markdown("```mermaid\ngraph TD; A-->B;\n```\n")
    assert 'class="mermaid-popout"' in html_out
    assert 'data-mermaid-source="graph TD; A--&gt;B;\n"' in html_out


def test_split_front_matter_extracts_yaml():
    source = "---\ntitle: Hello\ntags:\n  - a\n  - b\n---\n# Body\n"
    data, body = split_front_matter(source)
    assert data == {"title": "Hello", "tags": ["a", "b"]}
    assert body == "# Body\n"


def test_split_front_matter_without_front_matter_returns_none():
    data, body = split_front_matter("# Body\n")
    assert data is None
    assert body == "# Body\n"


def test_split_front_matter_ignores_non_mapping_yaml():
    source = "---\n- a\n- b\n---\n# Body\n"
    data, body = split_front_matter(source)
    assert data is None
    assert body == source


def test_split_front_matter_ignores_invalid_yaml():
    source = "---\nkey: [unclosed\n---\n# Body\n"
    data, body = split_front_matter(source)
    assert data is None
    assert body == source


def test_render_front_matter_table_scalar_values():
    html_out = render_front_matter_table({"title": "Hello", "draft": False})
    assert '<table class="front-matter">' in html_out
    assert "<th>title</th><td>Hello</td>" in html_out
    assert "<th>draft</th><td>false</td>" in html_out


def test_render_front_matter_table_list_value():
    html_out = render_front_matter_table({"tags": ["a", "b"]})
    assert "<ul><li>a</li><li>b</li></ul>" in html_out


def test_render_front_matter_table_escapes_html():
    html_out = render_front_matter_table({"title": "<script>"})
    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out

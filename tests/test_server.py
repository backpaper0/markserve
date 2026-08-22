import http.client
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from markserve.server import _make_handler_class


@pytest.fixture
def running_server(tmp_path):
    (tmp_path / "index.md").write_text("# Hello\n", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 10)
    (tmp_path / "notes.txt").write_text("plain text\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "README.md").write_text("# Sub\n", encoding="utf-8")

    handler_class = _make_handler_class(tmp_path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]

    yield "127.0.0.1", port

    httpd.shutdown()
    thread.join()


def test_markdown_preview(running_server):
    host, port = running_server
    with urllib.request.urlopen(f"http://{host}:{port}/index.md") as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        assert "<h1>Hello</h1>" in body


def test_front_matter_rendered_as_table(running_server, tmp_path):
    (tmp_path / "with_fm.md").write_text(
        "---\ntitle: My Doc\ntags:\n  - a\n  - b\n---\n# Body\n",
        encoding="utf-8",
    )
    host, port = running_server
    with urllib.request.urlopen(f"http://{host}:{port}/with_fm.md") as resp:
        body = resp.read().decode("utf-8")
        assert '<table class="front-matter">' in body
        assert "<th>title</th><td>My Doc</td>" in body
        assert "<h1>Body</h1>" in body
        assert "title: My Doc" not in body


def test_front_matter_shown_raw_in_raw_mode(running_server, tmp_path):
    (tmp_path / "with_fm.md").write_text(
        "---\ntitle: My Doc\n---\n# Body\n",
        encoding="utf-8",
    )
    host, port = running_server
    with urllib.request.urlopen(f"http://{host}:{port}/with_fm.md?raw=1") as resp:
        body = resp.read().decode("utf-8")
        assert "title: My Doc" in body
        assert '<table class="front-matter">' not in body


def test_markdown_raw_source(running_server):
    host, port = running_server
    with urllib.request.urlopen(f"http://{host}:{port}/index.md?raw=1") as resp:
        body = resp.read().decode("utf-8")
        assert "# Hello" in body
        assert "<h1>" not in body


def test_image_content_type(running_server):
    host, port = running_server
    with urllib.request.urlopen(f"http://{host}:{port}/image.png") as resp:
        assert resp.headers["Content-Type"] == "image/png"


def test_plain_text_shown_as_source(running_server):
    host, port = running_server
    with urllib.request.urlopen(f"http://{host}:{port}/notes.txt") as resp:
        body = resp.read().decode("utf-8")
        assert "plain text" in body


def test_directory_index_raw_mode(running_server):
    host, port = running_server
    with urllib.request.urlopen(f"http://{host}:{port}/?raw=1") as resp:
        body = resp.read().decode("utf-8")
        assert "# Hello" in body
        assert "<h1>" not in body


def test_subdirectory_redirect_preserves_query(running_server):
    host, port = running_server
    conn = http.client.HTTPConnection(host, port)
    try:
        conn.request("GET", "/sub?raw=1")
        resp = conn.getresponse()
        assert resp.status == 301
        assert resp.getheader("Location") == "/sub/?raw=1"
        resp.read()
    finally:
        conn.close()


def test_subdirectory_readme_raw_mode(running_server):
    host, port = running_server
    with urllib.request.urlopen(f"http://{host}:{port}/sub/?raw=1") as resp:
        body = resp.read().decode("utf-8")
        assert "# Sub" in body
        assert "<h1>" not in body


def test_path_traversal_is_forbidden(running_server):
    host, port = running_server
    conn = http.client.HTTPConnection(host, port)
    try:
        conn.request("GET", "/../../etc/passwd")
        resp = conn.getresponse()
        assert resp.status == 403
        resp.read()
    finally:
        conn.close()


def test_missing_file_is_not_found(running_server):
    host, port = running_server
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"http://{host}:{port}/missing.md")
    assert exc_info.value.code == 404


@pytest.fixture
def running_server_with_base_url(tmp_path):
    (tmp_path / "index.md").write_text("# Hello\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "README.md").write_text("# Sub\n", encoding="utf-8")

    handler_class = _make_handler_class(tmp_path, base_url="/docs")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]

    yield "127.0.0.1", port

    httpd.shutdown()
    thread.join()


def test_base_url_serves_page_under_prefix(running_server_with_base_url):
    host, port = running_server_with_base_url
    with urllib.request.urlopen(f"http://{host}:{port}/docs/index.md") as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        assert "<h1>Hello</h1>" in body


def test_base_url_prefixes_static_and_link_hrefs(running_server_with_base_url):
    host, port = running_server_with_base_url
    with urllib.request.urlopen(f"http://{host}:{port}/docs/index.md") as resp:
        body = resp.read().decode("utf-8")
        assert 'href="/docs/__markserve_static__/style.css"' in body
        assert 'href="/docs/"' in body


def test_base_url_serves_static_css(running_server_with_base_url):
    host, port = running_server_with_base_url
    with urllib.request.urlopen(f"http://{host}:{port}/docs/__markserve_static__/style.css") as resp:
        assert resp.status == 200


def test_base_url_root_without_trailing_slash_redirects(running_server_with_base_url):
    host, port = running_server_with_base_url
    conn = http.client.HTTPConnection(host, port)
    try:
        conn.request("GET", "/docs")
        resp = conn.getresponse()
        assert resp.status == 301
        assert resp.getheader("Location") == "/docs/"
        resp.read()
    finally:
        conn.close()


def test_base_url_rejects_paths_outside_prefix(running_server_with_base_url):
    host, port = running_server_with_base_url
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"http://{host}:{port}/index.md")
    assert exc_info.value.code == 404

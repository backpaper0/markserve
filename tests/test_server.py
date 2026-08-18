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

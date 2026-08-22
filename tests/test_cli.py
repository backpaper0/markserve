import pytest

from markserve.cli import _build_parser, _normalize_base_url, _resolve_base_url


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/docs", "/docs"),
        ("docs", "/docs"),
        ("/docs/", "/docs"),
        ("/", ""),
        ("https://example.com/docs", "/docs"),
    ],
)
def test_normalize_base_url(value, expected):
    assert _normalize_base_url(value) == expected


def test_resolve_base_url_defaults_to_empty():
    assert _resolve_base_url(None, False, 8000) == ""


def test_resolve_base_url_uses_explicit_base_url():
    assert _resolve_base_url("/docs", False, 8000) == "/docs"


def test_resolve_base_url_code_server_uses_proxy_port():
    assert _resolve_base_url(None, True, 9999) == "/proxy/9999"


def test_base_url_and_code_server_are_mutually_exclusive():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--base-url", "/docs", "--code-server"])

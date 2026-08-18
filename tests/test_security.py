import pytest

from markserve.security import PathTraversalError, safe_resolve


def test_safe_resolve_normal(tmp_path):
    (tmp_path / "a.md").write_text("hi", encoding="utf-8")
    result = safe_resolve(tmp_path, "/a.md")
    assert result == tmp_path / "a.md"


def test_safe_resolve_root(tmp_path):
    result = safe_resolve(tmp_path, "/")
    assert result == tmp_path


def test_safe_resolve_dotdot_rejected(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_resolve(tmp_path, "/../etc/passwd")


def test_safe_resolve_encoded_dotdot_rejected(tmp_path):
    with pytest.raises(PathTraversalError):
        safe_resolve(tmp_path, "/%2e%2e/etc/passwd")


def test_safe_resolve_symlink_escape_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (root / "escape").symlink_to(outside)

    with pytest.raises(PathTraversalError):
        safe_resolve(root, "/escape/secret.txt")

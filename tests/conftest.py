from pathlib import Path

import pytest


@pytest.fixture
def sample_root(tmp_path: Path) -> Path:
    (tmp_path / "index.md").write_text("# Hello\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("plain text\n", encoding="utf-8")
    guide = tmp_path / "guide"
    guide.mkdir()
    (guide / "nested.md").write_text("# Nested\n", encoding="utf-8")
    return tmp_path

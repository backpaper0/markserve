from markserve.tree import build_tree


def test_directory_first_then_alphabetical(tmp_path):
    (tmp_path / "b.md").write_text("x", encoding="utf-8")
    (tmp_path / "a_dir").mkdir()
    (tmp_path / "a.md").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path)

    names = [c.name for c in result.root.children]
    assert names == ["a_dir", "a.md", "b.md"]


def test_dotfiles_are_excluded(tmp_path):
    (tmp_path / ".hidden").write_text("x", encoding="utf-8")
    (tmp_path / "visible.md").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path)

    names = [c.name for c in result.root.children]
    assert names == ["visible.md"]


def test_current_file_ancestors_are_open(tmp_path):
    guide = tmp_path / "guide"
    guide.mkdir()
    (guide / "nested.md").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path, current_rel_path="guide/nested.md")

    guide_node = result.root.children[0]
    assert guide_node.name == "guide"
    assert guide_node.is_open is True

    nested_node = guide_node.children[0]
    assert nested_node.name == "nested.md"
    assert nested_node.is_current is True


def test_per_directory_limit_adds_truncation_marker(tmp_path):
    for i in range(10):
        (tmp_path / f"file{i}.md").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path, max_entries_per_dir=3, max_total_nodes=100)

    assert result.truncated is True
    assert len(result.root.children) == 4
    marker = result.root.children[-1]
    assert marker.is_truncated_marker is True


def test_total_node_limit_stops_walk(tmp_path):
    for i in range(10):
        (tmp_path / f"file{i}.md").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path, max_entries_per_dir=100, max_total_nodes=3)

    assert result.truncated is True
    real_nodes = [c for c in result.root.children if not c.is_truncated_marker]
    assert len(real_nodes) == 3

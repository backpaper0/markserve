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


def test_gitignore_excludes_matching_entries(tmp_path):
    (tmp_path / ".gitignore").write_text("node_modules/\n*.log\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("x", encoding="utf-8")
    (tmp_path / "debug.log").write_text("x", encoding="utf-8")
    (tmp_path / "visible.md").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path)

    names = [c.name for c in result.root.children]
    assert names == ["visible.md"]


def test_gitignore_negation_within_same_file(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\n!keep.log\n", encoding="utf-8")
    (tmp_path / "drop.log").write_text("x", encoding="utf-8")
    (tmp_path / "keep.log").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path)

    names = [c.name for c in result.root.children]
    assert names == ["keep.log"]


def test_nested_gitignore_only_applies_within_its_own_subtree(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / ".gitignore").write_text("skip.txt\n", encoding="utf-8")
    (tmp_path / "a" / "skip.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "skip.txt").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path)

    a_node = next(c for c in result.root.children if c.name == "a")
    b_node = next(c for c in result.root.children if c.name == "b")
    assert [c.name for c in a_node.children] == []
    assert [c.name for c in b_node.children] == ["skip.txt"]


def test_respect_gitignore_false_disables_filtering(tmp_path):
    (tmp_path / ".gitignore").write_text("visible.md\n", encoding="utf-8")
    (tmp_path / "visible.md").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path, respect_gitignore=False)

    names = [c.name for c in result.root.children]
    assert names == ["visible.md"]


def test_total_node_limit_is_fair_across_top_level_dirs(tmp_path):
    for i in range(10):
        d = tmp_path / f"dir{i}"
        d.mkdir()
        for j in range(5):
            (d / f"file{j}.md").write_text("x", encoding="utf-8")

    result = build_tree(tmp_path, max_entries_per_dir=100, max_total_nodes=15)

    assert result.truncated is True
    top_level_names = [c.name for c in result.root.children]
    assert top_level_names == [f"dir{i}" for i in range(10)]


def test_current_file_is_reachable_even_under_tight_budget(tmp_path):
    for i in range(20):
        (tmp_path / f"noise{i}").mkdir()
        (tmp_path / f"noise{i}" / "f.md").write_text("x", encoding="utf-8")
    target_dir = tmp_path / "z_target"
    target_dir.mkdir()
    (target_dir / "current.md").write_text("x", encoding="utf-8")

    result = build_tree(
        tmp_path,
        current_rel_path="z_target/current.md",
        max_entries_per_dir=100,
        max_total_nodes=3,
    )

    target_node = next(c for c in result.root.children if c.name == "z_target")
    assert target_node.is_open is True
    current_node = next(c for c in target_node.children if c.name == "current.md")
    assert current_node.is_current is True
    assert result.truncated is True

"""サイドバーに表示するファイルツリーの構築。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 1ディレクトリあたりの表示上限。誤ってnode_modules等の巨大なディレクトリを
# 開いてしまった場合に、ページやサーバーが固まる事故を防ぐための安全弁。
MAX_ENTRIES_PER_DIR = 200

# ツリー全体のノード総数の上限。上限に達したら以降の走査を打ち切る。
MAX_TOTAL_NODES = 3000


@dataclass
class TreeNode:
    name: str
    rel_path: str
    is_dir: bool
    children: list["TreeNode"] = field(default_factory=list)
    is_open: bool = False
    is_current: bool = False
    is_truncated_marker: bool = False


@dataclass
class TreeResult:
    root: TreeNode
    truncated: bool


def build_tree(
    root: Path,
    current_rel_path: str | None = None,
    max_entries_per_dir: int = MAX_ENTRIES_PER_DIR,
    max_total_nodes: int = MAX_TOTAL_NODES,
) -> TreeResult:
    """rootディレクトリ配下のファイルツリーを構築する。

    current_rel_path（現在表示中のファイルの root からの相対パス）が指定されている場合、
    その祖先ディレクトリは is_open=True になる。
    """
    current_parts = _split(current_rel_path)
    state = _WalkState(max_entries_per_dir=max_entries_per_dir, max_total_nodes=max_total_nodes)

    root_node = TreeNode(name=root.name or str(root), rel_path="", is_dir=True, is_open=True)
    _walk(root, root_node, current_parts, state)

    return TreeResult(root=root_node, truncated=state.truncated)


def _split(rel_path: str | None) -> list[str]:
    if not rel_path:
        return []
    return [part for part in rel_path.split("/") if part]


@dataclass
class _WalkState:
    max_entries_per_dir: int
    max_total_nodes: int
    node_count: int = 0
    truncated: bool = False


def _walk(dir_path: Path, node: TreeNode, current_parts: list[str], state: _WalkState) -> None:
    if state.node_count >= state.max_total_nodes:
        state.truncated = True
        return

    try:
        entries = [e for e in os.scandir(dir_path) if not e.name.startswith(".")]
    except OSError:
        return

    entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))

    shown = entries[: state.max_entries_per_dir]
    omitted = len(entries) - len(shown)

    for entry in shown:
        if state.node_count >= state.max_total_nodes:
            state.truncated = True
            break

        state.node_count += 1
        is_dir = entry.is_dir(follow_symlinks=False)
        rel_path = f"{node.rel_path}/{entry.name}" if node.rel_path else entry.name
        child = TreeNode(name=entry.name, rel_path=rel_path, is_dir=is_dir)

        if is_dir:
            is_ancestor = bool(current_parts) and current_parts[0] == entry.name
            child.is_open = is_ancestor
            next_parts = current_parts[1:] if is_ancestor else []
            _walk(Path(entry.path), child, next_parts, state)
        else:
            child.is_current = current_parts == [entry.name]

        node.children.append(child)

    if omitted > 0:
        node.children.append(
            TreeNode(
                name=f"他 {omitted} 件を省略",
                rel_path="",
                is_dir=False,
                is_truncated_marker=True,
            )
        )
        state.truncated = True

"""サイドバーに表示するファイルツリーの構築。"""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from pathspec import PathSpec

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
    respect_gitignore: bool = True,
) -> TreeResult:
    """rootディレクトリ配下のファイルツリーを構築する。

    current_rel_path（現在表示中のファイルの root からの相対パス）が指定されている場合、
    その祖先ディレクトリは is_open=True になり、node_count の上限に関わらず必ず生成される。

    ディレクトリの展開は幅優先(BFS)で行う。ツリー全体のノード総数上限
    (max_total_nodes)に達した場合でも、浅い階層は既に展開済みのため、
    一部のディレクトリだけが丸ごと表示から消えることがない。
    """
    current_parts = _split(current_rel_path)
    state = _WalkState(
        max_entries_per_dir=max_entries_per_dir,
        max_total_nodes=max_total_nodes,
        respect_gitignore=respect_gitignore,
    )

    root_node = TreeNode(name=root.name or str(root), rel_path="", is_dir=True, is_open=True)

    queue: deque[_QueueItem] = deque()
    queue.append(_QueueItem(node=root_node, dir_path=root, current_parts=current_parts, ignore_stack=[]))
    while queue:
        _expand(queue.popleft(), queue, state)

    return TreeResult(root=root_node, truncated=state.truncated)


def _split(rel_path: str | None) -> list[str]:
    if not rel_path:
        return []
    return [part for part in rel_path.split("/") if part]


@dataclass
class _WalkState:
    max_entries_per_dir: int
    max_total_nodes: int
    respect_gitignore: bool = True
    node_count: int = 0
    truncated: bool = False


@dataclass
class _QueueItem:
    node: TreeNode
    dir_path: Path
    # このディレクトリより下で辿るべき、現在表示中ファイルへの残りのパス要素。
    # 空リストなら祖先チェーン外(=打ち切りの対象になりうる)。
    current_parts: list[str]
    ignore_stack: list[tuple[str, PathSpec]]


def _child_rel_path(parent_rel: str, name: str) -> str:
    return f"{parent_rel}/{name}" if parent_rel else name


def _load_gitignore(dir_path: Path) -> PathSpec | None:
    try:
        text = (dir_path / ".gitignore").read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    return PathSpec.from_lines("gitignore", text.splitlines())


def _is_ignored(rel_path: str, is_dir: bool, ignore_stack: list[tuple[str, PathSpec]]) -> bool:
    # 親の.gitignoreによる除外を、子の.gitignoreの`!`で再インクルードすることはサポートしない。
    # (gitも除外済みディレクトリの中は基本的に走査しないため、実用上の乖離は小さい)
    ignored = False
    for base_rel, spec in ignore_stack:
        sub = rel_path[len(base_rel) + 1 :] if base_rel else rel_path
        check_path = f"{sub}/" if is_dir else sub
        if spec.match_file(check_path):
            ignored = True
    return ignored


def _per_dir_marker(omitted: int) -> TreeNode:
    return TreeNode(
        name=f"他 {omitted} 件を省略",
        rel_path="",
        is_dir=False,
        is_truncated_marker=True,
    )


def _budget_marker() -> TreeNode:
    return TreeNode(
        name="…(表示上限のため、このフォルダの中身は省略されました)",
        rel_path="",
        is_dir=False,
        is_truncated_marker=True,
    )


def _dir_probably_nonempty(dir_path: Path) -> bool:
    try:
        with os.scandir(dir_path) as it:
            return next(it, None) is not None
    except OSError:
        return False


def _expand(item: _QueueItem, queue: deque[_QueueItem], state: _WalkState) -> None:
    is_mandatory_dir = bool(item.current_parts)

    if state.node_count >= state.max_total_nodes and not is_mandatory_dir:
        if _dir_probably_nonempty(item.dir_path):
            item.node.children.append(_budget_marker())
            state.truncated = True
        return

    try:
        entries = [e for e in os.scandir(item.dir_path) if not e.name.startswith(".")]
    except OSError:
        return

    ignore_stack = item.ignore_stack
    if state.respect_gitignore:
        spec = _load_gitignore(item.dir_path)
        if spec is not None:
            ignore_stack = [*ignore_stack, (item.node.rel_path, spec)]
        if ignore_stack:
            entries = [
                e
                for e in entries
                if not _is_ignored(
                    _child_rel_path(item.node.rel_path, e.name),
                    e.is_dir(follow_symlinks=False),
                    ignore_stack,
                )
            ]

    entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))

    shown = entries[: state.max_entries_per_dir]
    omitted = len(entries) - len(shown)

    for entry in shown:
        entry_is_mandatory = bool(item.current_parts) and item.current_parts[0] == entry.name
        if state.node_count >= state.max_total_nodes and not entry_is_mandatory:
            # break ではなく continue: ソート順で祖先チェーン上のエントリが
            # 後方にあっても、予算を使い切っていない他のエントリを飛ばして必ず生成する。
            state.truncated = True
            continue

        state.node_count += 1
        is_dir = entry.is_dir(follow_symlinks=False)
        rel_path = _child_rel_path(item.node.rel_path, entry.name)
        child = TreeNode(name=entry.name, rel_path=rel_path, is_dir=is_dir)

        if is_dir:
            child.is_open = entry_is_mandatory
            next_parts = item.current_parts[1:] if entry_is_mandatory else []
            queue.append(
                _QueueItem(
                    node=child,
                    dir_path=Path(entry.path),
                    current_parts=next_parts,
                    ignore_stack=ignore_stack,
                )
            )
        else:
            child.is_current = item.current_parts == [entry.name]

        item.node.children.append(child)

    if omitted > 0:
        item.node.children.append(_per_dir_marker(omitted))
        state.truncated = True

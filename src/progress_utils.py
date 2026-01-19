# progress_utils.py
"""
进度管理工具模块
用于跟踪和恢复文件处理进度
"""

import os


# ============ 进度标记常量 ============

PROGRESS_MARKER_PREFIX = "<!-- PROCESSING: segment="
PROGRESS_MARKER_SUFFIX = "-->"


# ============ 进度标记操作 ============

def make_progress_marker(segment_index: int, total: int, status: str) -> str:
    """
    创建进度标记

    参数:
        segment_index: 当前段落索引
        total: 总段落数
        status: 状态 ("processing", "complete", "failed")

    返回:
        进度标记字符串
    """
    return f"{PROGRESS_MARKER_PREFIX}{segment_index}/{total}, status={status} {PROGRESS_MARKER_SUFFIX}"


def parse_progress_marker(content: str) -> tuple[int, int, str] | None:
    """
    解析进度标记

    参数:
        content: 文件内容（从末尾读取的部分内容）

    返回:
        (index, total, status) 元组，如果未找到标记则返回 None
    """
    lines = content.strip().split('\n')
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith(PROGRESS_MARKER_PREFIX) and stripped.endswith(PROGRESS_MARKER_SUFFIX):
            try:
                marker = stripped[len(PROGRESS_MARKER_PREFIX):-len(PROGRESS_MARKER_SUFFIX)]
                parts = marker.split(', ')
                segment_part = parts[0]
                status_part = parts[1] if len(parts) > 1 else "processing"
                index, total = segment_part.split('/')
                status = status_part.split('=')[1].strip() if '=' in status_part else "processing"
                return int(index), int(total), status
            except (ValueError, IndexError):
                continue
    return None


def load_progress(output_path: str, total_segments: int) -> tuple[int, str]:
    """
    检查输出文件的进度标记

    参数:
        output_path: 输出文件路径
        total_segments: 总段落数

    返回:
        (start_index, status) - 开始处理的段落索引和状态
        status: "new", "processing", "complete", "failed", "unknown"
    """
    if not os.path.exists(output_path):
        return 0, "new"

    # 读取文件末尾 1KB（优化性能）
    with open(output_path, 'rb') as f:
        f.seek(max(0, os.path.getsize(output_path) - 1024))
        tail_content = f.read().decode('utf-8', errors='ignore')

    marker = parse_progress_marker(tail_content)
    if marker is None:
        # 无标记：检查文件是否有内容
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if content:
            # 有内容但无标记：可能是旧版本文件，尝试用旧方法估算
            estimated = content.count('\n\n') + 1
            return min(estimated, total_segments), "unknown"
        return 0, "new"

    index, total, status = marker
    if status == "complete":
        return total_segments, "complete"
    if status == "failed":
        return index, "failed"
    # processing 状态：标记显示正在处理中，可能需要重试当前段落
    return index, "processing"


# ============ 文件标记清理工具 ============

def remove_trailing_markers(lines: list[str]) -> list[str]:
    """
    从行列表末尾删除所有进度标记行

    参数:
        lines: 文件内容行列表

    返回:
        删除标记后的行列表
    """
    while lines and lines[-1].strip().startswith(PROGRESS_MARKER_PREFIX):
        lines.pop()
    return lines


def rewrite_file_without_marker(file_handle, content: str) -> None:
    """
    读取文件内容，删除末尾标记，重新写入

    参数:
        file_handle: 已打开的文件句柄（读写模式）
        content: 当前文件内容
    """
    lines = content.split('\n')
    lines = remove_trailing_markers(lines)
    file_handle.seek(0)
    file_handle.truncate()
    file_handle.write('\n'.join(lines))
    file_handle.flush()

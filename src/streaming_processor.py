# streaming_processor.py
"""
流式处理模块
提供通用的流式写入和处理功能
"""

from collections.abc import Callable

from openai import OpenAI

from progress_utils import (
    make_progress_marker,
    remove_trailing_markers,
)
from api_utils import call_deepseek_api


def process_segments_streaming(
    client: OpenAI,
    system_prompt: str,
    segments: list[str],
    output_path: str,
    start_index: int = 0,
    start_status: str = "new",
    content_transformer: Callable[[str, int], str] | None = None,
) -> None:
    """
    流式处理段落并立即写入文件（支持进度标记）

    参数:
        client: OpenAI 客户端实例
        system_prompt: 系统提示词
        segments: 分段文本列表
        output_path: 输出文件路径
        start_index: 开始处理的段落索引
        start_status: 起始状态 ("new", "processing", "failed")
        content_transformer: 可选的内容转换函数，接收 (segment, index) 返回用于 API 的内容

    每处理完一个段落立即写入文件并 flush，确保容错性
    """
    total = len(segments)
    file_handle = None

    def read_and_remove_marker(handle, content: str) -> list[str]:
        """读取文件内容，去掉末尾标记"""
        lines = content.split('\n')
        lines = remove_trailing_markers(lines)
        return lines

    def write_lines(handle, lines: list[str]) -> None:
        """将行列表写入文件"""
        handle.seek(0)
        handle.truncate()
        handle.write('\n'.join(lines))
        handle.flush()

    def prepare_segment_content(segment: str, index: int) -> str:
        """准备用于 API 调用的内容"""
        if content_transformer:
            return content_transformer(segment, index)
        return segment

    try:
        # 根据起始状态决定文件模式
        mode = 'w+' if start_status == "new" else 'r+'
        file_handle = open(output_path, mode, encoding='utf-8')

        # 如果不是从头开始，需要删除末尾的旧标记
        if start_index > 0 and start_status in ("processing", "failed"):
            rewrite_file_without_marker(file_handle, file_handle.read())

        for i in range(start_index, total):
            print(f"\n正在处理段落 {i + 1}/{total}...")

            # 写入当前处理标记
            file_handle.write(f"\n{make_progress_marker(i, total, 'processing')}")
            file_handle.flush()

            try:
                user_content = prepare_segment_content(segments[i], i)
                result = call_deepseek_api(client, system_prompt, user_content)

                # 删除标记并写入结果
                # 如果是第一个段落且是新文件，直接写入结果（无需读取）
                if i == 0 and start_status == "new":
                    lines = []
                else:
                    # 修复：在读取前重置文件指针到文件开头
                    file_handle.seek(0)
                    lines = read_and_remove_marker(file_handle, file_handle.read())

                # 添加段落分隔符和内容
                if i > 0 or lines:
                    lines.append("")
                lines.append(result)

                write_lines(file_handle, lines)
                print(f"  段落 {i + 1} 处理完成")

            except Exception as e:
                print(f"  段落 {i + 1} 处理失败: {e}")
                handle_segment_failure(file_handle, i, total, segments[i])

        # 所有段落处理完成，标记完成
        write_completion_marker(file_handle, total)

    finally:
        if file_handle:
            file_handle.close()


def rewrite_file_without_marker(file_handle, content: str) -> None:
    """读取文件内容，删除末尾标记，重新写入"""
    lines = content.split('\n')
    lines = remove_trailing_markers(lines)
    file_handle.seek(0)
    file_handle.truncate()
    file_handle.write('\n'.join(lines))
    file_handle.flush()


def handle_segment_failure(file_handle, index: int, total: int, segment: str) -> None:
    """处理段落失败的情况"""
    # 读取当前内容并删除处理标记
    file_handle.seek(0)
    content = file_handle.read()
    lines = content.split('\n')
    lines = remove_trailing_markers(lines)

    # 写入失败标记
    lines.append(make_progress_marker(index, total, "failed"))
    file_handle.seek(0)
    file_handle.truncate()
    file_handle.write('\n'.join(lines))
    file_handle.flush()

    # 写入失败内容
    if len(lines) > 1:
        file_handle.write("\n\n")
    file_handle.write(f"[处理失败，保留原文]\n\n{segment}")
    file_handle.flush()


def write_completion_marker(file_handle, total: int) -> None:
    """写入完成标记"""
    if file_handle is None:
        return

    file_handle.seek(0)
    content = file_handle.read()
    lines = content.split('\n')
    lines = remove_trailing_markers(lines)

    file_handle.seek(0)
    file_handle.truncate()
    file_handle.write('\n'.join(lines))
    file_handle.write(f"\n{make_progress_marker(total, total, 'complete')}")
    file_handle.flush()

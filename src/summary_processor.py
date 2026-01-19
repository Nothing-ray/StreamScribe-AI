# summary_processor.py
"""
直播文稿摘要处理程序
功能：支持带时间戳和纯文本两种输入格式，调用 DeepSeek API 进行两阶段摘要
"""

import sys
from pathlib import Path
from typing import Literal

from openai import OpenAI

from preprocessor import (
    segment_with_time_ranges,
    segment_by_spaces,
    segment_with_srt_timestamps,
    normalize_whitespace,
    detect_file_format,
    process_srt_with_time,
    FormatType,
)
from api_utils import create_client, call_deepseek_api
from config_utils import initialize_project_setup, load_prompt
from progress_utils import load_progress
from streaming_processor import process_segments_streaming


# ============ 配置常量 ============

DEFAULT_MIN_SPACES = 50
DEFAULT_MAX_SPACES = 60


# ============ 格式检测与分段 ============

def adaptive_segment(
    text: str,
    min_spaces: int = DEFAULT_MIN_SPACES,
    max_spaces: int = DEFAULT_MAX_SPACES,
) -> tuple[FormatType, list[str]]:
    """
    自适应分段：根据文本格式选择合适的分段方式

    支持格式：
    - timestamp: [0.5s --> 2.3s] 标准时间戳格式
    - srt_timestamp: [00:00:00.000 --> 00:00:03.080] SRT时间戳格式
    - srt: 标准SRT字幕格式
    - plain: 纯文本

    参数:
        text: 原始文本
        min_spaces: 每段最少空格数
        max_spaces: 每段最多空格数

    返回:
        (format_type, segments)
        - format_type: "timestamp", "srt_timestamp", "srt" 或 "plain"
        - segments: 分段后的文本列表
    """
    import re

    TIMESTAMP_PATTERN = r'\[\d+\.\d+s\s*-->\s*\d+\.\d+s\]'
    SRT_TIMESTAMP_PATTERN = r'\[(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\]'

    # 检测格式
    if re.search(SRT_TIMESTAMP_PATTERN, text):
        format_type = "srt_timestamp"
    elif re.search(r'^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', text, re.MULTILINE):
        format_type = "srt"
    elif re.search(TIMESTAMP_PATTERN, text):
        format_type = "timestamp"
    else:
        format_type = "plain"

    # 根据格式分段
    if format_type == "timestamp":
        print("检测到标准时间戳格式，使用时间范围分段")
        segments = segment_with_time_ranges(text, min_spaces, max_spaces)
    elif format_type == "srt_timestamp":
        print("检测到 SRT 时间戳格式，使用 SRT 时间范围分段")
        segments = segment_with_srt_timestamps(text, min_spaces, max_spaces)
    else:  # srt 或 plain
        format_name = "SRT 字幕" if format_type == "srt" else "纯文本"
        print(f"检测到 {format_name} 格式，使用空格分段")
        clean_text = normalize_whitespace(text)
        segments = segment_by_spaces(clean_text, min_spaces, max_spaces)

    return format_type, segments


# ============ 段落内容提取 ============

def extract_segment_content(segment: str, format_type: FormatType) -> str:
    """
    从段落中提取用于 API 调用的内容

    对于带时间戳的格式，将时间范围和内容分离
    对于纯文本格式，直接返回原文

    参数:
        segment: 段落文本
        format_type: 文本格式类型

    返回:
        处理后的内容文本
    """
    if format_type in ("timestamp", "srt_timestamp", "srt"):
        lines = segment.split('\n', 1)
        time_range = lines[0]
        content = lines[1] if len(lines) > 1 else ""
        return f"时间范围：{time_range}\n\n内容：\n{content}"
    return segment


def create_content_transformer(format_type: FormatType):
    """
    创建内容转换函数用于流式处理

    参数:
        format_type: 文本格式类型

    返回:
        转换函数
    """
    def transformer(segment: str, index: int) -> str:
        return extract_segment_content(segment, format_type)
    return transformer


# ============ 摘要合并模块 ============

def build_merge_content(content: str, format_type: FormatType) -> str:
    """
    构造合并摘要的 prompt 内容

    参数:
        content: 各段落摘要内容
        format_type: 文本格式类型

    返回:
        合并 prompt 的完整内容
    """
    if format_type in ("timestamp", "srt_timestamp", "srt"):
        return f"""以下是按时间顺序排列的各时段摘要：

{content}

请将这些时段摘要整合成一篇完整的全文摘要，要求：
1. 保持时间线逻辑，展示内容在不同时间段的发展
2. 提炼核心主题和关键信息
3. 使用清晰的段落结构
4. 在适当位置引用时间范围"""
    # plain 格式
    return f"""以下是各段落的摘要：

{content}

请将这些段落摘要整合成一篇完整的全文摘要，要求：
1. 提炼核心主题和关键信息
2. 使用清晰的段落结构
3. 保持内容的连贯性和逻辑性"""


def merge_summaries(
    client: OpenAI,
    merge_prompt: str,
    segments_path: str,
    output_path: str,
    format_type: FormatType,
) -> None:
    """
    将段落摘要合并为最终全文摘要

    参数:
        client: OpenAI 客户端
        merge_prompt: 合并提示词
        segments_path: 段落摘要文件路径
        output_path: 最终输出路径
        format_type: "timestamp", "srt_timestamp", "srt" 或 "plain"
    """
    format_name = "时段" if format_type in ("timestamp", "srt_timestamp", "srt") else "段落"
    print(f"\n正在合并各{format_name}摘要...")

    with open(segments_path, 'r', encoding='utf-8') as f:
        content = f.read()

    merge_content = build_merge_content(content, format_type)

    print("正在生成最终全文摘要...")
    final_summary = call_deepseek_api(client, merge_prompt, merge_content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_summary)

    print(f"  最终摘要已保存到: {output_path}")


# ============ 主处理流程 ============

def process_summary(
    input_path: str,
    output_dir: Path,
    client: OpenAI,
    summary_prompt: str,
    merge_prompt: str,
    min_spaces: int = DEFAULT_MIN_SPACES,
    max_spaces: int = DEFAULT_MAX_SPACES,
) -> None:
    """
    完整的摘要处理流程

    支持格式：
    - .srt 文件（标准 SRT 字幕）
    - SRT 时间戳格式（.txt 中的 [00:00:00.000 --> 00:00:03.080]）
    - 标准时间戳格式（.txt 中的 [0.5s --> 2.3s]）
    - 纯文本

    参数:
        input_path: 输入文件路径
        output_dir: 输出目录路径
        client: OpenAI 客户端实例
        summary_prompt: 摘要提示词
        merge_prompt: 合并提示词
        min_spaces: 每段最少空格数
        max_spaces: 每段最多空格数
    """
    print(f"正在读取文件: {input_path}")

    # 检测文件格式
    file_format = detect_file_format(input_path)
    print(f"检测到文件格式: {file_format}")

    # 根据格式处理
    if file_format == "srt":
        print("使用 SRT 专用处理（保留时间范围）...")
        segments = process_srt_with_time(input_path, min_spaces, max_spaces)
        format_type = "srt"
        print(f"共生成 {len(segments)} 个段落")
    else:
        with open(input_path, 'r', encoding='utf-8') as f:
            original_text = f.read()

        print(f"原始文本长度: {len(original_text)} 字符")
        print(f"\n正在分段（每段 {min_spaces}-{max_spaces} 个空格）...")
        format_type, segments = adaptive_segment(original_text, min_spaces, max_spaces)
        print(f" 检测到格式: {format_type}")
        print(f" 共生成 {len(segments)} 个段落")

    # 计算输出路径
    input_path_obj = Path(input_path)
    segments_output = output_dir / f"{input_path_obj.stem}_segment_summaries.md"
    final_output = output_dir / f"{input_path_obj.stem}_final_summary.md"

    # 检查进度
    start_index, start_status = load_progress(str(segments_output), len(segments))

    if start_status == "complete":
        print("\n  摘要处理已完成！")
        merge_summaries(client, merge_prompt, str(segments_output), str(final_output), format_type)
        return

    if start_index > 0:
        print(f"\n检测到未完成的处理，将从段落 {start_index + 1} 继续...")
        print(f"已处理: {start_index}/{len(segments)} 个段落")
        print(f"状态: {start_status}")

    # 流式处理段落摘要
    print("\n" + "-" * 60)
    print("阶段 1: 处理各时段摘要（流式写入）")
    print("-" * 60)

    content_transformer = create_content_transformer(format_type)
    process_segments_streaming(
        client,
        summary_prompt,
        segments,
        str(segments_output),
        start_index,
        start_status,
        content_transformer,
    )

    # 生成最终摘要
    print("\n" + "-" * 60)
    print("阶段 2: 合并生成最终摘要")
    print("-" * 60)
    merge_summaries(client, merge_prompt, str(segments_output), str(final_output), format_type)


# ============ CLI 参数解析 ============

def parse_cli_args() -> tuple[str, int, int]:
    """
    解析命令行参数

    返回:
        (input_path, min_spaces, max_spaces)
    """
    if len(sys.argv) < 2:
        print("用法: python summary_processor.py <输入文件路径> [最小空格数] [最大空格数]")
        print("示例: python summary_processor.py input.txt 50 60")
        sys.exit(1)

    input_path = sys.argv[1]
    min_spaces = DEFAULT_MIN_SPACES
    max_spaces = DEFAULT_MAX_SPACES

    if len(sys.argv) >= 3:
        try:
            min_spaces = int(sys.argv[2])
        except ValueError:
            print(f"错误: 最小空格数必须是整数，得到 '{sys.argv[2]}'")
            sys.exit(1)

    if len(sys.argv) >= 4:
        try:
            max_spaces = int(sys.argv[3])
        except ValueError:
            print(f"错误: 最大空格数必须是整数，得到 '{sys.argv[3]}'")
            sys.exit(1)

    if min_spaces > max_spaces:
        print(f"错误: 最小空格数 ({min_spaces}) 不能大于最大空格数 ({max_spaces})")
        sys.exit(1)

    return input_path, min_spaces, max_spaces


# ============ 主程序 ============

def main() -> None:
    """主程序入口"""
    input_path, min_spaces, max_spaces = parse_cli_args()

    script_dir = Path(__file__).parent.parent
    config_dir = script_dir / "config"
    output_dir = script_dir / "output"

    print("=" * 60)
    print("直播文稿摘要处理程序")
    print("=" * 60)
    print(f"配置: 每段 {min_spaces}-{max_spaces} 个空格\n")

    try:
        print("正在初始化配置...")
        api_key_path = config_dir / "api_key.txt"
        summary_prompt_path = config_dir / "summary_prompt.md"
        merge_prompt_path = config_dir / "merge_prompt.md"

        api_key = initialize_project_setup(api_key_path, output_dir)
        summary_prompt = load_prompt(summary_prompt_path)
        merge_prompt = load_prompt(merge_prompt_path)

        print(f"  API key: {api_key[:10]}...")
        print(f"  摘要提示词: 已加载 ({len(summary_prompt)} 字符)")
        print(f"  合并提示词: 已加载 ({len(merge_prompt)} 字符)")

        print("\n正在初始化 DeepSeek 客户端...")
        client = create_client(api_key)
        print("  客户端初始化成功")

        print("\n" + "-" * 60)
        print("开始处理摘要")
        print("-" * 60)
        process_summary(input_path, output_dir, client, summary_prompt, merge_prompt, min_spaces, max_spaces)

        print("\n" + "=" * 60)
        print("摘要处理完成!")
        print("=" * 60)

        input_path_obj = Path(input_path)
        print(f"\n输出文件:")
        print(f"  - {output_dir / input_path_obj.stem}_segment_summaries.md (各时段摘要)")
        print(f"  - {output_dir / input_path_obj.stem}_final_summary.md (最终全文摘要)")

    except FileNotFoundError as e:
        print(f"\n错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n处理文件时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

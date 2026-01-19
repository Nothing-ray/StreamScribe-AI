# transcript_processor.py
"""
直播文稿处理程序（完整版）
功能：去除时间戳、分段、调用 DeepSeek API 处理、输出 Markdown
"""

import sys
from pathlib import Path

from openai import OpenAI

from preprocessor import (
    remove_timestamps,
    segment_by_spaces,
    detect_file_format,
    process_srt_plain,
)
from api_utils import create_client, call_deepseek_api
from config_utils import initialize_project_setup, load_prompt
from progress_utils import load_progress
from streaming_processor import process_segments_streaming


# ============ 配置常量 ============

DEFAULT_MIN_SPACES = 50
DEFAULT_MAX_SPACES = 60


# ============ 预处理模块 ============

def preprocess_file(input_path: str, min_spaces: int = DEFAULT_MIN_SPACES,
                   max_spaces: int = DEFAULT_MAX_SPACES) -> list[str]:
    """
    预处理文件：去除时间戳并分段

    支持格式：
    - .srt 文件（标准 SRT 字幕）
    - SRT 时间戳格式（.txt 中的 [00:00:00.000 --> 00:00:03.080]）
    - 标准时间戳格式（.txt 中的 [0.5s --> 2.3s]）
    - 纯文本

    参数:
        input_path: 输入文件路径
        min_spaces: 每段最少空格数
        max_spaces: 每段最多空格数

    返回:
        分段后的文本列表
    """
    import os

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"文件不存在: {input_path}")

    print(f"正在读取文件: {input_path}")

    # 检测文件格式
    file_format = detect_file_format(input_path)
    print(f"检测到文件格式: {file_format}")

    # 根据格式选择处理方式
    if file_format == "srt":
        print("\n检测到 SRT 字幕文件，提取纯文本...")
        cleaned_text = process_srt_plain(input_path)
    else:
        with open(input_path, 'r', encoding='utf-8') as f:
            original_text = f.read()

        print(f"原始文本长度: {len(original_text)} 字符")
        print("\n正在去除时间戳...")
        cleaned_text = remove_timestamps(original_text)

    print(f"处理后文本长度: {len(cleaned_text)} 字符")
    print(f"\n正在分段（每段 {min_spaces}-{max_spaces} 个空格）...")
    segments = segment_by_spaces(cleaned_text, min_spaces, max_spaces)

    return segments


# ============ CLI 参数解析 ============

def parse_cli_args() -> tuple[str, int, int]:
    """
    解析命令行参数

    返回:
        (input_path, min_spaces, max_spaces)
    """
    if len(sys.argv) < 2:
        print("用法: python transcript_processor.py <输入文件路径> [最小空格数] [最大空格数]")
        print("示例: python transcript_processor.py input.txt 50 60")
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
    print("直播文稿处理程序")
    print("=" * 60)
    print(f"配置: 每段 {min_spaces}-{max_spaces} 个空格\n")

    try:
        print("正在初始化配置...")
        api_key_path = config_dir / "api_key.txt"
        prompt_path = config_dir / "transcript_prompt.md"

        api_key = initialize_project_setup(api_key_path, output_dir)
        system_prompt = load_prompt(prompt_path)

        print(f"  API key: {api_key[:10]}...")
        print(f"  提示词: 已加载 ({len(system_prompt)} 字符)")

        print("\n正在初始化 DeepSeek 客户端...")
        client = create_client(api_key)
        print("  客户端初始化成功")

        print("\n" + "-" * 60)
        print("阶段 1: 预处理")
        print("-" * 60)
        segments = preprocess_file(input_path, min_spaces, max_spaces)
        print(f"\n预处理完成，共 {len(segments)} 个段落")

        input_path_obj = Path(input_path)
        output_path = output_dir / f"{input_path_obj.stem}_processed.md"

        start_index, start_status = load_progress(str(output_path), len(segments))

        if start_status == "complete":
            print("\n  文件已处理完成！")
            print(f"\n结果已保存到: {output_path}")
            return

        if start_index > 0:
            print(f"\n检测到未完成的处理，将从段落 {start_index + 1} 继续...")
            print(f"已处理: {start_index}/{len(segments)} 个段落")
            print(f"状态: {start_status}")

        print("\n" + "-" * 60)
        print("阶段 2: API 处理（流式写入）")
        print("-" * 60)
        process_segments_streaming(client, system_prompt, segments, str(output_path), start_index, start_status)
        print(f"\n结果已保存到: {output_path}")

        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)

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

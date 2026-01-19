# preprocessor.py
"""
通用文本处理器
支持格式: 现有时间戳、SRT字幕、纯文本
"""

import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Literal, Union, Callable

import pysrt

# ============ 类型定义 ============

FormatType = Literal["timestamp", "srt_timestamp", "srt", "plain"]
ProcessMode = Literal["plain", "with-time", "slice"]

TimestampInfo = Tuple[int, float, float]  # (end_position, start_time, end_time)
TimeDict = dict[str, Union[int, float]]

# 常量
TIMESTAMP_PATTERN = r'\[(\d+\.\d+)s\s*-->\s*(\d+\.\d+)s\]'  # [0.5s --> 2.3s] 格式
SRT_TIMESTAMP_PATTERN = r'\[(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\]'  # [00:00:00.000 --> 00:00:03.080] 格式（支持逗号和点）
SRT_TIME_PATTERN = r'^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}'  # 标准 SRT 字幕文件格式


# ============ 模块导出声明 ============

__all__ = [
    # 类型
    'FormatType',
    'ProcessMode',
    'TimestampInfo',
    'TimeDict',
    # 基础工具
    'normalize_whitespace',
    'remove_timestamps',
    'read_file_content',
    # 时间处理
    'extract_timestamps',
    'find_timestamp_at_position',
    'format_seconds',
    'format_time_range',
    'parse_time_input',
    'time_dict_to_seconds',
    # 分段功能
    'segment_by_spaces',
    'segment_with_time_ranges',
    'segment_text_by_spaces',
    # 格式检测
    'detect_file_format',
    'detect_text_format',
    # SRT处理
    'load_srt_file',
    'srt_time_to_seconds',
    'process_srt_plain',
    'process_srt_with_time',
    'process_srt_slice',
    # SRT 时间戳格式支持
    'SRT_TIMESTAMP_PATTERN',
    'srt_timestamp_to_seconds',
    'extract_srt_timestamps',
    'segment_with_srt_timestamps',
]


# ============ 帮助信息 ============

def print_help() -> None:
    """打印完整帮助信息"""
    print("""
通用文本处理器 v1.0
支持格式: 现有时间戳、SRT字幕、纯文本

用法: python preprocessor.py <输入文件> [选项]

选项:
  -h, --help              显示完整帮助信息
  --mode <模式>           处理模式 (默认: with-time)
                          可用模式:
                            plain      - 提取纯文本（去除所有时间戳）
                            with-time  - 保留时间范围分段
                            slice      - 时间范围切片（仅SRT格式）

  --min <数量>            每段最少空格数 (默认: 50)
  --max <数量>            每段最多空格数 (默认: 60)
  --start <时间>          切片开始时间（仅slice模式）
  --end <时间>            切片结束时间（仅slice模式）

时间格式支持 (用于 --start/--end):
  SS              纯秒数 (如: 90)
  MM:SS           分:秒 (如: 2:30)
  HH:MM:SS,mmm    SRT格式 (如: 00:02:30,500)
  MMmSSs          分秒格式 (如: 2m30s)

示例:
  python preprocessor.py input.txt
  python preprocessor.py input.txt --mode plain
  python preprocessor.py subtitles.srt --mode with-time --min 40 --max 50
  python preprocessor.py subtitles.srt --mode slice --start 2m30s --end 5m45s

输出文件保存在: output/ 目录
""")


# ============ 基础工具函数 ============

def normalize_whitespace(text: str) -> str:
    """规范化空格：换行转空格，去除多余空格"""
    text = text.replace('\n', ' ')
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def remove_timestamps(text: str) -> str:
    """
    去除文本中的时间戳并规范化空格

    支持两种时间戳格式：
    - [0.5s --> 2.3s]
    - [00:00:00.000 --> 00:00:03.080]

    参数:
        text: 原始文本（可能包含时间戳）

    返回:
        去除时间戳并规范化后的文本
    """
    # 先去除 SRT 时间戳
    clean_text = re.sub(SRT_TIMESTAMP_PATTERN, ' ', text)
    # 再去除标准时间戳
    clean_text = re.sub(TIMESTAMP_PATTERN, ' ', clean_text)
    return normalize_whitespace(clean_text)


def srt_timestamp_to_seconds(srt_time: str) -> float:
    """
    将 SRT 时间戳格式 (HH:MM:SS,mmm 或 HH:MM:SS.mmm) 转换为秒数

    参数:
        srt_time: SRT 时间戳字符串，如 "00:00:03,080" 或 "00:00:03.080"

    返回:
        秒数 (浮点数)
    """
    parts = srt_time.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    # 支持逗号和点两种分隔符
    sec_ms = parts[2].replace(',', '.').split('.')
    seconds = int(sec_ms[0])
    milliseconds = int(sec_ms[1])
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0


def extract_srt_timestamps(text: str) -> List[Tuple[int, float, float, str]]:
    """
    提取 SRT 格式的时间戳及其位置

    参数:
        text: 原始文本（包含 SRT 时间戳）

    返回:
        [(end_position, start_time, end_time, original_timestamp), ...]
    """
    results: List[Tuple[int, float, float, str]] = []
    for match in re.finditer(SRT_TIMESTAMP_PATTERN, text):
        start_time_str = match.group(1)
        end_time_str = match.group(2)
        start_time = srt_timestamp_to_seconds(start_time_str)
        end_time = srt_timestamp_to_seconds(end_time_str)
        original_timestamp = match.group(0)
        results.append((match.end(), start_time, end_time, original_timestamp))
    return results


def read_file_content(file_path: str) -> str:
    """读取文件内容，自动检测编码"""
    encodings = ('utf-8', 'gbk', 'latin-1')
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    # 如果所有编码都失败，使用 latin-1 作为最后的回退
    with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
        return f.read()


def time_dict_to_seconds(time_dict: TimeDict) -> float:
    """将时间字典转换为秒数"""
    return (
        time_dict.get('hours', 0) * 3600 +
        time_dict.get('minutes', 0) * 60 +
        time_dict.get('seconds', 0) +
        time_dict.get('milliseconds', 0) / 1000.0
    )


# ============ 格式检测模块 ============

def detect_file_format(file_path: str) -> FormatType:
    """
    自动检测输入文件格式

    参数:
        file_path: 文件路径

    返回:
        "timestamp" - 现有时间戳格式 [0.5s --> 2.3s]
        "srt_timestamp" - SRT时间戳格式 [00:00:00.000 --> 00:00:03.080]
        "srt" - SRT字幕格式
        "plain" - 纯文本
    """
    path_obj = Path(file_path)

    # 检查文件扩展名
    if path_obj.suffix.lower() == '.srt':
        return "srt"

    # 读取文件内容进行检测
    content = read_file_content(file_path)

    # 只需读取前2000字符用于检测
    content = content[:2000]

    # 检查 SRT 时间戳格式（.txt 文件中的 SRT 时间戳）
    if re.search(SRT_TIMESTAMP_PATTERN, content):
        return "srt_timestamp"

    # 检查现有时间戳格式
    if re.search(TIMESTAMP_PATTERN, content):
        return "timestamp"

    # 检查SRT内容格式
    if re.search(SRT_TIME_PATTERN, content, re.MULTILINE):
        return "srt"

    return "plain"


def detect_text_format(text: str) -> FormatType:
    """
    检测文本格式（基于内容而非文件）

    参数:
        text: 文本内容

    返回:
        "timestamp" - 包含 [0.5s --> 2.3s] 格式时间戳
        "srt_timestamp" - 包含 [00:00:00.000 --> 00:00:03.080] 格式时间戳
        "srt" - SRT字幕格式
        "plain" - 纯文本
    """
    # 只需读取前2000字符用于检测
    sample = text[:2000] if len(text) > 2000 else text

    # 检查 SRT 时间戳格式（.txt 文件中的 SRT 时间戳）
    if re.search(SRT_TIMESTAMP_PATTERN, sample):
        return "srt_timestamp"

    # 检查标准 SRT 字幕格式
    if re.search(SRT_TIME_PATTERN, sample, re.MULTILINE):
        return "srt"

    # 检查现有时间戳格式
    if re.search(TIMESTAMP_PATTERN, sample):
        return "timestamp"

    return "plain"


# ============ 时间处理模块 ============

def extract_timestamps(text: str) -> List[TimestampInfo]:
    """
    提取所有时间戳及其位置

    参数:
        text: 原始文本（包含时间戳）

    返回:
        [(end_position, start_time, end_time), ...]
    """
    results: List[TimestampInfo] = []
    for match in re.finditer(TIMESTAMP_PATTERN, text):
        start_time = float(match.group(1))
        end_time = float(match.group(2))
        results.append((match.end(), start_time, end_time))
    return results


def find_timestamp_at_position(
    position: int,
    timestamps: List[TimestampInfo],
    find_first: bool = True
) -> Optional[float]:
    """
    找到指定位置附近的时间戳

    参数:
        position: 原始文本中的位置
        timestamps: 时间戳列表
        find_first: True 找第一个，False 找最后一个

    返回:
        时间值（秒），如果没有找到返回 None
    """
    if not timestamps:
        return None

    if find_first:
        for pos, start, _ in timestamps:
            if pos >= position:
                return start
        return timestamps[-1][1]
    else:
        result = None
        for pos, _, end in timestamps:
            if pos <= position:
                result = end
            else:
                break
        return result


def format_seconds(seconds: float) -> str:
    """将秒数格式化为可读字符串"""
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes}分{secs:.1f}秒"
    return f"{secs:.1f}秒"


def format_time_range(start_ts: Optional[float], end_ts: Optional[float]) -> str:
    """
    格式化时间范围为可读字符串

    参数:
        start_ts: 开始时间（秒）
        end_ts: 结束时间（秒）

    返回:
        格式化的时间范围字符串，如 "【1分30秒 - 3分45秒】"
    """
    if start_ts is None or end_ts is None:
        return "【时间未知】"
    return f"【{format_seconds(start_ts)} - {format_seconds(end_ts)}】"


def parse_time_input(time_str: str) -> TimeDict:
    """
    解析灵活的时间输入格式

    参数:
        time_str: 时间字符串

    返回:
        包含 hours, minutes, seconds, milliseconds 的字典
    """
    time_str = time_str.strip()
    patterns: List[Tuple[str, Callable[[Tuple[str, ...]], TimeDict]]] = [
        # SRT 格式: HH:MM:SS,mmm
        (r'(\d+):(\d+):(\d+),(\d+)',
         lambda m: {'hours': int(m[0]), 'minutes': int(m[1]),
                    'seconds': int(m[2]), 'milliseconds': int(m[3])}),
        # MM:SS 格式
        (r'(\d+):(\d+)',
         lambda m: {'minutes': int(m[0]), 'seconds': int(m[1])}),
        # MMmSSs 格式
        (r'(\d+)m(\d+)s',
         lambda m: {'minutes': int(m[0]), 'seconds': int(m[1])}),
        # MMm 格式
        (r'(\d+)m\s*$',
         lambda m: {'minutes': int(m[0]), 'seconds': 0}),
        # SSs 格式
        (r'(\d+)s\s*$',
         lambda m: {'seconds': int(m[0])}),
    ]

    for pattern, builder in patterns:
        match = re.match(pattern, time_str)
        if match:
            return builder(match.groups())

    # 尝试纯秒数
    try:
        return {'seconds': float(time_str)}
    except ValueError:
        pass

    raise ValueError(f"无法解析时间格式: {time_str}")


# ============ 分段处理模块 ============

def segment_text_by_spaces(
    text: str,
    min_spaces: int,
    max_spaces: int
) -> List[Tuple[int, int]]:
    """
    按空格数量计算分段位置

    返回:
        [(start_idx, end_idx), ...] 分段位置列表
    """
    space_positions = [i for i, char in enumerate(text) if char == ' ']
    segments: List[Tuple[int, int]] = []
    start_idx = 0
    i = 0

    while i < len(space_positions):
        target_end = min(i + max_spaces, len(space_positions))

        if len(space_positions) - i < min_spaces:
            end_idx = len(text)
        else:
            end_idx = space_positions[target_end - 1] + 1

        segments.append((start_idx, end_idx))
        start_idx = end_idx
        i = target_end

    return segments


def segment_by_spaces(text: str, min_spaces: int = 50, max_spaces: int = 60) -> List[str]:
    """
    按空格数量分段（纯文本模式）

    参数:
        text: 去除时间戳后的文本
        min_spaces: 每段最少空格数
        max_spaces: 每段最多空格数

    返回:
        分段后的文本列表
    """
    segments = segment_text_by_spaces(text, min_spaces, max_spaces)
    return [text[start:end].strip() for start, end in segments if text[start:end].strip()]


def segment_with_time_ranges(
    text: str,
    min_spaces: int = 50,
    max_spaces: int = 60
) -> List[str]:
    """
    分段并保留时间范围（现有格式）

    参数:
        text: 原始文本（包含时间戳）
        min_spaces: 每段最少空格数
        max_spaces: 每段最多空格数

    返回:
        带时间范围的段落列表
    """
    timestamps = extract_timestamps(text)
    clean_text = re.sub(TIMESTAMP_PATTERN, ' ', text)
    clean_text = normalize_whitespace(clean_text)

    segments = segment_text_by_spaces(clean_text, min_spaces, max_spaces)
    results: List[str] = []

    for start_idx, end_idx in segments:
        segment = clean_text[start_idx:end_idx].strip()
        if not segment:
            continue

        # 计算该段在原始文本中的大致位置
        ratio_start = start_idx / len(clean_text) if clean_text else 0
        ratio_end = end_idx / len(clean_text) if clean_text else 0

        original_start = int(ratio_start * len(text))
        original_end = int(ratio_end * len(text))

        first_ts = find_timestamp_at_position(original_start, timestamps, find_first=True)
        last_ts = find_timestamp_at_position(original_end, timestamps, find_first=False)

        time_range = format_time_range(first_ts, last_ts)
        results.append(f"{time_range}\n{segment}")

    return results


def segment_with_srt_timestamps(
    text: str,
    min_spaces: int = 50,
    max_spaces: int = 60
) -> List[str]:
    """
    分段并保留 SRT 时间戳范围

    参数:
        text: 原始文本（包含 SRT 时间戳）
        min_spaces: 每段最少空格数
        max_spaces: 每段最多空格数

    返回:
        带时间范围的段落列表
    """
    srt_timestamps = extract_srt_timestamps(text)
    # 去除 SRT 时间戳
    clean_text = re.sub(SRT_TIMESTAMP_PATTERN, ' ', text)
    clean_text = normalize_whitespace(clean_text)

    segments = segment_text_by_spaces(clean_text, min_spaces, max_spaces)
    results: List[str] = []

    for start_idx, end_idx in segments:
        segment = clean_text[start_idx:end_idx].strip()
        if not segment:
            continue

        # 计算该段在原始文本中的大致位置
        ratio_start = start_idx / len(clean_text) if clean_text else 0
        ratio_end = end_idx / len(clean_text) if clean_text else 0

        original_start = int(ratio_start * len(text))
        original_end = int(ratio_end * len(text))

        # 找到对应的时间戳
        first_ts = None
        last_ts = None
        for pos, start, end, _ in srt_timestamps:
            if pos >= original_start and first_ts is None:
                first_ts = start
            if pos <= original_end:
                last_ts = end

        if first_ts is None and srt_timestamps:
            first_ts = srt_timestamps[0][1]
        if last_ts is None and srt_timestamps:
            last_ts = srt_timestamps[-1][2]

        time_range = format_time_range(first_ts, last_ts)
        results.append(f"{time_range}\n{segment}")

    return results


# ============ SRT 格式处理模块 ============

def load_srt_file(file_path: str) -> pysrt.SubRipFile:
    """加载SRT文件，自动检测编码，处理 BOM"""
    # 先尝试读取并去除 BOM
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        # 去除 UTF-8 BOM (如果存在)
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        # 创建临时文件处理
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.srt', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        # 使用临时文件
        result = pysrt.open(tmp_path, encoding='utf-8')
        import os
        os.unlink(tmp_path)
        return result
    except Exception:
        # 回退到原有逻辑
        encodings = ('utf-8', 'iso-8859-1')
        for encoding in encodings:
            try:
                return pysrt.open(file_path, encoding=encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        # 最后尝试
        return pysrt.open(file_path, encoding='iso-8859-1', errors='replace')


def srt_time_to_seconds(time_obj: pysrt.SubRipTime) -> float:
    """将 pysrt SubRipTime 对象转换为秒数"""
    return (
        time_obj.hours * 3600 +
        time_obj.minutes * 60 +
        time_obj.seconds +
        time_obj.milliseconds / 1000.0
    )


def process_srt_plain(file_path: str) -> str:
    """
    SRT → 纯文本

    参数:
        file_path: SRT文件路径

    返回:
        纯文本内容
    """
    subs = load_srt_file(file_path)
    texts = [sub.text.replace('\n', ' ') for sub in subs]
    return normalize_whitespace(' '.join(texts))


def process_srt_with_time(
    file_path: str,
    min_spaces: int = 50,
    max_spaces: int = 60
) -> List[str]:
    """
    SRT → 带时间范围的分段

    参数:
        file_path: SRT文件路径
        min_spaces: 每段最少空格数
        max_spaces: 每段最多空格数

    返回:
        带时间范围的段落列表
    """
    subs = load_srt_file(file_path)

    # 构建文本和字幕边界映射
    all_texts = []
    sub_boundaries: List[int] = []
    current_length = 0

    for sub in subs:
        text = sub.text.replace('\n', ' ')
        all_texts.append(text)
        current_length += len(text) + 1  # +1 for space
        sub_boundaries.append(current_length)

    full_text = ' '.join(all_texts)
    segments = segment_text_by_spaces(full_text, min_spaces, max_spaces)
    results: List[str] = []

    for start_idx, end_idx in segments:
        segment = full_text[start_idx:end_idx].strip()
        if not segment:
            continue

        # 找到第一个字幕：边界 > start_idx 的字幕
        first_ts = None
        for boundary_idx, boundary in enumerate(sub_boundaries):
            if boundary > start_idx:
                first_ts = srt_time_to_seconds(subs[boundary_idx].start)
                break

        # 找到最后一个字幕：边界 >= end_idx 的字幕
        last_ts = None
        for boundary_idx, boundary in enumerate(sub_boundaries):
            if boundary >= end_idx:
                last_ts = srt_time_to_seconds(subs[boundary_idx].end)
                break
        else:
            if subs:
                last_ts = srt_time_to_seconds(subs[-1].end)

        if first_ts is None and subs:
            first_ts = srt_time_to_seconds(subs[0].start)

        time_range = format_time_range(first_ts, last_ts)
        results.append(f"{time_range}\n{segment}")

    return results


def process_srt_slice(
    file_path: str,
    start_time: str,
    end_time: str
) -> Tuple[List[str], str]:
    """
    SRT → 时间范围切片

    参数:
        file_path: SRT文件路径
        start_time: 开始时间字符串
        end_time: 结束时间字符串

    返回:
        (切片内容列表, 时间范围字符串)
    """
    subs = load_srt_file(file_path)

    start_dict = parse_time_input(start_time)
    end_dict = parse_time_input(end_time)

    sliced = subs.slice(starts_after=start_dict, ends_before=end_dict)

    start_sec = time_dict_to_seconds(start_dict)
    end_sec = time_dict_to_seconds(end_dict)
    time_range_str = format_time_range(start_sec, end_sec)

    results = [
        f"{format_time_range(srt_time_to_seconds(sub.start), srt_time_to_seconds(sub.end))}\n{sub.text}"
        for sub in sliced
    ]

    return results, time_range_str


# ============ 输出保存函数 ============

def save_plain_text(text: str, output_path: Path, input_name: str) -> None:
    """保存纯文本输出"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"{'='*60}\n")
        f.write(f"纯文本提取\n")
        f.write(f"{'='*60}\n\n")
        f.write(text)
        f.write(f"\n\n{'='*60}\n")
        f.write(f"处理完成\n")
        f.write(f"{'='*60}\n")
        f.write(f"总字符数: {len(text)}\n")
        f.write(f"源文件: {input_name}\n")


def save_with_time_segments(segments: List[str], output_path: Path) -> None:
    """保存带时间范围的分段"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            f.write(f"{'='*60}\n")
            f.write(f"段落 {i}\n")
            f.write(f"{'='*60}\n")
            f.write(segment)
            f.write("\n\n")


def save_sliced_content(
    segments: List[str],
    output_path: Path,
    time_range: str,
    start_time: str,
    end_time: str
) -> None:
    """保存切片内容"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"{'='*60}\n")
        f.write(f"字幕切片\n")
        f.write(f"{'='*60}\n")
        f.write(f"时间范围: {time_range}\n")
        f.write(f"原始范围: {start_time} --> {end_time}\n")
        f.write(f"\n{'='*60}\n")
        f.write(f"内容\n")
        f.write(f"{'='*60}\n\n")

        for segment in segments:
            f.write(segment)
            f.write("\n\n")

        f.write(f"{'='*60}\n")
        f.write(f"处理完成\n")
        f.write(f"{'='*60}\n")
        f.write(f"切片字幕数: {len(segments)}\n")


# ============ 统一处理接口 ============

def process_timestamp_plain(file_path: str, output_dir: Path, stem: str) -> None:
    """处理时间戳格式文件为纯文本"""
    content = read_file_content(file_path)
    clean_text = remove_timestamps(content)
    output_path = output_dir / f"{stem}_plain.txt"
    save_plain_text(clean_text, output_path, Path(file_path).name)
    print(f"处理后文本长度: {len(clean_text)} 字符")
    print(f"\n已保存输出文件: {output_path}")


def process_timestamp_with_time(
    file_path: str,
    output_dir: Path,
    stem: str,
    min_spaces: int,
    max_spaces: int
) -> None:
    """处理时间戳格式文件为带时间分段"""
    content = read_file_content(file_path)
    print(f"原始文本长度: {len(content)} 字符")

    # 检测是哪种时间戳格式
    if re.search(SRT_TIMESTAMP_PATTERN, content[:2000]):
        print("检测到 SRT 时间戳格式")
        segments = segment_with_srt_timestamps(content, min_spaces, max_spaces)
    else:
        print("检测到标准时间戳格式")
        segments = segment_with_time_ranges(content, min_spaces, max_spaces)

    output_path = output_dir / f"{stem}_with_time.txt"
    save_with_time_segments(segments, output_path)
    print(f"生成了 {len(segments)} 个段落")
    print(f"\n已保存输出文件: {output_path}")


def process_srt_by_mode(
    file_path: str,
    mode: ProcessMode,
    output_dir: Path,
    stem: str,
    min_spaces: int = 50,
    max_spaces: int = 60,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> None:
    """根据模式处理SRT文件"""
    if mode == "plain":
        print("\n模式: 纯文本提取")
        text = process_srt_plain(file_path)
        output_path = output_dir / f"{stem}_plain.txt"
        save_plain_text(text, output_path, Path(file_path).name)
        print(f"提取了 {len(text)} 个字符")
        print(f"\n已保存输出文件: {output_path}")

    elif mode == "with-time":
        print(f"\n模式: 保留时间范围分段 (每段 {min_spaces}-{max_spaces} 个空格)")
        segments = process_srt_with_time(file_path, min_spaces, max_spaces)
        output_path = output_dir / f"{stem}_with_time.txt"
        save_with_time_segments(segments, output_path)
        print(f"生成了 {len(segments)} 个段落")
        print(f"\n已保存输出文件: {output_path}")

    else:  # mode == "slice"
        if not start_time or not end_time:
            raise ValueError("slice 模式需要指定 --start 和 --end 时间")
        print(f"\n模式: 时间范围切片")
        print(f"切片范围: {start_time} --> {end_time}")
        segments, time_range = process_srt_slice(file_path, start_time, end_time)
        output_path = output_dir / f"{stem}_slice.txt"
        save_sliced_content(segments, output_path, time_range, start_time, end_time)
        print(f"切片包含 {len(segments)} 条字幕")
        print(f"\n已保存输出文件: {output_path}")


def process_plain_text_by_mode(
    file_path: str,
    mode: ProcessMode,
    output_dir: Path,
    stem: str,
    min_spaces: int = 50,
    max_spaces: int = 60
) -> None:
    """根据模式处理纯文本文件"""
    content = read_file_content(file_path)
    print(f"原始文本长度: {len(content)} 字符")
    clean_text = normalize_whitespace(content)

    if mode == "plain":
        print("\n模式: 纯文本")
        output_path = output_dir / f"{stem}_plain.txt"
        save_plain_text(clean_text, output_path, Path(file_path).name)
        print(f"\n已保存输出文件: {output_path}")

    elif mode == "with-time":
        print(f"\n模式: 分段处理 (每段 {min_spaces}-{max_spaces} 个空格)")
        segments = segment_by_spaces(clean_text, min_spaces, max_spaces)
        output_path = output_dir / f"{stem}_with_time.txt"
        save_with_time_segments(segments, output_path)
        print(f"生成了 {len(segments)} 个段落")
        print(f"\n已保存输出文件: {output_path}")

    else:  # mode == "slice"
        raise ValueError("slice 模式仅支持 SRT 格式")


def process_file(
    file_path: str,
    mode: ProcessMode,
    output_dir: Path,
    min_spaces: int = 50,
    max_spaces: int = 60,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> None:
    """
    统一处理入口：根据文件类型和处理模式路由到相应处理函数

    参数:
        file_path: 输入文件路径
        mode: 处理模式
        output_dir: 输出目录
        min_spaces: 每段最少空格数
        max_spaces: 每段最多空格数
        start_time: 切片开始时间（仅slice模式）
        end_time: 切片结束时间（仅slice模式）
    """
    from os.path import exists

    if not exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    file_format = detect_file_format(file_path)
    print(f"检测到文件格式: {file_format}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(file_path).stem

    if file_format == "srt":
        print(f"正在读取SRT文件: {file_path}")
        process_srt_by_mode(
            file_path, mode, output_dir, stem, min_spaces, max_spaces, start_time, end_time
        )

    elif file_format == "srt_timestamp":
        print(f"正在读取文件: {file_path}")
        if mode == "plain":
            process_timestamp_plain(file_path, output_dir, stem)
        elif mode == "with-time":
            process_timestamp_with_time(file_path, output_dir, stem, min_spaces, max_spaces)
        else:
            raise ValueError("slice 模式仅支持 SRT 格式")

    elif file_format == "timestamp":
        print(f"正在读取文件: {file_path}")
        if mode == "plain":
            process_timestamp_plain(file_path, output_dir, stem)
        elif mode == "with-time":
            process_timestamp_with_time(file_path, output_dir, stem, min_spaces, max_spaces)
        else:
            raise ValueError("slice 模式仅支持 SRT 格式")

    else:  # plain
        print(f"正在读取文件: {file_path}")
        process_plain_text_by_mode(file_path, mode, output_dir, stem, min_spaces, max_spaces)


# ============ CLI 参数解析 ============

class Args:
    """命令行参数容器"""
    def __init__(
        self,
        input_path: str,
        mode: ProcessMode = "with-time",
        min_spaces: int = 50,
        max_spaces: int = 60,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ):
        self.input_path = input_path
        self.mode = mode
        self.min_spaces = min_spaces
        self.max_spaces = max_spaces
        self.start_time = start_time
        self.end_time = end_time


def parse_arguments() -> Args:
    """
    解析命令行参数

    返回:
        Args 对象
    """
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    if sys.argv[1] in ('-h', '--help'):
        print_help()
        sys.exit(0)

    input_path = sys.argv[1]
    mode: ProcessMode = "with-time"
    min_spaces = 50
    max_spaces = 60
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == '--mode':
            if i + 1 >= len(sys.argv):
                print("错误: --mode 需要指定模式")
                sys.exit(1)
            mode_val = sys.argv[i + 1]
            if mode_val in ('plain', 'with-time', 'slice'):
                mode = mode_val
            else:
                print(f"错误: 无效的模式 '{mode_val}'")
                print("可用模式: plain, with-time, slice")
                sys.exit(1)
            i += 2

        elif arg == '--min':
            if i + 1 >= len(sys.argv):
                print("错误: --min 需要指定数量")
                sys.exit(1)
            try:
                min_spaces = int(sys.argv[i + 1])
            except ValueError:
                print(f"错误: --min 需要整数，得到 '{sys.argv[i + 1]}'")
                sys.exit(1)
            i += 2

        elif arg == '--max':
            if i + 1 >= len(sys.argv):
                print("错误: --max 需要指定数量")
                sys.exit(1)
            try:
                max_spaces = int(sys.argv[i + 1])
            except ValueError:
                print(f"错误: --max 需要整数，得到 '{sys.argv[i + 1]}'")
                sys.exit(1)
            i += 2

        elif arg == '--start':
            if i + 1 >= len(sys.argv):
                print("错误: --start 需要指定时间")
                sys.exit(1)
            start_time = sys.argv[i + 1]
            i += 2

        elif arg == '--end':
            if i + 1 >= len(sys.argv):
                print("错误: --end 需要指定时间")
                sys.exit(1)
            end_time = sys.argv[i + 1]
            i += 2

        else:
            print(f"错误: 未知参数 '{arg}'")
            print("使用 --help 查看帮助信息")
            sys.exit(1)

    return Args(input_path, mode, min_spaces, max_spaces, start_time, end_time)


# ============ 主程序 ============

def main() -> None:
    """主程序入口"""
    print("=" * 60)
    print("通用文本处理器 v1.0")
    print("=" * 60)

    try:
        args = parse_arguments()

        output_dir = Path(__file__).parent.parent / "output"

        # 验证参数
        if args.min_spaces > args.max_spaces:
            print(f"错误: 最小空格数 ({args.min_spaces}) 不能大于最大空格数 ({args.max_spaces})")
            sys.exit(1)

        if args.mode == 'slice' and (not args.start_time or not args.end_time):
            print("错误: slice 模式需要指定 --start 和 --end 时间")
            sys.exit(1)

        print(f"\n配置:")
        print(f"  输入文件: {args.input_path}")
        print(f"  处理模式: {args.mode}")
        if args.mode == 'with-time':
            print(f"  分段参数: {args.min_spaces}-{args.max_spaces} 个空格")
        elif args.mode == 'slice':
            print(f"  切片范围: {args.start_time} --> {args.end_time}")

        print("\n" + "-" * 60)

        process_file(
            args.input_path,
            args.mode,
            output_dir,
            args.min_spaces,
            args.max_spaces,
            args.start_time,
            args.end_time
        )

        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"\n错误: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n处理文件时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

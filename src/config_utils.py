# config_utils.py
"""
配置加载工具模块
提供 API key 和提示词文件的加载功能
"""

import os
from pathlib import Path


def load_api_key(key_path: str | Path) -> str:
    """
    从文件加载 API key

    参数:
        key_path: API key 文件路径

    返回:
        API key 字符串

    异常:
        FileNotFoundError: 文件不存在
        ValueError: 无法读取有效的 API key
    """
    key_path = str(key_path)
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"API key 文件不存在: {key_path}")

    with open(key_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        for line in content.split('\n'):
            line = line.strip()
            # 跳过注释行和空行
            if line and not line.startswith('#'):
                return line

    raise ValueError(f"无法从 {key_path} 读取有效的 API key")


def load_prompt(prompt_path: str | Path) -> str:
    """
    从文件加载提示词

    参数:
        prompt_path: 提示词文件路径

    返回:
        提示词内容

    异常:
        FileNotFoundError: 文件不存在
    """
    prompt_path = str(prompt_path)
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")

    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

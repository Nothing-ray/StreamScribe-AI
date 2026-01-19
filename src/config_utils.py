# config_utils.py
"""
配置加载工具模块
提供 API key 和提示词文件的加载功能
"""

import os
from pathlib import Path


def load_api_key(key_path: str | Path, interactive: bool = True) -> str:
    """
    从文件加载 API key，如果文件不存在则交互式创建

    参数:
        key_path: API key 文件路径
        interactive: 是否在文件不存在时启用交互式输入（默认 True）

    返回:
        API key 字符串

    异常:
        FileNotFoundError: 文件不存在且 interactive=False
        ValueError: 无法读取有效的 API key
    """
    key_path = Path(key_path)

    # 如果文件不存在且启用交互模式
    if not key_path.exists() and interactive:
        print(f"\n⚠️  API key 文件不存在: {key_path}")
        print(f"⚠️  API key file not found: {key_path}")
        print("📝 首次使用需要设置 DeepSeek API Key")
        print("📝 First time setup: DeepSeek API Key required")
        print("   获取地址: https://api-docs.deepseek.com.zh-cn/")
        print("   Get your key: https://api-docs.deepseek.com.zh-cn/\n")

        api_key = input("请输入你的 API Key / Enter your API Key: ").strip()

        while not api_key:
            print("❌ API Key 不能为空，请重新输入")
            print("❌ API Key cannot be empty, please try again")
            api_key = input("请输入你的 API Key / Enter your API Key: ").strip()

        # 创建目录并保存
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(
            f"# DeepSeek API Key\n# 获取地址: https://api-docs.deepseek.com.zh-cn/\n{api_key}\n",
            encoding='utf-8'
        )
        print(f"✅ API Key 已保存到: {key_path}")
        print(f"✅ API Key saved to: {key_path}\n")
        return api_key

    # 原有的读取逻辑（当文件存在或 interactive=False 时）
    if not key_path.exists():
        raise FileNotFoundError(f"API key 文件不存在: {key_path}")

    content = key_path.read_text(encoding='utf-8').strip()
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

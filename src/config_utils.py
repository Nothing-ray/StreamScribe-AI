# config_utils.py
"""
配置加载工具模块
提供 API key 和提示词文件的加载功能
"""

import os
from pathlib import Path


def _prompt_api_key(key_path: Path) -> str:
    """
    交互式提示用户输入 API key（内部辅助函数）

    参数:
        key_path: API key 文件路径

    返回:
        API key 字符串
    """
    api_key = input("\n请输入你的 API Key / Enter your API Key: ").strip()

    while not api_key:
        print("[ERROR] API Key 不能为空，请重新输入")
        print("[ERROR] API Key cannot be empty, please try again")
        api_key = input("请输入你的 API Key / Enter your API Key: ").strip()

    # 创建目录并保存
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(
        f"# DeepSeek API Key\n# 获取地址: https://api-docs.deepseek.com.zh-cn/\n{api_key}\n",
        encoding='utf-8'
    )
    print(f"[OK] API Key 已保存到: {key_path}")
    print(f"[OK] API Key saved to: {key_path}")

    return api_key


def initialize_project_setup(
    key_path: str | Path,
    output_path: str | Path,
    interactive: bool = True
) -> str:
    """
    首次运行项目初始化：设置 API key 并创建 output 文件夹

    参数:
        key_path: API key 文件路径
        output_path: output 文件夹路径
        interactive: 是否启用交互式输入（默认 True）

    返回:
        API key 字符串

    异常:
        FileNotFoundError: 文件不存在且 interactive=False
        ValueError: 无法读取有效的 API key
    """
    key_path = Path(key_path)
    output_path = Path(output_path)

    # 检测是否为首次运行
    is_first_run = not key_path.exists()

    if is_first_run and interactive:
        print("\n" + "=" * 60)
        print("[INIT] StreamScribe-AI 首次运行初始化")
        print("[INIT] First-time setup for StreamScribe-AI")
        print("=" * 60)
        print("\n[SETUP] 首次使用需要设置 DeepSeek API Key")
        print("[SETUP] First time setup: DeepSeek API Key required")
        print("   获取地址 Get your key: https://api-docs.deepseek.com.zh-cn/")

        # 调用 API key 输入逻辑
        api_key = _prompt_api_key(key_path)

        # 创建 output 文件夹
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Output 文件夹已创建: {output_path}")
        print(f"[OK] Output folder created: {output_path}")

        print("\n" + "=" * 60)
        print("[OK] 初始化完成！Initialization complete!")
        print("=" * 60 + "\n")

        return api_key
    else:
        # 非首次运行：仅确保 output 文件夹存在
        output_path.mkdir(parents=True, exist_ok=True)
        return load_api_key(key_path, interactive)


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
        print(f"\n[WARN] API key 文件不存在: {key_path}")
        print(f"[WARN] API key file not found: {key_path}")
        return _prompt_api_key(key_path)

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

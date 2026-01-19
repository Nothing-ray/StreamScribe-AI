# api_utils.py
"""
API 调用工具模块
提供与 DeepSeek API 交互的公共函数
"""

import time
from openai import OpenAI


# ============ 配置常量 ============

MODEL_NAME = "deepseek-chat"
API_BASE_URL = "https://api.deepseek.com"
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0


def create_client(api_key: str) -> OpenAI:
    """
    创建 OpenAI 客户端实例

    参数:
        api_key: API 密钥

    返回:
        OpenAI 客户端实例
    """
    return OpenAI(api_key=api_key, base_url=API_BASE_URL)


def call_deepseek_api(
    client: OpenAI,
    system_prompt: str,
    user_content: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
) -> str:
    """
    调用 DeepSeek API 处理文本

    参数:
        client: OpenAI 客户端实例
        system_prompt: 系统提示词
        user_content: 用户输入内容
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）

    返回:
        API 返回的文本内容

    异常:
        当所有重试都失败时，抛出原始异常
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  API 调用失败: {e}，{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise

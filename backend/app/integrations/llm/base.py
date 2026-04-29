"""LLM Provider 抽象接口"""
from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """大模型抽象接口，所有供应商实现必须继承此类"""

    @abstractmethod
    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """
        发送 chat 请求并返回解析后的 JSON

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            model: 模型名（可选，默认使用 credential 配置的模型）
            temperature: 温度参数
            max_tokens: 最大输出 token

        Returns:
            解析后的 JSON dict

        Raises:
            ValueError: JSON 解析或校验失败
        """
        ...

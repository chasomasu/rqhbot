"""OpenAI 兼容 LLM 客户端。

替换原 sirius_chat 平台的 engine_proxy 组件。
支持同步 generate() 和流式 generate_stream() 两种调用方式。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI 兼容 API 的 LLM 调用封装。

    用法:
        llm = LLMClient(base_url="https://api.openai.com/v1",
                        api_key="sk-xxx",
                        model="gpt-4o")
        result = await llm.generate("hello", system_prompt="you are a helper")
        async for chunk_type, text in llm.generate_stream(...):
            ...
    """

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "",
    ) -> None:
        self._client = AsyncOpenAI(
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key or "sk-placeholder",
        )
        self._default_model = model or "gpt-4o"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "",
        json_mode: bool = False,
        **kwargs: Any,
    ) -> str:
        """单次 LLM 调用，返回文本结果。

        替换 engine_proxy.generate_raw()，移除了 inject_persona/return_reasoning/task_name 等
        SiriusChat 特有参数。json_mode=True 时设置 response_format={type: json_object}。
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_kwargs: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "timeout": kwargs.get("timeout_seconds", 120.0) or 120.0,
        }
        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._client.chat.completions.create(**request_kwargs)
            return response.choices[0].message.content or ""
        except Exception:
            logger.exception("LLM generate 调用失败")
            raise

    async def generate_stream(
        self,
        messages: list[dict],
        model: str = "",
        **kwargs: Any,
    ) -> "AsyncGenerator[tuple[str, str], None]":
        """流式调用 LLM，异步逐块 yield (chunk_type, text)。

        替换 agent_loop._streaming_generate() 中的 SirisChat 流式调用。
        chunk_type: "reasoning" | "content"
        """
        request_kwargs: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "timeout": kwargs.get("timeout_seconds", 120.0) or 120.0,
            "stream": True,
            "stream_options": {"include_usage": False},
        }

        try:
            stream = await self._client.chat.completions.create(**request_kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.refusal:
                    yield "content", f"[refusal] {delta.refusal}"
                    continue
                if delta.reasoning_content:
                    yield "reasoning", delta.reasoning_content
                if delta.content:
                    yield "content", delta.content
        except Exception:
            logger.exception("LLM generate_stream 调用失败")
            raise

    @classmethod
    def from_config(cls, config: dict) -> "LLMClient":
        """从配置字典中创建 LLMClient。"""
        llm_cfg = config.get("llm", {})
        return cls(
            base_url=llm_cfg.get("base_url", ""),
            api_key=llm_cfg.get("api_key", ""),
            model=llm_cfg.get("model", ""),
        )

"""LLM 调用包装(参考 google_search_plugin)。

设计要点:
- 必须显式传 ``model=`` 参数,否则 host ``resolve_task_name("")`` 字母序回退到
  ``embedding`` task,导致 chat completion 失败(google_search 计划 Bug C)。
- 区分"调用失败"(异常 / success=False / 超时) vs "模型返空响应"。
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from ._envelope import peel_envelope

if TYPE_CHECKING:
    from maibot_sdk import PluginContext

    from ..config import DefaultModelSection

logger = logging.getLogger(__name__)


class LLMCallError(RuntimeError):
    """LLM 调用层失败(异常 / success=False / 超时)。"""


class LLMRunner:
    """``ctx.llm.generate`` 的薄包装。"""

    def __init__(self, ctx: "PluginContext", model_config: "DefaultModelSection") -> None:
        self._ctx = ctx
        self._config = model_config

    async def generate(self, prompt: str) -> str:
        """生成文本。返回空串表示模型返空,失败抛 LLMCallError。"""
        if not prompt or not prompt.strip():
            logger.warning("prompt 为空,跳过 LLM 调用")
            return ""

        target_model = str(self._config.model_name or "replyer")
        temperature = self._config.temperature
        timeout = max(int(self._config.llm_timeout_seconds or 60), 1)
        logger.info(
            "调用 ctx.llm.generate model=%s temperature=%s prompt_len=%d timeout=%ds",
            target_model,
            temperature,
            len(prompt),
            timeout,
        )

        try:
            result = await asyncio.wait_for(
                self._ctx.llm.generate(
                    prompt=prompt,
                    model=target_model,
                    temperature=temperature,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            logger.error("ctx.llm.generate 超时(%ds)", timeout)
            raise LLMCallError(f"LLM 调用超时 ({timeout}s)") from exc
        except Exception as exc:
            logger.error("ctx.llm.generate 抛异常: %s", exc, exc_info=True)
            raise LLMCallError(f"LLM 调用异常: {exc}") from exc

        result = peel_envelope(result)
        if not isinstance(result, dict):
            raise LLMCallError(f"LLM 返回非 dict: {type(result).__name__}")

        success = bool(result.get("success", False))
        response_text = str(result.get("response") or "")
        if not success:
            err = result.get("error") or "<no error key>"
            logger.error("LLM 调用失败 model=%s error=%s", target_model, err)
            raise LLMCallError(f"LLM 调用失败: {err}")
        return response_text.strip()

"""diary_plugin 主入口

业务逻辑全部抽到 ``pipelines/`` 子模块,本文件只负责装配 + 派发 + 调度器。

提供两个面向 LLM/用户的组件:
- ``@Tool("emotion_analysis")`` 情感分析(关键词匹配,可选)
- ``@Command("diary")``         日记管理命令树(/diary generate|list|view|debug|help)

外加一个后台调度器,每天到点自动生成日记并发布到 QQ 空间。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from maibot_sdk import MaiBotPlugin

from .config import DiaryPluginConfig


logger = logging.getLogger(__name__)


class DiaryPlugin(MaiBotPlugin):
    """日记插件主类"""

    config_model = DiaryPluginConfig

    # 运行时组件,在 on_load / on_config_update 中装配
    # (阶段 3 实现后填充)
    _scheduler_task: Optional[Any]

    def __init__(self) -> None:
        super().__init__()
        self._scheduler_task = None

    # ---------------------------------------------------------------- #
    # 生命周期
    # ---------------------------------------------------------------- #

    async def on_load(self) -> None:
        """插件加载完成时调用。"""
        cfg = self.config
        self.ctx.logger.info(
            "diary_plugin v%s 已加载 (style=%s, schedule_time=%s, filter_mode=%s, "
            "use_custom_model=%s, default_model=%s)",
            cfg.plugin.version,
            cfg.diary_generation.style,
            cfg.schedule.schedule_time,
            cfg.schedule.filter_mode,
            cfg.custom_model.use_custom_model,
            cfg.default_model.model_name,
        )
        # 阶段 3-4 在此装配 pipelines + 启动调度器

    async def on_unload(self) -> None:
        """插件卸载时调用。"""
        self.ctx.logger.info("diary_plugin 已卸载")
        # 阶段 4 在此取消调度器

    async def on_config_update(
        self,
        scope: str,
        config_data: dict[str, Any],
        version: str,
    ) -> None:
        """配置热更新:重建 pipelines。"""
        del config_data
        self.ctx.logger.info("配置更新: scope=%s version=%s", scope, version)
        # 阶段 3 在此重建 pipelines


def create_plugin() -> DiaryPlugin:
    """Runner 通过此工厂函数实例化插件。"""
    return DiaryPlugin()

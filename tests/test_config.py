"""config.py PluginConfigBase 单元测试。"""

import pytest

from diary_plugin.config import (
    CustomModelSection,
    DefaultModelSection,
    DiaryGenerationSection,
    DiaryPluginConfig,
    PluginSection,
    QzonePublishingSection,
    ScheduleSection,
)


def test_default_config_loads():
    cfg = DiaryPluginConfig()
    assert cfg.plugin.enabled is True
    assert cfg.plugin.config_version == "3.0.0"
    assert cfg.diary_generation.style == "diary"
    assert cfg.diary_generation.enable_style_send is False  # 新默认值
    assert cfg.default_model.model_name == "replyer"
    assert cfg.schedule.filter_mode == "whitelist"


def test_section_count():
    """6 个 section,缺一不可。"""
    expected = {"plugin", "diary_generation", "qzone_publishing",
                "custom_model", "default_model", "schedule"}
    assert set(DiaryPluginConfig.model_fields.keys()) == expected


def test_extra_fields_silently_ignored():
    """老用户 toml 残留 enable_action / enable_syle_send 应被忽略,不抛错。"""
    legacy_data = {
        "plugin": {
            "enabled": True,
            "admin_qqs": [12345],
            "enable_action": True,        # 已删除字段
            "enable_tool": False,
            "enable_command": True,
        },
        "diary_generation": {
            "style": "diary",
            "enable_syle_send": True,      # 错误拼写,应被忽略,新字段保留默认 False
        },
    }
    cfg = DiaryPluginConfig(**legacy_data)
    assert not hasattr(cfg.plugin, "enable_action")
    assert cfg.diary_generation.enable_style_send is False
    assert cfg.plugin.admin_qqs == [12345]


def test_custom_model_not_named_model_config():
    """避开 Pydantic 保留属性名 model_config。"""
    cfg = DiaryPluginConfig()
    assert hasattr(cfg, "custom_model")
    assert isinstance(cfg.custom_model, CustomModelSection)


def test_qzone_word_count_constraints():
    """min/max 字数有边界校验。"""
    with pytest.raises(Exception):
        QzonePublishingSection(qzone_min_word_count=10)  # < 20
    with pytest.raises(Exception):
        QzonePublishingSection(qzone_max_word_count=9000)  # > 8000


def test_default_model_choices_are_literal():
    """default_model.model_name 限定四个选项之一。"""
    DefaultModelSection(model_name="replyer")
    DefaultModelSection(model_name="utils")
    DefaultModelSection(model_name="planner")
    DefaultModelSection(model_name="vlm")
    with pytest.raises(Exception):
        DefaultModelSection(model_name="embedding")


def test_filter_mode_choices():
    ScheduleSection(filter_mode="whitelist")
    ScheduleSection(filter_mode="blacklist")
    with pytest.raises(Exception):
        ScheduleSection(filter_mode="random")


def test_style_choices():
    DiaryGenerationSection(style="diary")
    DiaryGenerationSection(style="qqzone")
    DiaryGenerationSection(style="custom")
    with pytest.raises(Exception):
        DiaryGenerationSection(style="essay")

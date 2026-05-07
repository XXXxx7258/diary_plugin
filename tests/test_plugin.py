"""plugin.py 装饰器注册 + 入口测试。"""

from diary_plugin.config import DiaryPluginConfig
from diary_plugin.plugin import DiaryPlugin, create_plugin

_COMPONENT_INFO_ATTR = "__maibot_component_info__"


def test_create_plugin_returns_instance():
    inst = create_plugin()
    assert isinstance(inst, DiaryPlugin)


def test_config_model_attached():
    assert DiaryPlugin.config_model is DiaryPluginConfig


def test_decorated_components_registered():
    """plugin 应注册 @Tool emotion_analysis 和 @Command diary。"""
    decorated = []
    for name in dir(DiaryPlugin):
        attr = getattr(DiaryPlugin, name, None)
        if callable(attr) and hasattr(attr, _COMPONENT_INFO_ATTR):
            info = getattr(attr, _COMPONENT_INFO_ATTR)
            decorated.append((name, info.type.value, info.name))

    component_names = {(name, comp_name) for _, name, comp_name in decorated}
    component_types = {comp_type for _, comp_type, _ in decorated}
    assert ("TOOL", "emotion_analysis") in component_names
    assert ("COMMAND", "diary") in component_names
    assert "TOOL" in component_types
    assert "COMMAND" in component_types
    # 不应有 ACTION(已废弃)
    assert "ACTION" not in component_types


def test_command_pattern_has_named_groups():
    handle = DiaryPlugin.handle_diary
    info = getattr(handle, _COMPONENT_INFO_ATTR)
    pattern = info.command_pattern
    assert pattern  # 非空
    # 命名捕获组 action / param
    assert "(?P<action>" in pattern
    assert "(?P<param>" in pattern

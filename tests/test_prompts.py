"""pipelines/prompts.py 单元测试。"""

import pytest

from diary_plugin.pipelines.prompts import (
    build_custom_prompt,
    build_diary_prompt,
    build_qqzone_prompt,
)


def test_diary_prompt_contains_required_fields():
    prompt = build_diary_prompt(
        date="2025-01-15",
        timeline="【上午9点】\nAlice: 早安",
        date_with_weather="2025年1月15日,星期三,晴。",
        target_length=300,
        personality_desc="是一只猫",
        style_desc="爱卖萌",
        name="麦麦",
    )
    assert "2025-01-15" in prompt
    assert "Alice: 早安" in prompt
    assert "2025年1月15日" in prompt
    assert "300字" in prompt
    assert "是一只猫" in prompt
    assert "爱卖萌" in prompt


def test_qqzone_prompt_differs_from_diary():
    args = dict(
        date="2025-01-15",
        timeline="hi",
        date_with_weather="day",
        target_length=200,
        personality_desc="x",
        style_desc="y",
        name="z",
    )
    diary_p = build_diary_prompt(**args)
    qq_p = build_qqzone_prompt(**args)
    assert diary_p != qq_p
    assert "QQ空间" in qq_p
    assert "日记内容:" in diary_p


class TestCustomPrompt:
    def test_renders_placeholders(self):
        template = "{date} - {timeline} - {target_length}"
        ctx = {"date": "2025-01-15", "timeline": "hi", "target_length": "300"}
        # 添加其他可选 key 以避免 KeyError(虽然 template 没用到)
        ctx.update({"date_with_weather": "", "personality_desc": "", "style": "", "name": ""})
        result = build_custom_prompt(template, ctx)
        assert result == "2025-01-15 - hi - 300"

    def test_empty_template_raises(self):
        with pytest.raises(ValueError):
            build_custom_prompt("", {})

    def test_missing_placeholder_raises(self):
        template = "{nonexistent_key}"
        with pytest.raises(ValueError):
            build_custom_prompt(template, {"date": "x"})

    def test_whitespace_only_template_raises(self):
        with pytest.raises(ValueError):
            build_custom_prompt("   \n  ", {})

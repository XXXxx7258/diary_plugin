"""utils/{date,tokens}.py 单元测试。"""

import datetime

import pytest

from diary_plugin.utils.date import date_with_weather, format_date_str
from diary_plugin.utils.tokens import (
    MAX_DIARY_LENGTH,
    TOKEN_LIMIT_50K,
    estimate_tokens,
    smart_truncate,
    truncate_by_tokens,
)


class TestFormatDateStr:
    def test_datetime_object(self):
        dt = datetime.datetime(2025, 1, 15)
        assert format_date_str(dt) == "2025-01-15"

    def test_iso_format(self):
        assert format_date_str("2025-01-15") == "2025-01-15"

    def test_slash_format(self):
        assert format_date_str("2025/01/15") == "2025-01-15"

    def test_dot_format(self):
        assert format_date_str("2025.01.15") == "2025-01-15"

    def test_short_form_yyyy_m_d(self):
        # Python strptime 接受单位数字,正规化为零填充
        assert format_date_str("2025-1-5") == "2025-01-05"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            format_date_str("not a date")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            format_date_str("")


class TestDateWithWeather:
    def test_basic(self):
        # 2025-01-15 是星期三
        result = date_with_weather("2025-01-15", "晴")
        assert result == "2025年1月15日,星期三,晴。"

    def test_invalid_falls_back(self):
        # 解析失败时返回 fallback 格式
        result = date_with_weather("garbage", "雨")
        assert "garbage" in result and "雨" in result


class TestEstimateTokens:
    def test_empty(self):
        assert estimate_tokens("") == 0

    def test_chinese_only(self):
        # 中文 1.5 字 / token
        # "你好" 2 字 → ceil(2/1.5) ≈ 1
        assert estimate_tokens("你好") >= 1
        assert estimate_tokens("你好") <= 2

    def test_english_only(self):
        # 英文 4 字 / token,"hello" 5 字 → ~1
        result = estimate_tokens("hello world")
        assert 2 <= result <= 4

    def test_mixed(self):
        # 中英混合
        text = "今天 the weather is 晴朗"
        result = estimate_tokens(text)
        assert result > 0

    def test_token_limit_constant(self):
        assert TOKEN_LIMIT_50K == 50000


class TestSmartTruncate:
    def test_within_limit(self):
        text = "短文本"
        assert smart_truncate(text, max_length=100) == text

    def test_truncate_at_punctuation(self):
        text = "第一句。第二句很长很长很长很长很长很长。"
        result = smart_truncate(text, max_length=10)
        # 应在标点处截断
        assert len(result) <= 10
        assert result.endswith("。") or result.endswith("...")

    def test_no_punctuation_uses_ellipsis(self):
        text = "abcdefghijklmnopqrstuvwxyz"
        result = smart_truncate(text, max_length=10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_max_diary_length_constant(self):
        assert MAX_DIARY_LENGTH == 8000


class TestTruncateByTokens:
    def test_within_limit(self):
        text = "你好 hello"
        # 远小于 1000 token,不截断
        assert truncate_by_tokens(text, max_tokens=1000) == text

    def test_exceeds_limit_appends_marker(self):
        # 构造一段足够长的中文
        text = "今天天气真好。" * 5000  # ~5000*5 ≈ 25000 char,~16000 tokens
        result = truncate_by_tokens(text, max_tokens=100)
        assert len(result) < len(text)
        assert "[聊天记录过长,已截断]" in result

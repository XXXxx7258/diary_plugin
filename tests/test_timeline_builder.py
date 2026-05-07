"""pipelines/timeline_builder.py 单元测试。"""

from diary_plugin.pipelines.timeline_builder import (
    TimelineBuilder,
    weather_by_emotion,
)


def _msg(ts, user_id, nickname, text="", is_picture=False, raw_message=None):
    return {
        "timestamp": str(ts),
        "session_id": "s1",
        "is_picture": is_picture,
        "processed_plain_text": text,
        "raw_message": raw_message or [],
        "message_info": {
            "user_info": {"user_id": user_id, "user_nickname": nickname},
            "group_info": None,
        },
    }


class TestTimelineBuilderEmpty:
    def test_empty_returns_placeholder(self):
        b = TimelineBuilder()
        assert b.build([]) == "今天没有什么特别的对话。"
        assert b.stats == {"total_messages": 0, "bot_messages": 0, "user_messages": 0}


class TestTimelineBuilderText:
    def test_user_messages_with_nickname(self):
        msgs = [
            _msg(1700000000, "111", "Alice", text="早安"),
            _msg(1700003600, "222", "Bob", text="嗨"),
        ]
        b = TimelineBuilder(bot_qq_account="999")
        result = b.build(msgs)
        assert "Alice: 早安" in result
        assert "Bob: 嗨" in result
        assert b.stats["user_messages"] == 2
        assert b.stats["bot_messages"] == 0

    def test_bot_message_uses_我(self):
        msgs = [
            _msg(1700000000, "999", "MaiBot", text="你好"),
            _msg(1700003600, "111", "Alice", text="嗨"),
        ]
        b = TimelineBuilder(bot_qq_account="999")
        result = b.build(msgs)
        assert "我: 你好" in result
        assert "Alice: 嗨" in result
        assert b.stats["bot_messages"] == 1
        assert b.stats["user_messages"] == 1

    def test_long_text_truncated(self):
        long_text = "今" * 100
        msgs = [_msg(1700000000, "111", "Alice", text=long_text)]
        b = TimelineBuilder()
        result = b.build(msgs)
        assert "..." in result
        # 截断后的"今"+...部分不超过 60
        assert long_text not in result


class TestTimelineBuilderImage:
    def test_is_picture_flag(self):
        msgs = [_msg(1700000000, "111", "Alice", is_picture=True)]
        b = TimelineBuilder()
        result = b.build(msgs)
        assert "[图片]" in result
        assert "Alice:" in result

    def test_image_with_description_in_raw(self):
        raw = [{"type": "image", "data": {"description": "猫咪照片"}}]
        msgs = [_msg(1700000000, "111", "Alice", is_picture=True, raw_message=raw)]
        b = TimelineBuilder()
        result = b.build(msgs)
        assert "[图片]猫咪照片" in result

    def test_picture_fallback_via_raw_message(self):
        # 即便 is_picture=False,raw_message 含 image segment 也应识别
        raw = [{"type": "Image", "data": {"file": "abc.jpg"}}]
        msgs = [_msg(1700000000, "111", "Alice", is_picture=False, raw_message=raw)]
        b = TimelineBuilder()
        result = b.build(msgs)
        assert "[图片]" in result


class TestTimelineHourBucket:
    def test_groups_by_hour_period(self):
        # 跨多个小时段
        msgs = [
            _msg(1700001600, "111", "A", text="早"),     # 上午
            _msg(1700045200, "222", "B", text="午"),     # 下午
            _msg(1700070000, "333", "C", text="晚"),     # 晚上
        ]
        b = TimelineBuilder()
        result = b.build(msgs)
        # 至少一个时间段标记应该出现
        assert any(p in result for p in ("上午", "下午", "晚上"))


class TestWeatherByEmotion:
    def test_empty_random_returns_one_of_4(self):
        result = weather_by_emotion([])
        assert result in ("晴", "多云", "阴", "多云转晴")

    def test_happy_words_yield_clear(self):
        msgs = [_msg(1, "a", "A", text="哈哈哈"), _msg(2, "b", "B", text="开心 笑")]
        assert weather_by_emotion(msgs) == "晴"

    def test_sad_words_yield_rain(self):
        msgs = [_msg(1, "a", "A", text="伤心 难过"), _msg(2, "b", "B", text="哭了 痛苦")]
        assert weather_by_emotion(msgs) == "雨"

    def test_angry_words_yield_overcast(self):
        msgs = [_msg(1, "a", "A", text="服了 真无语")]
        assert weather_by_emotion(msgs) == "阴"

    def test_calm_yields_partly_cloudy(self):
        msgs = [_msg(1, "a", "A", text="一般 淡定 平静")]
        assert weather_by_emotion(msgs) == "多云"

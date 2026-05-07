"""pipelines/message_fetcher.py 单元测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from diary_plugin.pipelines.chat_resolver import ChatResolver
from diary_plugin.pipelines.message_fetcher import MessageFetcher


def _make_msg(timestamp, user_id, session_id, group_id="", text="hi"):
    """构造一条 host 序列化后的 dict 消息。"""
    return {
        "message_id": f"msg_{timestamp}",
        "timestamp": str(timestamp),
        "platform": "qq",
        "session_id": session_id,
        "is_picture": False,
        "is_command": False,
        "processed_plain_text": text,
        "message_info": {
            "user_info": {"user_id": user_id, "user_nickname": f"user_{user_id}"},
            "group_info": {"group_id": group_id} if group_id else None,
        },
    }


class TestFilterMinMessagesPerChat:
    def test_zero_returns_unchanged(self):
        msgs = [_make_msg(1.0, "a", "s1"), _make_msg(2.0, "b", "s2")]
        assert MessageFetcher.filter_min_messages_per_chat(msgs, 0) == msgs

    def test_filters_chats_below_threshold(self):
        msgs = [
            _make_msg(1.0, "a", "s1"),
            _make_msg(2.0, "b", "s1"),
            _make_msg(3.0, "c", "s1"),  # s1: 3 条
            _make_msg(4.0, "d", "s2"),  # s2: 1 条 → 过滤
        ]
        result = MessageFetcher.filter_min_messages_per_chat(msgs, min_per_chat=3)
        assert len(result) == 3
        assert all(m["session_id"] == "s1" for m in result)

    def test_keeps_all_when_threshold_one(self):
        msgs = [_make_msg(1.0, "a", "s1"), _make_msg(2.0, "b", "s2")]
        result = MessageFetcher.filter_min_messages_per_chat(msgs, min_per_chat=1)
        assert len(result) == 2

    def test_empty_input(self):
        assert MessageFetcher.filter_min_messages_per_chat([], min_per_chat=3) == []


class TestBlacklistFilter:
    def test_excludes_group(self):
        msgs = [
            _make_msg(1.0, "a", "s_group_111", group_id="111"),
            _make_msg(2.0, "b", "s_group_222", group_id="222"),
        ]
        result = MessageFetcher._filter_blacklist(msgs, ["group:111"])
        assert len(result) == 1
        assert result[0]["session_id"] == "s_group_222"

    def test_excludes_private(self):
        msgs = [
            _make_msg(1.0, "111", "s_priv_111"),  # 无 group_id → 私聊
            _make_msg(2.0, "222", "s_priv_222"),
        ]
        result = MessageFetcher._filter_blacklist(msgs, ["private:111"])
        assert len(result) == 1
        assert result[0]["session_id"] == "s_priv_222"

    def test_empty_blacklist_passes_all(self):
        msgs = [_make_msg(1.0, "a", "s1")]
        assert MessageFetcher._filter_blacklist(msgs, []) == msgs


class TestFetchAll:
    @pytest.mark.asyncio
    async def test_calls_get_by_time_with_str_args(self, tmp_path):
        ctx = MagicMock()
        ctx.message.get_by_time = AsyncMock(
            return_value={"success": True, "messages": [_make_msg(1.0, "a", "s1")]}
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        fetcher = MessageFetcher(ctx, resolver)
        result = await fetcher.fetch_all(start_time=100.0, end_time=200.0)
        assert len(result) == 1
        # 验证 R2 spike:start_time/end_time 转 str 透传
        call_kwargs = ctx.message.get_by_time.call_args.kwargs
        assert call_kwargs["start_time"] == "100.0"
        assert call_kwargs["end_time"] == "200.0"
        assert call_kwargs["filter_mai"] is False
        # get_by_time 不应带 filter_command
        assert "filter_command" not in call_kwargs

    @pytest.mark.asyncio
    async def test_envelope_peeled(self, tmp_path):
        ctx = MagicMock()
        ctx.message.get_by_time = AsyncMock(
            return_value={"success": True, "result": {
                "success": True, "messages": [_make_msg(1.0, "a", "s1")]
            }}
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        fetcher = MessageFetcher(ctx, resolver)
        result = await fetcher.fetch_all(100.0, 200.0)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_failure_returns_empty(self, tmp_path):
        ctx = MagicMock()
        ctx.message.get_by_time = AsyncMock(
            return_value={"success": False, "error": "denied"}
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        fetcher = MessageFetcher(ctx, resolver)
        result = await fetcher.fetch_all(100.0, 200.0)
        assert result == []


class TestFetchForChats:
    @pytest.mark.asyncio
    async def test_calls_get_by_time_in_chat_per_chat(self, tmp_path):
        ctx = MagicMock()
        ctx.message.get_by_time_in_chat = AsyncMock(
            side_effect=[
                {"success": True, "messages": [_make_msg(1.0, "a", "s1")]},
                {"success": True, "messages": [_make_msg(2.0, "b", "s2")]},
            ]
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        fetcher = MessageFetcher(ctx, resolver)
        result = await fetcher.fetch_for_chats(["s1", "s2"], 0, 1000)
        assert len(result) == 2
        assert ctx.message.get_by_time_in_chat.call_count == 2
        # filter_command 应当传给 get_by_time_in_chat
        first_call_kwargs = ctx.message.get_by_time_in_chat.call_args_list[0].kwargs
        assert first_call_kwargs.get("filter_command") is False
        assert first_call_kwargs.get("filter_mai") is False

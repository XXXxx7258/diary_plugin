"""pipelines/chat_resolver.py 单元测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from diary_plugin.pipelines.chat_resolver import (
    ChatResolver,
    parse_target_config,
    resolve_filter_strategy,
)


class TestParseTargetConfig:
    def test_groups_only(self):
        groups, privates = parse_target_config(["group:111", "group:222"])
        assert groups == ["111", "222"]
        assert privates == []

    def test_privates_only(self):
        groups, privates = parse_target_config(["private:333"])
        assert groups == []
        assert privates == ["333"]

    def test_mixed(self):
        groups, privates = parse_target_config(["group:111", "private:222", "group:333"])
        assert groups == ["111", "333"]
        assert privates == ["222"]

    def test_invalid_logged_skipped(self, caplog):
        groups, privates = parse_target_config(["bogus:444", "group:555"])
        assert groups == ["555"]
        assert privates == []

    def test_empty(self):
        assert parse_target_config([]) == ([], [])


class TestResolveFilterStrategy:
    def test_whitelist_with_targets(self):
        strategy, configs = resolve_filter_strategy("whitelist", ["group:1"])
        assert strategy == "PROCESS_WHITELIST"
        assert configs == ["group:1"]

    def test_whitelist_empty_disables(self):
        strategy, _ = resolve_filter_strategy("whitelist", [])
        assert strategy == "DISABLE_SCHEDULER"

    def test_blacklist_with_targets(self):
        strategy, configs = resolve_filter_strategy("blacklist", ["group:1"])
        assert strategy == "PROCESS_BLACKLIST"
        assert configs == ["group:1"]

    def test_blacklist_empty_processes_all(self):
        strategy, _ = resolve_filter_strategy("blacklist", [])
        assert strategy == "PROCESS_ALL"

    def test_unknown_mode_falls_back(self):
        strategy, _ = resolve_filter_strategy("???", [])
        assert strategy in ("DISABLE_SCHEDULER", "PROCESS_WHITELIST")


class TestChatResolverQuery:
    """ctx.chat 调用模拟测试 — 验证 R1 spike 结论(session_id 字段)。"""

    @pytest.mark.asyncio
    async def test_group_id_query_returns_session_id(self, tmp_path):
        ctx = MagicMock()
        # host 实际返回结构:{"success": True, "stream": {"session_id": "...", ...}}
        ctx.chat.get_stream_by_group_id = AsyncMock(
            return_value={"success": True, "stream": {
                "session_id": "qq_group_111",
                "platform": "qq",
                "user_id": "",
                "group_id": "111",
                "is_group_session": True,
            }}
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        sid = await resolver._query_session_id("111", is_group=True)
        assert sid == "qq_group_111"
        ctx.chat.get_stream_by_group_id.assert_awaited_once_with("111")

    @pytest.mark.asyncio
    async def test_user_id_query_returns_session_id(self, tmp_path):
        ctx = MagicMock()
        ctx.chat.get_stream_by_user_id = AsyncMock(
            return_value={"success": True, "stream": {"session_id": "qq_priv_222"}}
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        sid = await resolver._query_session_id("222", is_group=False)
        assert sid == "qq_priv_222"

    @pytest.mark.asyncio
    async def test_double_envelope_peeled(self, tmp_path):
        ctx = MagicMock()
        # 双层信封(SDK 2.4 偶发场景)
        ctx.chat.get_stream_by_group_id = AsyncMock(
            return_value={"success": True, "result": {
                "success": True, "stream": {"session_id": "deep_sid"}
            }}
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        sid = await resolver._query_session_id("999", is_group=True)
        assert sid == "deep_sid"

    @pytest.mark.asyncio
    async def test_stream_none_returns_none(self, tmp_path):
        ctx = MagicMock()
        ctx.chat.get_stream_by_group_id = AsyncMock(
            return_value={"success": True, "stream": None}
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        sid = await resolver._query_session_id("404", is_group=True)
        assert sid is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, tmp_path):
        ctx = MagicMock()
        ctx.chat.get_stream_by_group_id = AsyncMock(side_effect=RuntimeError("boom"))
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        sid = await resolver._query_session_id("err", is_group=True)
        assert sid is None

    @pytest.mark.asyncio
    async def test_resolve_caches(self, tmp_path):
        ctx = MagicMock()
        ctx.chat.get_stream_by_group_id = AsyncMock(
            return_value={"success": True, "stream": {"session_id": "sid1"}}
        )
        resolver = ChatResolver(ctx, plugin_dir=str(tmp_path))
        # 第一次查询
        result1 = await resolver.resolve_to_session_ids(["group:111"])
        # 第二次:命中缓存,不再调 ctx
        result2 = await resolver.resolve_to_session_ids(["group:111"])
        assert result1 == result2 == ["sid1"]
        # 配置 hash 不变,只调一次
        assert ctx.chat.get_stream_by_group_id.call_count == 1

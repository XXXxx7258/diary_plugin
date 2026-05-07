"""pipelines/_envelope.py 单元测试。"""

from diary_plugin.pipelines._envelope import peel_envelope


def test_non_dict_returned_as_is():
    assert peel_envelope(42) == 42
    assert peel_envelope("hello") == "hello"
    assert peel_envelope([1, 2, 3]) == [1, 2, 3]
    assert peel_envelope(None) is None


def test_no_envelope_returned_as_is():
    payload = {"messages": [], "stream": {}}
    assert peel_envelope(payload) == payload


def test_single_layer_envelope():
    inner = {"messages": [1, 2, 3]}
    payload = {"success": True, "result": inner}
    assert peel_envelope(payload) == inner


def test_double_layer_envelope():
    inner = {"messages": [1, 2, 3]}
    payload = {"success": True, "result": {"success": True, "result": inner}}
    assert peel_envelope(payload) == inner


def test_envelope_with_none_inner():
    payload = {"success": True, "result": None}
    # inner 是 None 时不剥(原样返回)
    assert peel_envelope(payload) == payload


def test_max_depth_safety():
    # 构造 5 层信封,max_depth=4 时应保留最内层包装
    payload = {"success": True, "result": {"success": True, "result": {
        "success": True, "result": {"success": True, "result": "core"}
    }}}
    result = peel_envelope(payload, max_depth=2)
    # 剥 2 层后还剩 2 层信封
    assert isinstance(result, dict)
    assert "success" in result

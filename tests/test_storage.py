"""pipelines/storage.py 单元测试(用 tmpdir 隔离 IO)。"""

import time

import pytest

from diary_plugin.pipelines.storage import DiaryStorage


@pytest.fixture
def storage(tmp_path):
    return DiaryStorage(plugin_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_save_and_get_diary(storage):
    diary = {
        "date": "2025-01-15",
        "diary_content": "今天天气真好",
        "word_count": 8,
        "generation_time": time.time(),
        "weather": "晴",
        "is_published_qzone": False,
    }
    assert await storage.save_diary(diary) is True
    retrieved = await storage.get_diary("2025-01-15")
    assert retrieved is not None
    assert retrieved["diary_content"] == "今天天气真好"


@pytest.mark.asyncio
async def test_get_diary_nonexistent_returns_none(storage):
    assert await storage.get_diary("1999-01-01") is None


@pytest.mark.asyncio
async def test_get_diaries_by_date_returns_all(storage):
    base = time.time()
    for i in range(3):
        await storage.save_diary({
            "date": "2025-01-15",
            "diary_content": f"日记 {i}",
            "word_count": 3,
            "generation_time": base + i * 10,
            "is_published_qzone": False,
        })
    diaries = await storage.get_diaries_by_date("2025-01-15")
    assert len(diaries) == 3
    # 升序
    assert diaries[0]["generation_time"] < diaries[-1]["generation_time"]


@pytest.mark.asyncio
async def test_list_diaries_descending_with_limit(storage):
    for i in range(5):
        await storage.save_diary({
            "date": f"2025-01-{10 + i:02d}",
            "diary_content": "x",
            "word_count": 1,
            "generation_time": float(1700000000 + i),
            "is_published_qzone": i % 2 == 0,
        })
    recent = await storage.list_diaries(limit=3)
    assert len(recent) == 3
    # 降序
    assert recent[0]["generation_time"] > recent[-1]["generation_time"]


@pytest.mark.asyncio
async def test_list_diaries_unlimited(storage):
    for i in range(7):
        await storage.save_diary({
            "date": f"2025-02-{10 + i:02d}",
            "diary_content": "x",
            "word_count": 1,
            "generation_time": float(1700000000 + i),
        })
    all_diaries = await storage.list_diaries(limit=0)
    assert len(all_diaries) == 7


@pytest.mark.asyncio
async def test_get_stats(storage):
    for i in range(3):
        await storage.save_diary({
            "date": f"2025-03-{10 + i:02d}",
            "diary_content": "x" * (10 * (i + 1)),
            "word_count": 10 * (i + 1),
            "generation_time": float(1700000000 + i),
            "is_published_qzone": i == 0,
        })
    stats = await storage.get_stats()
    assert stats["total_count"] == 3
    assert stats["total_words"] == 60  # 10+20+30
    assert stats["avg_words"] == 20


@pytest.mark.asyncio
async def test_get_stats_empty(storage):
    stats = await storage.get_stats()
    assert stats == {"total_count": 0, "total_words": 0, "avg_words": 0, "latest_date": "无"}

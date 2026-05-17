"""JSON 文件键值存储。

替换原 sirius_chat 平台的 data_store 组件。
提供 get/set/all 接口，数据持久化到单个 JSON 文件。
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonFileStore:
    """基于 JSON 文件的键值持久化存储。

    用法:
        store = JsonFileStore("data/store.json")
        store.set("key1", {"hello": "world"})
        value = store.get("key1")         # {"hello": "world"}
        value = store.get("not_exist")    # None
        all_data = store.all()            # {"key1": {"hello": "world"}}

    线程安全：写操作加锁，读操作不加锁（假设主线程读写）。
    """

    def __init__(self, file_path: str) -> None:
        self._file = Path(file_path)
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """从磁盘加载数据。"""
        if self._file.exists():
            try:
                raw = self._file.read_text(encoding="utf-8")
                self._data = json.loads(raw) if raw.strip() else {}
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("加载存储文件失败 %s: %s", self._file, exc)
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        """写入磁盘。"""
        try:
            self._file.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("写入存储文件失败 %s: %s", self._file, exc)

    def get(self, key: str) -> Any:
        """获取键对应的值，不存在时返回 None。"""
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        """设置键值对并持久化。"""
        with self._lock:
            self._data[key] = value
            self._save()

    def all(self) -> dict[str, Any]:
        """返回全部数据的浅拷贝。"""
        return dict(self._data)

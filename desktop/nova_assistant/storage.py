from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class LocalStorage:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, collection: str) -> Path:
        return self.data_dir / f"{collection}.jsonl"

    def _append(self, collection: str, record: dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            **record,
        }
        with self._lock, self._path(collection).open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _read(self, collection: str, limit: int) -> list[dict[str, Any]]:
        path = self._path(collection)
        if not path.exists() or limit <= 0:
            return []
        valid: list[dict[str, Any]] = []
        with self._lock, path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(item, dict):
                    valid.append(item)
        return valid[-limit:]

    def append_command(self, command: str) -> None:
        self._append("commands", {"command": command})

    def remember(self, content: str) -> None:
        self._append("memories", {"content": content})

    def recent_memories(self, limit: int = 5) -> list[dict[str, Any]]:
        return self._read("memories", limit)

    def add_note(self, content: str) -> None:
        self._append("notes", {"content": content})

    def recent_notes(self, limit: int = 5) -> list[dict[str, Any]]:
        return self._read("notes", limit)

    def append_conversation(self, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Conversation role must be user or assistant")
        self._append("conversations", {"role": role, "content": content})

    def recent_conversation(self, limit: int = 10) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for item in self._read("conversations", limit):
            role, content = item.get("role"), item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str):
                result.append({"role": role, "content": content})
        return result


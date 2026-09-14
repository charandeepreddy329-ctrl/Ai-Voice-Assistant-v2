from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True, slots=True)
class Settings:
    assistant_name: str
    chat_model: str
    reasoning_model: str
    ollama_host: str
    data_dir: Path
    speech_enabled: bool
    max_spoken_characters: int = 700

    @property
    def generated_dir(self) -> Path:
        return self.data_dir / "generated"

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        if load_dotenv is not None:
            load_dotenv(dotenv_path=env_file, override=False)
        data_dir = Path(
            os.getenv("NOVA_DATA_DIR", str(Path.home() / ".nova-assistant"))
        ).expanduser()
        return cls(
            assistant_name=os.getenv("NOVA_ASSISTANT_NAME", "Nova"),
            chat_model=os.getenv("NOVA_CHAT_MODEL", "llama3.2:3b"),
            reasoning_model=os.getenv("NOVA_REASONING_MODEL", "deepseek-r1:8b"),
            ollama_host=os.getenv("NOVA_OLLAMA_HOST", "http://127.0.0.1:11434"),
            data_dir=data_dir,
            speech_enabled=_as_bool(os.getenv("NOVA_SPEECH_ENABLED"), True),
        )


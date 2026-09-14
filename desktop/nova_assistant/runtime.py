from dataclasses import dataclass
from pathlib import Path

from .actions import DesktopActions
from .assistant import NovaAssistant
from .config import Settings
from .llm import OllamaLLM
from .speech import SpeechService
from .storage import LocalStorage


@dataclass(slots=True)
class Runtime:
    settings: Settings
    assistant: NovaAssistant
    speech: SpeechService


def build_runtime(env_file: Path | None = None) -> Runtime:
    settings = Settings.load(env_file)
    storage = LocalStorage(settings.data_dir)
    llm = OllamaLLM(storage, settings.chat_model, settings.reasoning_model, settings.ollama_host)
    actions = DesktopActions(llm, settings.generated_dir)
    return Runtime(settings, NovaAssistant(storage, llm, actions),
                   SpeechService(settings.speech_enabled, settings.max_spoken_characters))


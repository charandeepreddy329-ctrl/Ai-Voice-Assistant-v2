from __future__ import annotations

import re
from typing import Any

from .models import LLMUnavailableError
from .storage import LocalStorage


SYSTEM_PROMPT = """You are Nova, a capable local personal assistant. Answer
naturally in clear, simple English. Keep the first paragraph concise and
voice-friendly. Use prior conversation only when relevant. Be honest about
uncertainty. Never claim an action happened unless a tool confirms it."""

MATH_PROMPT = """You are Nova's math tutor. Solve accurately, explain only the
essential steps, and state the final answer clearly for spoken output."""

CODE_PROMPT = """Return only complete, runnable Python source code. Do not include
Markdown fences or prose. Prefer the standard library. Include a main guard. Do
not read secrets, install packages, or execute shell commands."""


def _response_text(response: Any) -> str:
    try:
        text = response.message.content
    except AttributeError:
        text = response["message"]["content"]
    if not isinstance(text, str) or not text.strip():
        raise LLMUnavailableError("The local model returned an empty response.")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


class OllamaLLM:
    def __init__(self, storage: LocalStorage, chat_model: str, reasoning_model: str, host: str):
        self.storage = storage
        self.chat_model = chat_model
        self.reasoning_model = reasoning_model
        self.host = host
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import ollama
        except ImportError as error:
            raise LLMUnavailableError("Install the Ollama Python package first.") from error
        self._client = ollama.Client(host=self.host)
        return self._client

    def _chat(self, model: str, messages: list[dict[str, str]]) -> str:
        try:
            response = self._get_client().chat(model=model, messages=messages)
        except Exception as error:
            raise LLMUnavailableError(
                f"I could not reach model '{model}'. Start Ollama and pull the model."
            ) from error
        return _response_text(response)

    def answer(self, question: str, *, math_mode: bool = False) -> str:
        messages = [
            {"role": "system", "content": MATH_PROMPT if math_mode else SYSTEM_PROMPT},
            *self.storage.recent_conversation(limit=10),
            {"role": "user", "content": question},
        ]
        answer = self._chat(self.reasoning_model if math_mode else self.chat_model, messages)
        self.storage.append_conversation("user", question)
        self.storage.append_conversation("assistant", answer)
        return answer

    def generate_python(self, request: str) -> str:
        answer = self._chat(
            self.reasoning_model,
            [{"role": "system", "content": CODE_PROMPT}, {"role": "user", "content": request}],
        )
        answer = re.sub(r"^```(?:python)?\s*", "", answer, flags=re.IGNORECASE)
        answer = re.sub(r"\s*```$", "", answer)
        return answer.strip() + "\n"

    def health(self) -> str:
        try:
            self._get_client().list()
        except Exception as error:
            raise LLMUnavailableError("Ollama is not reachable.") from error
        return f"Ollama is online. Chat model: {self.chat_model}."


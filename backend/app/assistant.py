from __future__ import annotations

import re
from datetime import datetime
from typing import Callable

from .actions import DesktopActions
from .calculator import extract_expression, safe_calculate
from .llm import OllamaLLM
from .models import AssistantResponse, NovaError
from .storage import LocalStorage


HELP_TEXT = (
    "I can chat, solve math, remember information, manage notes, search Google or "
    "YouTube, open approved websites, and generate downloadable Python files. Desktop apps are unavailable on the web."
)


class NovaAssistant:
    def __init__(self, storage: LocalStorage, llm: OllamaLLM, actions: DesktopActions,
                 now: Callable[[], datetime] = datetime.now):
        self.storage, self.llm, self.actions, self.now = storage, llm, actions, now

    @staticmethod
    def _normalize(command: str) -> str:
        text = " ".join(command.strip().split())
        return re.sub(r"^(?:hey\s+)?(?:nova|innova|lenovo)\b[\s,]*", "", text,
                      flags=re.IGNORECASE).strip()

    def handle(self, command: str) -> AssistantResponse:
        original = " ".join(command.strip().split())
        if not original:
            return AssistantResponse("Yes, I am listening.")
        self.storage.append_command(original)
        normalized = self._normalize(original)
        try:
            return self._route(normalized, normalized.lower())
        except NovaError as error:
            return AssistantResponse(str(error))
        except Exception as error:
            print(f"Unexpected Nova error: {error}")
            return AssistantResponse("Something went wrong while handling that request.")

    def _route(self, command: str, lowered: str) -> AssistantResponse:
        if not command:
            return AssistantResponse("Yes, I am listening.")
        if lowered in {"exit", "stop", "quit", "bye", "close"}:
            return AssistantResponse("Goodbye. Have a nice day.", should_exit=True)
        if lowered in {"hello", "hi", "hey"}:
            return AssistantResponse("Hello. I am Nova. How can I help you?")
        if lowered in {"help", "what can you do", "show help"}:
            return AssistantResponse(HELP_TEXT)
        if lowered in {"time", "what is the time", "tell me the time", "current time"}:
            return AssistantResponse("The current time is " + self.now().strftime("%I:%M %p").lstrip("0") + ".")
        if lowered in {"date", "today's date", "what is today's date", "tell me the date"}:
            return AssistantResponse("Today is " + self.now().strftime("%A, %d %B %Y") + ".")
        if lowered in {"status", "system status", "project status"}:
            return AssistantResponse(self.llm.health())
        if lowered in {"what do you remember", "show memory", "show memories"}:
            items = self.storage.recent_memories(5)
            if not items:
                return AssistantResponse("I do not remember anything yet.")
            return AssistantResponse("Here is what I remember: " + "; ".join(str(x["content"]) for x in items))
        match = re.match(r"^remember(?:\s+that)?\s+(.+)$", command, re.IGNORECASE)
        if match:
            self.storage.remember(match.group(1).strip())
            return AssistantResponse("I will remember that.")
        if lowered in {"show notes", "read notes", "show my notes"}:
            items = self.storage.recent_notes(5)
            if not items:
                return AssistantResponse("You do not have any saved notes yet.")
            return AssistantResponse("Your recent notes are: " + "; ".join(str(x["content"]) for x in items))
        match = re.match(r"^(?:take|save)\s+(?:a\s+)?note(?:\s+that)?\s+(.+)$", command, re.IGNORECASE)
        if match:
            self.storage.add_note(match.group(1).strip())
            return AssistantResponse("I saved your note.")
        if re.match(r"^(?:create\s+(?:a\s+)?python\s+file|generate\s+python\s+code|write\s+python\s+code)\b", lowered):
            return AssistantResponse(self.actions.create_python_file(command))
        match = re.match(r"^(?:search\s+youtube|youtube\s+search)(?:\s+for)?\s+(.+)$", command, re.IGNORECASE)
        if match:
            return AssistantResponse(self.actions.search_youtube(match.group(1)))
        match = re.match(r"^(?:search(?:\s+google)?|google\s+search)(?:\s+for)?\s+(.+)$", command, re.IGNORECASE)
        if match:
            return AssistantResponse(self.actions.search_google(match.group(1)))
        match = re.match(r"^(?:open|launch)(?:\s+app)?\s+(.+)$", command, re.IGNORECASE)
        if match and any(name in lowered for name in MAC_APP_WORDS):
            return AssistantResponse(self.actions.open_app(match.group(1)))
        match = re.match(r"^open\s+(.+)$", command, re.IGNORECASE)
        if match:
            return AssistantResponse(self.actions.open_website(match.group(1)))
        expression = extract_expression(command)
        if expression is not None:
            return AssistantResponse(f"The answer is {safe_calculate(expression)}.")
        if re.match(r"^(?:calculate|compute|solve|math)\b", lowered):
            return AssistantResponse(self.llm.answer(command, math_mode=True))
        return AssistantResponse(self.llm.answer(command))


MAC_APP_WORDS = (
    "calculator", "calendar", "chrome", "facetime", "messages", "notes", "safari",
    "spotify", "terminal", "visual studio code", "vs code", "vscode",
)


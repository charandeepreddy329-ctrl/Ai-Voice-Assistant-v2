from __future__ import annotations

import re
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from .llm import OllamaLLM
from .models import NovaError


WEBSITES = {
    "chatgpt": "https://chatgpt.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "linkedin": "https://www.linkedin.com",
    "youtube": "https://www.youtube.com",
}
MAC_APPS = {
    "calculator": "Calculator", "calendar": "Calendar", "chrome": "Google Chrome",
    "facetime": "FaceTime", "messages": "Messages", "notes": "Notes",
    "safari": "Safari", "spotify": "Spotify", "terminal": "Terminal",
    "visual studio code": "Visual Studio Code", "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
}


class DesktopActions:
    def __init__(self, llm: OllamaLLM, generated_dir: Path):
        self.llm = llm
        self.generated_dir = Path(generated_dir)

    def search_google(self, query: str) -> str:
        query = query.strip()
        if not query:
            return "Please tell me what to search for."
        webbrowser.open("https://www.google.com/search?q=" + quote_plus(query))
        return f"Searching Google for {query}."

    def search_youtube(self, query: str) -> str:
        query = query.strip()
        if not query:
            return "Please tell me what to search for on YouTube."
        webbrowser.open("https://www.youtube.com/results?search_query=" + quote_plus(query))
        return f"Searching YouTube for {query}."

    def open_website(self, name: str) -> str:
        normalized = name.lower().strip()
        for key in sorted(WEBSITES, key=len, reverse=True):
            if re.search(rf"\b{re.escape(key)}\b", normalized):
                webbrowser.open(WEBSITES[key])
                return f"Opening {key}."
        return "I can open Google, YouTube, GitHub, Gmail, ChatGPT, or LinkedIn."

    def open_app(self, name: str) -> str:
        normalized = name.lower().strip()
        for key in sorted(MAC_APPS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(key)}\b", normalized):
                app_name = MAC_APPS[key]
                try:
                    subprocess.run(["open", "-a", app_name], check=True, capture_output=True,
                                   text=True, timeout=15)
                except (subprocess.SubprocessError, OSError) as error:
                    raise NovaError(f"I could not open {app_name}.") from error
                return f"Opening {app_name}."
        return "I do not know that application yet."

    def create_python_file(self, request: str) -> str:
        match = re.search(r"\bcalled\s+([a-zA-Z0-9_-]{1,48})", request)
        stem = match.group(1) if match else datetime.now().strftime("nova_%Y%m%d_%H%M%S")
        filename = f"{stem}.py"
        code = self.llm.generate_python(request)
        if len(code) > 100_000:
            raise NovaError("The generated program is too large to save safely.")
        try:
            compile(code, filename, "exec")
        except SyntaxError as error:
            raise NovaError("The model produced invalid Python, so I did not save it.") from error
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        destination = self.generated_dir / filename
        destination.write_text(code, encoding="utf-8")
        return f"I saved the Python program as {destination}. I did not execute it."


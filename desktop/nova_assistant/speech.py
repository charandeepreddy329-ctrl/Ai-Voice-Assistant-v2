from __future__ import annotations

import re
import shutil
import subprocess

from .models import SpeechInputError


class SpeechService:
    def __init__(self, enabled: bool = True, max_characters: int = 700):
        self.enabled, self.max_characters = enabled, max_characters

    def speak(self, text: str) -> None:
        if not self.enabled or not text or shutil.which("say") is None:
            return
        spoken = re.sub(r"[`*_#]", "", text)[:self.max_characters]
        try:
            subprocess.run(["say", spoken], check=False, timeout=60, capture_output=True)
        except (OSError, subprocess.SubprocessError):
            pass

    def listen(self) -> str:
        try:
            import speech_recognition as sr
        except ImportError as error:
            raise SpeechInputError("Voice input dependencies are not installed.") from error
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1.2
        recognizer.dynamic_energy_threshold = True
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
        except sr.WaitTimeoutError as error:
            raise SpeechInputError("I did not hear anything.") from error
        except (OSError, AttributeError) as error:
            raise SpeechInputError("I could not access the microphone.") from error
        try:
            return recognizer.recognize_google(audio).strip()
        except sr.UnknownValueError as error:
            raise SpeechInputError("Sorry, I could not understand your voice.") from error
        except sr.RequestError as error:
            raise SpeechInputError("Speech recognition is unavailable. Check your internet connection.") from error


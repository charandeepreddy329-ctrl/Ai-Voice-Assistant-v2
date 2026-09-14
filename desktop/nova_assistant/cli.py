from __future__ import annotations

import argparse
from pathlib import Path

from .models import SpeechInputError
from .runtime import build_runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Nova local AI voice assistant")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--text", action="store_true")
    parser.add_argument("--no-speech", action="store_true")
    args = parser.parse_args()
    env_file = Path.cwd() / ".env"
    runtime = build_runtime(env_file if env_file.exists() else None)
    if args.no_speech:
        runtime.speech.enabled = False
    if args.gui:
        from .gui import launch_gui
        launch_gui(runtime)
        return
    greeting = "Nova is ready. Type a message"
    if not args.text:
        greeting += " or press Enter to use the microphone"
    print(greeting + ". Type 'exit' to stop.")
    while True:
        try:
            typed = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNova: Goodbye.")
            break
        if not typed:
            if args.text:
                continue
            print("Listening…")
            try:
                typed = runtime.speech.listen()
            except SpeechInputError as error:
                print(f"Nova: {error}")
                continue
            print(f"You said: {typed}")
        response = runtime.assistant.handle(typed)
        print(f"Nova: {response.text}")
        runtime.speech.speak(response.text)
        if response.should_exit:
            break


if __name__ == "__main__":
    main()


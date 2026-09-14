# Nova AI Voice Assistant v2

A clean, local-first macOS assistant with CLI and GUI modes, microphone input,
macOS speech, structured memory, safe tools, and local Ollama models.

## Improvements

- One command engine powers both interfaces.
- Replies are spoken once, and long work runs off the GUI thread.
- Safe AST arithmetic replaces `eval`.
- Generated Python is validated and saved but never auto-executed.
- No automatic package installation or arbitrary shell execution.
- Memory and chat use structured JSONL outside the source tree.
- Imports no longer launch the application.
- Tests cover routing, memory, query parsing, and calculator safety.

## Run

Using the existing prototype environment:

```bash
cd /Users/charandeepreddy/Desktop/AI-Voice-Assistant-v2
PYTHONPATH=. ../AI-Voice-Assistant/venv/bin/python -m nova_assistant --gui
```

Ollama must be running with `llama3.2:3b` and `deepseek-r1:8b` installed.

## Test

```bash
python3 -m unittest discover -s tests -v
```

Data is stored under `~/.nova-assistant` by default. Microphone transcription
uses Google speech recognition; typed prompts and Ollama inference remain local.


from __future__ import annotations

import sys

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from .models import AssistantResponse, SpeechInputError
from .runtime import Runtime


class CommandWorker(QThread):
    completed = pyqtSignal(object)
    def __init__(self, runtime: Runtime, command: str):
        super().__init__(); self.runtime, self.command = runtime, command
    def run(self) -> None:
        self.completed.emit(self.runtime.assistant.handle(self.command))


class ListenWorker(QThread):
    recognized = pyqtSignal(str)
    failed = pyqtSignal(str)
    def __init__(self, runtime: Runtime):
        super().__init__(); self.runtime = runtime
    def run(self) -> None:
        try:
            self.recognized.emit(self.runtime.speech.listen())
        except SpeechInputError as error:
            self.failed.emit(str(error))


class SpeechWorker(QThread):
    def __init__(self, runtime: Runtime, text: str):
        super().__init__(); self.runtime, self.text = runtime, text
    def run(self) -> None:
        self.runtime.speech.speak(self.text)


class NovaWindow(QMainWindow):
    def __init__(self, runtime: Runtime):
        super().__init__()
        self.runtime = runtime
        self.command_worker = None
        self.listen_worker = None
        self.speech_workers = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("Nova AI Assistant v2")
        self.resize(920, 680)
        root = QWidget(); layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24); layout.setSpacing(14)
        title = QLabel("NOVA"); title.setObjectName("title")
        subtitle = QLabel("Local intelligence. Your voice. Your data."); subtitle.setObjectName("subtitle")
        self.chat = QPlainTextEdit(); self.chat.setReadOnly(True)
        self.status = QLabel("Ready"); self.status.setObjectName("status")
        self.input = QLineEdit(); self.input.setPlaceholderText("Ask Nova anything…")
        self.input.returnPressed.connect(self.send_message)
        self.send_button = QPushButton("Send"); self.send_button.clicked.connect(self.send_message)
        self.mic_button = QPushButton("Use microphone"); self.mic_button.setObjectName("secondary")
        self.mic_button.clicked.connect(self.listen)
        clear = QPushButton("Clear chat"); clear.setObjectName("quiet"); clear.clicked.connect(self.chat.clear)
        self.speech_toggle = QCheckBox("Speak replies"); self.speech_toggle.setChecked(self.runtime.speech.enabled)
        row = QHBoxLayout(); row.addWidget(self.input, 1); row.addWidget(self.send_button); row.addWidget(self.mic_button)
        footer = QHBoxLayout(); footer.addWidget(self.status); footer.addStretch(); footer.addWidget(self.speech_toggle); footer.addWidget(clear)
        layout.addWidget(title); layout.addWidget(subtitle); layout.addWidget(self.chat, 1); layout.addLayout(row); layout.addLayout(footer)
        self.setCentralWidget(root)
        self.setStyleSheet("""
          QMainWindow,QWidget{background:#0b1020;color:#e8ecf4;font-size:15px}
          QLabel#title{color:#75e6da;font-size:32px;font-weight:800;letter-spacing:5px}
          QLabel#subtitle{color:#8f9bb3;font-size:14px;margin-bottom:8px}
          QLabel#status{color:#75e6da;font-size:13px}
          QPlainTextEdit{background:#111a2e;border:1px solid #24304a;border-radius:14px;padding:14px}
          QLineEdit{background:#111a2e;border:1px solid #33415f;border-radius:10px;padding:12px}
          QLineEdit:focus{border:1px solid #75e6da}
          QPushButton{background:#3e8e88;border:0;border-radius:10px;padding:12px 18px;font-weight:650}
          QPushButton:hover{background:#4aa69f} QPushButton:disabled{background:#293244;color:#6d7890}
          QPushButton#secondary{background:#263653} QPushButton#quiet{background:transparent;color:#9aa6bb;padding:8px}
          QCheckBox{color:#aab4c7;spacing:8px}
        """)
        self.chat.appendPlainText("Nova: Hello. I am ready when you are.")

    def _busy(self, busy: bool, status: str = "Ready") -> None:
        self.send_button.setEnabled(not busy); self.mic_button.setEnabled(not busy)
        self.input.setEnabled(not busy); self.status.setText(status)

    def send_message(self) -> None:
        command = self.input.text().strip()
        if not command or self.command_worker is not None: return
        self.input.clear(); self.chat.appendPlainText(f"\nYou: {command}"); self._run(command)

    def _run(self, command: str) -> None:
        self._busy(True, "Thinking…")
        self.command_worker = CommandWorker(self.runtime, command)
        self.command_worker.completed.connect(self._show)
        self.command_worker.finished.connect(self._command_done)
        self.command_worker.start()

    def _command_done(self) -> None:
        if self.command_worker:
            self.command_worker.deleteLater(); self.command_worker = None

    def _show(self, response: AssistantResponse) -> None:
        self.chat.appendPlainText(f"Nova: {response.text}"); self._busy(False); self.input.setFocus()
        if response.should_exit: self.close(); return
        if self.speech_toggle.isChecked():
            worker = SpeechWorker(self.runtime, response.text); self.speech_workers.append(worker)
            worker.finished.connect(lambda: self._speech_done(worker)); worker.start()

    def _speech_done(self, worker) -> None:
        if worker in self.speech_workers: self.speech_workers.remove(worker)
        worker.deleteLater()

    def listen(self) -> None:
        if self.listen_worker is not None or self.command_worker is not None: return
        self._busy(True, "Listening…"); self.listen_worker = ListenWorker(self.runtime)
        self.listen_worker.recognized.connect(self._recognized)
        self.listen_worker.failed.connect(self._listen_failed)
        self.listen_worker.finished.connect(self._listen_done); self.listen_worker.start()

    def _recognized(self, command: str) -> None:
        self.chat.appendPlainText(f"\nYou: {command}"); self._run(command)

    def _listen_failed(self, message: str) -> None:
        self.chat.appendPlainText(f"Nova: {message}"); self._busy(False)

    def _listen_done(self) -> None:
        if self.listen_worker:
            self.listen_worker.deleteLater(); self.listen_worker = None


def launch_gui(runtime: Runtime) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = NovaWindow(runtime); window.show(); app.exec()


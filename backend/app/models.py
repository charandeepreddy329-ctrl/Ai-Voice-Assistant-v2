from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssistantResponse:
    text: str
    should_exit: bool = False


class NovaError(RuntimeError):
    """A failure that can be displayed safely to the user."""


class LLMUnavailableError(NovaError):
    pass


class SpeechInputError(NovaError):
    pass


class UnsafeExpressionError(NovaError):
    pass


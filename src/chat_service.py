from __future__ import annotations

from typing import TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class ChatService:
    def __init__(self) -> None:
        self.history: list[ChatMessage] = []

    def reset_history(self) -> None:
        self.history = []

    def add_user_message(self, content: str) -> None:
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.history.append({"role": "assistant", "content": content})

    def build_messages(self) -> list[ChatMessage]:
        return [message.copy() for message in self.history]

"""
Short-term Conversation Memory Buffer.
Maintains multi-turn Q&A chat history using a sliding window without storing vector embeddings.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ChatMessage:
    """Represents a single message in the conversation session."""
    role: str  # 'user' | 'assistant'
    content: str
    timestamp: float = field(default_factory=time.time)
    citations: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "citations": self.citations or []
        }


class ConversationMemoryBuffer:
    """
    Manages multi-turn conversation memory.
    Maintains a sliding window of recent dialogue turns to provide ongoing context
    without overloading the LLM context window.
    """

    def __init__(self, max_history_turns: int = 6):
        self.max_history_turns = max_history_turns
        self._messages: List[ChatMessage] = []

    def add_user_message(self, content: str) -> None:
        """Append a message from the user."""
        self._messages.append(ChatMessage(role="user", content=content))

    def add_assistant_message(
        self,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Append a response from the assistant with optional citations."""
        self._messages.append(ChatMessage(
            role="assistant",
            content=content,
            citations=citations
        ))

    def get_messages(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """Retrieve recent messages."""
        max_msgs = (limit or self.max_history_turns) * 2
        return self._messages[-max_msgs:] if max_msgs > 0 else []

    def get_formatted_history(self, limit: Optional[int] = None) -> str:
        """
        Format recent conversation history as a text block for prompt context.
        """
        recent_messages = self.get_messages(limit=limit)
        if not recent_messages:
            return ""

        formatted_lines: List[str] = []
        for msg in recent_messages:
            prefix = "User" if msg.role == "user" else "HedgeDoc"
            formatted_lines.append(f"{prefix}: {msg.content}")

        return "\n".join(formatted_lines)

    def clear(self) -> None:
        """Clear all conversation history."""
        self._messages.clear()

    @property
    def total_messages(self) -> int:
        return len(self._messages)

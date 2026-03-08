from dataclasses import dataclass

from libs.llm.base import LLMMessage
from libs.schemas.chat import ChatMessageRead


@dataclass
class ChatContextBuilder:
    system_prompt: str
    max_messages: int

    def build(self, messages: list[ChatMessageRead]) -> list[LLMMessage]:
        trimmed = messages[-self.max_messages :]
        llm_messages: list[LLMMessage] = [
            {"role": "system", "content": self.system_prompt}
        ]
        llm_messages.extend(
            {
                "role": "assistant" if message.role == "assistant" else "user",
                "content": message.content,
            }
            for message in trimmed
            if message.role in {"user", "assistant"}
        )
        return llm_messages

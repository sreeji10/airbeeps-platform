from libs.schemas.chat import ChatMessageRead
from services.chat.context import ChatContextBuilder


def test_context_builder_applies_system_prompt_and_window() -> None:
    builder = ChatContextBuilder(system_prompt="System prompt", max_messages=2)
    history = [
        ChatMessageRead(
            id="m1",
            role="user",
            content="first",
            created_by="u1",
            created_at="2026-01-01T00:00:00Z",
        ),
        ChatMessageRead(
            id="m2",
            role="assistant",
            content="second",
            created_by="u1",
            created_at="2026-01-01T00:00:01Z",
        ),
        ChatMessageRead(
            id="m3",
            role="user",
            content="third",
            created_by="u1",
            created_at="2026-01-01T00:00:02Z",
        ),
    ]

    result = builder.build(history)

    assert result[0] == {"role": "system", "content": "System prompt"}
    assert result[1:] == [
        {"role": "assistant", "content": "second"},
        {"role": "user", "content": "third"},
    ]

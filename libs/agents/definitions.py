from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDefinition:
    key: str
    name: str
    description: str


DEFAULT_AGENT = AgentDefinition(
    key="general-assistant",
    name="General Assistant",
    description="Default planning and response synthesis agent.",
)

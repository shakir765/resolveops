from dataclasses import dataclass

from resolveops_core.config import settings
from resolveops_core.prompts.loader import load_prompt


@dataclass
class AgentConfig:
    name: str
    prompt_version: str
    enabled: bool = True

    def load_prompt(self) -> str:
        return load_prompt(self.name, self.prompt_version)


DEFAULT_AGENTS = [
    "supervisor",
    "triage",
    "classifier",
    "knowledge",
    "diagnostic",
    "resolution",
    "tool_executor",
    "validator",
    "escalation",
    "communication",
]


def get_agent_configs(version: str | None = None) -> dict[str, AgentConfig]:
    prompt_version = version or settings.prompt_version
    return {
        name: AgentConfig(name=name, prompt_version=prompt_version, enabled=True)
        for name in DEFAULT_AGENTS
    }

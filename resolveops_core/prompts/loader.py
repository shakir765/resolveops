from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def load_prompt(name: str, version: str) -> str:
    path = PROMPTS_DIR / version / f"{name}.txt"
    if not path.exists():
        fallback = PROMPTS_DIR / "v1" / f"{name}.txt"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")

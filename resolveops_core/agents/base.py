from typing import Any

from resolveops_core.config import settings


def llm_available() -> bool:
    return bool(settings.openai_api_key)


def invoke_structured(prompt: str, context: dict[str, Any]) -> dict[str, Any]:
    """Rule-based fallback when no LLM key is configured."""
    text = f"{context.get('title', '')} {context.get('description', '')}".lower()
    return {"prompt": prompt, "context": context, "text": text}


def maybe_llm_summarize(prompt: str, context: dict[str, Any]) -> str:
    if not llm_available():
        return prompt
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)
        message = f"{prompt}\n\nTicket:\nTitle: {context.get('title')}\nDescription: {context.get('description')}"
        response = llm.invoke(message)
        return str(response.content)
    except Exception:
        return prompt

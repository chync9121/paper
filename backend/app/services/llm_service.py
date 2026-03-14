from __future__ import annotations

from typing import Any

import requests

from app.core.config import settings


class LLMServiceError(RuntimeError):
    pass


def call_llm(endpoint: str, payload: dict[str, Any], api_key: str | None = None, timeout: int = 90) -> dict[str, Any]:
    proxies = {
        "http": settings.http_proxy,
        "https": settings.https_proxy,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(
        endpoint,
        json=payload,
        headers=headers,
        proxies=proxies,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def generate_chat_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 1400,
) -> tuple[str, str, dict[str, Any]]:
    if not settings.llm_api_key:
        raise LLMServiceError("LLM_API_KEY is not configured.")

    endpoint = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model or settings.llm_model,
        "messages": messages,
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
    }

    try:
        data = call_llm(endpoint=endpoint, payload=payload, api_key=settings.llm_api_key)
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else str(exc)
        raise LLMServiceError(f"LLM HTTP error: {body}") from exc
    except requests.RequestException as exc:
        raise LLMServiceError(f"LLM request failed: {exc}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise LLMServiceError("LLM response contains no choices.")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise LLMServiceError("LLM response content is empty.")

    used_model = data.get("model") or (model or settings.llm_model)
    return content, used_model, data

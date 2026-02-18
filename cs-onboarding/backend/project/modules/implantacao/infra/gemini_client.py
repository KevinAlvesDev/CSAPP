import os
from typing import Any

import requests


class GeminiClientError(RuntimeError):
    pass


def generate_text(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 900,
    timeout_seconds: int = 20,
) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiClientError("GEMINI_API_KEY nao configurada.")

    model_name = (model or os.getenv("GEMINI_MODEL") or "gemini-1.5-flash").strip()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={api_key}"
    )

    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ],
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout_seconds)
    except requests.RequestException as exc:
        raise GeminiClientError(f"Falha ao chamar Gemini: {exc}") from exc

    if not response.ok:
        raise GeminiClientError(f"Gemini retornou erro {response.status_code}.")

    try:
        data = response.json() or {}
    except ValueError as exc:
        raise GeminiClientError("Resposta invalida do Gemini (nao-JSON).") from exc
    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiClientError("Gemini nao retornou candidatos.")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        raise GeminiClientError("Gemini nao retornou texto.")

    text = parts[0].get("text")
    if not text:
        raise GeminiClientError("Gemini retornou resposta vazia.")

    return str(text).strip()

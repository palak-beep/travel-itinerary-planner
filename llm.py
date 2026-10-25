"""Thin LLM client for Gemini and Groq using plain REST calls.

Using `requests` (not vendor SDKs) keeps deployment simple and avoids SDK
version breakage. Both providers are asked for JSON output.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

import requests

from models import ModelError

T = TypeVar("T")

DEMO = "Demo (no key needed)"
DEFAULT_MODELS = {"Gemini": "gemini-2.5-flash", "Groq": "llama-3.3-70b-versatile"}
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT = 90


class LLMError(Exception):
    """A readable error for the UI (bad key, quota, network, unusable reply)."""


@dataclass
class LLMConfig:
    provider: str = DEMO
    api_key: str = ""
    model: str = ""

    @property
    def is_demo(self) -> bool:
        return self.provider == DEMO or not self.api_key


def _http_error(provider: str, resp: requests.Response) -> LLMError:
    code = resp.status_code
    detail = ""
    try:
        body = resp.json()
        detail = body.get("error", {}).get("message", "") if isinstance(body.get("error"), dict) else str(body.get("error", ""))
    except ValueError:
        pass
    if code in (400, 401, 403):
        return LLMError(f"{provider} rejected the request ({code}). Check your API key and model name. {detail[:160]}")
    if code == 404:
        return LLMError(f"{provider} could not find that model. Check the model name in the sidebar.")
    if code == 429:
        return LLMError(f"{provider} rate limit or free quota reached. Wait a minute and try again.")
    return LLMError(f"{provider} returned an error ({code}). {detail[:160]}")


def _post(provider: str, url: str, **kwargs) -> dict:
    try:
        resp = requests.post(url, timeout=TIMEOUT, **kwargs)
    except requests.Timeout:
        raise LLMError(f"{provider} took too long to respond. Try again, or use a shorter trip.")
    except requests.RequestException as exc:
        raise LLMError(f"Could not reach {provider}. Check your internet connection. ({type(exc).__name__})")
    if resp.status_code != 200:
        raise _http_error(provider, resp)
    try:
        return resp.json()
    except ValueError:
        raise LLMError(f"{provider} sent a reply that was not JSON.")


def call_llm(cfg: LLMConfig, system: str, prompt: str, temperature: float = 0.7) -> str:
    model = cfg.model or DEFAULT_MODELS.get(cfg.provider, "")
    if cfg.provider == "Gemini":
        data = _post(
            "Gemini", GEMINI_URL.format(model=model),
            headers={"x-goog-api-key": cfg.api_key, "Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "responseMimeType": "application/json",
                                     "maxOutputTokens": 8192},
            },
        )
        try:
            return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, TypeError):
            raise LLMError("Gemini returned no content (the request may have been blocked). Try rephrasing.")
    if cfg.provider == "Groq":
        data = _post(
            "Groq", GROQ_URL,
            headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
            json={
                "model": model, "temperature": temperature, "max_tokens": 8000,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            },
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError("Groq returned no content. Try again.")
    raise LLMError("No AI provider selected.")


def extract_json(text: str) -> Any:
    """Parse JSON even if the model wrapped it in fences or added chatter."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def generate(parser: Callable[[Any], T], cfg: LLMConfig, system: str, prompt: str, retries: int = 1) -> T:
    """Call the model, parse + validate the JSON, and retry once with the error."""
    attempt_prompt, last_error = prompt, None
    for attempt in range(retries + 1):
        text = call_llm(cfg, system, attempt_prompt, temperature=0.7 if attempt == 0 else 0.2)
        try:
            return parser(extract_json(text))
        except (json.JSONDecodeError, ModelError) as exc:
            last_error = exc
            attempt_prompt = (prompt + f"\n\nYour previous reply was invalid ({exc}). "
                              "Return ONLY the corrected, complete JSON object.")
    raise LLMError(f"The AI reply could not be read as a valid plan ({last_error}). Please try again.")

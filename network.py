"""HTTP-запросы к API нейросетей."""

from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Any

import httpx
import os
from dotenv import load_dotenv

import db

load_dotenv()
load_dotenv(".env.local", override=False)

logger = logging.getLogger(__name__)
_logging_configured = False

OPENAI_COMPATIBLE_PROVIDERS = {"openai", "deepseek", "groq", "openrouter"}


def setup_request_logging() -> None:
    global _logging_configured
    if _logging_configured:
        return
    log_requests = (db.get_setting("log_requests") or "0") == "1"
    if not log_requests:
        _logging_configured = True
        return

    log_file = db.get_setting("log_file") or "chatlist.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    _logging_configured = True


def get_api_key(env_var_name: str) -> str | None:
    value = os.getenv(env_var_name)
    if value:
        return value.strip()
    return None


def _resolve_provider(model: dict[str, Any]) -> str:
    provider = model.get("provider")
    if provider:
        return str(provider).lower()
    return "openai"


def _extract_openai_content(data: dict[str, Any]) -> str | None:
    choices = data.get("choices")
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None:
        return None
    return str(content).strip() or None


def _build_headers(provider: str, api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["Referer"] = "https://chatlist.local"
        headers["HTTP-Referer"] = "https://chatlist.local"
        headers["X-Title"] = "ChatList"
    return headers


def _send_openai_compatible(
    model: dict[str, Any],
    prompt_text: str,
    api_key: str,
    timeout: float,
    provider: str,
) -> str:
    payload = {
        "model": model["api_id"],
        "messages": [{"role": "user", "content": prompt_text}],
    }
    headers = _build_headers(provider, api_key)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(model["api_url"], json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    content = _extract_openai_content(data)
    if not content:
        raise ValueError("API вернул пустой ответ")
    return content


def send_prompt(model: dict[str, Any], prompt_text: str) -> str:
    """Отправляет промт в модель и возвращает текст ответа или сообщение об ошибке."""
    setup_request_logging()

    env_var = model.get("api_key_env", "")
    api_key = get_api_key(env_var)
    if not api_key:
        return f"Ошибка: не задан API-ключ (переменная {env_var} в .env)"

    timeout_raw = db.get_setting("request_timeout") or "60"
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 60.0

    provider = _resolve_provider(model)
    log_requests = (db.get_setting("log_requests") or "0") == "1"
    started = time.perf_counter()

    try:
        result = _send_openai_compatible(
            model, prompt_text, api_key, timeout, provider
        )

        if log_requests:
            elapsed = time.perf_counter() - started
            logger.info(
                "Запрос к %s (%s): OK за %.2f с",
                model.get("name"),
                model.get("api_url"),
                elapsed,
            )
        return result

    except httpx.TimeoutException:
        message = f"Ошибка: превышен таймаут ({int(timeout)} с)"
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        try:
            detail = exc.response.json()
            error_text = detail.get("error", {}).get("message", str(detail))
        except Exception:
            error_text = exc.response.text[:200]
        message = f"Ошибка HTTP {status}: {error_text}"
    except httpx.RequestError as exc:
        message = f"Ошибка сети: {exc}"
    except (ValueError, KeyError) as exc:
        message = f"Ошибка разбора ответа: {exc}"
    except Exception as exc:
        message = f"Ошибка: {exc}"

    if log_requests:
        elapsed = time.perf_counter() - started
        logger.warning(
            "Запрос к %s (%s): %s за %.2f с",
            model.get("name"),
            model.get("api_url"),
            message,
            elapsed,
        )
    return message

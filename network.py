"""HTTP-запросы к API нейросетей."""

from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Any

import httpx
import os

import db
from env_loader import load_app_env
from version import __version__

load_app_env()

logger = logging.getLogger(__name__)
_logging_configured = False

OPENAI_COMPATIBLE_PROVIDERS = {"openai", "deepseek", "groq", "openrouter", "huggingface"}


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
    logger.info("ChatList %s — логирование запросов включено", __version__)


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
        referer = db.get_setting("openrouter_referer") or "http://localhost:3000"
        title = db.get_setting("openrouter_app_title") or "ChatList"
        headers["HTTP-Referer"] = referer
        headers["X-OpenRouter-Title"] = title
        headers["X-Title"] = title
    return headers


def _create_http_client(timeout: float) -> httpx.Client:
    """Создаёт HTTP-клиент. По умолчанию игнорирует системный SOCKS-прокси."""
    use_proxy = (db.get_setting("use_system_proxy") or "0") == "1"
    if use_proxy:
        try:
            return httpx.Client(timeout=timeout, trust_env=True)
        except ValueError:
            pass
    return httpx.Client(timeout=timeout, trust_env=False)


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
    with _create_http_client(timeout) as client:
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
            raw_error = detail.get("error")
            if isinstance(raw_error, str):
                error_text = raw_error
            elif isinstance(raw_error, dict):
                error_text = raw_error.get("message", str(raw_error))
            else:
                error_text = str(detail)
        except Exception:
            error_text = exc.response.text[:200]
        message = f"Ошибка HTTP {status}: {error_text}"
        if status == 403 and provider == "openrouter":
            message += (
                ". OpenRouter заблокировал запрос. "
                "Создайте новый ключ на openrouter.ai/keys или используйте Hugging Face."
            )
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

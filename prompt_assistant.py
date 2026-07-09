"""AI-ассистент для улучшения промтов."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import db
import network
from models import Model

MAX_PROMPT_LENGTH = 8000

IMPROVE_PROMPT_TEMPLATE = """Ты — эксперт по prompt engineering. Пользователь прислал промт:

---
{user_prompt}
---

Улучши промт: сделай его яснее, конкретнее и структурированнее. Сохрани исходный смысл и язык промта.

Верни ТОЛЬКО валидный JSON без markdown и пояснений со следующей структурой:
{{
  "improved": "улучшенная версия промта",
  "alternatives": ["вариант переформулировки 1", "вариант 2", "вариант 3"],
  "adaptations": {{
    "code": "адаптация для задач программирования",
    "analysis": "адаптация для аналитики и анализа данных",
    "creative": "адаптация для креативных задач"
  }}
}}

Поле alternatives должно содержать 2–3 строки. Все тексты в JSON — на том же языке, что и исходный промт."""


@dataclass
class PromptImprovementResult:
    original: str
    improved: str
    alternatives: list[str] = field(default_factory=list)
    adaptations: dict[str, str] = field(default_factory=dict)


def build_improvement_prompt(user_prompt: str) -> str:
    return IMPROVE_PROMPT_TEMPLATE.format(user_prompt=user_prompt.strip())


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return stripped


def parse_improvement_response(raw: str, original: str) -> PromptImprovementResult:
    cleaned = _strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return PromptImprovementResult(original=original, improved=raw.strip())

    improved = str(data.get("improved") or "").strip()
    if not improved:
        improved = raw.strip()

    alternatives_raw = data.get("alternatives") or []
    alternatives = [str(item).strip() for item in alternatives_raw if str(item).strip()]

    adaptations_raw = data.get("adaptations") or {}
    adaptations: dict[str, str] = {}
    if isinstance(adaptations_raw, dict):
        for key in ("code", "analysis", "creative"):
            value = adaptations_raw.get(key)
            if value and str(value).strip():
                adaptations[key] = str(value).strip()

    return PromptImprovementResult(
        original=original,
        improved=improved,
        alternatives=alternatives,
        adaptations=adaptations,
    )


def get_default_assistant_model() -> Model | None:
    """Первая активная модель с API-ключом; приоритет — OpenRouter."""
    active_rows = db.list_models(active_only=True)
    openrouter_rows = [row for row in active_rows if (row.get("provider") or "").lower() == "openrouter"]
    candidates = openrouter_rows + [row for row in active_rows if row not in openrouter_rows]
    for row in candidates:
        if network.get_api_key(row["api_key_env"]):
            return Model.from_row(row)
    return None


def get_assistant_model() -> Model | None:
    raw_id = db.get_setting("improve_prompt_model_id") or ""
    if raw_id.strip().isdigit():
        row = db.get_model(int(raw_id))
        if row and row.get("is_active"):
            return Model.from_row(row)
    return get_default_assistant_model()


def validate_prompt_for_improvement(user_prompt: str) -> str | None:
    text = user_prompt.strip()
    if not text:
        return "Введите текст промта."
    if len(text) > MAX_PROMPT_LENGTH:
        return f"Промт слишком длинный (максимум {MAX_PROMPT_LENGTH} символов)."
    return None


def improve_prompt(user_prompt: str, model: Model | None = None) -> PromptImprovementResult:
    error = validate_prompt_for_improvement(user_prompt)
    if error:
        raise ValueError(error)

    assistant_model = model or get_assistant_model()
    if assistant_model is None:
        raise ValueError(
            "Не выбрана модель для улучшения промтов. "
            "Укажите её на вкладке «Настройки»."
        )

    meta_prompt = build_improvement_prompt(user_prompt)
    raw_response = network.send_prompt(assistant_model.to_dict(), meta_prompt)
    if raw_response.startswith("Ошибка"):
        raise RuntimeError(raw_response)

    return parse_improvement_response(raw_response, user_prompt.strip())

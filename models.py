"""Бизнес-логика ChatList: промты, модели, временные результаты."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import db
import network


@dataclass
class Prompt:
    id: int | None
    text: str
    tags: str = ""
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> Prompt:
        return cls(
            id=row["id"],
            text=row["prompt"],
            tags=row.get("tags") or "",
            created_at=row.get("created_at"),
        )

    def save(self) -> int:
        prompt_id = db.add_prompt(self.text, self.tags or None)
        self.id = prompt_id
        return prompt_id


@dataclass
class Model:
    id: int
    name: str
    api_url: str
    api_id: str
    api_key_env: str
    is_active: bool
    provider: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> Model:
        return cls(
            id=row["id"],
            name=row["name"],
            api_url=row["api_url"],
            api_id=row["api_id"],
            api_key_env=row["api_key_env"],
            is_active=bool(row["is_active"]),
            provider=row.get("provider"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "api_url": self.api_url,
            "api_id": self.api_id,
            "api_key_env": self.api_key_env,
            "is_active": self.is_active,
            "provider": self.provider,
        }


@dataclass
class TempResult:
    model_id: int
    model_name: str
    response_text: str
    selected: bool = False


_temp_results: list[TempResult] = []
_current_prompt_id: int | None = None


def load_saved_prompts() -> list[Prompt]:
    return [Prompt.from_row(row) for row in db.list_prompts()]


def load_active_models() -> list[Model]:
    return [Model.from_row(row) for row in db.list_models(active_only=True)]


def get_temp_results() -> list[TempResult]:
    return list(_temp_results)


def get_current_prompt_id() -> int | None:
    return _current_prompt_id


def set_current_prompt_id(prompt_id: int | None) -> None:
    global _current_prompt_id
    _current_prompt_id = prompt_id


def clear_temp_results() -> None:
    global _temp_results
    _temp_results = []


def _fetch_one(model: Model, prompt_text: str) -> TempResult:
    response = network.send_prompt(model.to_dict(), prompt_text)
    return TempResult(
        model_id=model.id,
        model_name=model.name,
        response_text=response,
    )


def run_prompt(prompt_text: str, active_models: list[Model] | None = None) -> list[TempResult]:
    """Отправляет промт во все активные модели (параллельно)."""
    models = active_models if active_models is not None else load_active_models()
    if not models:
        return []

    results: list[TempResult] = []
    with ThreadPoolExecutor(max_workers=min(len(models), 8)) as executor:
        futures = {
            executor.submit(_fetch_one, model, prompt_text): model
            for model in models
        }
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item.model_name.lower())
    global _temp_results
    _temp_results = results
    return results


def save_selected_results(
    prompt_id: int,
    temp_results: list[TempResult] | None = None,
) -> int:
    """Сохраняет отмеченные строки в таблицу results."""
    items = temp_results if temp_results is not None else _temp_results
    rows = [
        {
            "prompt_id": prompt_id,
            "model_id": item.model_id,
            "response_text": item.response_text,
        }
        for item in items
        if item.selected
    ]
    count = db.insert_results(rows)
    clear_temp_results()
    return count

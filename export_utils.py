"""Экспорт результатов в Markdown и JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import models as app_models


def export_to_markdown(
    results: list[app_models.TempResult],
    prompt_text: str = "",
) -> str:
    lines = ["# ChatList — результаты", ""]
    if prompt_text:
        lines.extend(["## Промт", "", prompt_text, ""])
    lines.append("## Ответы")
    lines.append("")
    for item in results:
        lines.append(f"### {item.model_name}")
        lines.append("")
        lines.append(item.response_text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_to_json(
    results: list[app_models.TempResult],
    prompt_text: str = "",
) -> str:
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt_text,
        "results": [
            {
                "model_id": item.model_id,
                "model_name": item.model_name,
                "response_text": item.response_text,
                "selected": item.selected,
            }
            for item in results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

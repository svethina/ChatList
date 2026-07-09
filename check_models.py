"""Проверка работоспособности моделей и удаление неработающих."""

from __future__ import annotations

import sys

import db
import network

TEST_PROMPT = "Ответь одним словом: OK"


def check_model(model: dict) -> tuple[bool, str]:
    api_key = network.get_api_key(model["api_key_env"])
    if not api_key:
        return False, f"нет API-ключа ({model['api_key_env']})"

    response = network.send_prompt(model, TEST_PROMPT)
    if response.startswith("Ошибка"):
        return False, response
    if not response.strip():
        return False, "пустой ответ"
    return True, response.strip()[:120]


def main() -> int:
    models = db.list_models(active_only=False)
    working: list[dict] = []
    broken: list[tuple[dict, str]] = []

    print(f"Проверка {len(models)} моделей...\n")
    for model in models:
        ok, detail = check_model(model)
        status = "OK" if ok else "FAIL"
        print(f"[{status}] id={model['id']} {model['name']}")
        print(f"       {detail}\n")
        if ok:
            working.append(model)
        else:
            broken.append((model, detail))

    if not broken:
        print("Все модели работают. Удалять нечего.")
        return 0

    print("Удаление неработающих моделей:")
    removed = 0
    deactivated = 0
    for model, reason in broken:
        try:
            db.delete_model(model["id"])
            print(f"- удалена id={model['id']} {model['name']} ({reason})")
            removed += 1
        except Exception:
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE models SET is_active = 0 WHERE id = ?",
                    (model["id"],),
                )
            print(f"- деактивирована id={model['id']} {model['name']} ({reason})")
            deactivated += 1

    print(
        f"\nИтог: работает {len(working)}, удалено {removed}, "
        f"деактивировано {deactivated}, всего было {len(models)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

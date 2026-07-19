"""Загрузка переменных окружения (.env) для ChatList."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv


def _env_candidates() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        paths.append(path)

    if getattr(sys, "frozen", False):
        add(Path(sys.executable).resolve().parent)
    else:
        add(Path(__file__).resolve().parent)

    add(Path.cwd())
    return paths


def load_app_env() -> None:
    """Ищет .env / .env.local рядом с exe, исходниками и в текущей папке."""
    for directory in _env_candidates():
        env_file = directory / ".env"
        local_file = directory / ".env.local"
        if env_file.is_file():
            load_dotenv(env_file, override=False)
        if local_file.is_file():
            load_dotenv(local_file, override=False)

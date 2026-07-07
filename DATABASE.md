# Схема базы данных ChatList

База данных: **SQLite** (один файл, например `chatlist.db`).

Доступ к БД инкапсулирован в модуле `db.py`. API-ключи в БД **не хранятся** — только имя переменной окружения.

---

## Диаграмма связей

```
prompts (1) ──────< results >────── (N) models
                      │
                      └── prompt_id, model_id — внешние ключи

settings — отдельная таблица «ключ → значение»
```

---

## Таблица `prompts`

Сохранённые запросы пользователя.

| Поле         | Тип          | Ограничения        | Описание                          |
|--------------|--------------|--------------------|-----------------------------------|
| `id`         | INTEGER      | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор   |
| `created_at` | TEXT         | NOT NULL           | Дата и время (ISO 8601)           |
| `prompt`     | TEXT         | NOT NULL           | Текст промта                      |
| `tags`       | TEXT         | NULL               | Теги через запятую или JSON-массив |

**Индексы:** `idx_prompts_created_at` на `created_at` (сортировка по дате).

---

## Таблица `models`

Зарегистрированные нейросети и параметры подключения.

| Поле           | Тип     | Ограничения        | Описание                                      |
|----------------|---------|--------------------|-----------------------------------------------|
| `id`           | INTEGER | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор               |
| `name`         | TEXT    | NOT NULL UNIQUE    | Отображаемое имя (GPT-4, DeepSeek и т.д.)     |
| `api_url`      | TEXT    | NOT NULL           | URL endpoint API                              |
| `api_id`       | TEXT    | NOT NULL           | Идентификатор модели в API (например `gpt-4o`) |
| `api_key_env`  | TEXT    | NOT NULL           | Имя переменной в `.env` (например `OPENAI_API_KEY`) |
| `is_active`    | INTEGER | NOT NULL DEFAULT 1 | 1 — участвует в рассылке, 0 — отключена     |
| `provider`     | TEXT    | NULL               | Тип провайдера: `openai`, `deepseek`, `groq` (для адаптера) |

**Индексы:** `idx_models_is_active` на `is_active`.

При отправке промта выбираются записи: `WHERE is_active = 1`.

---

## Таблица `results`

Постоянно сохранённые ответы (только строки, отмеченные пользователем).

| Поле            | Тип     | Ограничения        | Описание                              |
|-----------------|---------|--------------------|---------------------------------------|
| `id`            | INTEGER | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор       |
| `prompt_id`     | INTEGER | NOT NULL, FK → prompts(id) | Связь с промтом              |
| `model_id`      | INTEGER | NOT NULL, FK → models(id)  | Связь с моделью              |
| `response_text` | TEXT    | NOT NULL           | Текст ответа нейросети                |
| `created_at`    | TEXT    | NOT NULL           | Дата и время сохранения (ISO 8601)    |

**Индексы:**
- `idx_results_prompt_id` на `prompt_id`
- `idx_results_model_id` на `model_id`
- `idx_results_created_at` на `created_at`

**Внешние ключи:** при удалении промта или модели — `ON DELETE RESTRICT` (запрет удаления, если есть связанные результаты) или каскад по решению при реализации.

---

## Таблица `settings`

Настройки приложения в формате «ключ — значение».

| Поле    | Тип  | Ограничения   | Описание           |
|---------|------|---------------|--------------------|
| `key`   | TEXT | PRIMARY KEY   | Имя настройки      |
| `value` | TEXT | NOT NULL      | Значение (строка)  |

**Примеры записей:**

| key              | value   | Назначение                    |
|------------------|---------|-------------------------------|
| `request_timeout`| `60`    | Таймаут HTTP-запроса (сек)    |
| `db_path`        | `chatlist.db` | Путь к файлу БД         |
| `log_requests`   | `1`     | Включить логирование запросов |

---

## Временная таблица результатов (не в SQLite)

Используется только в памяти приложения до нажатия «Сохранить».

| Поле            | Тип   | Описание                    |
|-----------------|-------|-----------------------------|
| `model_name`    | str   | Имя модели для отображения  |
| `model_id`      | int   | ID из таблицы `models`      |
| `response_text` | str   | Ответ API                   |
| `selected`      | bool  | Отмечен ли чекбоксом        |

При новом промте список очищается. При сохранении строки с `selected = True` переносятся в таблицу `results`.

---

## SQL инициализации

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prompts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,
    prompt      TEXT    NOT NULL,
    tags        TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts (created_at);

CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    api_url     TEXT    NOT NULL,
    api_id      TEXT    NOT NULL,
    api_key_env TEXT    NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1,
    provider    TEXT
);

CREATE INDEX IF NOT EXISTS idx_models_is_active ON models (is_active);

CREATE TABLE IF NOT EXISTS results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id     INTEGER NOT NULL,
    model_id      INTEGER NOT NULL,
    response_text TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE RESTRICT,
    FOREIGN KEY (model_id)  REFERENCES models (id)  ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_results_prompt_id  ON results (prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id   ON results (model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results (created_at);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## Переменные окружения (`.env`, вне БД)

Ключи API хранятся только в файле `.env`, не в SQLite:

```env
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...
GROQ_API_KEY=...
```

В таблице `models` поле `api_key_env` указывает, какую переменную читать для конкретной модели.

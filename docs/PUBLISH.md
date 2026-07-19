# Публикация ChatList: GitHub Releases и GitHub Pages

Пошаговая инструкция для Windows (PowerShell). Репозиторий: [svethina/ChatList](https://github.com/svethina/ChatList).

---

## Что куда публикуется

| Канал | Назначение | Где лежит |
|-------|------------|-----------|
| **GitHub Releases** | Установщик `.exe` и заметки к версии | Вкладка Releases репозитория |
| **GitHub Pages** | Лендинг сайта | Папка `docs/` → сайт `https://svethina.github.io/ChatList/` |

Версия приложения берётся **только** из `version.py` (`__version__`).

---

## Подготовка (один раз)

### 1. Инструменты

- Git + [GitHub CLI](https://cli.github.com/) (`gh`)
- Python 3.11+ и зависимости проекта
- [PyInstaller](https://pyinstaller.org/) (обычно через `pip install pyinstaller`)
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) — для `ChatList-Setup-*.exe`

Проверка входа в GitHub:

```powershell
gh auth status
```

Если не авторизованы:

```powershell
gh auth login
```

### 2. Включить GitHub Pages

1. Откройте репозиторий на GitHub → **Settings** → **Pages**.
2. **Source**: Deploy from a branch.
3. **Branch**: `main` / папка `/docs`.
4. Save.

Сайт появится через 1–2 минуты:

`https://svethina.github.io/ChatList/`

Опционально: **Settings** → **General** → **Website** → укажите этот URL.

### 3. Файлы лендинга (уже в репозитории)

| Файл | Роль |
|------|------|
| `docs/index.html` | Страница |
| `docs/styles.css` | Стили |
| `docs/release.js` | Кнопка «Скачать» тянет latest release |
| `docs/assets/` | Иконка |
| `docs/.nojekyll` | Отключает Jekyll на Pages |

---

## Каждый новый релиз

### Шаг 1. Поднять версию

Отредактируйте `version.py`:

```python
__version__ = "1.0.1"
```

Правило тегов: `v` + версия → `v1.0.1`.

### Шаг 2. Собрать установщик

```powershell
cd C:\Work\ChatList
.\build.ps1
```

Ожидаемые артефакты:

- `.\dist\ChatList.exe`
- `.\installer\ChatList-Setup-<версия>.exe`

Папки `dist/` и `installer/` в git не коммитятся.

### Шаг 3. Закоммитить исходники (без exe)

```powershell
git add version.py docs\ .github\RELEASE_TEMPLATE.md scripts\publish-release.ps1
git status
git commit -m "Релиз v1.0.1"
git push origin main
```

Подставьте актуальную версию и список файлов, которые реально менялись.

### Шаг 4. Создать GitHub Release

**Вариант A — скрипт (рекомендуется):**

```powershell
.\scripts\publish-release.ps1
```

Скрипт:

1. Читает версию из `version.py`
2. Проверяет наличие установщика
3. Создаёт релиз `vX.Y.Z` и прикрепляет `ChatList-Setup-X.Y.Z.exe`

**Вариант B — вручную через `gh`:**

```powershell
$version = python -c "from version import __version__; print(__version__)"
$tag = "v$version"
$installer = ".\installer\ChatList-Setup-$version.exe"

gh release create $tag $installer `
  --title "ChatList $version" `
  --notes-file .github\RELEASE_TEMPLATE.md
```

Перед созданием отредактируйте `.github\RELEASE_TEMPLATE.md` под этот релиз (раздел «Что нового»).

**Вариант C — через сайт GitHub:**

1. Releases → **Draft a new release**
2. Tag: `v1.0.1` (создать на `main`)
3. Title: `ChatList 1.0.1`
4. Вставьте текст из шаблона
5. Attach binaries: `ChatList-Setup-1.0.1.exe` (и при желании `ChatList.exe`)
6. **Publish release**

### Шаг 5. Проверить

1. Releases: файл скачивается, тег верный.
2. Pages: на лендинге кнопка ведёт на установщик / latest.
3. Локально: установка с чистой машины (или VM).

---

## Шаблон имени файлов

| Артефакт | Имя |
|----------|-----|
| Установщик | `ChatList-Setup-<версия>.exe` |
| Portable (опционально) | `ChatList.exe` |
| Git-тег | `v<версия>` |

Лендинг ищет asset по шаблону `ChatList-Setup-*.exe`.

---

## Чеклист перед публикацией

- [ ] `__version__` в `version.py` обновлён
- [ ] `.\build.ps1` завершился без ошибок
- [ ] Установщик запускается, «О программе» показывает ту же версию
- [ ] Заметки релиза заполнены
- [ ] В Release прикреплён exe (не ссылка на локальный путь)
- [ ] Pages открывается, кнопка «Скачать» работает
- [ ] В релиз не попали `.env`, ключи API, `chatlist.db`

---

## Частые проблемы

| Симптом | Что сделать |
|---------|-------------|
| Pages 404 | Settings → Pages: branch `main`, folder `/docs` |
| Кнопка «Скачать» без прямой ссылки | Нет release или asset не называется `ChatList-Setup-*.exe` |
| `gh: HTTP 404` при релизе | Нет прав `repo` / неверный remote |
| Inno Setup не найден | Установите Inno Setup 6 или соберите только `dist\ChatList.exe` |
| Cursor: `Bad status code: 500` | Push через терминал: `git push origin main` |

---

## Связанные файлы

- `.github/RELEASE_TEMPLATE.md` — шаблон заметок к релизу
- `scripts/publish-release.ps1` — создание релиза из PowerShell
- `build.ps1` — сборка exe + установщика
- `docs/index.html` — лендинг

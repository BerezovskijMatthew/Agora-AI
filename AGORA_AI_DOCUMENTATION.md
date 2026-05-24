# Agora-AI — Полная документация

> **Версия:** 2.0 · **Python:** 3.12+ · **Flet:** 0.85+ · **Groq API** · **SQLite**

---

## Содержание

1. [Обзор проекта](#1-обзор-проекта)
2. [Установка и запуск](#2-установка-и-запуск)
   - [2.1. Развёртывание в Docker](#21-развёртывание-в-docker)
3. [Архитектура приложения](#3-архитектура-приложения)
4. [Конфигурация](#4-конфигурация)
5. [База данных](#5-база-данных)
6. [Аутентификация и безопасность](#6-аутентификация-и-безопасность)
7. [ИИ-агент: интеграция с Groq](#7-ии-агент-интеграция-с-groq) — выбор платформы, сравнение, разбор кода
8. [Система промтов](#8-система-промтов)
9. [Состояние приложения (AppState)](#9-состояние-приложения-appstate)
10. [Темизация и интернационализация](#10-темизация-и-интернационализация)
11. [UI-компоненты](#11-ui-компоненты)
12. [Экраны приложения](#12-экраны-приложения)
13. [Поток данных: отправка сообщения](#13-поток-данных-отправка-сообщения)
14. [Работа с файлами](#14-работа-с-файлами)
15. [Навигация и перерисовка UI](#15-навигация-и-перерисовка-ui)
16. [Ограничения и возможные улучшения](#16-ограничения-и-возможные-улучшения)
17. [Справочник функций](#17-справочник-функций)

---

## 1. Обзор проекта

**Agora-AI** — это кроссплатформенное десктопное приложение-чат с ИИ-ассистентом на Python. Интерфейс построен на фреймворке Flet (Flutter под капотом), общение с ИИ осуществляется через Groq API (модель LLaMA 3.3 70B), данные хранятся в локальной базе SQLite.

### Ключевые возможности

| Возможность | Описание |
|---|---|
| Многопользовательская авторизация | Регистрация, вход, восстановление пароля |
| Безопасное хранение паролей | PBKDF2-SHA256, 100 000 итераций, случайная соль |
| История чатов | SQLite, создание/открытие/удаление диалогов |
| ИИ-ассистент | LLaMA 3.3 70B через Groq API с сохранением контекста |
| Посимвольный стриминг | Анимация ответа ИИ (~250 символов/сек) |
| Прикрепление файлов | 20+ форматов, до 8 000 символов |
| Двуязычность | Русский и английский интерфейс |
| Тёмная / светлая тема | Переключается в настройках |
| Мобильный форм-фактор | Окно 420×820 px |

### Технологический стек

| Библиотека | Версия | Назначение |
|---|---|---|
| `flet` | 0.85+ | UI-фреймворк на базе Flutter |
| `groq` | актуальная | Клиент Groq API |
| `sqlite3` | stdlib | Локальная реляционная БД |
| `hashlib` | stdlib | PBKDF2-SHA256 хэширование |
| `secrets` | stdlib | Криптографически стойкие соли |
| `asyncio` | stdlib | Асинхронное выполнение, стриминг UI |
| `math` | stdlib | Константа `pi` для поворота логотипа |
| `datetime` | stdlib | Форматирование дат в истории |

---

## 2. Установка и запуск

### Требования

- Python 3.12 или новее
- pip (менеджер пакетов Python)
- Интернет-соединение (для Groq API)

### Пошаговая установка

```bash
# 1. Клонировать или скачать проект
git clone <url-репозитория>
cd agora-ai

# 2. (Опционально) создать виртуальное окружение
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# 3. Установить зависимости
pip install flet groq

# 4. Запустить приложение
python main.py
```

При первом запуске в директории скрипта автоматически создаётся файл `agora_ai.db` и учётная запись `admin` / `admin`.

### Получение API-ключа Groq

1. Зарегистрироваться на [console.groq.com](https://console.groq.com)
2. Перейти в раздел **API Keys** → **Create API Key**
3. Скопировать ключ вида `gsk_...` в переменную `GROQ_API_KEY` в начале `main.py`

> ⚠️ **Безопасность:** в продакшн-окружении не храните ключ в коде. Используйте переменную окружения:
> ```python
> GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
> ```
> Затем запуск: `GROQ_API_KEY=gsk_... python main.py`

### Запуск как веб-приложение (экспериментально)

Flet поддерживает запуск в браузере:

```bash
flet run main.py --web --port 8080
```

> ⚠️ В веб-режиме файловый пикер работает через загрузку байтов (`pf.bytes`), а не через файловую систему. Этот режим в коде поддержан через fallback-ветку.

---

## 2.1. Развёртывание в Docker

Приложение запускается в Docker в **веб-режиме** Flet: без графического дисплея, как обычный HTTP-сервер. Пользователь открывает браузер и работает с интерфейсом через него.

### Структура файлов для Docker

```
agora-ai/
├── main.py                 ← исходный код приложения
├── Dockerfile              ← инструкция сборки образа
├── docker-compose.yml      ← удобный запуск одной командой
├── requirements.txt        ← зависимости Python
├── .env                    ← секреты (НЕ коммитить в Git)
├── .env.example            ← шаблон без реального ключа
└── .gitignore
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

LABEL description="Agora-AI — чат с ИИ-ассистентом на Flet + Groq"
LABEL version="2.0"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

VOLUME ["/app/data"]
ENV DB_PATH=/app/data/agora_ai.db

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080 || exit 1

CMD ["python", "-m", "flet", "run", "main.py", \
     "--web", "--host", "0.0.0.0", "--port", "8080"]
```

### docker-compose.yml

```yaml
version: "3.9"
services:
  agora-ai:
    build: .
    container_name: agora-ai
    ports:
      - "8080:8080"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
    volumes:
      - agora_data:/app/data
    restart: unless-stopped

volumes:
  agora_data:
```

### Запуск через Docker

**Шаг 1.** Создать файл `.env` рядом с `docker-compose.yml`:
```
GROQ_API_KEY=gsk_ваш_ключ_здесь
```

**Шаг 2.** Собрать и запустить:
```bash
docker compose up --build
```

**Шаг 3.** Открыть в браузере: [http://localhost:8080](http://localhost:8080)

### Полезные команды

```bash
# Запуск в фоне
docker compose up -d --build

# Просмотр логов
docker compose logs -f

# Остановка
docker compose down

# Пересборка после изменений в main.py
docker compose up --build
```

### Персистентность данных

База данных `agora_ai.db` хранится в Docker-томе `agora_data`. Данные сохраняются между перезапусками и пересборками контейнера. При `docker compose down` том **не удаляется**. Для полного сброса:

```bash
docker compose down -v   # удалить контейнер И том с данными
```

### .gitignore (рекомендуемый)

```
.env
*.db
__pycache__/
*.pyc
.venv/
```

---

## 3. Архитектура приложения

### Структура модулей (один файл)

```
main.py  (≈1 520 строк)
│
├── ── Конфигурация ──────────────────────────────── строки 13–18
│       GROQ_API_KEY, GROQ_MODEL, DB_PATH
│       groq_client = Groq(api_key=...)
│
├── ══ БАЗА ДАННЫХ ═══════════════════════════════ строки 22–165
│       _db()                  фабрика соединений SQLite
│       db_init()              создание схемы + миграция + admin
│       _hash_pwd()            PBKDF2-SHA256
│       db_login()             аутентификация
│       db_register()          регистрация с валидацией
│       db_get_security_question()
│       db_verify_security_answer()
│       db_reset_password()
│       db_new_chat()
│       db_save_msg()
│       db_set_title()
│       db_user_chats()
│       db_chat_msgs()
│       db_delete_chat()
│
├── ══ ПЕРЕВОДЫ (LANG) ═══════════════════════════ строки 170–317
│       LANG["ru"] — строки на русском + system-prompt RU
│       LANG["en"] — строки на английском + system-prompt EN
│
├── ══ ТЕМЫ ══════════════════════════════════════ строки 322–367
│       DARK  — тёмная палитра (18 цветовых ключей)
│       LIGHT — светлая палитра (18 цветовых ключей)
│
├── ══ СОСТОЯНИЕ ═════════════════════════════════ строки 376–393
│       class AppState         синглтон состояния приложения
│       state = AppState()
│
├── ══ ИИ-АГЕНТ ══════════════════════════════════ строки 399–417
│       groq_ask(user_text)    запрос к Groq, сохранение в БД
│
├── ══ UI-КОМПОНЕНТЫ ═════════════════════════════ строки 423–492
│       _user_av()             аватар пользователя
│       _ai_av()               аватар ИИ (градиент)
│       class ChatBubble       пузырь сообщения
│       _file_bubble()         пузырь прикреплённого файла
│
└── ══ MAIN ══════════════════════════════════════ строки 498–1519
        async def main(page)
        │
        ├── Toast-уведомления
        ├── AlertDialog (подтверждение удаления)
        ├── FilePicker
        ├── _apply_theme()
        ├── show_toast()
        ├── _navbar()
        ├── _bottom_nav()
        ├── _rebuild()         центральная функция перерисовки
        ├── _field_wrap()      обёртка полей ввода
        ├── _text_field()      стилизованный TextField
        ├── _logo()            SVG-подобный логотип
        ├── _grad_btn()        кнопка с градиентом
        │
        ├── _login_view()
        ├── _register_view()
        ├── _forgot_view()     3-шаговый мастер
        ├── _chat_view()
        ├── _history_view()
        ├── _settings_view()
        └── _do_logout()
```

### Схема взаимодействия слоёв

```
┌─────────────────────────────────────────────┐
│               Пользователь (UI)             │
│  Login / Register / Chat / History / Settings│
└────────────────────┬────────────────────────┘
                     │ события (on_click, on_submit)
                     ▼
┌─────────────────────────────────────────────┐
│            Логика (main.py)                 │
│  AppState · _rebuild() · _send() · _forgot  │
└──────────┬──────────────────────┬───────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────┐
│   SQLite (БД)    │   │   Groq API (LLM)      │
│  agora_ai.db     │   │  llama-3.3-70b        │
│  users / chats   │   │  temperature=0.7      │
│  messages        │   │  max_tokens=1024      │
└──────────────────┘   └──────────────────────┘
```

---

## 4. Конфигурация

Все параметры читаются из переменных окружения — это обеспечивает совместимость с Docker и исключает хранение секретов в коде.

```python
# Читается из переменных окружения; при локальном запуске — задать через .env
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
DB_PATH      = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "agora_ai.db"),
)

# При отсутствии ключа — понятная ошибка сразу при старте
if not GROQ_API_KEY:
    raise RuntimeError("Не задан GROQ_API_KEY. Установите: export GROQ_API_KEY=gsk_...")

groq_client = Groq(api_key=GROQ_API_KEY)
```

### Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ да | — | API-ключ Groq (получить на console.groq.com) |
| `GROQ_MODEL` | ❌ нет | `llama-3.3-70b-versatile` | Идентификатор модели |
| `DB_PATH` | ❌ нет | рядом с `main.py` | Путь к файлу SQLite; в Docker — `/app/data/agora_ai.db` |

### Параметры запросов к модели

| Параметр | Значение | Влияние |
|---|---|---|
| `model` | `llama-3.3-70b-versatile` | Языковая модель Meta LLaMA 3.3, 70B параметров |
| `temperature` | `0.7` | Умеренная вариативность ответов; 0 = детерминировано, 1 = максимально творчески |
| `max_tokens` | `1024` | Максимум ~750 слов на один ответ |

---

## 5. База данных

### Схема (ERD)

```
users
─────────────────────────────────
id               INTEGER  PK AI
username         TEXT     UNIQUE NOT NULL
password_hash    TEXT     NOT NULL        ← PBKDF2-SHA256 hex
salt             TEXT     NOT NULL        ← secrets.token_hex(16)
security_question TEXT
security_answer   TEXT                   ← хэш ответа (нижн. регистр)
created_at       TIMESTAMP DEFAULT now
        │
        │ 1 ──── N
        ▼
chats
─────────────────────────────────
id         INTEGER  PK AI
user_id    INTEGER  FK → users(id)
title      TEXT     DEFAULT 'Новый чат'  ← первые 40 символов первого сообщения
created_at TIMESTAMP DEFAULT now
        │
        │ 1 ──── N
        ▼
messages
─────────────────────────────────
id         INTEGER  PK AI
chat_id    INTEGER  FK → chats(id) ON DELETE CASCADE
role       TEXT     NOT NULL             ← "user" | "assistant"
content    TEXT     NOT NULL
created_at TIMESTAMP DEFAULT now
```

**Каскадное удаление:** при удалении чата все его сообщения удаляются автоматически (`ON DELETE CASCADE`).

**Внешние ключи:** включены явно через `PRAGMA foreign_keys = ON` в фабрике `_db()`.

### Миграция существующих баз

При каждом запуске `db_init()` пытается добавить новые колонки в уже существующие таблицы:

```python
for col, typ in [("security_question","TEXT"), ("security_answer","TEXT")]:
    try:
        conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
    except Exception:
        pass  # колонка уже существует — пропускаем
```

Это позволяет обновлять схему без потери данных пользователей, которые уже использовали предыдущую версию приложения.

### Справочник функций БД

| Функция | Сигнатура | Возвращает | Описание |
|---|---|---|---|
| `_db()` | `() → Connection` | соединение | Фабрика соединений с `row_factory=Row` и `foreign_keys=ON` |
| `db_init()` | `() → None` | — | Создаёт схему, мигрирует колонки, создаёт admin |
| `_hash_pwd()` | `(pwd, salt) → str` | hex-строка | PBKDF2-HMAC-SHA256, 100 000 итераций |
| `db_login()` | `(username, password) → int\|None` | user_id или None | Проверяет хэш, возвращает ID при успехе |
| `db_register()` | `(username, password, question, answer) → (bool, str)` | (успех, сообщение) | Валидирует длины, сохраняет, ловит конфликт уникальности |
| `db_get_security_question()` | `(username) → str\|None` | вопрос или None | None = пользователь не найден, "" = вопрос не задан |
| `db_verify_security_answer()` | `(username, answer) → bool` | True/False | Нормализует к нижнему регистру, сравнивает хэши |
| `db_reset_password()` | `(username, new_password) → None` | — | Генерирует новую соль, сохраняет новый хэш |
| `db_new_chat()` | `(user_id) → int` | chat_id | Создаёт пустой чат |
| `db_save_msg()` | `(chat_id, role, content) → None` | — | Вставляет одно сообщение |
| `db_set_title()` | `(chat_id, title) → None` | — | Обновляет заголовок, обрезает до 45 символов |
| `db_user_chats()` | `(user_id) → list[dict]` | список чатов | С COUNT сообщений, ORDER BY created_at DESC, LIMIT 100 |
| `db_chat_msgs()` | `(chat_id) → list[dict]` | сообщения | role + content, ORDER BY created_at ASC |
| `db_delete_chat()` | `(chat_id) → None` | — | Удаляет чат (CASCADE удаляет messages) |

---

## 6. Аутентификация и безопасность

### Хэширование паролей

```python
def _hash_pwd(pwd: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",       # хэш-функция
        pwd.encode(),   # пароль в байтах
        salt.encode(),  # соль в байтах
        100_000         # количество итераций
    ).hex()             # → строка из 64 hex-символов
```

| Параметр | Значение | Пояснение |
|---|---|---|
| Алгоритм | PBKDF2-HMAC-SHA256 | Стандарт NIST SP 800-132 |
| Итерации | 100 000 | Рекомендация OWASP 2024 для SHA-256 |
| Соль | `secrets.token_hex(16)` | 16 байт = 32 hex-символа, уникальна для каждого пользователя |
| Хранение | hex-строка в `password_hash` | 64 символа |

### Хэширование ответов на секретные вопросы

```python
ans_hash = _hash_pwd(
    security_answer.strip().lower(),  # нормализация: пробелы + регистр
    "sec_salt_fixed"                  # фиксированная соль
)
```

Фиксированная соль для ответов — намеренное упрощение, позволяющее сравнивать хэши без хранения соли отдельно. Это приемлемо, так как ответы на секретные вопросы — не основной способ аутентификации.

### Процесс входа

```
Пользователь вводит логин + пароль
         ↓
db_login(username, password)
         ↓
SELECT id, password_hash, salt FROM users WHERE username = ?
         ↓
_hash_pwd(password, row["salt"]) == row["password_hash"]?
    ДА → вернуть user_id
    НЕТ → вернуть None
```

### Восстановление пароля (3 шага)

```
ШАГ 1 — Ввод логина
    db_get_security_question(username)
    → None   : "Пользователь не найден"
    → ""     : "У аккаунта нет секретного вопроса"
    → вопрос : переход к шагу 2

ШАГ 2 — Ответ на секретный вопрос
    db_verify_security_answer(username, answer)
    → False  : "Неверный ответ"
    → True   : переход к шагу 3

ШАГ 3 — Новый пароль
    Валидация: len(p) >= 4, p == p2
    db_reset_password(username, new_password)
    → show_toast("Пароль успешно изменён!")
    → _rebuild("login")
```

### Учётная запись по умолчанию

| Логин | Пароль | Создаётся |
|---|---|---|
| `admin` | `admin` | Автоматически при первом запуске, если отсутствует в БД |

> ⚠️ Смените пароль admin сразу после первого запуска, если приложение используется в многопользовательской среде.

---

## 7. ИИ-агент: интеграция с Groq

### Почему Groq

При выборе платформы для ИИ-ассистента рассматривались три основных варианта: OpenAI API, Anthropic API (Claude) и Groq. Groq был выбран по совокупности факторов.

**Скорость генерации.** Groq использует собственные чипы LPU (Language Processing Unit), спроектированные специально для инференса языковых моделей. В отличие от GPU-кластеров OpenAI или Anthropic, LPU обеспечивает стабильно низкую задержку первого токена и высокую скорость генерации — в среднем 400–700 токенов в секунду против 40–80 у конкурентов. Для чат-приложения с посимвольной анимацией ответа это критично: ответ приходит быстро и анимируется в реальном времени, не заставляя пользователя ждать.

**Бесплатный тир с высокими лимитами.** На момент разработки Groq предлагает бесплатный доступ к мощным моделям с лимитами, достаточными для полноценной разработки и тестирования: 14 400 запросов в день и 500 000 токенов в минуту для llama-3.3-70b-versatile. OpenAI и Anthropic предоставляют только платный доступ с небольшим стартовым кредитом.

**Модель LLaMA 3.3 70B.** Groq предоставляет доступ к открытой модели Meta LLaMA 3.3 с 70 миллиардами параметров. По качеству ответов на практических задачах (код, объяснения, анализ текста) она сопоставима с GPT-4o mini и Claude Haiku, но при этом работает значительно быстрее благодаря аппаратной оптимизации Groq.

**Совместимость с OpenAI SDK.** Groq API полностью совместим с форматом запросов OpenAI (`chat.completions.create`, роли `user`/`assistant`/`system`). Это означает, что при необходимости можно переключиться на любой другой провайдер, изменив только URL и ключ — весь остальной код остаётся без изменений.

**Простая интеграция.** Официальный Python-пакет `groq` устанавливается одной командой, не требует настройки прокси или дополнительных зависимостей и работает одинаково на Windows, macOS и Linux.

### Сравнение альтернатив

| Критерий | Groq + LLaMA 3.3 70B | OpenAI GPT-4o mini | Anthropic Claude Haiku |
|---|---|---|---|
| Скорость генерации | ~500 токенов/сек | ~80 токенов/сек | ~100 токенов/сек |
| Бесплатный тир | ✅ щедрый | ❌ только кредит $5 | ❌ только кредит $5 |
| Качество ответов | Высокое | Высокое | Высокое |
| Контекстное окно | 128K токенов | 128K токенов | 200K токенов |
| Совместимость API | OpenAI-формат | Нативный | Собственный |
| Модель | Открытая (Meta) | Проприетарная | Проприетарная |

### Функция `groq_ask` — подробный разбор

```python
def groq_ask(user_text: str) -> str:
    # ── Шаг 1: добавить сообщение пользователя в сессионную историю ──────────
    state.history.append({"role": "user", "content": user_text})

    # ── Шаг 2: сформировать полный контекст для API ───────────────────────────
    # System-prompt идёт первым, затем вся история диалога
    messages = [
        {"role": "system", "content": state.T["system_prompt"]}
    ] + state.history
    # Пример итогового списка messages при 2 обменах:
    # [
    #   {"role": "system",    "content": "Ты — умный ИИ-ассистент..."},
    #   {"role": "user",      "content": "Привет!"},
    #   {"role": "assistant", "content": "Привет! Чем могу помочь?"},
    #   {"role": "user",      "content": "Расскажи про Python"},
    # ]

    try:
        # ── Шаг 3: вызов Groq API ─────────────────────────────────────────────
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,       # llama-3.3-70b-versatile
            messages=messages,
            temperature=0.7,        # умеренная творческость
            max_tokens=1024,        # ~750 слов максимум
        )

        # ── Шаг 4: извлечь ответ ──────────────────────────────────────────────
        answer = resp.choices[0].message.content

        # ── Шаг 5: добавить ответ в историю ──────────────────────────────────
        state.history.append({"role": "assistant", "content": answer})

        # ── Шаг 6: персистентность ────────────────────────────────────────────
        if state.current_chat_id:
            db_save_msg(state.current_chat_id, "user",      user_text)
            db_save_msg(state.current_chat_id, "assistant", answer)

            # Автоназвание чата — первые 40 символов первого сообщения
            if len(state.history) == 2:   # история: 1 user + 1 assistant
                db_set_title(state.current_chat_id, user_text[:40])

        return answer

    except Exception as exc:
        # Ошибки сети, превышения квоты и т.д. — возвращаем текст ошибки
        return f"[Ошибка Groq]: {exc}"
```

### Управление контекстом диалога

Groq API — **stateless**: каждый запрос не помнит предыдущих. Для поддержания связного диалога приложение передаёт **всю историю целиком** при каждом обращении:

```
Запрос 1:  [system]
Запрос 2:  [system, user1, assistant1]
Запрос 3:  [system, user1, assistant1, user2, assistant2]
...
```

| Событие | Что происходит с историей |
|---|---|
| Открытие нового чата | `state.history.clear()` |
| Открытие чата из истории | История восстанавливается из БД через `db_chat_msgs()` |
| Выход из аккаунта | `state.history.clear()` |
| Переключение вкладок | История сохраняется в памяти |

> ⚠️ При очень длинных диалогах суммарный объём `messages` может превысить контекстное окно модели (128K токенов для llama-3.3-70b). В текущей версии ограничений нет — потенциальное место для улучшения (см. раздел 16).

### Асинхронный вызов

`groq_client.chat.completions.create()` — синхронный блокирующий вызов. Чтобы не заморозить UI Flet во время ожидания ответа, он выполняется в отдельном потоке через `run_in_executor`:

```python
# В _send() [async]:
loop   = asyncio.get_event_loop()
answer = await loop.run_in_executor(
    None,       # executor=None → использует ThreadPoolExecutor по умолчанию
    groq_ask,   # блокирующая функция
    groq_text   # аргумент
)
# UI остаётся отзывчивым пока Groq думает
```

---

## 8. Система промтов

### System-prompt на русском

```
Ты — умный и полезный ИИ-ассистент по имени Agora.
Отвечай подробно и по существу.
Если пользователь прислал содержимое файла — проанализируй его.
Пиши на русском языке, если пользователь пишет по-русски.
```

### System-prompt на английском

```
You are Agora, a smart and helpful AI assistant.
Answer questions thoroughly and helpfully.
If the user sent file contents — analyse them.
Reply in English if the user writes in English.
```

### Что задаёт промт

| Директива | Цель |
|---|---|
| Имя `Agora` | Персонализация — ИИ представляется именно так в чате |
| «Отвечай подробно» | Избегает коротких уклончивых ответов |
| «Если прислал файл — проанализируй» | Активирует режим анализа при наличии блока `[Файл: ...]` |
| «Пиши на языке пользователя» | Автодетект языка без ручного переключения |

### Формат пользовательского сообщения без файла

```
Расскажи про сортировку пузырьком
```

### Формат пользовательского сообщения с прикреплённым файлом

```
Найди баги в этом коде

[Файл: server.py]
```python
import flask
app = flask.Flask(__name__)

@app.route('/')
def index():
    name = request.args.get('name')  # ← NameError: request не импортирован
    return f"Hello, {name}"
```
```

Обёртка в markdown-блок кода позволяет модели чётко отделить запрос пользователя от содержимого файла и применить соответствующий режим анализа.

### Кастомизация промта

System-prompt хранится в словаре `LANG` как обычная строка `"system_prompt"`. Для изменения поведения ИИ достаточно отредактировать эту строку — например, добавить тон, специализацию или ограничения:

```python
"system_prompt": (
    "Ты — Agora, ИИ-ассистент компании XYZ. "
    "Отвечай только на вопросы о продуктах компании. "
    "Будь вежлив и лаконичен. Не обсуждай политику. "
    "Пиши на языке пользователя."
),
```

---

## 9. Состояние приложения (AppState)

```python
class AppState:
    lang            = "ru"    # текущий язык: "ru" | "en"
    dark            = True    # тёмная тема
    logged_in       = False   # флаг авторизации
    user_id: int | None = None      # ID текущего пользователя в БД
    username: str         = ""      # логин для отображения в UI
    current_chat_id: int | None = None  # ID активного чата
    history: list[dict]   = []     # контекст для Groq API

    @property
    def C(self) -> dict:      # текущая цветовая палитра
        return DARK if self.dark else LIGHT

    @property
    def T(self) -> dict:      # текущие строки интерфейса
        return LANG[self.lang]

state = AppState()            # глобальный синглтон
```

`state` — единственный источник истины для всего приложения. Любая функция читает из него текущий язык (`state.T`), палитру (`state.C`), пользователя (`state.user_id`, `state.username`) и историю диалога (`state.history`).

### Жизненный цикл состояния

```
Запуск приложения
    state.logged_in = False
    state.lang = "ru", state.dark = True
         ↓
Успешный вход / регистрация
    state.logged_in = True
    state.user_id = <id>
    state.username = "<login>"
    state.current_chat_id = db_new_chat(uid)
    state.history = []
         ↓
Работа с чатом
    state.history ← накапливает диалог
    state.current_chat_id может меняться
         ↓
Выход (logout)
    state.logged_in = False
    state.user_id = None
    state.username = ""
    state.current_chat_id = None
    state.history.clear()
```

---

## 10. Темизация и интернационализация

### Цветовые палитры

#### Тёмная тема (DARK)

| Ключ | Цвет | Применение |
|---|---|---|
| `bg` | `#0D0F1A` | Фон всех страниц |
| `surface` | `#151829` | Навбар, нижняя панель, карточки |
| `surface2` | `#1E2235` | Поля ввода, кнопки второго плана |
| `border` | `#2A2F4A` | Все рамки |
| `accent` | `#7C6FFF` | Фиолетовый акцент, кнопки, аватар |
| `accent2` | `#FF6B9D` | Розовый акцент, аватар ИИ |
| `text` | `#E8EAF6` | Основной текст |
| `text_dim` | `#9CA3AF` | Подписи, плейсхолдеры |
| `text_muted` | `#4B5563` | Мелкий вспомогательный текст |
| `error` | `#FF6B6B` | Ошибки, кнопка выхода |
| `success` | `#4ADE80` | (зарезервировано) |
| `user_bubble` | `#7C6FFF22` | Фон пузыря пользователя |
| `ai_bubble` | `#FF6B9D11` | Фон пузыря ИИ |
| `logout_bg` | `#2A1A1A` | Фон кнопки выхода |
| `logout_brd` | `#5A2020` | Рамка кнопки выхода |
| `nav_active` | `#7C6FFF` | Активная вкладка навигации |
| `nav_inactive` | `#4B5563` | Неактивная вкладка |
| `file_bg` | `#1E2235` | Фон пузыря файла |
| `file_brd` | `#7C6FFF55` | Рамка пузыря файла |

#### Светлая тема (LIGHT) — основные отличия

| Ключ | Цвет |
|---|---|
| `bg` | `#F0F2FF` |
| `surface` | `#FFFFFF` |
| `accent` | `#6355EE` |
| `accent2` | `#E8527A` |
| `text` | `#1A1B2E` |

### Переключение темы

```python
# В _settings_view():
def _on_dark(e):
    state.dark = e.control.value   # True / False
    _rebuild("settings")           # пересобрать весь UI
```

`_rebuild()` вызывает `_apply_theme()`, которая устанавливает `page.theme_mode` и `page.bgcolor`, затем полностью пересобирает дерево виджетов с новой палитрой.

### Интернационализация

Все строки интерфейса хранятся в `LANG["ru"]` и `LANG["en"]` и доступны через `state.T["ключ"]`. Переключение происходит мгновенно: `state.lang = "en"` → `_rebuild("settings")`.

Перечень секретных вопросов также локализован:

```python
# RU:
"Кличка вашего первого питомца?",
"Город, где вы родились?",
"Девичья фамилия матери?",
...

# EN:
"Name of your first pet?",
"City where you were born?",
"Mother's maiden name?",
...
```

---

## 11. UI-компоненты

### `ChatBubble(sender, is_user)` — пузырь сообщения

Класс наследует `ft.Container`. Создаётся заранее с пустым текстом, затем заполняется посимвольно.

```
Пользователь (is_user=True):        ИИ (is_user=False):
 ┌─────────────────────────┐         ┌─────────────────────────┐
 │  [расширитель]  [пузырь] [av] │   │ [av] [пузырь]  [расш.] │
 └─────────────────────────┘         └─────────────────────────┘

Пузырь:
┌────────────────────────────┐
│ Вы (10px, bold, accent)    │
│ Текст сообщения (14px)     │
│ selectable=True            │
└────────────────────────────┘
Скруглённые углы: верхний-левый = 4px (у пользователя),
                  верхний-правый = 4px (у ИИ)
```

Ключевое поле для стриминга:
```python
self.txt = ft.Text("", color=C["text"], size=14, selectable=True)
# При стриминге:
bbl.txt.value = "".join(buf)
page.update()
```

### `_file_bubble(filename, is_user)` — пузырь файла

Отображается **перед** текстовым пузырём. Содержит иконку скрепки и имя файла.

### `_grad_btn(label, on_click)` — основная кнопка

```
┌──────────────────────────────────────────┐
│  gradient: accent ──────────────► accent2│  340×52 px
│           [label]  (bold, white, 15px)   │  blur-shadow: accent+44
└──────────────────────────────────────────┘
```

Используется для: Войти, Зарегистрироваться, Далее, Сменить пароль.

### `_field_wrap(icon, field)` — обёртка поля ввода

```
┌───────────────────────────────────────────────┐
│  [icon 18px accent]  [TextField expand=True]  │  54px высота
│                                               │  border-radius=12
└───────────────────────────────────────────────┘
```

### `_logo()` — логотип

Два квадрата 42×42 в `ft.Stack 64×64`:
- Нижний: рамка `accent2`, обычный (0°)
- Верхний: рамка `accent`, полупрозрачный фон, повёрнут на `π/4 = 45°`

### `_navbar()` — верхняя панель

Градиентная полоса `accent → accent2` с текстом «Agora-AI» по центру. Присутствует на всех экранах (в том числе Login/Register).

### `_bottom_nav(active)` — нижняя навигация

Три вкладки: Чат · История · Настройки. Активная — цвет `nav_active`, остальные — `nav_inactive`.

---

## 12. Экраны приложения

### Экран Login

**Маршрут:** `_login_view()` | **Условие показа:** `state.logged_in == False`

```
┌─────────────────────────────┐
│        [navbar]             │
│                             │
│        [logo]               │
│    "Добро пожаловать"       │
│    "Войдите в Agora-AI"     │
│                             │
│  [👤 Логин________________] │
│  [🔒 Пароль_______________] │
│                             │
│  [статус ошибки]            │
│                             │
│  [════ ВОЙТИ ═════════════] │
│       Забыли пароль?        │
│  Нет аккаунта? Регистрация  │
│       Agora-AI v2.0         │
└─────────────────────────────┘
```

**Полная логика:**
```python
def _try_login(e=None):
    u = login_f.value.strip()
    p = pwd_f.value.strip()

    # 1. Валидация пустых полей
    if not u or not p:
        status.value = T["err_empty"]
        page.update(); return

    # 2. Проверка в БД
    uid = db_login(u, p)
    if uid is None:
        status.value = T["err_wrong"]
        login_f.value = ""; pwd_f.value = ""
        page.update(); return

    # 3. Успешный вход
    state.logged_in = True
    state.user_id   = uid
    state.username  = u
    state.history.clear()
    _chat_messages.controls.clear()
    _welcome_shown[0] = True
    state.current_chat_id = db_new_chat(uid)
    _rebuild("chat")
```

Поля поддерживают отправку по `Enter` (`on_submit = _try_login`).

---

### Экран Register

**Маршрут:** `_register_view()` | **Переход:** кнопка «Зарегистрироваться» на Login

Дополнительно к Login содержит:
- Поле повтора пароля
- Выпадающий список секретных вопросов (`ft.Dropdown`)
- Поле ответа

**Валидации:**
1. Логин ≥ 3 символов (проверяется в `db_register`)
2. Пароль ≥ 4 символов
3. Пароли совпадают (проверяется в UI)
4. Ответ не пустой

После успешной регистрации — автоматический вход и переход в чат.

---

### Экран Forgot Password

**Маршрут:** `_forgot_view(step=1|2|3)` | **Переход:** ссылка «Забыли пароль?» на Login

Реализован как одна функция с тремя состояниями, передаваемыми через параметры:

```python
def _forgot_view(step: int = 1,
                 username: str = "",
                 question: str = "") -> ft.Container:
```

Индикатор прогресса: три анимированных точки — активная расширяется до 24px, неактивные — 8px.

```
Шаг 1 ●──○──○    Шаг 2 ○──●──○    Шаг 3 ○──○──●
```

Кнопка «← Назад» рекурсивно вызывает `_forgot_view(step-1, ...)`, сохраняя введённые данные.

---

### Экран Chat

**Маршрут:** `_chat_view()` | **Активная вкладка:** «Чат»

**Структура виджетов:**
```
ft.Container(expand=True)
└── ft.Column(expand=True)
    ├── new_chat_btn          [Кнопка + Новый чат]
    ├── ft.Stack(expand=True)
    │   ├── _chat_messages    [ft.ListView, auto_scroll=True]
    │   └── welcome_ctr       [заглушка до первого сообщения]
    └── Панель ввода
        ├── file_badge        [индикатор прикреплённого файла]
        └── ft.Row
            ├── attach_btn    [📎 кнопка]
            ├── prompt        [ft.TextField]
            └── send_btn      [➤ кнопка]
```

**Welcome-экран** (`welcome_ctr`) — иконка ✨ + «Agora-AI готов к работе». Скрывается при первом отправленном сообщении. Показывается снова при создании нового чата.

**Хранение состояния чата:**

```python
_chat_messages = ft.ListView(...)   # глобальный ListView
_welcome_shown = [True]             # mutable через list
_pending_file  = [None]             # прикреплённый файл
```

Все три — глобальные переменные внутри `main()`, используют паттерн `[значение]` для мутации из вложенных функций без `nonlocal`.

---

### Экран History

**Маршрут:** `_history_view()` | **Активная вкладка:** «История»

Каждая карточка чата:
```
┌──────────────────────────────────────────────┐
│ [💬]  Заголовок чата (bold, ellipsis)    [🗑️] │
│       5 сообщ.  •  14:32                     │
└──────────────────────────────────────────────┘
```
Активный чат выделен рамкой цвета `accent`.

**Дата:** если чат создан сегодня — показывается время `HH:MM`, иначе `DD.MM.YY`.

**Открытие чата:**
```python
def _open_chat(chat_id):
    msgs = db_chat_msgs(chat_id)
    state.current_chat_id = chat_id
    state.history = [{"role": m["role"], "content": m["content"]} for m in msgs]
    # Восстановить пузыри сообщений в ListView
    for m in msgs:
        bbl = ChatBubble(sender, is_user)
        bbl.txt.value = m["content"]
        _chat_messages.controls.append(bbl)
    # Переключиться на вкладку Chat
    root.controls[1] = _chat_view()
    root.controls[2] = _bottom_nav("chat")
    page.update()
```

**Удаление** — через `ft.AlertDialog` с подтверждением. Если удаляется текущий чат — автоматически создаётся новый.

---

### Экран Settings

**Маршрут:** `_settings_view()` | **Активная вкладка:** «Настройки»

| Пункт | Виджет | Действие |
|---|---|---|
| Аккаунт `@username` | Строка info | Только отображение |
| Тёмная тема | `ft.Switch` | `state.dark` → `_rebuild("settings")` |
| Уведомления | `ft.Switch` | Декоративный (не реализован) |
| Язык `🇷🇺/🇺🇸` | Tap | `state.lang` чередует RU↔EN → `_rebuild` |
| Выйти | Красная кнопка | `_do_logout()` |

---

## 13. Поток данных: отправка сообщения

```
Пользователь нажимает ➤ или Enter
              │
              ▼
     async _send(e=None)
              │
    ┌─────────┴──────────┐
    │ Есть текст и/или   │
    │ прикреплённый файл?│
    └─────────┬──────────┘
              │ ДА
              ▼
    prompt.value = ""          (очистить поле)
    welcome_ctr.visible = False (скрыть заглушку)
              │
    ┌─────────┴──────────────────────┐
    │ Формирование groq_text         │
    │  if file and text:             │
    │    "{text}\n\n[Файл:...]\n```  │
    │  elif file only:               │
    │    "[Файл:...]\n```..."        │
    │  else:                         │
    │    text                        │
    └─────────┬──────────────────────┘
              │
    ┌─────────┴────────────────────────┐
    │ UI: показать сообщение           │
    │  _file_bubble (если файл)        │
    │  ChatBubble(is_user=True)        │
    │  анимация посимвольно 4мс/символ │
    └─────────┬────────────────────────┘
              │
              ▼
    loop.run_in_executor(None, groq_ask, groq_text)
    ══════════ ПОТОК: GROQ API ════════
      history.append({"role":"user", ...})
      groq_client.chat.completions.create(...)
      answer = resp.choices[0].message.content
      history.append({"role":"assistant", ...})
      db_save_msg(..., "user", user_text)
      db_save_msg(..., "assistant", answer)
      if первое сообщение → db_set_title(...)
    ═══════════════════════════════════
              │
              ▼
    ChatBubble(is_user=False)
    анимация ответа посимвольно 4мс/символ
              │
              ▼
             END
```

---

## 14. Работа с файлами

### Поддерживаемые форматы

| Категория | Расширения |
|---|---|
| Текст / разметка | `txt`, `md`, `log` |
| Веб | `html`, `css`, `js`, `ts` |
| Данные | `json`, `csv`, `yaml`, `yml`, `xml` |
| Python | `py` |
| Системные языки | `c`, `cpp` |
| Прочие языки | `java`, `go`, `rs`, `swift` |

### Полный процесс прикрепления файла

```python
async def _pick_file(e=None):
    # 1. Открыть системный диалог выбора файла
    picked = await file_picker.pick_files(
        dialog_title=T["attach"],
        allow_multiple=False,
        with_data=False,          # не загружать байты сразу (десктоп)
        file_type=ft.FilePickerFileType.CUSTOM,
        allowed_extensions=[...], # белый список форматов
    )
    if not picked: return         # пользователь отменил

    pf = picked[0]
    fname    = pf.name or "file"
    content  = ""
    file_path = pf.path if pf.path else None

    # 2a. Десктоп: читать через файловую систему
    if file_path and os.path.exists(file_path):
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read(8000)   # макс. 8 000 символов

    # 2b. Веб/мобиль: читать из байтов
    elif pf.bytes:
        content = pf.bytes.decode("utf-8", errors="replace")[:8000]

    # 3. Сохранить в pending
    _pending_file[0] = {"name": fname, "content": content}

    # 4. Показать badge
    file_badge.content.controls[1].value = fname
    file_badge.visible = True
    page.update()
```

### Жизненный цикл прикреплённого файла

```
Пользователь нажимает 📎
    → file_picker открывается
    → _pending_file[0] = {name, content}
    → file_badge показывается

Пользователь нажимает ✕ на badge
    → _pending_file[0] = None
    → file_badge скрывается

Пользователь нажимает ➤ (отправить)
    → файл добавляется к groq_text
    → _pending_file[0] = None
    → file_badge скрывается
    → _file_bubble добавляется в чат
```

---

## 15. Навигация и перерисовка UI

### Структура дерева виджетов страницы

```
page
└── ft.Stack
    ├── root (ft.Column)                ← основное содержимое
    │   ├── root.controls[0]: _navbar()
    │   ├── root.controls[1]: <текущий экран>
    │   └── root.controls[2]: _bottom_nav() (только если logged_in)
    └── _toast_box                      ← поверх всего
```

### Функция `_rebuild(screen)`

Центральная функция управления навигацией:

```python
def _rebuild(screen: str = "login") -> None:
    _apply_theme()              # применить тему к page
    root.controls.clear()       # очистить дерево
    root.controls.append(_navbar())   # всегда добавить navbar

    if state.logged_in:
        views = {
            "chat":     _chat_view,
            "history":  _history_view,
            "settings": _settings_view,
        }
        root.controls.append(views.get(screen, _chat_view)())
        root.controls.append(_bottom_nav(screen))   # с активной вкладкой
    else:
        root.controls.append(
            _register_view() if screen == "register" else _login_view()
        )

    page.update()
```

### Переключение вкладок (без rebuild)

Для переключения между Chat/History/Settings используется более быстрый метод — только обновить `controls[1]` и `controls[2]`:

```python
def _switch(key: str) -> None:
    views = {"chat": _chat_view, "history": _history_view, "settings": _settings_view}
    root.controls[1] = views[key]()
    root.controls[2] = _bottom_nav(key)
    page.update()
```

### Toast-уведомления

```python
async def _run():
    _toast_txt.value = msg
    _toast_box.visible = True
    page.update()
    await asyncio.sleep(2.2)       # показывать 2.2 секунды
    _toast_box.visible = False
    page.update()

page.run_task(_run)               # запустить в фоне без блокировки
```

Toast позиционируется абсолютно `bottom=90` через `ft.Stack`, появляется поверх любого контента.

---

## 16. Ограничения и возможные улучшения

### Известные ограничения

| Область | Ограничение | Возможное решение |
|---|---|---|
| **Безопасность** | API-ключ захардкожен в коде | Вынести в `.env` / переменные окружения |
| **Безопасность** | Секретный ответ хэшируется с фиксированной солью | Использовать уникальную соль per-user |
| **Контекст ИИ** | Вся история передаётся без ограничений | Ввести скользящее окно или суммаризацию |
| **Хранение** | Одна база на всех пользователей | Нормально для десктопа; для сервера — отдельные БД |
| **Файлы** | Только текстовые, до 8 000 символов | Поддержка PDF, изображений через OCR |
| **Уведомления** | Переключатель декоративный | Реализовать системные уведомления |
| **Одновременные сессии** | `state` — один глобальный объект | Перенести в `page.session_id` для веб-режима |
| **Ошибки сети** | Только текстовое сообщение об ошибке | Retry-логика, индикатор загрузки |
| **Длина ответа** | `max_tokens=1024` ≈ 750 слов | Увеличить при необходимости |

### Идеи для развития

- **Экспорт чата** в `.txt` или `.md`
- **Поиск** по истории сообщений
- **Смена пароля** из настроек (без сброса через секретный вопрос)
- **Удаление аккаунта** с каскадным удалением данных
- **Стриминг через WebSocket** вместо посимвольной эмуляции
- **Markdown-рендеринг** ответов ИИ (заголовки, блоки кода, списки)
- **Несколько языков** (добавить новый ключ в `LANG`)
- **Кастомный system-prompt** в настройках пользователя

---

## 17. Справочник функций

### Глобальные функции (вне `main`)

| Функция | Сигнатура | Описание |
|---|---|---|
| `_db` | `() → Connection` | Фабрика SQLite-соединений |
| `db_init` | `() → None` | Инициализация БД и миграция |
| `_hash_pwd` | `(pwd, salt) → str` | PBKDF2-SHA256 хэш |
| `db_login` | `(username, password) → int\|None` | Аутентификация |
| `db_register` | `(username, password, question, answer) → (bool, str)` | Регистрация |
| `db_get_security_question` | `(username) → str\|None` | Получить секретный вопрос |
| `db_verify_security_answer` | `(username, answer) → bool` | Проверить ответ |
| `db_reset_password` | `(username, new_password) → None` | Сбросить пароль |
| `db_new_chat` | `(user_id) → int` | Создать чат |
| `db_save_msg` | `(chat_id, role, content) → None` | Сохранить сообщение |
| `db_set_title` | `(chat_id, title) → None` | Обновить заголовок чата |
| `db_user_chats` | `(user_id) → list[dict]` | Список чатов пользователя |
| `db_chat_msgs` | `(chat_id) → list[dict]` | Сообщения чата |
| `db_delete_chat` | `(chat_id) → None` | Удалить чат |
| `groq_ask` | `(user_text) → str` | Запрос к ИИ + сохранение |
| `_user_av` | `() → ft.Container` | Аватар пользователя |
| `_ai_av` | `() → ft.Container` | Аватар ИИ |
| `_file_bubble` | `(filename, is_user) → ft.Container` | Пузырь файла |

### Функции внутри `main(page)`

| Функция | Тип | Описание |
|---|---|---|
| `_apply_theme` | sync | Применить тему к `page` и toast |
| `show_toast` | async | Показать всплывающее уведомление 2.2с |
| `_navbar` | → Container | Верхняя градиентная панель |
| `_bottom_nav` | → Container | Нижняя панель навигации |
| `_rebuild` | sync | Полная перерисовка интерфейса |
| `_field_wrap` | → Container | Стилизованная обёртка TextField |
| `_text_field` | → TextField | Стилизованный TextField |
| `_logo` | → Stack | Логотип (два повёрнутых квадрата) |
| `_grad_btn` | → Container | Кнопка с градиентом |
| `_login_view` | → Container | Экран входа |
| `_register_view` | → Container | Экран регистрации |
| `_forgot_view` | → Container | Мастер восстановления пароля |
| `_chat_view` | → Container | Экран чата |
| `_history_view` | → Container | Экран истории чатов |
| `_settings_view` | → Container | Экран настроек |
| `_do_logout` | sync | Сброс состояния и выход |
| `_send` | async | Отправка сообщения с анимацией |
| `_pick_file` | async | Выбор и чтение файла |

---

*Документация составлена для Agora-AI v2.0 · Python 3.12+ · Flet 0.85+*

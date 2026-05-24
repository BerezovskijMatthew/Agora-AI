# Agora-AI  •  Flet 0.85+  •  Groq  •  SQLite  •  Python 3.12+
import asyncio
import hashlib
import os
import secrets
import sqlite3
from datetime import datetime
from math import pi

import flet as ft
from groq import Groq

# ── Конфигурация ─────────────────────────────────────────────────────────────
# Для локального запуска ключ задан напрямую.
# В Docker переменная окружения GROQ_API_KEY переопределяет его.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GROQ_MODEL   = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
DB_PATH      = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "agora_ai.db"),
)

groq_client = Groq(api_key=GROQ_API_KEY)

# ═══════════════════════════════════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════════════════════════════════
def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def db_init() -> None:
    with _db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                username         TEXT    UNIQUE NOT NULL,
                password_hash    TEXT    NOT NULL,
                salt             TEXT    NOT NULL,
                security_question TEXT,
                security_answer   TEXT,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chats (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                title      TEXT    NOT NULL DEFAULT 'Новый чат',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Миграция: добавляем колонки если их нет (для уже существующих БД)
        for col, typ in [("security_question","TEXT"), ("security_answer","TEXT")]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
            except Exception:
                pass  # колонка уже существует
        # Создаём admin/admin при первом запуске
        if not conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            salt = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO users (username,password_hash,salt) VALUES (?,?,?)",
                ("admin", _hash_pwd("admin", salt), salt),
            )

def _hash_pwd(pwd: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt.encode(), 100_000).hex()

def db_login(username: str, password: str) -> int | None:
    row = _db().execute(
        "SELECT id,password_hash,salt FROM users WHERE username=?", (username,)
    ).fetchone()
    if row and _hash_pwd(password, row["salt"]) == row["password_hash"]:
        return row["id"]
    return None

def db_register(username: str, password: str,
                security_question: str = "", security_answer: str = "") -> tuple[bool, str]:
    if len(username) < 3:
        return False, "Логин: минимум 3 символа"
    if len(password) < 4:
        return False, "Пароль: минимум 4 символа"
    try:
        salt = secrets.token_hex(16)
        # Хешируем ответ в нижнем регистре для нечувствительного сравнения
        ans_hash = _hash_pwd(security_answer.strip().lower(), "sec_salt_fixed") if security_answer else ""
        with _db() as conn:
            conn.execute(
                "INSERT INTO users (username,password_hash,salt,security_question,security_answer) VALUES (?,?,?,?,?)",
                (username, _hash_pwd(password, salt), salt, security_question, ans_hash),
            )
        return True, ""
    except sqlite3.IntegrityError:
        return False, "Такой логин уже занят"

def db_get_security_question(username: str) -> str | None:
    """Возвращает секретный вопрос или None если пользователь не найден."""
    row = _db().execute(
        "SELECT security_question FROM users WHERE username=?", (username,)
    ).fetchone()
    if row is None:
        return None
    return row["security_question"] or ""

def db_verify_security_answer(username: str, answer: str) -> bool:
    row = _db().execute(
        "SELECT security_answer FROM users WHERE username=?", (username,)
    ).fetchone()
    if not row or not row["security_answer"]:
        return False
    ans_hash = _hash_pwd(answer.strip().lower(), "sec_salt_fixed")
    return ans_hash == row["security_answer"]

def db_reset_password(username: str, new_password: str) -> None:
    salt = secrets.token_hex(16)
    with _db() as conn:
        conn.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE username=?",
            (_hash_pwd(new_password, salt), salt, username),
        )

def db_new_chat(user_id: int) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO chats (user_id) VALUES (?)", (user_id,)
        )
        return cur.lastrowid

def db_save_msg(chat_id: int, role: str, content: str) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id,role,content) VALUES (?,?,?)",
            (chat_id, role, content),
        )

def db_set_title(chat_id: int, title: str) -> None:
    with _db() as conn:
        conn.execute("UPDATE chats SET title=? WHERE id=?", (title[:45], chat_id))

def db_user_chats(user_id: int) -> list[dict]:
    rows = _db().execute("""
        SELECT c.id, c.title, c.created_at,
               COUNT(m.id) AS msg_count
        FROM   chats c
        LEFT JOIN messages m ON m.chat_id = c.id
        WHERE  c.user_id = ?
        GROUP BY c.id
        ORDER BY c.created_at DESC
        LIMIT 100
    """, (user_id,)).fetchall()
    return [dict(r) for r in rows]

def db_chat_msgs(chat_id: int) -> list[dict]:
    rows = _db().execute(
        "SELECT role,content FROM messages WHERE chat_id=? ORDER BY created_at",
        (chat_id,),
    ).fetchall()
    return [dict(r) for r in rows]

def db_delete_chat(chat_id: int) -> None:
    with _db() as conn:
        conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))

# ═══════════════════════════════════════════════════════════════════════════════
# ПЕРЕВОДЫ
# ═══════════════════════════════════════════════════════════════════════════════
LANG = {
    "ru": {
        "welcome_title":  "Добро пожаловать",
        "welcome_sub":    "Войдите в Agora-AI",
        "login_hint":     "Логин",
        "password_hint":  "Пароль",
        "forgot":         "Забыли пароль?",
        "sign_in":        "Войти",
        "no_account":     "Нет аккаунта?  ",
        "register":       "Зарегистрироваться",
        "reg_title":      "Регистрация",
        "reg_sub":        "Создайте аккаунт",
        "reg_btn":        "Создать аккаунт",
        "has_account":    "Уже есть аккаунт?  ",
        "back_login":     "Войти",
        "version":        "Agora-AI v2.0",
        "err_empty":      "Введите логин и пароль",
        "err_wrong":      "Неверный логин или пароль",
        "chat_hint":      "Напишите сообщение...",
        "chat_ready":     "Agora-AI готов к работе",
        "chat_sub":       "Задайте любой вопрос",
        "new_chat":       "Новый чат",
        "nav_chat":       "Чат",
        "nav_history":    "История",
        "nav_settings":   "Настройки",
        "history_title":  "История чатов",
        "history_empty":  "Нет сохранённых чатов",
        "msg_count":      "сообщ.",
        "del_title":      "Удалить чат?",
        "del_confirm":    "Это действие нельзя отменить.",
        "del_yes":        "Удалить",
        "del_no":         "Отмена",
        "settings_title": "Настройки",
        "dark_theme":     "Тёмная тема",
        "dark_sub":       "Переключить тёмный/светлый",
        "notifications":  "Уведомления",
        "notif_sub":      "Пуш-уведомления",
        "language":       "Язык",
        "lang_sub":       "Русский / English",
        "account":        "Аккаунт",
        "logout":         "Выйти из аккаунта",
        "logged_out":     "Вы вышли из аккаунта",
        "attach":         "Прикрепить файл",
        "you":            "Вы",
        "forgot":         "Забыли пароль?",
        "forgot_title":   "Восстановление пароля",
        "forgot_step1":   "Введите логин",
        "forgot_step2":   "Ответьте на вопрос",
        "forgot_step3":   "Новый пароль",
        "forgot_next":    "Далее",
        "forgot_reset":   "Сменить пароль",
        "forgot_back":    "← Назад",
        "forgot_done":    "Пароль успешно изменён!",
        "forgot_err_user":"Пользователь не найден",
        "forgot_err_ans": "Неверный ответ",
        "forgot_err_no_q":"У этого аккаунта нет секретного вопроса",
        "forgot_err_pwd": "Введите новый пароль (мин. 4 символа)",
        "sec_question_lbl":"Секретный вопрос",
        "sec_answer_lbl":  "Ответ",
        "sec_questions": [
            "Кличка вашего первого питомца?",
            "Город, где вы родились?",
            "Девичья фамилия матери?",
            "Название вашей первой школы?",
            "Любимое блюдо в детстве?",
            "Имя лучшего друга детства?",
        ],
        "system_prompt": (
            "Ты — умный и полезный ИИ-ассистент по имени Agora. "
            "Отвечай подробно и по существу. "
            "Если пользователь прислал содержимое файла — проанализируй его. "
            "Пиши на русском языке, если пользователь пишет по-русски."
        ),
    },
    "en": {
        "welcome_title":  "Welcome back",
        "welcome_sub":    "Sign in to Agora-AI",
        "login_hint":     "Login",
        "password_hint":  "Password",
        "forgot":         "Forgot password?",
        "sign_in":        "Sign In",
        "no_account":     "No account?  ",
        "register":       "Register",
        "reg_title":      "Sign Up",
        "reg_sub":        "Create your account",
        "reg_btn":        "Create Account",
        "has_account":    "Already have an account?  ",
        "back_login":     "Sign In",
        "version":        "Agora-AI v2.0",
        "err_empty":      "Enter login and password",
        "err_wrong":      "Incorrect login or password",
        "chat_hint":      "Type a message...",
        "chat_ready":     "Agora-AI is ready",
        "chat_sub":       "Ask me anything",
        "new_chat":       "New Chat",
        "nav_chat":       "Chat",
        "nav_history":    "History",
        "nav_settings":   "Settings",
        "history_title":  "Chat History",
        "history_empty":  "No saved chats",
        "msg_count":      "msgs",
        "del_title":      "Delete chat?",
        "del_confirm":    "This action cannot be undone.",
        "del_yes":        "Delete",
        "del_no":         "Cancel",
        "settings_title": "Settings",
        "dark_theme":     "Dark theme",
        "dark_sub":       "Toggle dark/light mode",
        "notifications":  "Notifications",
        "notif_sub":      "Push notifications",
        "language":       "Language",
        "lang_sub":       "Русский / English",
        "account":        "Account",
        "logout":         "Sign out",
        "logged_out":     "You have signed out",
        "attach":         "Attach file",
        "you":            "You",
        "forgot":         "Forgot password?",
        "forgot_title":   "Password Recovery",
        "forgot_step1":   "Enter your login",
        "forgot_step2":   "Answer your question",
        "forgot_step3":   "New password",
        "forgot_next":    "Next",
        "forgot_reset":   "Reset Password",
        "forgot_back":    "← Back",
        "forgot_done":    "Password changed successfully!",
        "forgot_err_user":"User not found",
        "forgot_err_ans": "Incorrect answer",
        "forgot_err_no_q":"This account has no security question",
        "forgot_err_pwd": "Enter a new password (min. 4 chars)",
        "sec_question_lbl":"Security question",
        "sec_answer_lbl":  "Answer",
        "sec_questions": [
            "Name of your first pet?",
            "City where you were born?",
            "Mother's maiden name?",
            "Name of your first school?",
            "Favourite childhood food?",
            "Name of your childhood best friend?",
        ],
        "system_prompt": (
            "You are Agora, a smart and helpful AI assistant. "
            "Answer questions thoroughly and helpfully. "
            "If the user sent file contents — analyse them. "
            "Reply in English if the user writes in English."
        ),
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# ТЕМЫ
# ═══════════════════════════════════════════════════════════════════════════════
DARK = {
    "bg":          "#0D0F1A",
    "surface":     "#151829",
    "surface2":    "#1E2235",
    "border":      "#2A2F4A",
    "accent":      "#7C6FFF",
    "accent2":     "#FF6B9D",
    "text":        "#E8EAF6",
    "text_dim":    "#9CA3AF",
    "text_muted":  "#4B5563",
    "error":       "#FF6B6B",
    "success":     "#4ADE80",
    "icon_bg":     "#2A2F4A",
    "logout_bg":   "#2A1A1A",
    "logout_brd":  "#5A2020",
    "nav_active":  "#7C6FFF",
    "nav_inactive":"#4B5563",
    "user_bubble": "#7C6FFF22",
    "ai_bubble":   "#FF6B9D11",
    "file_bg":     "#1E2235",
    "file_brd":    "#7C6FFF55",
    "card_del":    "#3A1A1A",
}
LIGHT = {
    "bg":          "#F0F2FF",
    "surface":     "#FFFFFF",
    "surface2":    "#E8EAFF",
    "border":      "#C8CADC",
    "accent":      "#6355EE",
    "accent2":     "#E8527A",
    "text":        "#1A1B2E",
    "text_dim":    "#555770",
    "text_muted":  "#9EA0B0",
    "error":       "#D94040",
    "success":     "#16A34A",
    "icon_bg":     "#DDE0FF",
    "logout_bg":   "#FFE8E8",
    "logout_brd":  "#FFBBBB",
    "nav_active":  "#6355EE",
    "nav_inactive":"#9EA0B0",
    "user_bubble": "#6355EE22",
    "ai_bubble":   "#E8527A11",
    "file_bg":     "#E8EAFF",
    "file_brd":    "#6355EE55",
    "card_del":    "#FFE8E8",
}

_C  = ft.Alignment(0,  0)
_TL = ft.Alignment(-1, -1)
_BR = ft.Alignment(1,  1)

# ═══════════════════════════════════════════════════════════════════════════════
# СОСТОЯНИЕ
# ═══════════════════════════════════════════════════════════════════════════════
class AppState:
    lang         = "ru"
    dark         = True
    logged_in    = False
    user_id: int | None   = None
    username: str         = ""
    current_chat_id: int | None = None
    history: list[dict]   = []   # Groq context

    @property
    def C(self) -> dict:
        return DARK if self.dark else LIGHT

    @property
    def T(self) -> dict:
        return LANG[self.lang]

state = AppState()


# ═══════════════════════════════════════════════════════════════════════════════
# GROQ
# ═══════════════════════════════════════════════════════════════════════════════
def groq_ask(user_text: str) -> str:
    state.history.append({"role": "user", "content": user_text})
    messages = [{"role": "system", "content": state.T["system_prompt"]}] + state.history
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL, messages=messages,
            temperature=0.7, max_tokens=1024,
        )
        answer = resp.choices[0].message.content
        state.history.append({"role": "assistant", "content": answer})
        if state.current_chat_id:
            db_save_msg(state.current_chat_id, "user", user_text)
            db_save_msg(state.current_chat_id, "assistant", answer)
            # Заголовок чата = первые 40 символов первого сообщения
            if len(state.history) == 2:
                db_set_title(state.current_chat_id, user_text[:40])
        return answer
    except Exception as exc:
        return f"[Ошибка Groq]: {exc}"


# ═══════════════════════════════════════════════════════════════════════════════
# UI-компоненты сообщений
# ═══════════════════════════════════════════════════════════════════════════════
def _user_av() -> ft.Container:
    return ft.Container(
        width=28, height=28, border_radius=14,
        bgcolor=state.C["accent"], alignment=_C,
        content=ft.Text(state.username[:1].upper() or "Я",
                        size=11, weight="bold", color="white"),
    )

def _ai_av() -> ft.Container:
    return ft.Container(
        width=28, height=28, border_radius=14,
        gradient=ft.LinearGradient(begin=_TL, end=_BR,
                                   colors=[state.C["accent"], state.C["accent2"]]),
        alignment=_C,
        content=ft.Text("A", size=11, weight="bold", color="white"),
    )

class ChatBubble(ft.Container):
    def __init__(self, sender: str, is_user: bool):
        C = state.C
        self.txt = ft.Text("", color=C["text"], size=14, selectable=True)
        bubble = ft.Container(
            padding=ft.Padding(left=12, top=8, right=12, bottom=8),
            border_radius=ft.BorderRadius(
                top_left=4 if is_user else 14,
                top_right=14 if is_user else 4,
                bottom_left=14, bottom_right=14,
            ),
            bgcolor=C["user_bubble"] if is_user else C["ai_bubble"],
            border=ft.Border.all(1, (C["accent"] if is_user else C["accent2"]) + "55"),
            content=ft.Column(spacing=3, controls=[
                ft.Text(sender, size=10, weight="bold",
                        color=C["accent"] if is_user else C["accent2"]),
                self.txt,
            ]),
        )
        av = _user_av() if is_user else _ai_av()
        row_ctrls = (
            [ft.Container(expand=True), bubble, ft.Container(width=6), av]
            if is_user else
            [av, ft.Container(width=6), bubble, ft.Container(expand=True)]
        )
        super().__init__(
            padding=ft.Padding(left=8, top=3, right=8, bottom=3),
            content=ft.Row(controls=row_ctrls,
                           vertical_alignment=ft.CrossAxisAlignment.START),
        )

def _file_bubble(filename: str, is_user: bool) -> ft.Container:
    C = state.C
    card = ft.Container(
        padding=ft.Padding(left=10, top=8, right=10, bottom=8),
        border_radius=10, bgcolor=C["file_bg"],
        border=ft.Border.all(1, C["file_brd"]),
        content=ft.Row(spacing=8, controls=[
            ft.Icon(ft.Icons.ATTACH_FILE_ROUNDED, size=15, color=C["accent"]),
            ft.Text(filename, size=12, color=C["text"], weight="bold"),
        ]),
    )
    av = _user_av() if is_user else _ai_av()
    row_ctrls = (
        [ft.Container(expand=True), card, ft.Container(width=6), av]
        if is_user else
        [av, ft.Container(width=6), card, ft.Container(expand=True)]
    )
    return ft.Container(
        padding=ft.Padding(left=8, top=3, right=8, bottom=3),
        content=ft.Row(controls=row_ctrls,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
async def main(page: ft.Page) -> None:
    page.title   = "Agora-AI"
    page.padding = 0
    page.spacing = 0
    page.window.width  = 420
    page.window.height = 820

    root = ft.Column(expand=True, spacing=0)

    # Toast
    _toast_txt = ft.Text("", size=13, text_align="center")
    _toast_box = ft.Container(
        visible=False, bottom=90, left=30, right=30,
        content=ft.Container(
            border_radius=10,
            padding=ft.Padding(left=14, top=9, right=14, bottom=9),
            content=_toast_txt,
        ),
    )

    # Диалог подтверждения удаления
    _del_dialog = ft.AlertDialog(
        modal=True, open=False,
        title=ft.Text(""),
        content=ft.Text(""),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    page.overlay.extend([_del_dialog])
    page.add(ft.Stack(expand=True, controls=[root, _toast_box]))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _apply_theme() -> None:
        page.theme_mode = ft.ThemeMode.DARK if state.dark else ft.ThemeMode.LIGHT
        page.bgcolor    = state.C["bg"]
        C = state.C
        _toast_box.content.bgcolor = C["surface2"]
        _toast_box.content.border  = ft.Border.all(1, C["accent"])
        _toast_txt.color           = C["text"]

    def show_toast(msg: str) -> None:
        async def _run():
            _toast_txt.value = msg
            _toast_box.visible = True
            page.update()
            await asyncio.sleep(2.2)
            _toast_box.visible = False
            page.update()
        page.run_task(_run)

    # ── Navbar ────────────────────────────────────────────────────────────────
    def _navbar() -> ft.Container:
        C = state.C
        return ft.Container(
            gradient=ft.LinearGradient(begin=_TL, end=_BR,
                                       colors=[C["accent"], C["accent2"]]),
            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
            shadow=ft.BoxShadow(blur_radius=20, color=C["accent"] + "44"),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[ft.Text("Agora-AI", size=20, color="white", weight="bold")],
            ),
        )

    # ── Bottom nav (3 пункта) ─────────────────────────────────────────────────
    def _bottom_nav(active: str) -> ft.Container:
        C = state.C
        T = state.T
        items = [
            (ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED, T["nav_chat"],     "chat"),
            (ft.Icons.HISTORY_ROUNDED,             T["nav_history"],  "history"),
            (ft.Icons.SETTINGS_OUTLINED,           T["nav_settings"], "settings"),
        ]

        def _item(icon, label, key):
            is_a = key == active
            col  = C["nav_active"] if is_a else C["nav_inactive"]
            return ft.Container(
                expand=True,
                on_click=lambda e, k=key: _switch(k),
                padding=ft.Padding(left=0, top=8, right=0, bottom=8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
                    controls=[ft.Icon(icon, size=22, color=col),
                               ft.Text(label, size=10, color=col)],
                ),
            )

        def _switch(key: str) -> None:
            views = {
                "chat":     _chat_view,
                "history":  _history_view,
                "settings": _settings_view,
            }
            root.controls[1] = views[key]()
            root.controls[2] = _bottom_nav(key)
            page.update()

        return ft.Container(
            bgcolor=C["surface"],
            border=ft.Border(top=ft.BorderSide(1, C["border"])),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[_item(i, l, k) for i, l, k in items],
            ),
        )

    # ── Rebuild ───────────────────────────────────────────────────────────────
    def _rebuild(screen: str = "login") -> None:
        _apply_theme()
        root.controls.clear()
        root.controls.append(_navbar())
        if state.logged_in:
            views = {
                "chat":     _chat_view,
                "history":  _history_view,
                "settings": _settings_view,
            }
            root.controls.append(views.get(screen, _chat_view)())
            root.controls.append(_bottom_nav(screen))
        else:
            root.controls.append(
                _register_view() if screen == "register" else _login_view()
            )
        page.update()

    # ── Общий билдер полей ввода ──────────────────────────────────────────────
    def _field_wrap(icon, field) -> ft.Container:
        C = state.C
        return ft.Container(
            height=54, border_radius=12,
            bgcolor=C["surface2"], border=ft.Border.all(1, C["border"]),
            padding=ft.Padding(left=16, top=0, right=16, bottom=0),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
                controls=[ft.Icon(icon, size=18, color=C["accent"]), field],
            ),
        )

    def _text_field(hint, hide=False) -> ft.TextField:
        C = state.C
        return ft.TextField(
            hint_text=hint,
            hint_style=ft.TextStyle(color=C["text_muted"], size=14),
            border=ft.InputBorder.NONE, bgcolor="transparent",
            color=C["text"], cursor_color=C["accent"],
            content_padding=ft.Padding(0, 0, 0, 0), text_size=14, expand=True,
            password=hide, can_reveal_password=hide,
        )

    def _logo() -> ft.Stack:
        C = state.C
        return ft.Stack(width=64, height=64, controls=[
            ft.Container(
                width=42, height=42, left=11, top=11,
                border=ft.Border.all(2.5, C["accent2"]), border_radius=5,
                rotate=ft.Rotate(angle=0, alignment=_C),
            ),
            ft.Container(
                width=42, height=42, left=11, top=11,
                border=ft.Border.all(2.5, C["accent"]),
                bgcolor=C["bg"] + "cc", border_radius=5,
                rotate=ft.Rotate(angle=pi / 4, alignment=_C),
            ),
        ])

    def _grad_btn(label: str, on_click) -> ft.Container:
        C = state.C
        return ft.Container(
            width=340, height=52, border_radius=14,
            gradient=ft.LinearGradient(begin=_TL, end=_BR,
                                       colors=[C["accent"], C["accent2"]]),
            shadow=ft.BoxShadow(blur_radius=20, color=C["accent"] + "44"),
            alignment=_C, on_click=on_click,
            content=ft.Text(label, size=15, weight="bold", color="white"),
        )

    # ── LOGIN ─────────────────────────────────────────────────────────────────
    def _login_view() -> ft.Container:
        C = state.C
        T = state.T
        login_f = _text_field(T["login_hint"])
        pwd_f   = _text_field(T["password_hint"], hide=True)
        status  = ft.Text("", color=C["error"], size=12, text_align="center")

        def _try_login(e=None):
            u = (login_f.value or "").strip()
            p = (pwd_f.value   or "").strip()
            if not u or not p:
                status.value = T["err_empty"]; page.update(); return
            uid = db_login(u, p)
            if uid is None:
                status.value = T["err_wrong"]
                login_f.value = ""; pwd_f.value = ""; page.update(); return
            state.logged_in = True
            state.user_id   = uid
            state.username  = u
            state.history.clear()
            _chat_messages.controls.clear()
            _welcome_shown[0] = True
            # Создаём новый чат
            state.current_chat_id = db_new_chat(uid)
            _rebuild("chat")

        login_f.on_submit = _try_login
        pwd_f.on_submit   = _try_login

        return ft.Container(
            expand=True, bgcolor=C["bg"],
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO, spacing=0,
                controls=[
                    ft.Container(height=48),
                    _logo(),
                    ft.Container(height=22),
                    ft.Text(T["welcome_title"], size=26, weight="bold", color=C["text"]),
                    ft.Container(height=6),
                    ft.Text(T["welcome_sub"], size=14, color=C["text_dim"]),
                    ft.Container(height=38),
                    ft.Container(width=340,
                                 content=_field_wrap(ft.Icons.PERSON_OUTLINE_ROUNDED, login_f)),
                    ft.Container(height=12),
                    ft.Container(width=340,
                                 content=_field_wrap(ft.Icons.LOCK_OUTLINE_ROUNDED, pwd_f)),
                    ft.Container(height=14),
                    status,
                    ft.Container(height=10),
                    _grad_btn(T["sign_in"], _try_login),
                    ft.Container(height=12),
                    ft.Container(
                        on_click=lambda e: (
                            root.controls.__setitem__(1, _forgot_view(step=1))
                            or page.update()
                        ),
                        content=ft.Text(T["forgot"], size=13,
                                        color=C["accent"], text_align="center"),
                    ),
                    ft.Container(height=16),
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                        ft.Text(T["no_account"], size=13, color=C["text_dim"]),
                        ft.Container(
                            on_click=lambda e: _rebuild("register"),
                            content=ft.Text(T["register"], size=13, color=C["accent"],
                                            weight="bold"),
                        ),
                    ]),
                    ft.Container(height=16),
                    ft.Text(T["version"], size=11, color=C["text_muted"]),
                    ft.Container(height=24),
                ],
            ),
        )

    # ── REGISTER ──────────────────────────────────────────────────────────────
    def _register_view() -> ft.Container:
        C = state.C
        T = state.T
        login_f  = _text_field(T["login_hint"])
        pwd_f    = _text_field(T["password_hint"], hide=True)
        pwd2_f   = _text_field(T["password_hint"] + " ещё раз", hide=True)
        ans_f    = _text_field(T["sec_answer_lbl"])
        status   = ft.Text("", color=C["error"], size=12, text_align="center")

        q_options = [ft.dropdown.Option(key=q, text=q) for q in T["sec_questions"]]
        q_dropdown = ft.Dropdown(
            value=T["sec_questions"][0],
            options=q_options,
            bgcolor=C["surface2"],
            border_color=C["border"],
            focused_border_color=C["accent"],
            color=C["text"],
            text_size=13,
            border_radius=12,
        )

        def _try_register(e=None):
            u   = (login_f.value or "").strip()
            p   = (pwd_f.value   or "").strip()
            p2  = (pwd2_f.value  or "").strip()
            q   = q_dropdown.value or ""
            ans = (ans_f.value   or "").strip()
            if not u or not p:
                status.value = T["err_empty"]; page.update(); return
            if p != p2:
                status.value = "Пароли не совпадают"; page.update(); return
            if not ans:
                status.value = T["sec_answer_lbl"] + "?"; page.update(); return
            ok, err = db_register(u, p, q, ans)
            if not ok:
                status.value = err; page.update(); return
            uid = db_login(u, p)
            state.logged_in = True
            state.user_id   = uid
            state.username  = u
            state.history.clear()
            _chat_messages.controls.clear()
            _welcome_shown[0] = True
            state.current_chat_id = db_new_chat(uid)
            _rebuild("chat")

        login_f.on_submit = _try_register
        pwd2_f.on_submit  = _try_register
        ans_f.on_submit   = _try_register

        return ft.Container(
            expand=True, bgcolor=C["bg"],
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO, spacing=0,
                controls=[
                    ft.Container(height=32),
                    _logo(),
                    ft.Container(height=14),
                    ft.Text(T["reg_title"], size=26, weight="bold", color=C["text"]),
                    ft.Container(height=4),
                    ft.Text(T["reg_sub"], size=14, color=C["text_dim"]),
                    ft.Container(height=24),
                    ft.Container(width=340,
                                 content=_field_wrap(ft.Icons.PERSON_OUTLINE_ROUNDED, login_f)),
                    ft.Container(height=10),
                    ft.Container(width=340,
                                 content=_field_wrap(ft.Icons.LOCK_OUTLINE_ROUNDED, pwd_f)),
                    ft.Container(height=10),
                    ft.Container(width=340,
                                 content=_field_wrap(ft.Icons.LOCK_ROUNDED, pwd2_f)),
                    ft.Container(height=14),
                    ft.Container(
                        width=340,
                        content=ft.Column(spacing=6, controls=[
                            ft.Text(T["sec_question_lbl"], size=12,
                                    color=C["text_dim"], weight="bold"),
                            ft.Container(
                                border_radius=12,
                                bgcolor=C["surface2"],
                                border=ft.Border.all(1, C["border"]),
                                padding=ft.Padding(left=12, top=4, right=12, bottom=4),
                                content=q_dropdown,
                            ),
                        ]),
                    ),
                    ft.Container(height=10),
                    ft.Container(width=340,
                                 content=_field_wrap(ft.Icons.QUESTION_ANSWER_OUTLINED, ans_f)),
                    ft.Container(height=14),
                    status,
                    ft.Container(height=8),
                    _grad_btn(T["reg_btn"], _try_register),
                    ft.Container(height=20),
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                        ft.Text(T["has_account"], size=13, color=C["text_dim"]),
                        ft.Container(
                            on_click=lambda e: _rebuild("login"),
                            content=ft.Text(T["back_login"], size=13,
                                            color=C["accent"], weight="bold"),
                        ),
                    ]),
                    ft.Container(height=24),
                ],
            ),
        )

    # ── FORGOT PASSWORD (3 шага) ──────────────────────────────────────────────
    def _forgot_view(step: int = 1, username: str = "",
                     question: str = "") -> ft.Container:
        C = state.C
        T = state.T
        status = ft.Text("", color=C["error"], size=12, text_align="center")

        # ── Шаг 1: ввод логина ────────────────────────────────────────────
        if step == 1:
            login_f = _text_field(T["login_hint"])

            def _next1(e=None):
                u = (login_f.value or "").strip()
                if not u:
                    status.value = T["forgot_err_user"]
                    page.update(); return
                q = db_get_security_question(u)
                if q is None:
                    status.value = T["forgot_err_user"]
                    page.update(); return
                if not q:
                    status.value = T["forgot_err_no_q"]
                    page.update(); return
                root.controls[1] = _forgot_view(step=2, username=u, question=q)
                page.update()

            login_f.on_submit = _next1
            body = [
                ft.Text(T["forgot_step1"], size=14, color=C["text_dim"]),
                ft.Container(height=20),
                ft.Container(width=340,
                             content=_field_wrap(ft.Icons.PERSON_OUTLINE_ROUNDED, login_f)),
                ft.Container(height=14),
                status,
                ft.Container(height=8),
                _grad_btn(T["forgot_next"], _next1),
            ]

        # ── Шаг 2: секретный вопрос ───────────────────────────────────────
        elif step == 2:
            ans_f = _text_field(T["sec_answer_lbl"])

            def _next2(e=None):
                ans = (ans_f.value or "").strip()
                if not db_verify_security_answer(username, ans):
                    status.value = T["forgot_err_ans"]
                    page.update(); return
                root.controls[1] = _forgot_view(step=3, username=username)
                page.update()

            ans_f.on_submit = _next2
            body = [
                ft.Text(T["forgot_step2"], size=14, color=C["text_dim"]),
                ft.Container(height=16),
                ft.Container(
                    width=340,
                    padding=ft.Padding(left=14, top=12, right=14, bottom=12),
                    border_radius=12,
                    bgcolor=C["surface2"],
                    border=ft.Border.all(1, C["accent"] + "55"),
                    content=ft.Row(spacing=10, controls=[
                        ft.Icon(ft.Icons.HELP_OUTLINE_ROUNDED,
                                size=16, color=C["accent"]),
                        ft.Text(question, size=13, color=C["text"],
                                expand=True, weight="bold"),
                    ]),
                ),
                ft.Container(height=10),
                ft.Container(width=340,
                             content=_field_wrap(ft.Icons.QUESTION_ANSWER_OUTLINED, ans_f)),
                ft.Container(height=14),
                status,
                ft.Container(height=8),
                _grad_btn(T["forgot_next"], _next2),
            ]

        # ── Шаг 3: новый пароль ───────────────────────────────────────────
        else:
            pwd_f  = _text_field(T["password_hint"], hide=True)
            pwd2_f = _text_field(T["password_hint"] + " ещё раз", hide=True)

            def _reset(e=None):
                p  = (pwd_f.value  or "").strip()
                p2 = (pwd2_f.value or "").strip()
                if len(p) < 4:
                    status.value = T["forgot_err_pwd"]
                    page.update(); return
                if p != p2:
                    status.value = "Пароли не совпадают"
                    page.update(); return
                db_reset_password(username, p)
                show_toast(T["forgot_done"])
                _rebuild("login")

            pwd_f.on_submit  = _reset
            pwd2_f.on_submit = _reset
            body = [
                ft.Text(T["forgot_step3"], size=14, color=C["text_dim"]),
                ft.Container(height=20),
                ft.Container(width=340,
                             content=_field_wrap(ft.Icons.LOCK_OUTLINE_ROUNDED, pwd_f)),
                ft.Container(height=10),
                ft.Container(width=340,
                             content=_field_wrap(ft.Icons.LOCK_ROUNDED, pwd2_f)),
                ft.Container(height=14),
                status,
                ft.Container(height=8),
                _grad_btn(T["forgot_reset"], _reset),
            ]

        def _back(e=None):
            if step == 1:
                _rebuild("login")
            elif step == 2:
                root.controls[1] = _forgot_view(step=1)
                page.update()
            else:
                root.controls[1] = _forgot_view(step=2,
                                                  username=username, question=question)
                page.update()

        # Индикатор шагов
        def _step_dot(n):
            active = n == step
            return ft.Container(
                width=8 if not active else 24,
                height=8, border_radius=4,
                bgcolor=C["accent"] if active else C["border"],
                animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
            )

        return ft.Container(
            expand=True, bgcolor=C["bg"],
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO, spacing=0,
                controls=[
                    ft.Container(height=40),
                    ft.Container(
                        width=56, height=56, border_radius=16,
                        gradient=ft.LinearGradient(begin=_TL, end=_BR,
                                                   colors=[C["accent"], C["accent2"]]),
                        alignment=_C,
                        content=ft.Icon(ft.Icons.LOCK_RESET_ROUNDED,
                                        size=28, color="white"),
                    ),
                    ft.Container(height=16),
                    ft.Text(T["forgot_title"], size=24, weight="bold", color=C["text"]),
                    ft.Container(height=10),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER, spacing=6,
                        controls=[_step_dot(1), _step_dot(2), _step_dot(3)],
                    ),
                    ft.Container(height=24),
                    *body,
                    ft.Container(height=20),
                    ft.Container(
                        on_click=_back,
                        content=ft.Text(T["forgot_back"], size=13,
                                        color=C["accent"], weight="bold"),
                    ),
                    ft.Container(height=24),
                ],
            ),
        )

    # ── CHAT ──────────────────────────────────────────────────────────────────
    _chat_messages  = ft.ListView(
        expand=True, spacing=4, auto_scroll=True,
        padding=ft.Padding(left=4, top=12, right=4, bottom=8),
    )
    _welcome_shown  = [True]
    _pending_file: list = [None]

    def _chat_view() -> ft.Container:
        C = state.C
        T = state.T

        prompt = ft.TextField(
            hint_text=T["chat_hint"],
            hint_style=ft.TextStyle(color=C["text_muted"], size=14),
            border=ft.InputBorder.NONE, bgcolor="transparent",
            color=C["text"], cursor_color=C["accent"],
            content_padding=ft.Padding(left=14, top=12, right=14, bottom=12),
            text_size=14, expand=True,
        )

        file_badge = ft.Container(
            visible=False,
            padding=ft.Padding(left=14, top=6, right=14, bottom=0),
            content=ft.Row(spacing=6, controls=[
                ft.Icon(ft.Icons.ATTACH_FILE_ROUNDED, size=13, color=C["accent"]),
                ft.Text("", size=12, color=C["accent"]),
                ft.Container(
                    on_click=lambda e: _clear_file(),
                    content=ft.Icon(ft.Icons.CLOSE_ROUNDED, size=13, color=C["text_dim"]),
                ),
            ]),
        )

        def _clear_file():
            _pending_file[0] = None
            file_badge.visible = False
            page.update()

        welcome_ctr = ft.Container(
            expand=True, alignment=_C,
            visible=_welcome_shown[0],
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER, spacing=8,
                controls=[
                    ft.Container(
                        width=64, height=64, border_radius=18,
                        gradient=ft.LinearGradient(begin=_TL, end=_BR,
                                                   colors=[C["accent"], C["accent2"]]),
                        alignment=_C,
                        content=ft.Icon(ft.Icons.AUTO_AWESOME, size=32, color="white"),
                    ),
                    ft.Container(height=6),
                    ft.Text(T["chat_ready"], size=18, weight="bold", color=C["text"]),
                    ft.Text(T["chat_sub"],   size=13, color=C["text_dim"]),
                ],
            ),
        )

        # Кнопка "Новый чат"
        new_chat_btn = ft.Container(
            padding=ft.Padding(left=16, top=10, right=16, bottom=4),
            content=ft.Container(
                height=36, border_radius=10,
                border=ft.Border.all(1, C["border"]),
                bgcolor=C["surface2"],
                on_click=lambda e: _new_chat(),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER, spacing=6,
                    controls=[
                        ft.Icon(ft.Icons.ADD_ROUNDED, size=16, color=C["accent"]),
                        ft.Text(T["new_chat"], size=13, color=C["accent"]),
                    ],
                ),
            ),
        )

        def _new_chat():
            state.current_chat_id = db_new_chat(state.user_id)
            state.history.clear()
            _chat_messages.controls.clear()
            _welcome_shown[0] = True
            welcome_ctr.visible = True
            page.update()

        async def _send(e=None) -> None:
            text = (prompt.value or "").strip()
            file = _pending_file[0]
            if not text and not file:
                return

            prompt.value = ""
            if _welcome_shown[0]:
                _welcome_shown[0]   = False
                welcome_ctr.visible = False

            groq_text = text
            if file:
                groq_text = (
                    f"{text}\n\n[Файл: {file['name']}]\n```\n{file['content']}\n```"
                    if text else
                    f"[Файл: {file['name']}]\n```\n{file['content']}\n```"
                )
                _pending_file[0] = None
                file_badge.visible = False

            page.update()

            if file:
                _chat_messages.controls.append(_file_bubble(file["name"], True))
                page.update()

            if text:
                bbl_u = ChatBubble(T["you"], True)
                _chat_messages.controls.append(bbl_u)
                buf: list[str] = []
                for ch in text:
                    buf.append(ch)
                    bbl_u.txt.value = "".join(buf)
                    page.update()
                    await asyncio.sleep(0.004)

            loop   = asyncio.get_event_loop()
            answer = await loop.run_in_executor(None, groq_ask, groq_text)

            bbl_a = ChatBubble("Agora", False)
            _chat_messages.controls.append(bbl_a)
            buf2: list[str] = []
            for ch in answer:
                buf2.append(ch)
                bbl_a.txt.value = "".join(buf2)
                page.update()
                await asyncio.sleep(0.004)

        prompt.on_submit = lambda e: page.run_task(_send, e)

        async def _pick_file(e=None) -> None:
            picked = await file_picker.pick_files(
                dialog_title=T["attach"],
                allow_multiple=False, with_data=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=[
                    "txt","md","py","js","ts","json","csv",
                    "html","css","yaml","yml","xml","log",
                    "c","cpp","java","go","rs","swift",
                ],
            )
            if not picked:
                return
            pf = picked[0]
            fname = pf.name or "file"
            content = ""
            file_path = pf.path if pf.path else None
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, encoding="utf-8", errors="replace") as fh:
                        content = fh.read(8000)
                except Exception as err:
                    content = f"[ошибка: {err}]"
            elif pf.bytes:
                try:
                    content = pf.bytes.decode("utf-8", errors="replace")[:8000]
                except Exception as err:
                    content = f"[ошибка: {err}]"
            _pending_file[0] = {"name": fname, "content": content}
            file_badge.content.controls[1].value = fname
            file_badge.visible = True
            page.update()

        attach_btn = ft.Container(
            width=44, height=44, border_radius=12,
            bgcolor=C["surface2"], border=ft.Border.all(1, C["border"]),
            alignment=_C,
            on_click=lambda e: page.run_task(_pick_file),
            content=ft.Icon(ft.Icons.ATTACH_FILE_ROUNDED, size=20, color=C["accent"]),
        )
        send_btn = ft.Container(
            width=44, height=44, border_radius=12,
            gradient=ft.LinearGradient(begin=_TL, end=_BR,
                                       colors=[C["accent"], C["accent2"]]),
            shadow=ft.BoxShadow(blur_radius=12, color=C["accent"] + "55"),
            alignment=_C, on_click=lambda e: page.run_task(_send),
            content=ft.Icon(ft.Icons.SEND_ROUNDED, size=20, color="white"),
        )

        return ft.Container(
            expand=True, bgcolor=C["bg"],
            content=ft.Column(expand=True, spacing=0, controls=[
                new_chat_btn,
                ft.Stack(expand=True, controls=[_chat_messages, welcome_ctr]),
                ft.Container(
                    bgcolor=C["surface"],
                    border=ft.Border(top=ft.BorderSide(1, C["border"])),
                    content=ft.Column(spacing=0, controls=[
                        file_badge,
                        ft.Container(
                            padding=ft.Padding(left=10, top=6, right=10, bottom=10),
                            content=ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                                controls=[
                                    attach_btn,
                                    ft.Container(
                                        expand=True, height=52, border_radius=14,
                                        bgcolor=C["surface2"],
                                        border=ft.Border.all(1, C["border"]),
                                        content=prompt,
                                    ),
                                    send_btn,
                                ],
                            ),
                        ),
                    ]),
                ),
            ]),
        )

    # ── HISTORY ───────────────────────────────────────────────────────────────
    def _history_view() -> ft.Container:
        C = state.C
        T = state.T
        chats = db_user_chats(state.user_id)

        def _fmt_date(dt_str: str) -> str:
            try:
                dt = datetime.fromisoformat(dt_str)
                now = datetime.now()
                if dt.date() == now.date():
                    return dt.strftime("%H:%M")
                return dt.strftime("%d.%m.%y")
            except Exception:
                return ""

        def _open_chat(chat_id: int) -> None:
            # Загружаем сообщения из БД
            msgs = db_chat_msgs(chat_id)
            state.current_chat_id = chat_id
            state.history.clear()
            _chat_messages.controls.clear()
            _welcome_shown[0] = len(msgs) == 0
            for m in msgs:
                state.history.append({"role": m["role"], "content": m["content"]})
                is_user = m["role"] == "user"
                sender  = T["you"] if is_user else "Agora"
                bbl = ChatBubble(sender, is_user)
                bbl.txt.value = m["content"]
                _chat_messages.controls.append(bbl)
            # Переходим на вкладку чата
            root.controls[1] = _chat_view()
            root.controls[2] = _bottom_nav("chat")
            page.update()

        def _confirm_delete(chat_id: int) -> None:
            def _do_delete(e):
                db_delete_chat(chat_id)
                _del_dialog.open = False
                # Если удалили текущий чат — создаём новый
                if state.current_chat_id == chat_id:
                    state.current_chat_id = db_new_chat(state.user_id)
                    state.history.clear()
                    _chat_messages.controls.clear()
                    _welcome_shown[0] = True
                root.controls[1] = _history_view()
                page.update()

            def _cancel(e):
                _del_dialog.open = False
                page.update()

            _del_dialog.title   = ft.Text(T["del_title"],   color=C["text"])
            _del_dialog.content = ft.Text(T["del_confirm"], color=C["text_dim"])
            _del_dialog.bgcolor = C["surface"]
            _del_dialog.actions = [
                ft.Button(
                    content=ft.Text(T["del_no"], color=C["text_dim"]),
                    on_click=_cancel,
                ),
                ft.Button(
                    content=ft.Text(T["del_yes"], color=C["error"], weight="bold"),
                    on_click=_do_delete,
                ),
            ]
            _del_dialog.open = True
            page.update()

        def _chat_card(chat: dict) -> ft.Container:
            is_current = chat["id"] == state.current_chat_id
            brd_color  = C["accent"] if is_current else C["border"]
            return ft.Container(
                border_radius=12,
                bgcolor=C["surface"],
                border=ft.Border.all(1, brd_color),
                padding=ft.Padding(left=14, top=10, right=10, bottom=10),
                on_click=lambda e, cid=chat["id"]: _open_chat(cid),
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=36, height=36, border_radius=10,
                            bgcolor=C["icon_bg"], alignment=_C,
                            content=ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,
                                            size=16, color=C["accent"]),
                        ),
                        ft.Container(width=10),
                        ft.Column(
                            expand=True, spacing=2,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(chat["title"], size=13, weight="bold",
                                        color=C["text"],
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        max_lines=1),
                                ft.Text(
                                    f"{chat['msg_count']} {T['msg_count']}  •  "
                                    f"{_fmt_date(chat['created_at'])}",
                                    size=11, color=C["text_dim"],
                                ),
                            ],
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                            icon_size=18, icon_color=C["text_muted"],
                            on_click=lambda e, cid=chat["id"]: _confirm_delete(cid),
                        ),
                    ],
                ),
            )

        cards = [_chat_card(c) for c in chats] if chats else [
            ft.Container(
                height=200, alignment=_C,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER, spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.HISTORY_ROUNDED,
                                size=48, color=C["text_muted"]),
                        ft.Text(T["history_empty"], size=14, color=C["text_dim"]),
                    ],
                ),
            )
        ]

        return ft.Container(
            expand=True, bgcolor=C["bg"],
            content=ft.Column(spacing=0, expand=True, controls=[
                ft.Container(
                    padding=ft.Padding(left=20, top=20, right=20, bottom=12),
                    content=ft.Text(T["history_title"], size=22,
                                    weight="bold", color=C["text"]),
                ),
                ft.Container(
                    expand=True,
                    content=ft.ListView(
                        expand=True, spacing=8,
                        padding=ft.Padding(left=14, top=0, right=14, bottom=20),
                        controls=cards,
                    ),
                ),
            ]),
        )

    # ── SETTINGS ──────────────────────────────────────────────────────────────
    def _settings_view() -> ft.Container:
        C = state.C
        T = state.T

        def _row(icon, title, subtitle,
                 toggle=False, toggle_val=False,
                 on_toggle=None, on_tap=None,
                 right_text="") -> ft.Container:
            if toggle:
                right = ft.Switch(
                    value=toggle_val, active_color=C["accent"],
                    inactive_thumb_color=C["text_dim"],
                    inactive_track_color=C["border"],
                    on_change=on_toggle,
                )
            elif right_text:
                right = ft.Text(right_text, size=12, color=C["text_dim"])
            else:
                right = ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                size=18, color=C["text_dim"])
            return ft.Container(
                height=64, border_radius=12,
                bgcolor=C["surface"], border=ft.Border.all(1, C["border"]),
                padding=ft.Padding(left=14, top=0, right=14, bottom=0),
                on_click=on_tap,
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=36, height=36, border_radius=9,
                            bgcolor=C["icon_bg"], alignment=_C,
                            content=ft.Icon(icon, size=17, color=C["accent"]),
                        ),
                        ft.Container(width=12),
                        ft.Column(
                            expand=True, spacing=2,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(title,    size=14,
                                        weight="bold", color=C["text"]),
                                ft.Text(subtitle, size=11, color=C["text_dim"]),
                            ],
                        ),
                        right,
                    ],
                ),
            )

        def _on_dark(e):
            state.dark = e.control.value
            _rebuild("settings")

        def _on_lang(e=None):
            state.lang = "en" if state.lang == "ru" else "ru"
            _rebuild("settings")

        lang_label = "🇷🇺 Русский" if state.lang == "ru" else "🇺🇸 English"

        return ft.Container(
            expand=True, bgcolor=C["bg"],
            content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, controls=[
                ft.Container(height=24),
                ft.Container(
                    padding=ft.Padding(left=20, top=0, right=0, bottom=4),
                    content=ft.Text(T["settings_title"], size=24,
                                    weight="bold", color=C["text"]),
                ),
                ft.Container(height=16),
                ft.Container(
                    padding=ft.Padding(left=14, top=0, right=14, bottom=0),
                    content=ft.Column(spacing=8, controls=[
                        _row(ft.Icons.PERSON_OUTLINE_ROUNDED,
                             T["account"], f"@{state.username}",
                             right_text=""),
                        _row(ft.Icons.DARK_MODE_OUTLINED,
                             T["dark_theme"], T["dark_sub"],
                             toggle=True, toggle_val=state.dark, on_toggle=_on_dark),
                        _row(ft.Icons.NOTIFICATIONS_OUTLINED,
                             T["notifications"], T["notif_sub"],
                             toggle=True, toggle_val=False),
                        _row(ft.Icons.LANGUAGE_ROUNDED,
                             T["language"], lang_label, on_tap=_on_lang),
                    ]),
                ),
                ft.Container(height=20),
                ft.Container(
                    padding=ft.Padding(left=14, top=0, right=14, bottom=30),
                    content=ft.Container(
                        height=52, border_radius=12,
                        bgcolor=C["logout_bg"],
                        border=ft.Border.all(1, C["logout_brd"]),
                        alignment=_C,
                        on_click=lambda e: _do_logout(),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER, spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.LOGOUT_ROUNDED,
                                        size=18, color=C["error"]),
                                ft.Text(T["logout"], size=14,
                                        weight="bold", color=C["error"]),
                            ],
                        ),
                    ),
                ),
            ]),
        )

    # ── Logout ────────────────────────────────────────────────────────────────
    def _do_logout() -> None:
        state.logged_in       = False
        state.user_id         = None
        state.username        = ""
        state.current_chat_id = None
        state.history.clear()
        _chat_messages.controls.clear()
        _welcome_shown[0] = True
        _pending_file[0]  = None
        _rebuild("login")
        show_toast(state.T["logged_out"])

    # ── Старт ─────────────────────────────────────────────────────────────────
    _apply_theme()
    _rebuild("login")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    db_init()
    ft.run(main)

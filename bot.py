import os
import json
from datetime import date, timedelta

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# Храним data.json рядом с bot.py (абсолютный путь — меньше проблем)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")


# ---------- JSON storage ----------
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"users": {}}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(data: dict, chat_id: int) -> dict:
    users = data.setdefault("users", {})
    return users.setdefault(str(chat_id), {"habits": {}})


# ---------- helpers ----------
def norm(text: str) -> str:
    return " ".join(text.strip().lower().split())


def today_str() -> str:
    return date.today().isoformat()


def last_7_days_window() -> set[str]:
    end = date.today()
    start = end - timedelta(days=6)
    return {(start + timedelta(days=i)).isoformat() for i in range(7)}


# ---------- core actions ----------
def add_habit_for_user(chat_id: int, habit_name: str) -> tuple[bool, str]:
    """Return (created_new, message)."""
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if habit_name in habits:
        return False, f"Привычка уже есть: «{habit_name}»"

    habits[habit_name] = {"created": today_str(), "done_dates": []}
    save_data(data)
    return True, f"Добавил привычку: «{habit_name}» ✅"


def mark_done_for_user(chat_id: int, habit_name: str) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if habit_name not in habits:
        return f"Не нашёл привычку «{habit_name}». Напиши её текстом — я добавлю 🙂"

    t = today_str()
    done_dates = habits[habit_name].setdefault("done_dates", [])
    if t in done_dates:
        return f"Уже отмечено сегодня: «{habit_name}» ✅"
    done_dates.append(t)
    save_data(data)
    return f"Отметил выполненной сегодня: «{habit_name}» 🔥"


def remove_habit_for_user(chat_id: int, habit_name: str) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if habit_name not in habits:
        return f"Нет такой привычки: «{habit_name}»"

    del habits[habit_name]
    save_data(data)
    return f"Удалил привычку: «{habit_name}» 🗑️"


def list_habits_for_user(chat_id: int) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if not habits:
        return "Пока нет привычек. Просто напиши название привычки текстом (например: «зарядка 20мин»)."

    lines = ["📋 Твои привычки:"]
    for h, info in habits.items():
        done_count = len(info.get("done_dates", []))
        lines.append(f"• {h} — выполнено: {done_count} раз(а)")
    lines.append("\nЧтобы отметить выполнение: просто напиши название привычки ещё раз ✅")
    return "\n".join(lines)


def stats_for_user(chat_id: int) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if not habits:
        return "Пока нет привычек. Добавь — просто напиши текстом (например: «читать 20 минут»)."

    window = last_7_days_window()
    end = date.today()
    start = end - timedelta(days=6)

    lines = [f"📊 Статистика за 7 дней ({start.isoformat()} — {end.isoformat()}):"]
    for h, info in habits.items():
        done_dates = set(info.get("done_dates", []))
        count_7 = len(done_dates & window)
        lines.append(f"• {h}: {count_7}/7")
    lines.append("\nПодсказка: чтобы отметить выполнение — просто напиши привычку текстом.")
    return "\n".join(lines)


# ---------- bot handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я StreakBuddy 😊\n\n"
        "Как пользоваться (без команд):\n"
        "1) Напиши привычку текстом: «зарядка 20мин» → я добавлю\n"
        "2) Напиши эту же привычку ещё раз → отмечу выполненной сегодня ✅\n\n"
        "Полезные слова:\n"
        "• «список» — покажу привычки\n"
        "• «стат» или «статистика» — покажу прогресс\n"
        "• «удалить <привычка>» — удалю\n"
        "• «сделал <привычка>» — отметить явно\n"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (update.message.text or "").strip()
    if not msg:
        return

    chat_id = update.effective_chat.id
    text = norm(msg)

    # ---- "служебные" слова без слешей ----
    if text in {"список", "лист", "list"}:
        await update.message.reply_text(list_habits_for_user(chat_id))
        return

    if text in {"стат", "статы", "статистика", "stats"}:
        await update.message.reply_text(stats_for_user(chat_id))
        return

    # ---- явные действия по ключевым словам ----
    if text.startswith("удалить "):
        habit_name = norm(msg[len("удалить "):])
        if not habit_name:
            await update.message.reply_text("Напиши так: удалить <название привычки>")
            return
        await update.message.reply_text(remove_habit_for_user(chat_id, habit_name))
        return

    if text.startswith("сделал ") or text.startswith("готово "):
        prefix = "сделал " if text.startswith("сделал ") else "готово "
        habit_name = norm(msg[len(prefix):])
        if not habit_name:
            await update.message.reply_text("Напиши так: сделал <название привычки>")
            return
        await update.message.reply_text(mark_done_for_user(chat_id, habit_name))
        return

    # ---- умная логика по умолчанию (главное) ----
    # Если привычка уже существует -> отметить выполненной сегодня
    # Если нет -> добавить как новую
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    habit_name = norm(msg)

    if habit_name in habits:
        await update.message.reply_text(mark_done_for_user(chat_id, habit_name))
    else:
        created, message = add_habit_for_user(chat_id, habit_name)
        await update.message.reply_text(message)


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не найден BOT_TOKEN. Проверь .env рядом с bot.py")

    app = Application.builder().token(token).build()

    # команды можно не использовать, но пусть будут
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # весь смысл: текст без команд
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()

import os
import json
import re
from datetime import date, timedelta, time

from dotenv import load_dotenv
from zoneinfo import ZoneInfo

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# Кыргызстан
TZ = ZoneInfo("Asia/Bishkek")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")


# ---------- storage ----------
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
    # reminders: { "<habit_name>": "HH:MM" }
    return users.setdefault(str(chat_id), {"habits": {}, "reminders": {}})


# ---------- helpers ----------
def norm(text: str) -> str:
    return " ".join(text.strip().lower().split())


def today_str() -> str:
    return date.today().isoformat()


def last_7_days_window() -> set[str]:
    end = date.today()
    start = end - timedelta(days=6)
    return {(start + timedelta(days=i)).isoformat() for i in range(7)}


def make_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton("✅ Отметить"), KeyboardButton("➕ Добавить")],
        [KeyboardButton("📋 Список"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("⏰ Напоминания"), KeyboardButton("🗑️ Удалить")],
        [KeyboardButton("❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def compute_streak(done_dates: list[str]) -> int:
    s = set(done_dates)
    streak = 0
    d = date.today()
    while d.isoformat() in s:
        streak += 1
        d = d - timedelta(days=1)
    return streak


def parse_hhmm(hhmm: str) -> time | None:
    m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", hhmm.strip())
    if not m:
        return None
    h = int(m.group(1))
    mi = int(m.group(2))
    return time(hour=h, minute=mi, tzinfo=TZ)


# ---------- reminders scheduling ----------
def _job_name(chat_id: int, habit_name: str) -> str:
    return f"reminder:{chat_id}:{habit_name}"


async def reminder_job_callback(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    habit_name = job.data["habit_name"]
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"⏰ Напоминание: {habit_name}\n"
            f"Чтобы отметить выполнение — просто напиши:\n{habit_name}"
        ),
        reply_markup=make_keyboard(),
    )


def schedule_reminder(app: Application, chat_id: int, habit_name: str, hhmm: str) -> tuple[bool, str]:
    t = parse_hhmm(hhmm)
    if t is None:
        return False, "Неверное время. Формат должен быть HH:MM (например 08:30)."

    name = _job_name(chat_id, habit_name)

    # убрать старые джобы с таким именем
    for j in app.job_queue.get_jobs_by_name(name):
        j.schedule_removal()

    app.job_queue.run_daily(
        reminder_job_callback,
        time=t,
        chat_id=chat_id,
        name=name,
        data={"habit_name": habit_name},
    )
    return True, f"Готово ✅ Буду напоминать про «{habit_name}» каждый день в {hhmm} (Кыргызстан)."


def unschedule_reminder(app: Application, chat_id: int, habit_name: str) -> bool:
    name = _job_name(chat_id, habit_name)
    jobs = app.job_queue.get_jobs_by_name(name)
    for j in jobs:
        j.schedule_removal()
    return len(jobs) > 0


def restore_all_reminders(app: Application) -> None:
    data = load_data()
    users = data.get("users", {})
    for chat_id_str, user in users.items():
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            continue
        reminders = user.get("reminders", {})
        for habit_name, hhmm in reminders.items():
            # молча рескейджим
            schedule_reminder(app, chat_id, habit_name, hhmm)


# ---------- core actions ----------
def add_habit(chat_id: int, habit_name: str) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if habit_name in habits:
        return f"Уже есть: «{habit_name}»"

    habits[habit_name] = {"created": today_str(), "done_dates": []}
    save_data(data)
    return f"Добавил: «{habit_name}» ✅"


def remove_habit(chat_id: int, habit_name: str) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]
    reminders = user.get("reminders", {})

    if habit_name not in habits:
        return f"Нет такой привычки: «{habit_name}»"

    del habits[habit_name]
    reminders.pop(habit_name, None)
    save_data(data)
    return f"Удалил: «{habit_name}» 🗑️"


def mark_done(chat_id: int, habit_name: str) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if habit_name not in habits:
        habits[habit_name] = {"created": today_str(), "done_dates": []}

    t = today_str()
    done_dates = habits[habit_name].setdefault("done_dates", [])

    if t in done_dates:
        streak = compute_streak(done_dates)
        return f"Уже отмечено сегодня: «{habit_name}» ✅\n🔥 Стрик: {streak} дн."

    done_dates.append(t)
    save_data(data)
    streak = compute_streak(done_dates)
    return f"Отмечено сегодня: «{habit_name}» ✅\n🔥 Стрик: {streak} дн."


def list_habits(chat_id: int) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if not habits:
        return "Пока нет привычек. Просто напиши привычку текстом (например: «зарядка 20мин»)."

    lines = ["📋 Твои привычки:"]
    for h, info in habits.items():
        done_dates = info.get("done_dates", [])
        streak = compute_streak(done_dates)
        done_total = len(done_dates)
        lines.append(f"• {h} — 🔥 {streak} дн. подряд — всего: {done_total}")
    lines.append("\nЧтобы отметить — просто напиши название привычки.")
    return "\n".join(lines)


def stats(chat_id: int) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]

    if not habits:
        return "Пока нет привычек. Добавь — просто напиши текстом (например: «читать 20 минут»)."

    window = last_7_days_window()
    end = date.today()
    start = end - timedelta(days=6)

    lines = [f"📊 За 7 дней ({start.isoformat()} — {end.isoformat()}):"]
    for h, info in habits.items():
        done_dates = set(info.get("done_dates", []))
        count_7 = len(done_dates & window)
        streak = compute_streak(list(done_dates))
        lines.append(f"• {h}: {count_7}/7  |  🔥 стрик: {streak}")
    return "\n".join(lines)


def reminders_text(chat_id: int) -> str:
    data = load_data()
    user = get_user(data, chat_id)
    rem = user.get("reminders", {})

    if not rem:
        return (
            "⏰ Напоминаний пока нет.\n\n"
            "Как поставить:\n"
            "напоминать <привычка> в HH:MM\n"
            "Пример:\n"
            "напоминать зарядка 20мин в 08:30"
        )

    lines = ["⏰ Твои напоминания:"]
    for habit_name, hhmm in rem.items():
        lines.append(f"• {habit_name} — {hhmm} (Кыргызстан)")
    lines.append("\nЧтобы убрать: не напоминать <привычка>")
    return "\n".join(lines)


# ---------- bot handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Я StreakBuddy 😊\n\n"
        "Без команд:\n"
        "• Напиши привычку — добавлю\n"
        "• Напиши её ещё раз — отмечу выполненной ✅\n\n"
        "Напоминания (Кыргызстан):\n"
        "напоминать зарядка 20мин в 08:30",
        reply_markup=make_keyboard(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Кнопки:\n"
        "➕ Добавить — введи привычку\n"
        "✅ Отметить — введи привычку\n"
        "⏰ Напоминания — список/инструкция\n\n"
        "Текстом (без слешей):\n"
        "• напоминать <привычка> в HH:MM\n"
        "• не напоминать <привычка>\n"
        "• список / статистика / напоминания\n\n"
        "Фишка: если просто пишешь «зарядка 20мин»,\n"
        "бот сам решит: если нет — добавит, если есть — отметит ✅",
        reply_markup=make_keyboard(),
    )


async def post_init(app: Application):
    # при старте восстанавливаем напоминания из data.json
    restore_all_reminders(app)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip()
    if not raw:
        return

    chat_id = update.effective_chat.id
    text = norm(raw)

    # --- кнопки/слова ---
    if text in {"❓ помощь", "помощь", "help"}:
        await help_cmd(update, context)
        return

    if text in {"📋 список", "список", "лист", "list"}:
        await update.message.reply_text(list_habits(chat_id), reply_markup=make_keyboard())
        return

    if text in {"📊 статистика", "статистика", "стат", "stats"}:
        await update.message.reply_text(stats(chat_id), reply_markup=make_keyboard())
        return

    if text in {"⏰ напоминания", "напоминания", "напоминание"}:
        await update.message.reply_text(reminders_text(chat_id), reply_markup=make_keyboard())
        return

    if text in {"➕ добавить", "добавить"}:
        context.user_data["mode"] = "add"
        await update.message.reply_text("Введи название привычки 🙂", reply_markup=make_keyboard())
        return

    if text in {"✅ отметить", "отметить"}:
        context.user_data["mode"] = "done"
        await update.message.reply_text("Что отметить? Введи привычку 🙂", reply_markup=make_keyboard())
        return

    if text in {"🗑️ удалить", "удалить"}:
        context.user_data["mode"] = "remove"
        await update.message.reply_text("Что удалить? Введи привычку 🙂", reply_markup=make_keyboard())
        return

    # --- режимы после кнопок ---
    mode = context.user_data.get("mode")
    if mode == "add":
        context.user_data["mode"] = None
        habit_name = norm(raw)
        await update.message.reply_text(add_habit(chat_id, habit_name), reply_markup=make_keyboard())
        return

    if mode == "done":
        context.user_data["mode"] = None
        habit_name = norm(raw)
        await update.message.reply_text(mark_done(chat_id, habit_name), reply_markup=make_keyboard())
        return

    if mode == "remove":
        context.user_data["mode"] = None
        habit_name = norm(raw)
        await update.message.reply_text(remove_habit(chat_id, habit_name), reply_markup=make_keyboard())
        return

    # --- парсинг напоминаний ---
    # "напоминать <привычка> в HH:MM"
    m = re.match(r"^\s*напоминать\s+(.+?)\s+в\s+(\d{1,2}:\d{2})\s*$", raw, flags=re.IGNORECASE)
    if m:
        habit_name = norm(m.group(1))
        hhmm = m.group(2)

        data = load_data()
        user = get_user(data, chat_id)

        ok, msg = schedule_reminder(context.application, chat_id, habit_name, hhmm)
        if ok:
            user.setdefault("reminders", {})[habit_name] = hhmm
            save_data(data)
        await update.message.reply_text(msg, reply_markup=make_keyboard())
        return

    # "не напоминать <привычка>"
    m = re.match(r"^\s*(не\s+напоминать|стоп\s+напоминать)\s+(.+)\s*$", raw, flags=re.IGNORECASE)
    if m:
        habit_name = norm(m.group(2))

        data = load_data()
        user = get_user(data, chat_id)
        user.setdefault("reminders", {}).pop(habit_name, None)
        save_data(data)

        removed = unschedule_reminder(context.application, chat_id, habit_name)
        if removed:
            await update.message.reply_text(f"Ок ✅ Больше не напоминаю про «{habit_name}».", reply_markup=make_keyboard())
        else:
            await update.message.reply_text(f"Напоминаний для «{habit_name}» не было.", reply_markup=make_keyboard())
        return

    # --- поведение по умолчанию ---
    data = load_data()
    user = get_user(data, chat_id)
    habits = user["habits"]
    habit_name = norm(raw)

    if habit_name in habits:
        await update.message.reply_text(mark_done(chat_id, habit_name), reply_markup=make_keyboard())
    else:
        await update.message.reply_text(add_habit(chat_id, habit_name), reply_markup=make_keyboard())


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не найден BOT_TOKEN. Проверь .env рядом с bot.py")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()

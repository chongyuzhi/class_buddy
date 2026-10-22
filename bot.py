"""
ClassBuddy Bot — Telegram timetable assistant
No LLM API required.

Python: 3.10+
Install: pip install "python-telegram-bot>=21,<23"
Run:
  Windows PowerShell: $env:TELEGRAM_BOT_TOKEN="YOUR_TOKEN"; python bot.py
  macOS/Linux:        export TELEGRAM_BOT_TOKEN="YOUR_TOKEN" && python bot.py
"""

import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")

# Schedule extracted from the uploaded image.
# Room numbers were not reliably readable, so the bot does not invent them.
# Times use 24-hour format. End time is exclusive: at the exact end time,
# the class is considered finished.
SCHEDULE = {
    "Monday": [
        (7 * 60 + 30, 8 * 60 + 30, "Perhimpunan", "Assembly"),
        (8 * 60 + 30, 9 * 60, "Rehat", "Break"),
        (9 * 60, 10 * 60, "Gantian / Ujian", "Replacement class / Test (as shown on timetable)"),
        (10 * 60, 12 * 60, "English Language Proficiency (MPU6122)", "English Language Proficiency (MPU6122)"),
        (13 * 60, 14 * 60, "Rehat", "Break"),
        (16 * 60, 17 * 60, "Sejarah Lisan dan Pendokumentasian (SJHK6023)", "Oral History and Documentation (SJHK6023)"),
    ],
    "Tuesday": [
        (7 * 60 + 30, 9 * 60 + 30, "Teknologi untuk Pengajaran dan Pembelajaran (EDUP6023)", "Technology for Teaching and Learning (EDUP6023)"),
        (9 * 60 + 30, 10 * 60, "Rehat", "Break"),
        (11 * 60, 13 * 60, "Sejarah Lisan dan Pendokumentasian (SJHK6023)", "Oral History and Documentation (SJHK6023)"),
        (13 * 60, 14 * 60, "Rehat", "Break"),
        (16 * 60, 17 * 60, "Perkembangan Perlembagaan Persekutuan Malaysia (SJHK6033)", "Development of the Federal Constitution of Malaysia (SJHK6033)"),
    ],
    "Wednesday": [
        (7 * 60 + 30, 9 * 60 + 30, "Pensejarahan Malaysia (SJHK6013)", "Malaysian Historiography (SJHK6013)"),
        (9 * 60 + 30, 10 * 60, "Rehat", "Break"),
        (10 * 60, 12 * 60, "Perkembangan Perlembagaan Persekutuan Malaysia (SJHK6033)", "Development of the Federal Constitution of Malaysia (SJHK6033)"),
        (12 * 60, 13 * 60, "Sejarah Pendidikan di Malaysia (EDUP6013)", "History of Education in Malaysia (EDUP6013)"),
        (13 * 60, 14 * 60, "Rehat", "Break"),
        (16 * 60, 17 * 60, "Mentor", "Mentor session"),
    ],
    "Thursday": [
        (7 * 60 + 30, 9 * 60 + 30, "GFEPS (kod/nama seperti dalam jadual)", "GFEPS (course name as shown on timetable)"),
        (9 * 60 + 30, 10 * 60, "Rehat", "Break"),
        (13 * 60, 14 * 60, "Rehat", "Break"),
    ],
    "Friday": [
        (7 * 60, 8 * 60, "Insaniah", "Insaniah"),
        (8 * 60, 8 * 60 + 30, "Rehat", "Break"),
        (8 * 60 + 30, 10 * 60 + 30, "Sejarah Pendidikan di Malaysia (EDUP6013)", "History of Education in Malaysia (EDUP6013)"),
        (10 * 60 + 30, 11 * 60 + 30, "Pensejarahan Malaysia (SJHK6013)", "Malaysian Historiography (SJHK6013)"),
        (11 * 60 + 30, 13 * 60, "Rehat", "Break"),
        (13 * 60, 14 * 60, "Rehat", "Break"),
        (16 * 60, 17 * 60, "Teknologi untuk Pengajaran dan Pembelajaran (EDUP6023)", "Technology for Teaching and Learning (EDUP6023)"),
    ],
}

DAYS = {
    "monday": "Monday", "mon": "Monday", "isnin": "Monday",
    "tuesday": "Tuesday", "tue": "Tuesday", "tues": "Tuesday", "selasa": "Tuesday",
    "wednesday": "Wednesday", "wed": "Wednesday", "rabu": "Wednesday",
    "thursday": "Thursday", "thu": "Thursday", "thurs": "Thursday", "khamis": "Thursday",
    "friday": "Friday", "fri": "Friday", "jumaat": "Friday", "jumaat": "Friday",
}
DAY_MS = {
    "Monday": "Isnin", "Tuesday": "Selasa", "Wednesday": "Rabu",
    "Thursday": "Khamis", "Friday": "Jumaat",
}
DAY_EN = {day: day for day in DAYS.values()}

def is_bm(update: Update) -> bool:
    # User can change language using /lang en or /lang bm.
    return update.effective_user and update.effective_user.id and \
        update.effective_chat and update.effective_chat.id and \
        USER_LANGUAGE.get(update.effective_user.id, "en") == "bm"

USER_LANGUAGE = {}

def fmt_time(minutes: int) -> str:
    hour, minute = divmod(minutes, 60)
    suffix = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d} {suffix}"

def fmt_range(start: int, end: int) -> str:
    return f"{fmt_time(start)}–{fmt_time(end)}"

def parse_day(text: str):
    low = text.lower()
    for token, day in DAYS.items():
        if re.search(rf"\b{re.escape(token)}\b", low):
            return day
    return None

def parse_time(text: str):
    """Return minutes after midnight, or None. Supports 10:30 AM, 14:30, 2 PM, 2pm."""
    low = text.lower().replace(".", "")
    # 12-hour or 24-hour time with minutes
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", low)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        suffix = m.group(3)
        if minute > 59:
            return None
        if suffix:
            if not 1 <= hour <= 12:
                return None
            hour = hour % 12 + (12 if suffix == "pm" else 0)
        elif not 0 <= hour <= 23:
            return None
        return hour * 60 + minute
    # Hour only, e.g. 2 PM or 14
    m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", low)
    if m:
        hour, suffix = int(m.group(1)), m.group(2)
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if suffix == "pm" else 0)
        return hour * 60
    m = re.search(r"\b(?:at\s+)?(\d{1,2})(?:\s*(?:o'?clock))?\b", low)
    if m and any(word in low for word in [" at ", "pukul ", "jam ", "now", "sekarang"]):
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return hour * 60
    return None

def get_event(day: str, minute: int):
    for start, end, bm_name, en_name in SCHEDULE.get(day, []):
        if start <= minute < end:
            return start, end, bm_name, en_name
    return None

def display_day(day: str, lang: str) -> str:
    rows = SCHEDULE.get(day, [])
    if lang == "bm":
        lines = [f"🗓️ Jadual {DAY_MS[day]}:"]
        if not rows:
            return f"Tiada jadual tersedia untuk {DAY_MS.get(day, day)}."
        for start, end, bm_name, en_name in rows:
            lines.append(f"• {fmt_range(start, end)} — {bm_name}")
        return "\n".join(lines)
    lines = [f"🗓️ Timetable for {day}:"]
    if not rows:
        return f"No timetable is available for {day}."
    for start, end, bm_name, en_name in rows:
        lines.append(f"• {fmt_range(start, end)} — {en_name}")
    return "\n".join(lines)

def find_next(day: str, minute: int):
    for start, end, bm_name, en_name in SCHEDULE.get(day, []):
        if start > minute and bm_name.lower() != "rehat":
            return start, end, bm_name, en_name
    return None

def check_time(day: str, minute: int, lang: str) -> str:
    event = get_event(day, minute)
    day_label = DAY_MS[day] if lang == "bm" else day
    if event:
        start, end, bm_name, en_name = event
        name = bm_name if lang == "bm" else en_name
        if bm_name.lower() == "rehat":
            if lang == "bm":
                return f"☕ {day_label}, {fmt_time(minute)}: Dalam jadual, waktu ini ditandakan sebagai rehat ({fmt_range(start, end)})."
            return f"☕ {day_label} at {fmt_time(minute)}: This time is marked as a break ({fmt_range(start, end)})."
        if lang == "bm":
            return f"📚 Ya, ada aktiviti pada {day_label}.\nMasa: {fmt_range(start, end)}\nAktiviti: {name}"
        return f"📚 Yes, you have a scheduled activity on {day_label}.\nTime: {fmt_range(start, end)}\nClass/activity: {name}"
    # Schedule image only gives some listed periods; be transparent about gaps.
    if lang == "bm":
        return f"✅ Tiada kelas atau aktiviti yang disenaraikan pada {day_label}, {fmt_time(minute)}. Sila semak jadual asal untuk memastikan waktu kosong ini bukan tempoh yang tidak dipaparkan."
    return f"✅ No class or activity is listed for {day_label} at {fmt_time(minute)}. Please check the original timetable to confirm this is a genuine free period rather than an unlisted period."

def home_keyboard(lang: str):
    if lang == "bm":
        return ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Semak sekarang"), KeyboardButton("🗓️ Jadual hari ini")],
             [KeyboardButton("📅 Pilih hari"), KeyboardButton("❓ Bantuan")]],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Check now"), KeyboardButton("🗓️ Today's timetable")],
         [KeyboardButton("📅 Choose a day"), KeyboardButton("❓ Help")]],
        resize_keyboard=True
    )

def day_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Monday / Isnin", callback_data="day:Monday"),
         InlineKeyboardButton("Tuesday / Selasa", callback_data="day:Tuesday")],
        [InlineKeyboardButton("Wednesday / Rabu", callback_data="day:Wednesday"),
         InlineKeyboardButton("Thursday / Khamis", callback_data="day:Thursday")],
        [InlineKeyboardButton("Friday / Jumaat", callback_data="day:Friday")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = USER_LANGUAGE.get(uid, "en")
    if lang == "bm":
        message = ("Hai! 👋 Saya ClassBuddy Bot.\n\n"
                   "Saya boleh menyemak jadual kelas berdasarkan jadual yang telah disediakan.\n"
                   "• Taip: Isnin 10:30 pagi\n"
                   "• Taip /schedule untuk memilih hari\n"
                   "• Taip /lang en untuk Bahasa Inggeris\n\n"
                   "Pilih menu di bawah atau taip hari dan masa.")
    else:
        message = ("Hi! 👋 I'm ClassBuddy Bot.\n\n"
                   "I can check your timetable using the schedule provided.\n"
                   "• Type: Monday 10:30 AM\n"
                   "• Use /schedule to choose a day\n"
                   "• Use /lang bm for Bahasa Melayu\n\n"
                   "Choose a menu option below or type a day and time.")
    await update.message.reply_text(message, reply_markup=home_keyboard(lang))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = USER_LANGUAGE.get(update.effective_user.id, "en")
    if lang == "bm":
        text = ("Cara menggunakan ClassBuddy Bot:\n"
                "• Semak masa: /check Isnin 10:30\n"
                "• Lihat jadual: /day Rabu\n"
                "• Lihat jadual hari ini: /today\n"
                "• Pilih hari: /schedule\n"
                "• Tukar bahasa: /lang en atau /lang bm\n\n"
                "Masa boleh ditaip seperti 10:30 AM, 2 PM atau 14:30.")
    else:
        text = ("How to use ClassBuddy Bot:\n"
                "• Check a time: /check Monday 10:30 AM\n"
                "• View a day: /day Wednesday\n"
                "• View today's timetable: /today\n"
                "• Choose a day: /schedule\n"
                "• Change language: /lang en or /lang bm\n\n"
                "Times can be entered as 10:30 AM, 2 PM, or 14:30.")
    await update.message.reply_text(text, reply_markup=home_keyboard(lang))

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0].lower() not in ("en", "bm"):
        await update.message.reply_text("Usage: /lang en or /lang bm")
        return
    lang = context.args[0].lower()
    USER_LANGUAGE[update.effective_user.id] = lang
    msg = "Language set to Bahasa Melayu." if lang == "bm" else "Language set to English."
    await update.message.reply_text(msg, reply_markup=home_keyboard(lang))

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = USER_LANGUAGE.get(update.effective_user.id, "en")
    today = datetime.now(TIMEZONE).strftime("%A")
    if today not in SCHEDULE:
        msg = "Tiada jadual untuk hari ini dalam jadual yang dimuatkan." if lang == "bm" else "No timetable is provided for today."
    else:
        msg = display_day(today, lang)
    await update.message.reply_text(msg, reply_markup=home_keyboard(lang))

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = USER_LANGUAGE.get(update.effective_user.id, "en")
    prompt = "Pilih hari:" if lang == "bm" else "Choose a day:"
    await update.message.reply_text(prompt, reply_markup=day_keyboard())

async def day_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = USER_LANGUAGE.get(update.effective_user.id, "en")
    text = " ".join(context.args)
    day = parse_day(text)
    if not day:
        await update.message.reply_text(
            "Contoh: /day Isnin" if lang == "bm" else "Example: /day Monday",
            reply_markup=home_keyboard(lang)
        )
        return
    await update.message.reply_text(display_day(day, lang), reply_markup=home_keyboard(lang))

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = USER_LANGUAGE.get(update.effective_user.id, "en")
    text = " ".join(context.args)
    day = parse_day(text)
    minute = parse_time(text)
    if not day or minute is None:
        prompt = ("Contoh: /check Isnin 10:30 pagi atau /check Tuesday 2 PM"
                  if lang == "bm" else
                  "Example: /check Monday 10:30 AM or /check Tuesday 14:00")
        await update.message.reply_text(prompt, reply_markup=home_keyboard(lang))
        return
    await update.message.reply_text(check_time(day, minute, lang), reply_markup=home_keyboard(lang))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = USER_LANGUAGE.get(query.from_user.id, "en")
    if query.data.startswith("day:"):
        day = query.data.split(":", 1)[1]
        await query.message.reply_text(display_day(day, lang), reply_markup=home_keyboard(lang))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = USER_LANGUAGE.get(user_id, "en")
    text = (update.message.text or "").strip()
    low = text.lower()

    if low in ("❓ help", "help", "bantuan", "❓ bantuan"):
        await help_command(update, context)
        return
    if low in ("📅 choose a day", "📅 pilih hari"):
        await schedule_command(update, context)
        return
    if low in ("🗓️ today's timetable", "jadual hari ini", "🗓️ jadual hari ini"):
        await today_command(update, context)
        return
    if low in ("📍 check now", "📍 semak sekarang", "check now", "sekarang"):
        now = datetime.now(TIMEZONE)
        day = now.strftime("%A")
        if day in SCHEDULE:
            await update.message.reply_text(check_time(day, now.hour * 60 + now.minute, lang), reply_markup=home_keyboard(lang))
        else:
            msg = "Tiada jadual untuk hari ini." if lang == "bm" else "No timetable is provided for today."
            await update.message.reply_text(msg, reply_markup=home_keyboard(lang))
        return

    day = parse_day(text)
    minute = parse_time(text)
    if day and minute is not None:
        await update.message.reply_text(check_time(day, minute, lang), reply_markup=home_keyboard(lang))
        return
    if day and minute is None and any(word in low for word in [
        "timetable", "schedule", "jadual", "classes", "kelas", "what do i have", "show"
    ]):
        await update.message.reply_text(display_day(day, lang), reply_markup=home_keyboard(lang))
        return
    if any(word in low for word in ["today", "hari ini", "sekarang", "right now", "now"]):
        now = datetime.now(TIMEZONE)
        current_day = now.strftime("%A")
        if current_day in SCHEDULE:
            await update.message.reply_text(check_time(current_day, now.hour * 60 + now.minute, lang), reply_markup=home_keyboard(lang))
        else:
            msg = "Tiada jadual untuk hari ini." if lang == "bm" else "No timetable is provided for today."
            await update.message.reply_text(msg, reply_markup=home_keyboard(lang))
        return

    if lang == "bm":
        response = ("Saya belum dapat memahami permintaan itu. Cuba taip 'Isnin 10:30 pagi', "
                    "gunakan /schedule untuk memilih hari, atau taip /help untuk bantuan.")
    else:
        response = ("I couldn't match that request. Try 'Monday 10:30 AM', use /schedule to choose a day, "
                    "or type /help for instructions.")
    await update.message.reply_text(response, reply_markup=home_keyboard(lang))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # Keep error details in the console for debugging; do not expose secrets to users.
    print(f"Bot error: {context.error!r}")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Missing TELEGRAM_BOT_TOKEN. Create a bot with @BotFather, then set the token "
            "as an environment variable before running this program."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CommandHandler("day", day_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)

    print("ClassBuddy Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

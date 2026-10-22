# ClassBuddy Bot (Telegram only, no LLM API)

A rule-based Telegram bot that checks a student's timetable using predefined data.

## Features
- Natural-language-style time checks: `Monday 10:30 AM`, `Isnin 10:30 pagi`
- Menu to choose a day
- Daily timetable: `/today`, `/day Wednesday`
- Time check command: `/check Monday 10:30 AM`
- English and Bahasa Melayu: `/lang en`, `/lang bm`
- Uses Malaysia time (`Asia/Kuala_Lumpur`)
- No LLM API; only Telegram's Bot API and local Python logic

## 1. Create a Telegram bot
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`.
3. Follow the instructions and copy the bot token.
4. Keep the token private. Do not post it in public or upload it to GitHub.

## 2. Install Python and the package
Install Python 3.10 or newer, then run:

```bash
python -m pip install "python-telegram-bot>=21,<23"
```

## 3. Set the token and run

### Windows PowerShell
```powershell
$env:TELEGRAM_BOT_TOKEN="PASTE_YOUR_BOT_TOKEN_HERE"
python bot.py
```

### macOS / Linux
```bash
export TELEGRAM_BOT_TOKEN="PASTE_YOUR_BOT_TOKEN_HERE"
python bot.py
```

Keep the terminal running while you use the bot. This uses long polling, so you do not need a public website or webhook for the initial version.

## 4. Try these messages
- `/start`
- `Monday 10:30 AM`
- `Isnin 10:30 pagi`
- `/check Tuesday 14:00`
- `/day Wednesday`
- `/today`
- `/schedule`
- `/lang bm`
- `/lang en`

## Important timetable notes
- The timetable was transcribed from the uploaded image. Check all entries against the original before relying on it.
- The Thursday entry is labelled `GFEPS` in the image; its full course name is unclear.
- Classroom details are not included because they were not reliably legible.
- Gaps in the visible timetable are reported as “no class listed”, not guaranteed free time.
- The current implementation treats the class end time as exclusive (e.g. at 10:00, a class ending at 10:00 has finished).

## Customising the timetable
Edit the `SCHEDULE` dictionary near the top of `bot.py`. Each item is:
`(start_minutes_after_midnight, end_minutes_after_midnight, Malay_name, English_name)`

For example, 10:00 AM to 12:00 PM is:
`(600, 720, "Nama subjek BM", "Subject name in English")`

## Limitations
This is a rule-based chatbot, not a generative AI system. It supports known days, time formats, commands, and predefined replies. If the message uses a phrase it cannot match, use a command or the day/time format above.

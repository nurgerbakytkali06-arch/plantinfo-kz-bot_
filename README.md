# plantinfo-kz-bot

Telegram plant encyclopedia bot for Render.

## Project files
- `bot.py` — Telegram webhook bot
- `requirements.txt` — Python dependencies
- `.env.example` — environment variable example
- `data/plants_kk.json` — 115 plant records
- `images/` — 115 plant images

## Render
- Service type: Web Service
- Build Command: `pip install -r requirements.txt`
- Start Command: `python bot.py`
- Environment variable: `BOT_TOKEN` = your Telegram bot token

The bot listens on Render's `PORT` and sets the Telegram webhook automatically.

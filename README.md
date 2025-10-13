# 🍏 Apple Store Stock Bot (Playwright + Telegram + Discord)

I was tired of checking the apple website for the stock of the iPhone 17 Pro Max so I just built this

Checks iPhone 17 Pro Max (Silver 512Gb) availability on the Apple SG Store at 8am, 9am, 10am, 1pm, 2pm, and 3pm (SGT),
then sends alerts to both Telegram and Discord.

### 🔧 Built with
- Python + Playwright
- GitHub Actions (free scheduler)
- Telegram & Discord webhooks
- Secure .env / GitHub Secrets

### 🧠 Features
- Headless browser automation (bypasses Apple anti-bot)
- Parses live pickup & delivery info
- Notifies with clean embedded messages

### 🚀 Setup
1. Fork this repo
2. Add secrets:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `DISCORD_WEBHOOK_URL`
3. Done — GitHub Actions will run 6 times a day and alert you automatically!

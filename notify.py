import os, requests, json
from datetime import datetime
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_telegram(message: str):
    """Send plain-text message to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials missing in .env")
        return
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        )
        if resp.status_code != 200:
            print(f"⚠️ Telegram send failed: {resp.text}")
    except Exception as e:
        print(f"⚠️ Telegram error: {e}")

def send_discord(embed_title: str, embed_description: str, color=0x00bfff):
    """Send rich embed to Discord."""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Discord webhook missing in .env")
        return
    data = {
        "username": "Apple Stock Bot",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg",
        "embeds": [{
            "title": embed_title,
            "description": embed_description,
            "color": color,
            "footer": {"text": f"Updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        }]
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(data),
                             headers={"Content-Type": "application/json"})
        if resp.status_code not in (200, 204):
            print(f"⚠️ Discord send failed: {resp.text}")
    except Exception as e:
        print(f"⚠️ Discord error: {e}")

def notify_both(data):
    """Send parsed stock data to both Telegram and Discord."""
    product = data["product"].get("title", "Unknown Product")
    delivery = data.get("delivery", "N/A")
    stores = data["pickup"].get("stores", [])
    sim = data.get("similar_models", [])

    # Main product summary
    msg_lines = [
        f"📱 *{product}*",
        f"🚚 *Delivery:* {delivery}",
        "",
        "🏬 *Stores:*"
    ]

    # Main pickup stores
    if stores:
        for s in stores:
            msg_lines.append(f"{'✅' if 'available' in (s['status'] or '').lower() else '❌'} {s['store']} — {s['status']}")
    else:
        msg_lines.append("❌ No stores currently have stock")

    # Similar models block (with nested store details)
    if sim:
        msg_lines.append("\n🧩 *Similar Models:*")
        for sm in sim:
            msg_lines.append(f"• {sm['model']} — {sm['price']} — {sm['availability_summary']}")
            for st in sm.get("stores", []):
                msg_lines.append(f"   └ {'✅' if 'available' in (st['status'] or '').lower() else '❌'} {st['store']} — {st['status']}")

    msg = "\n".join(msg_lines)

    # Send both notifications
    send_telegram(msg)
    send_discord(embed_title=product, embed_description=msg.replace("*", ""))

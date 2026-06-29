import logging
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ============================================================
#  ⚙️  CONFIG
# ============================================================
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "8846798377:AAEa4_4nVK14XmvmfOD0zd6UbSlRhzPKPS0")
BOT_USERNAME = "predictor_prediction_bot"

ADMIN_IDS = [6499436331]

CHANNELS = [
    {"name": "🔥 Main Channel",       "username": None,                 "invite_link": "https://t.me/+geNHq7jKIiAyYjJl", "id": -1001813666985},
    {"name": "📈 Trade With Sniper",  "username": "snipertradingshort", "invite_link": None,                              "id": -1003750001776},
    {"name": "💎 Premium Group",      "username": None,                 "invite_link": "https://t.me/+i1aDUi_W8bE3ZTVl",  "id": -1003765229156},
    {"name": "💬 Discussions On Top", "username": "disscussionbfx",     "invite_link": None,                              "id": -1003999268364},
]

DM_USERNAME      = "Predictorisdope"
REGISTER_LINK    = "https://dhani11.com/register?inviteCode=A7SSMNW&from=web"
NEW_USER_CREDITS = 7
REFER_CREDITS    = 4

MANAGER_USERNAME = "ManagerHarsh"
# ============================================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# CLOSED MESSAGE (sent to every user always)
# ──────────────────────────────────────────────
CLOSED_TEXT = (
    "🚫🚫🚫🚫🚫🚫🚫🚫🚫🚫\n"
    "        <b>BOT PERMANENTLY CLOSED</b>\n"
    "🚫🚫🚫🚫🚫🚫🚫🚫🚫🚫\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🔴  <b>यह बॉट अब बंद हो चुका है।</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "👑 <b>Closed By:</b>  <code>@ManagerHarsh</code>\n\n"
    "📅 <b>Status:</b>  ❌ Permanently Terminated\n"
    "⚠️ <b>All services have been stopped.</b>\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🔕  No predictions.\n"
    "🔕  No credits.\n"
    "🔕  No referrals.\n"
    "🔕  No support.\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "⛔️ <i>Koi bhi command ya message kaam nahi karega.</i>\n\n"
    "🚫🚫🚫🚫🚫🚫🚫🚫🚫🚫"
)

CLOSED_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("👑 @ManagerHarsh", url=f"https://t.me/ManagerHarsh")],
])

# ──────────────────────────────────────────────
# DATABASE  (kept intact for admin reference)
# ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id           INTEGER PRIMARY KEY,
            username          TEXT,
            first_name        TEXT,
            joined_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified          INTEGER DEFAULT 0,
            banned            INTEGER DEFAULT 0,
            credits           INTEGER DEFAULT 7,
            referred_by       INTEGER DEFAULT NULL,
            refer_count       INTEGER DEFAULT 0,
            predictions_count INTEGER DEFAULT 0
        )
    """)
    for col, defn in [
        ("last_active",       "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("banned",            "INTEGER DEFAULT 0"),
        ("credits",           "INTEGER DEFAULT 7"),
        ("referred_by",       "INTEGER DEFAULT NULL"),
        ("refer_count",       "INTEGER DEFAULT 0"),
        ("predictions_count", "INTEGER DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
        except Exception:
            pass
    conn.commit()
    conn.close()

def save_user(user, referred_by=None):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    exists = c.fetchone()
    if not exists:
        c.execute("""
            INSERT INTO users (user_id, username, first_name, credits, referred_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user.id, user.username, user.first_name, NEW_USER_CREDITS, referred_by))
    else:
        c.execute("UPDATE users SET username=?, first_name=?, last_active=CURRENT_TIMESTAMP WHERE user_id=?",
                  (user.username, user.first_name, user.id))
    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_today_stats():
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = date('now')")
    active_today = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE date(joined_at) = date('now')")
    joined_today = c.fetchone()[0]
    c.execute("SELECT SUM(predictions_count) FROM users")
    total_preds = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM users WHERE banned=1")
    banned_count = c.fetchone()[0]
    conn.close()
    return active_today, joined_today, total_preds, banned_count

# ──────────────────────────────────────────────
# ALL HANDLERS → show closed message
# ──────────────────────────────────────────────
async def closed_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends permanent closure message to any user action."""
    user = update.effective_user
    if user:
        save_user(user)
    await update.message.reply_text(
        CLOSED_TEXT,
        parse_mode="HTML",
        reply_markup=CLOSED_KEYBOARD
    )

async def closed_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answers any button press with closure message."""
    query = update.callback_query
    await query.answer("⛔ Bot permanently closed by @ManagerHarsh", show_alert=True)
    try:
        await query.edit_message_text(
            CLOSED_TEXT,
            parse_mode="HTML",
            reply_markup=CLOSED_KEYBOARD
        )
    except Exception:
        pass

# ──────────────────────────────────────────────
# ADMIN COMMANDS (still accessible for manager)
# ──────────────────────────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await closed_reply_message(update, context)
        return
    active_today, joined_today, total_preds, banned_count = get_today_stats()
    total = get_total_users()
    await update.message.reply_text(
        f"👑 <b>ADMIN PANEL</b>\n{'─'*30}\n\n"
        f"📊 <b>Stats:</b>\n"
        f"  👥 Total Users: <b>{total}</b>\n"
        f"  🟢 Active Today: <b>{active_today}</b>\n"
        f"  🆕 Joined Today: <b>{joined_today}</b>\n"
        f"  🎯 Total Predictions: <b>{total_preds}</b>\n"
        f"  🚫 Banned: <b>{banned_count}</b>\n\n"
        f"<i>Bot is permanently CLOSED for all users.</i>",
        parse_mode="HTML")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await closed_reply_message(update, context)
        return
    active_today, joined_today, total_preds, banned_count = get_today_stats()
    total = get_total_users()
    await update.message.reply_text(
        f"📊 <b>Bot Stats</b>\n\n"
        f"👥 Total Users: <b>{total}</b>\n"
        f"🟢 Active Today: <b>{active_today}</b>\n"
        f"🆕 Joined Today: <b>{joined_today}</b>\n"
        f"🎯 Total Predictions: <b>{total_preds}</b>\n"
        f"🚫 Banned: <b>{banned_count}</b>",
        parse_mode="HTML")

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Admin commands still work for manager
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # ALL other commands → closed message
    app.add_handler(CommandHandler("start",         closed_reply_message))
    app.add_handler(CommandHandler("users",         closed_reply_message))
    app.add_handler(CommandHandler("checkuser",     closed_reply_message))
    app.add_handler(CommandHandler("addcredits",    closed_reply_message))
    app.add_handler(CommandHandler("removecredits", closed_reply_message))
    app.add_handler(CommandHandler("ban",           closed_reply_message))
    app.add_handler(CommandHandler("unban",         closed_reply_message))
    app.add_handler(CommandHandler("broadcast",     closed_reply_message))

    # All button clicks → closed
    app.add_handler(CallbackQueryHandler(closed_reply_callback))

    # All text messages → closed
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, closed_reply_message))

    logger.info("🚫 Bot is running in CLOSED mode — permanently shut by @ManagerHarsh")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

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
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "8846798377:AAEZg4CZIOdzU52w37jYSuiE_---Yef0n6g")
BOT_USERNAME = "predictor_prediction_bot"

ADMIN_IDS = [6499436331]

DM_USERNAME      = "Predictorisdope"
REGISTER_LINK    = "https://dhani11.com/register?inviteCode=A7SSMNW&from=web"
NEW_USER_CREDITS = 7
REFER_CREDITS    = 4
MANAGER_USERNAME = "ManagerHarsh"
# ============================================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# CLOSED MESSAGE
# ──────────────────────────────────────────────
CLOSED_TEXT = (
    "🚫🚫🚫🚫🚫🚫🚫🚫🚫🚫\n"
    "  ⛔️  <b>BOT PERMANENTLY CLOSED</b>  ⛔️\n"
    "🚫🚫🚫🚫🚫🚫🚫🚫🚫🚫\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🔴  <b>यह बॉट अब बंद हो चुका है।</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "👑  <b>Closed By :</b>  <code>@ManagerHarsh</code>\n\n"
    "📅  <b>Status :</b>  ❌  Permanently Terminated\n"
    "⚠️  <b>All services have been stopped.</b>\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🔕  No Predictions\n"
    "🔕  No Credits\n"
    "🔕  No Referrals\n"
    "🔕  No Support\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "⛔️  <i>Koi bhi command ya message kaam nahi karega.</i>\n\n"
    "🚫🚫🚫🚫🚫🚫🚫🚫🚫🚫"
)

CLOSED_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("👑 @ManagerHarsh", url="https://t.me/ManagerHarsh")],
])

# ──────────────────────────────────────────────
# DATABASE  (kept for admin /stats reference)
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
    conn.commit()
    conn.close()

def save_user(user):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user.id, user.username, user.first_name)
        )
    else:
        c.execute(
            "UPDATE users SET username=?, first_name=?, last_active=CURRENT_TIMESTAMP WHERE user_id=?",
            (user.username, user.first_name, user.id)
        )
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
# CORE: send closed message (works for all cases)
# ──────────────────────────────────────────────
async def send_closed(update: Update):
    """Universal closed message — handles both message and callback contexts."""
    if update.message:
        await update.message.reply_text(
            CLOSED_TEXT,
            parse_mode="HTML",
            reply_markup=CLOSED_KEYBOARD
        )
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                CLOSED_TEXT,
                parse_mode="HTML",
                reply_markup=CLOSED_KEYBOARD
            )
        except Exception:
            await update.callback_query.answer(
                "⛔ Bot permanently closed by @ManagerHarsh", show_alert=True
            )

# ──────────────────────────────────────────────
# HANDLERS — everything → closed message
# ──────────────────────────────────────────────
async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start, any command, any text — always shows closed."""
    user = update.effective_user
    if user:
        save_user(user)  # silently log visitor

    # Let admins use /admin and /stats
    if update.message and update.message.text:
        cmd = update.message.text.split()[0].lower().lstrip("/")
        if cmd in ("admin", "stats") and user.id in ADMIN_IDS:
            return  # fall through to admin handlers below

    await send_closed(update)

async def handle_any_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles any inline button tap — always shows closed."""
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
# ADMIN COMMANDS (only for ADMIN_IDS)
# ──────────────────────────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
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
        f"<i>⛔ Bot is permanently CLOSED for all users.</i>\n"
        f"<i>Closed by @ManagerHarsh</i>",
        parse_mode="HTML"
    )

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
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
        parse_mode="HTML"
    )

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Admin-only commands
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # ALL other commands (including /start) → closed
    app.add_handler(MessageHandler(filters.COMMAND, handle_any_message))

    # ALL button taps → closed
    app.add_handler(CallbackQueryHandler(handle_any_callback))

    # ALL plain text messages → closed
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_message))

    logger.info("⛔ Bot running in PERMANENTLY CLOSED mode — @ManagerHarsh")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

import logging
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ============================================================
#  CONFIG
# ============================================================
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "8846798377:AAFeD5qeUog_5jzZHDAut9R56luVhCIp3lk")
BOT_USERNAME = "predictor_prediction_bot"

ADMIN_IDS = [6499436331]

CHANNELS = [
    {"name": "Main Channel",       "username": None,                 "invite_link": "https://t.me/+geNHq7jKIiAyYjJl", "id": -1001813666985},
    {"name": "Trade With Sniper",  "username": "snipertradingshort", "invite_link": None,                              "id": -1003750001776},
    {"name": "Premium Group",      "username": None,                 "invite_link": "https://t.me/+i1aDUi_W8bE3ZTVl",  "id": -1003765229156},
    {"name": "Discussions On Top", "username": "disscussionbfx",     "invite_link": None,                              "id": -1003999268364},
]

DM_USERNAME      = "Predictorisdope"
REGISTER_LINK    = "https://dhani11.com/register?inviteCode=A7SSMNW&from=web"
NEW_USER_CREDITS = 7
REFER_CREDITS    = 4

LINE  = "━━━━━━━━━━━━━━━━━━━━"
DLINE = "──────────────────────────────"
# ============================================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# CLOSED MESSAGE  (shown to EVERY user)
# ──────────────────────────────────────────────
CLOSED_TEXT = (
    "\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\n"
    "  \u26d4  <b>BOT PERMANENTLY CLOSED</b>  \u26d4\n"
    "\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\n\n"
    + LINE + "\n"
    "\U0001f534  <b>Yeh Bot Ab Hamesha Ke Liye Band Ho Gaya Hai.</b>\n"
    + LINE + "\n\n"
    "\U0001f451  <b>Closed By :</b>  <code>@ManagerHarsh</code>\n\n"
    "\U0001f4c5  <b>Status :</b>  \u274c  Permanently Terminated\n"
    "\u26a0\ufe0f  <b>All services have been stopped.</b>\n\n"
    + LINE + "\n"
    "\U0001f515  No Predictions\n"
    "\U0001f515  No Credits\n"
    "\U0001f515  No Referrals\n"
    "\U0001f515  No Support\n"
    + LINE + "\n\n"
    "\u26d4  <i>Koi bhi command ya message kaam nahi karega.</i>\n\n"
    "\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab"
)

CLOSED_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("👑 @ManagerHarsh", url="https://t.me/ManagerHarsh")],
])

# ──────────────────────────────────────────────
# DATABASE
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
            c.execute("ALTER TABLE users ADD COLUMN " + col + " " + defn)
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
        c.execute(
            "INSERT INTO users (user_id, username, first_name, credits, referred_by) VALUES (?, ?, ?, ?, ?)",
            (user.id, user.username, user.first_name, NEW_USER_CREDITS, referred_by)
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

def get_recent_users(limit=10):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute(
        "SELECT user_id, username, first_name, last_active, predictions_count, banned, credits "
        "FROM users ORDER BY last_active DESC LIMIT ?", (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_users():
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE banned=0")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def add_credits(user_id, amount):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def ban_user(user_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute(
        "SELECT user_id, username, first_name, joined_at, last_active, verified, banned, "
        "credits, referred_by, refer_count, predictions_count FROM users WHERE user_id=?",
        (user_id,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "username": row[1], "first_name": row[2],
                "joined_at": row[3], "last_active": row[4], "verified": row[5],
                "banned": row[6], "credits": row[7], "referred_by": row[8],
                "refer_count": row[9], "predictions_count": row[10]}
    return None

# ──────────────────────────────────────────────
# UNIVERSAL CLOSED SENDER
# ──────────────────────────────────────────────
async def send_closed(update: Update):
    if update.message:
        await update.message.reply_text(CLOSED_TEXT, parse_mode="HTML", reply_markup=CLOSED_KB)
    elif update.callback_query:
        await update.callback_query.answer(
            "Bot permanently closed by @ManagerHarsh", show_alert=True
        )
        try:
            await update.callback_query.edit_message_text(
                CLOSED_TEXT, parse_mode="HTML", reply_markup=CLOSED_KB
            )
        except Exception:
            pass

# ──────────────────────────────────────────────
# ALL USER HANDLERS  →  CLOSED
# ──────────────────────────────────────────────
async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        save_user(user)
    await send_closed(update)

async def handle_any_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_closed(update)

# ──────────────────────────────────────────────
# ADMIN COMMANDS  (only for ADMIN_IDS)
# ──────────────────────────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
        return
    active_today, joined_today, total_preds, banned_count = get_today_stats()
    total = get_total_users()
    text = (
        "<b>ADMIN PANEL</b>\n"
        + DLINE + "\n\n"
        "<b>Live Stats:</b>\n"
        "  Total Users: <b>" + str(total) + "</b>\n"
        "  Active Today: <b>" + str(active_today) + "</b>\n"
        "  Joined Today: <b>" + str(joined_today) + "</b>\n"
        "  Total Predictions: <b>" + str(total_preds) + "</b>\n"
        "  Banned: <b>" + str(banned_count) + "</b>\n\n"
        + DLINE + "\n"
        "<b>Commands:</b>\n"
        "  /users — Recent 10 users\n"
        "  /checkuser &lt;id&gt;\n"
        "  /addcredits &lt;id&gt; &lt;amt&gt;\n"
        "  /ban &lt;id&gt;  |  /unban &lt;id&gt;\n"
        "  /broadcast &lt;msg&gt;\n"
        "  /stats\n\n"
        "<i>Bot is PERMANENTLY CLOSED for all users.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
        return
    active_today, joined_today, total_preds, banned_count = get_today_stats()
    total = get_total_users()
    await update.message.reply_text(
        "<b>Bot Stats</b>\n\n"
        "Total Users: <b>" + str(total) + "</b>\n"
        "Active Today: <b>" + str(active_today) + "</b>\n"
        "Joined Today: <b>" + str(joined_today) + "</b>\n"
        "Total Predictions: <b>" + str(total_preds) + "</b>\n"
        "Banned: <b>" + str(banned_count) + "</b>",
        parse_mode="HTML"
    )

async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
        return
    recent = get_recent_users(10)
    if not recent:
        await update.message.reply_text("Koi user nahi mila.")
        return
    lines = ["<b>Recent 10 Users:</b>\n"]
    for u in recent:
        uid, uname, fname, last_active, preds, banned, credits = u
        status = "BANNED" if banned else "OK"
        uname_str = "@" + uname if uname else "No username"
        lines.append(
            status + " <b>" + str(fname) + "</b> (" + uname_str + ")\n"
            "   ID: <code>" + str(uid) + "</code> | Credits: " + str(credits) +
            " | Preds: " + str(preds) + "\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_checkuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
        return
    if not context.args:
        await update.message.reply_text("Usage: /checkuser <user_id>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Sahi User ID daalo.")
        return
    udata = get_user(uid)
    if not udata:
        await update.message.reply_text("User nahi mila.")
        return
    status = "BANNED" if udata["banned"] else ("Verified" if udata["verified"] else "Not Verified")
    await update.message.reply_text(
        "<b>User Info</b>\n\n"
        "Name: <b>" + str(udata["first_name"]) + "</b>\n"
        "Username: @" + str(udata["username"] or "None") + "\n"
        "ID: <code>" + str(uid) + "</code>\n"
        "Status: " + status + "\n"
        "Credits: <b>" + str(udata["credits"]) + "</b>\n"
        "Refers: <b>" + str(udata["refer_count"]) + "</b>\n"
        "Predictions: <b>" + str(udata["predictions_count"]) + "</b>",
        parse_mode="HTML"
    )

async def cmd_addcredits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /addcredits <user_id> <amount>")
        return
    try:
        uid = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Sahi values daalo.")
        return
    add_credits(uid, amount)
    await update.message.reply_text(
        "Done! User <code>" + str(uid) + "</code> ko <b>" + str(amount) + "</b> credits diye.",
        parse_mode="HTML"
    )

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Sahi User ID daalo.")
        return
    if uid in ADMIN_IDS:
        await update.message.reply_text("Admin ko ban nahi kar sakte!")
        return
    ban_user(uid)
    await update.message.reply_text("User <code>" + str(uid) + "</code> ban kar diya.", parse_mode="HTML")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Sahi User ID daalo.")
        return
    unban_user(uid)
    await update.message.reply_text("User <code>" + str(uid) + "</code> unban kar diya.", parse_mode="HTML")

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await send_closed(update)
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = " ".join(context.args)
    users = get_all_users()
    sent = 0
    failed = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, msg, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        "Broadcast Done!\nSent: " + str(sent) + "\nFailed: " + str(failed)
    )

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Admin commands
    app.add_handler(CommandHandler("admin",        admin_panel))
    app.add_handler(CommandHandler("stats",        cmd_stats))
    app.add_handler(CommandHandler("users",        cmd_users))
    app.add_handler(CommandHandler("checkuser",    cmd_checkuser))
    app.add_handler(CommandHandler("addcredits",   cmd_addcredits))
    app.add_handler(CommandHandler("ban",          cmd_ban))
    app.add_handler(CommandHandler("unban",        cmd_unban))
    app.add_handler(CommandHandler("broadcast",    cmd_broadcast))

    # ALL user commands + text + callbacks  →  CLOSED
    app.add_handler(MessageHandler(filters.COMMAND, handle_any_message))
    app.add_handler(CallbackQueryHandler(handle_any_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_message))

    logger.info("Bot running in PERMANENTLY CLOSED mode — @ManagerHarsh")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

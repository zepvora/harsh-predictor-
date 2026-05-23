import logging
import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ============================================================
#  ⚙️  CONFIG
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8846798377:AAEa4_4nVK14XmvmfOD0zd6UbSlRhzPKPS0")
BOT_USERNAME = "predictor_prediction_bot"

ADMIN_IDS = [6896407205]

CHANNELS = [
    {"name": "🔥 Main Channel",       "username": None,                 "invite_link": "https://t.me/+geNHq7jKIiAyYjJl", "id": -1001813666985},
    {"name": "📈 Trade With Sniper",  "username": "snipertradingshort", "invite_link": None,                              "id": -1003750001776},
    {"name": "💎 Premium Group",      "username": None,                 "invite_link": "https://t.me/+i1aDUi_W8bE3ZTVl",  "id": -1003765229156},
    {"name": "💬 Discussions On Top", "username": "disscussionbfx",     "invite_link": None,                              "id": -1003999268364},
]
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id          INTEGER PRIMARY KEY,
            username         TEXT,
            first_name       TEXT,
            joined_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified         INTEGER DEFAULT 0,
            banned           INTEGER DEFAULT 0,
            predictions_count INTEGER DEFAULT 0
        )
    """)
    # Add new columns if upgrading old DB
    for col, definition in [
        ("last_active", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("banned", "INTEGER DEFAULT 0"),
        ("predictions_count", "INTEGER DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        except Exception:
            pass
    conn.commit()
    conn.close()

def save_user(user):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user.id, user.username, user.first_name))
    c.execute("""
        UPDATE users SET username=?, first_name=?, last_active=CURRENT_TIMESTAMP
        WHERE user_id=?
    """, (user.username, user.first_name, user.id))
    conn.commit()
    conn.close()

def set_verified(user_id: int):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET verified=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def increment_predictions(user_id: int):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET predictions_count = predictions_count + 1, last_active=CURRENT_TIMESTAMP WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_all_users():
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE banned=0")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def is_banned(user_id: int) -> bool:
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])

def ban_user(user_id: int):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id: int):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_user_info(user_id: int):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, joined_at, last_active, verified, banned, predictions_count FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

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
    c.execute("""
        SELECT user_id, username, first_name, last_active, predictions_count, banned
        FROM users ORDER BY last_active DESC LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ──────────────────────────────────────────────
# PREDICTION ALGORITHM
# ──────────────────────────────────────────────
def predict_wingo(digits: str) -> dict:
    if len(digits) != 3 or not digits.isdigit():
        return {"error": True}

    d = [int(x) for x in digits]
    num = int(digits)
    digit_sum   = sum(d)
    digit_range = max(d) - min(d)
    even_count  = sum(1 for x in d if x % 2 == 0)

    big_score = 0
    small_score = 0

    if digit_sum >= 13:
        big_score += 2
    elif digit_sum <= 11:
        small_score += 2
    else:
        big_score += 1

    if num % 3 == 0 or num % 7 == 0:
        big_score += 2
    else:
        small_score += 2

    if even_count >= 2:
        big_score += 1
    else:
        small_score += 1

    if digit_range >= 5:
        big_score += 1
    else:
        small_score += 1

    if d[2] >= 5:
        big_score += 1
    else:
        small_score += 1

    total = big_score + small_score
    if big_score > small_score:
        result = "BIG 🔴"
        confidence = round((big_score / total) * 100)
        color = "🔴"
    else:
        result = "SMALL 🟢"
        confidence = round((small_score / total) * 100)
        color = "🟢"

    return {
        "error": False,
        "result": result,
        "confidence": confidence,
        "color": color,
        "digit_sum": digit_sum,
        "big_score": big_score,
        "small_score": small_score,
    }

# ──────────────────────────────────────────────
# CHANNEL VERIFICATION
# ──────────────────────────────────────────────
async def check_all_channels(user_id: int, bot) -> list:
    not_joined = []
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            if member.status in ["left", "kicked", "banned"]:
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined

def join_channels_keyboard():
    buttons = []
    for ch in CHANNELS:
        link = ch["invite_link"] if ch.get("invite_link") else f"https://t.me/{ch['username']}"
        buttons.append([InlineKeyboardButton(f"📢 {ch['name']}", url=link)])
    buttons.append([InlineKeyboardButton("✅ Verify Now", callback_data="verify")])
    return InlineKeyboardMarkup(buttons)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Get Prediction", callback_data="predict")],
        [InlineKeyboardButton("📊 How it works", callback_data="howto")],
        [InlineKeyboardButton("👥 Our Channels", callback_data="channels")],
    ])

# ──────────────────────────────────────────────
# ADMIN COMMANDS
# ──────────────────────────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied!")
        return

    active_today, joined_today, total_preds, banned_count = get_today_stats()
    total = get_total_users()

    text = (
        f"👑 <b>ADMIN PANEL</b>\n"
        f"{'─' * 30}\n\n"
        f"📊 <b>Live Stats:</b>\n"
        f"  👥 Total Users: <b>{total}</b>\n"
        f"  🟢 Active Today: <b>{active_today}</b>\n"
        f"  🆕 Joined Today: <b>{joined_today}</b>\n"
        f"  🎯 Total Predictions: <b>{total_preds}</b>\n"
        f"  🚫 Banned Users: <b>{banned_count}</b>\n\n"
        f"{'─' * 30}\n"
        f"<b>Commands:</b>\n"
        f"  /stats — Full stats\n"
        f"  /users — Recent 10 users\n"
        f"  /userinfo &lt;id&gt; — User detail\n"
        f"  /ban &lt;id&gt; — Ban user\n"
        f"  /unban &lt;id&gt; — Unban user\n"
        f"  /broadcast &lt;msg&gt; — Sabko bhejo\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
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

async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    recent = get_recent_users(10)
    if not recent:
        await update.message.reply_text("Koi user nahi mila.")
        return
    lines = ["👥 <b>Recent 10 Users:</b>\n"]
    for u in recent:
        uid, uname, fname, last_active, preds, banned = u
        status = "🚫" if banned else "✅"
        uname_str = f"@{uname}" if uname else "No username"
        lines.append(f"{status} <b>{fname}</b> ({uname_str})\n   ID: <code>{uid}</code> | Predictions: {preds}\n   Last: {last_active[:16] if last_active else 'N/A'}\n")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /userinfo <user_id>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Sahi User ID daalo.")
        return
    info = get_user_info(uid)
    if not info:
        await update.message.reply_text("❌ User nahi mila.")
        return
    uid, uname, fname, joined, last_active, verified, banned, preds = info
    status = "🚫 BANNED" if banned else ("✅ Verified" if verified else "⏳ Not Verified")
    await update.message.reply_text(
        f"👤 <b>User Info</b>\n\n"
        f"Name: <b>{fname}</b>\n"
        f"Username: @{uname if uname else 'None'}\n"
        f"ID: <code>{uid}</code>\n"
        f"Status: {status}\n"
        f"Joined: {joined[:16] if joined else 'N/A'}\n"
        f"Last Active: {last_active[:16] if last_active else 'N/A'}\n"
        f"Predictions: <b>{preds}</b>\n\n"
        f"{'🔓 /unban ' + str(uid) if banned else '🔒 /ban ' + str(uid)}",
        parse_mode="HTML"
    )

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Sahi User ID daalo.")
        return
    if uid in ADMIN_IDS:
        await update.message.reply_text("❌ Admin ko ban nahi kar sakte!")
        return
    ban_user(uid)
    await update.message.reply_text(f"🚫 User <code>{uid}</code> ban kar diya gaya!", parse_mode="HTML")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Sahi User ID daalo.")
        return
    unban_user(uid)
    await update.message.reply_text(f"✅ User <code>{uid}</code> unban kar diya gaya!", parse_mode="HTML")

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = " ".join(context.args)
    users = get_all_users()
    sent, failed = 0, 0
    for uid in users:
        try:
            await context.bot.send_message(uid, msg, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"📢 Broadcast done!\n✅ Sent: {sent}\n❌ Failed: {failed}")

# ──────────────────────────────────────────────
# HANDLERS
# ──────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    if is_banned(user.id):
        await update.message.reply_text("🚫 Aapko is bot se ban kar diya gaya hai.")
        return

    not_joined = await check_all_channels(user.id, context.bot)

    if not_joined:
        text = (
            f"👋 Welcome <b>{user.first_name}</b>!\n\n"
            "🔒 <b>Bot Access Locked</b>\n\n"
            "Humara bot use karne ke liye pehle <b>sabhi channels join karne honge</b>:\n\n"
            "⬇️ Neeche diye channels join karo phir\n"
            "<b>✅ Verify Now</b> button dabao!"
        )
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=join_channels_keyboard())
    else:
        set_verified(user.id)
        text = (
            f"✅ <b>Welcome back {user.first_name}!</b>\n\n"
            "🎯 <b>Wingo 30 Big/Small Predictor</b>\n\n"
            "3 digits enter karo aur prediction lo!\n\n"
            "👇 <b>Get Prediction</b> dabao:"
        )
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if is_banned(user.id):
        await query.edit_message_text("🚫 Aapko ban kar diya gaya hai.")
        return

    if query.data == "verify":
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            names = "\n".join([f"❌ {ch['name']}" for ch in not_joined])
            await query.edit_message_text(
                f"⚠️ <b>Abhi bhi join nahi kiya:</b>\n\n{names}\n\nUpar diye sabhi channels join karo phir verify karo! 👆",
                parse_mode="HTML", reply_markup=join_channels_keyboard()
            )
        else:
            set_verified(user.id)
            await query.edit_message_text(
                f"🎉 <b>Verified Successfully {user.first_name}!</b>\n\nAb tum bot use kar sakte ho!\n\n👇 Prediction lene ke liye button dabao:",
                parse_mode="HTML", reply_markup=main_keyboard()
            )

    elif query.data == "predict":
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            await query.edit_message_text("🔒 <b>Access Denied!</b>\n\nPehle sabhi channels join karo:", parse_mode="HTML", reply_markup=join_channels_keyboard())
            return
        context.user_data["waiting_for_digits"] = True
        await query.edit_message_text(
            "🎯 <b>Wingo 30 Predictor</b>\n\n📝 <b>Last 3 digits enter karo:</b>\n\nExample: <code>456</code> ya <code>789</code>\n\n⬇️ Neeche type karo:",
            parse_mode="HTML"
        )

    elif query.data == "howto":
        await query.edit_message_text(
            "📊 <b>Kaise kaam karta hai?</b>\n\n1️⃣ Wingo 30 ka last result dekho\n2️⃣ Last 3 digits copy karo\n3️⃣ Bot mein enter karo\n4️⃣ Algorithm analyze karta hai:\n\n   • Digit Sum Pattern\n   • Modulo Analysis (÷3, ÷7)\n   • Even/Odd Distribution\n   • Range Calculation\n   • Last Digit Weight\n\n5️⃣ BIG 🔴 ya SMALL 🟢 predict hota hai\n\n⚠️ <i>Sirf entertainment ke liye hai</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])
        )

    elif query.data == "channels":
        ch_lines = []
        for ch in CHANNELS:
            ch_lines.append(f"📢 @{ch['username']} — {ch['name']}" if ch.get("username") else f"🔒 {ch['name']} (Private)")
        await query.edit_message_text(
            f"📢 <b>Humare Channels:</b>\n\n{chr(10).join(ch_lines)}\n\nJoin karo latest predictions ke liye!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])
        )

    elif query.data == "back_main":
        await query.edit_message_text(
            "🎯 <b>Wingo 30 Big/Small Predictor</b>\n\n3 digits enter karo aur prediction lo!\n\n👇 <b>Get Prediction</b> dabao:",
            parse_mode="HTML", reply_markup=main_keyboard()
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if is_banned(user.id):
        await update.message.reply_text("🚫 Aapko ban kar diya gaya hai.")
        return

    save_user(user)

    if context.user_data.get("waiting_for_digits"):
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            context.user_data["waiting_for_digits"] = False
            await update.message.reply_text("🔒 Pehle sabhi channels join karo!", reply_markup=join_channels_keyboard())
            return

        digits = text.replace(" ", "")
        result = predict_wingo(digits)

        if result.get("error"):
            await update.message.reply_text("⚠️ <b>Invalid Input!</b>\n\nSirf 3 digits enter karo.\nExample: <code>456</code>", parse_mode="HTML")
            return

        context.user_data["waiting_for_digits"] = False
        increment_predictions(user.id)

        conf = result["confidence"]
        bar_filled = int(conf / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        response = (
            f"🎯 <b>WINGO 30 PREDICTION</b>\n"
            f"{'─' * 28}\n\n"
            f"📥 Input: <code>{digits}</code>\n\n"
            f"🔮 <b>Result: {result['result']}</b>\n\n"
            f"📊 Confidence: <b>{conf}%</b>\n"
            f"[{bar}]\n\n"
            f"📈 Analysis:\n"
            f"  • Digit Sum: <b>{result['digit_sum']}</b>\n"
            f"  • BIG Score: <b>{result['big_score']}/8</b>\n"
            f"  • SMALL Score: <b>{result['small_score']}/8</b>\n\n"
            f"{'─' * 28}\n"
            f"⚠️ <i>Sirf entertainment ke liye</i>"
        )

        await update.message.reply_text(
            response, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Predict Again", callback_data="predict")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")],
            ])
        )
    else:
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            await update.message.reply_text("🔒 Pehle channels join karo!", reply_markup=join_channels_keyboard())
        else:
            await update.message.reply_text("👇 Menu use karo:", reply_markup=main_keyboard())

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("userinfo", cmd_userinfo))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("✅ Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

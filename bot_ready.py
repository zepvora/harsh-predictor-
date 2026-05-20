import logging
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ============================================================
#  ⚙️  CONFIG - YAHAN APNI VALUES BHARO
# ============================================================
BOT_TOKEN = "8846798377:AAH8BKhwy6Z-GpFUDGBk_kCRnVwvSZJAiZw"           # @BotFather se lo
BOT_USERNAME = "predictor_bot"          # without @

ADMIN_IDS = [6896407205]                     # Tera Telegram User ID

# 4+ Channels jo join karwane hain (username without @)
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
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified    INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def save_user(user):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user.id, user.username, user.first_name))
    conn.commit()
    conn.close()

def set_verified(user_id: int):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET verified=1 WHERE user_id=?", (user_id,))
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
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

# ──────────────────────────────────────────────
# PREDICTION ALGORITHM (Wingo 30 Logic)
# ──────────────────────────────────────────────
def predict_wingo(digits: str) -> dict:
    """
    3 digits enter karo → Big/Small predict karta hai
    Multiple factors use karta hai accurate feel ke liye
    """
    if len(digits) != 3 or not digits.isdigit():
        return {"error": True}

    d = [int(x) for x in digits]
    num = int(digits)

    digit_sum   = sum(d)
    digit_prod  = d[0] * d[1] * d[2] if all(x > 0 for x in d) else 0
    digit_range = max(d) - min(d)
    even_count  = sum(1 for x in d if x % 2 == 0)

    # Scoring system
    big_score = 0
    small_score = 0

    # Factor 1: digit sum
    if digit_sum >= 13:
        big_score += 2
    elif digit_sum <= 11:
        small_score += 2
    else:
        big_score += 1

    # Factor 2: modulo pattern (original algo)
    if num % 3 == 0 or num % 7 == 0:
        big_score += 2
    else:
        small_score += 2

    # Factor 3: even/odd digits
    if even_count >= 2:
        big_score += 1
    else:
        small_score += 1

    # Factor 4: range
    if digit_range >= 5:
        big_score += 1
    else:
        small_score += 1

    # Factor 5: last digit
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
    """Returns list of channels user hasn't joined"""
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
    """Keyboard with channel join buttons + verify button"""
    buttons = []
    for ch in CHANNELS:
        if ch.get("invite_link"):
            link = ch["invite_link"]
        else:
            link = f"https://t.me/{ch['username']}"
        buttons.append([InlineKeyboardButton(f"📢 {ch['name']}", url=link)])
    buttons.append([InlineKeyboardButton("✅ Verify Now", callback_data="verify")])
    return InlineKeyboardMarkup(buttons)

def main_keyboard():
    """Main menu keyboard after verification"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Get Prediction", callback_data="predict")],
        [InlineKeyboardButton("📊 How it works", callback_data="howto")],
        [InlineKeyboardButton("👥 Our Channels", callback_data="channels")],
    ])

# ──────────────────────────────────────────────
# HANDLERS
# ──────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    not_joined = await check_all_channels(user.id, context.bot)

    if not_joined:
        text = (
            f"👋 Welcome <b>{user.first_name}</b>!\n\n"
            "🔒 <b>Bot Access Locked</b>\n\n"
            "Humara bot use karne ke liye pehle <b>sabhi channels join karne honge</b>:\n\n"
            "⬇️ Neeche diye channels join karo phir\n"
            "<b>✅ Verify Now</b> button dabao!"
        )
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=join_channels_keyboard()
        )
    else:
        set_verified(user.id)
        text = (
            f"✅ <b>Welcome back {user.first_name}!</b>\n\n"
            "🎯 <b>Wingo 30 Big/Small Predictor</b>\n\n"
            "3 digits enter karo aur prediction lo!\n\n"
            "👇 <b>Get Prediction</b> dabao:"
        )
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    # ── VERIFY ──
    if query.data == "verify":
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            names = "\n".join([f"❌ {ch['name']}" for ch in not_joined])
            await query.edit_message_text(
                f"⚠️ <b>Abhi bhi join nahi kiya:</b>\n\n{names}\n\n"
                "Upar diye sabhi channels join karo phir verify karo! 👆",
                parse_mode="HTML",
                reply_markup=join_channels_keyboard()
            )
        else:
            set_verified(user.id)
            await query.edit_message_text(
                f"🎉 <b>Verified Successfully {user.first_name}!</b>\n\n"
                "Ab tum bot use kar sakte ho!\n\n"
                "👇 Prediction lene ke liye button dabao:",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )

    # ── PREDICT ──
    elif query.data == "predict":
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            await query.edit_message_text(
                "🔒 <b>Access Denied!</b>\n\nPehle sabhi channels join karo:",
                parse_mode="HTML",
                reply_markup=join_channels_keyboard()
            )
            return
        context.user_data["waiting_for_digits"] = True
        await query.edit_message_text(
            "🎯 <b>Wingo 30 Predictor</b>\n\n"
            "📝 <b>Last 3 digits enter karo:</b>\n\n"
            "Example: <code>456</code> ya <code>789</code>\n\n"
            "⬇️ Neeche type karo:",
            parse_mode="HTML"
        )

    # ── HOW IT WORKS ──
    elif query.data == "howto":
        await query.edit_message_text(
            "📊 <b>Kaise kaam karta hai?</b>\n\n"
            "1️⃣ Wingo 30 ka last result dekho\n"
            "2️⃣ Last 3 digits copy karo\n"
            "3️⃣ Bot mein enter karo\n"
            "4️⃣ Algorithm analyze karta hai:\n\n"
            "   • Digit Sum Pattern\n"
            "   • Modulo Analysis (÷3, ÷7)\n"
            "   • Even/Odd Distribution\n"
            "   • Range Calculation\n"
            "   • Last Digit Weight\n\n"
            "5️⃣ BIG 🔴 ya SMALL 🟢 predict hota hai\n\n"
            "⚠️ <i>Sirf entertainment ke liye hai</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )

    # ── CHANNELS LIST ──
    elif query.data == "channels":
        ch_lines = []
        for ch in CHANNELS:
            if ch.get("username"):
                ch_lines.append(f"📢 @{ch['username']} — {ch['name']}")
            else:
                ch_lines.append(f"🔒 {ch['name']} (Private)")
        ch_list = "\n".join(ch_lines)
        await query.edit_message_text(
            f"📢 <b>Humare Channels:</b>\n\n{ch_list}\n\n"
            "Join karo latest predictions ke liye!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )

    # ── BACK ──
    elif query.data == "back_main":
        await query.edit_message_text(
            "🎯 <b>Wingo 30 Big/Small Predictor</b>\n\n"
            "3 digits enter karo aur prediction lo!\n\n"
            "👇 <b>Get Prediction</b> dabao:",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # Admin commands
    if user.id in ADMIN_IDS:
        if text.startswith("/broadcast "):
            msg = text[len("/broadcast "):]
            users = get_all_users()
            sent, failed = 0, 0
            for uid in users:
                try:
                    await context.bot.send_message(uid, msg, parse_mode="HTML")
                    sent += 1
                except Exception:
                    failed += 1
            await update.message.reply_text(
                f"📢 Broadcast done!\n✅ Sent: {sent}\n❌ Failed: {failed}"
            )
            return

        if text == "/stats":
            total = get_total_users()
            await update.message.reply_text(
                f"📊 <b>Bot Stats</b>\n\n👥 Total Users: <b>{total}</b>",
                parse_mode="HTML"
            )
            return

    # Prediction flow
    if context.user_data.get("waiting_for_digits"):
        # Verify channels first
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            context.user_data["waiting_for_digits"] = False
            await update.message.reply_text(
                "🔒 Pehle sabhi channels join karo!",
                reply_markup=join_channels_keyboard()
            )
            return

        digits = text.replace(" ", "")
        result = predict_wingo(digits)

        if result.get("error"):
            await update.message.reply_text(
                "⚠️ <b>Invalid Input!</b>\n\nSirf 3 digits enter karo.\nExample: <code>456</code>",
                parse_mode="HTML"
            )
            return

        context.user_data["waiting_for_digits"] = False

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
            response,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Predict Again", callback_data="predict")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")],
            ])
        )
    else:
        # Unknown message → show menu
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            await update.message.reply_text(
                "🔒 Pehle channels join karo!",
                reply_markup=join_channels_keyboard()
            )
        else:
            await update.message.reply_text(
                "👇 Menu use karo:",
                reply_markup=main_keyboard()
            )

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("✅ Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

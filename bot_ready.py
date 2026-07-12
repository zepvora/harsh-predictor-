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
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "88846798377:AAEZg4CZIOdzU52w37jYSuiE_---Yef0n6g")
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
# ============================================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

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
        is_new = True
    else:
        c.execute("UPDATE users SET username=?, first_name=?, last_active=CURRENT_TIMESTAMP WHERE user_id=?",
                  (user.username, user.first_name, user.id))
        is_new = False
    conn.commit()
    conn.close()
    return is_new

def set_verified(user_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET verified=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, joined_at, last_active, verified, banned, credits, referred_by, refer_count, predictions_count FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "username": row[1], "first_name": row[2],
                "joined_at": row[3], "last_active": row[4], "verified": row[5],
                "banned": row[6], "credits": row[7], "referred_by": row[8],
                "refer_count": row[9], "predictions_count": row[10]}
    return None

def is_banned(user_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])

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

def add_credits(user_id, amount):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def remove_credits(user_id, amount):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET credits = MAX(0, credits - ?) WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def deduct_credit(user_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits - 1, predictions_count = predictions_count + 1, last_active=CURRENT_TIMESTAMP WHERE user_id=? AND credits > 0", (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def increment_refer_count(referrer_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET refer_count = refer_count + 1, credits = credits + ? WHERE user_id=?", (REFER_CREDITS, referrer_id))
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
    c.execute("SELECT user_id, username, first_name, last_active, predictions_count, banned, credits FROM users ORDER BY last_active DESC LIMIT ?", (limit,))
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
    big_score = 0; small_score = 0
    if digit_sum >= 13: big_score += 2
    elif digit_sum <= 11: small_score += 2
    else: big_score += 1
    if num % 3 == 0 or num % 7 == 0: big_score += 2
    else: small_score += 2
    if even_count >= 2: big_score += 1
    else: small_score += 1
    if digit_range >= 5: big_score += 1
    else: small_score += 1
    if d[2] >= 5: big_score += 1
    else: small_score += 1
    total = big_score + small_score
    if big_score > small_score:
        result = "BIG 🔴"; confidence = round((big_score / total) * 100); color = "🔴"
    else:
        result = "SMALL 🟢"; confidence = round((small_score / total) * 100); color = "🟢"
    return {"error": False, "result": result, "confidence": confidence, "color": color,
            "digit_sum": digit_sum, "big_score": big_score, "small_score": small_score}

# ──────────────────────────────────────────────
# KEYBOARDS
# ──────────────────────────────────────────────
async def check_all_channels(user_id, bot):
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
    buttons.append([InlineKeyboardButton("✅ Verify Karo", callback_data="verify")])
    return InlineKeyboardMarkup(buttons)

def main_keyboard(credits=0):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎯 Get Prediction  [{credits} 🎟️]", callback_data="predict")],
        [InlineKeyboardButton("🔗 Refer & Earn Credits", callback_data="refer")],
        [InlineKeyboardButton("📊 How it works", callback_data="howto"),
         InlineKeyboardButton("👥 Channels", callback_data="channels")],
        [InlineKeyboardButton("💬 DM Admin", url=f"https://t.me/{DM_USERNAME}"),
         InlineKeyboardButton("🎰 Register Now", url=REGISTER_LINK)],
    ])

def no_credits_keyboard(refer_link):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Refer & Earn 4 Credits", url=refer_link)],
        [InlineKeyboardButton("💬 DM Admin", url=f"https://t.me/{DM_USERNAME}")],
        [InlineKeyboardButton("🎰 Register & Earn", url=REGISTER_LINK)],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")],
    ])

# ──────────────────────────────────────────────
# HANDLERS
# ──────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referred_by = None
    if context.args:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id:
                referred_by = ref_id
        except ValueError:
            pass
    is_new = save_user(user, referred_by)
    if is_new and referred_by:
        increment_refer_count(referred_by)
        try:
            await context.bot.send_message(referred_by,
                f"🎉 <b>+{REFER_CREDITS} Credits Mile!</b>\n\n✅ <b>{user.first_name}</b> ne tumhara refer link use kiya!\n🎟️ Tumhare account mein <b>{REFER_CREDITS} credits</b> add ho gaye!",
                parse_mode="HTML")
        except Exception:
            pass

    if is_banned(user.id):
        await update.message.reply_text("🚫 Aapko is bot se ban kar diya gaya hai.")
        return

    not_joined = await check_all_channels(user.id, context.bot)
    if not_joined:
        await update.message.reply_text(
            f"👋 Welcome <b>{user.first_name}</b>!\n\n"
            "🔒 <b>Bot Access Locked</b>\n\n"
            "Sabhi channels join karo, phir\n<b>✅ Verify Karo</b> button dabao!\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎟️ Join karne ke baad milenge: <b>{NEW_USER_CREDITS} Free Credits!</b>",
            parse_mode="HTML", reply_markup=join_channels_keyboard())
    else:
        set_verified(user.id)
        udata = get_user(user.id)
        credits = udata["credits"] if udata else NEW_USER_CREDITS
        await update.message.reply_text(
            f"✅ <b>Welcome {user.first_name}!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 <b>Wingo 30 Big/Small Predictor</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎟️ Tumhare Credits: <b>{credits}</b>\n\n"
            "👇 <b>Get Prediction</b> dabao:",
            parse_mode="HTML", reply_markup=main_keyboard(credits))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    await query.answer()
    if query.message.chat.type != "private":
        return
    if is_banned(user.id):
        await query.edit_message_text("🚫 Aapko ban kar diya gaya hai.")
        return

    udata = get_user(user.id)
    if not udata:
        save_user(user)
        udata = get_user(user.id)
    credits = udata["credits"] if udata else 0

    if query.data == "verify":
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            names = "\n".join([f"❌ {ch['name']}" for ch in not_joined])
            await query.edit_message_text(
                f"⚠️ <b>Abhi bhi join nahi kiya:</b>\n\n{names}\n\nSabhi join karo phir verify karo! 👆",
                parse_mode="HTML", reply_markup=join_channels_keyboard())
        else:
            set_verified(user.id)
            udata = get_user(user.id); credits = udata["credits"]
            await query.edit_message_text(
                f"🎉 <b>Verified! Welcome {user.first_name}!</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🎟️ Tumhare Credits: <b>{credits}</b>\n\n"
                "Ek prediction = 1 credit\nRefer karo = 4 credits kamao! 🔗\n\n"
                "👇 Prediction lene ke liye button dabao:",
                parse_mode="HTML", reply_markup=main_keyboard(credits))

    elif query.data == "predict":
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            await query.edit_message_text("🔒 <b>Access Denied!</b>\n\nPehle sabhi channels join karo:", parse_mode="HTML", reply_markup=join_channels_keyboard())
            return
        if credits <= 0:
            refer_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
            await query.edit_message_text(
                "😢 <b>Credits Khatam Ho Gaye!</b>\n\n🔗 Refer karo → +4 credits\n💬 Ya Admin se lo:",
                parse_mode="HTML", reply_markup=no_credits_keyboard(refer_link))
            return
        context.user_data["waiting_for_digits"] = True
        await query.edit_message_text(
            "🎯 <b>Wingo 30 Predictor</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎟️ Credits: <b>{credits}</b> (1 credit use hoga)\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 <b>Last 3 digits enter karo:</b>\n\nExample: <code>456</code> ya <code>789</code>\n\n⬇️ Neeche type karo:",
            parse_mode="HTML")

    elif query.data == "refer":
        refer_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
        await query.edit_message_text(
            "🔗 <b>Refer & Earn System</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Har refer pe: <b>+{REFER_CREDITS} Credits</b>\n"
            f"👥 Tumhare refers: <b>{udata.get('refer_count', 0)}</b>\n"
            f"🎟️ Tumhare credits: <b>{credits}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📎 <b>Tera Unique Refer Link:</b>\n"
            f"<code>{refer_link}</code>\n\n"
            "👆 Copy karo aur dosto ko bhejo!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={refer_link}&text=🎯+Wingo+30+Predictor+Bot!")],
                [InlineKeyboardButton("🏠 Back", callback_data="back_main")],
            ]))

    elif query.data == "howto":
        await query.edit_message_text(
            "📊 <b>Kaise Kaam Karta Hai?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Wingo 30 ka last result dekho\n"
            "2️⃣ Last 3 digits copy karo\n"
            "3️⃣ Bot mein enter karo\n\n"
            "🧠 <b>Algorithm Factors:</b>\n"
            "  • Digit Sum Pattern\n  • Modulo Analysis (÷3, ÷7)\n"
            "  • Even/Odd Distribution\n  • Range Calculation\n  • Last Digit Weight\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎟️ <b>Credit System:</b>\n"
            f"  • New user: {NEW_USER_CREDITS} free credits\n"
            f"  • Refer karo: +{REFER_CREDITS} credits\n"
            "  • 1 prediction = 1 credit\n\n"
            "⚠️ <i>Sirf entertainment ke liye hai</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]))

    elif query.data == "channels":
        ch_lines = [f"📢 @{ch['username']}" if ch.get("username") else f"🔒 {ch['name']} (Private)" for ch in CHANNELS]
        await query.edit_message_text(
            f"📢 <b>Humare Channels:</b>\n\n{chr(10).join(ch_lines)}\n\nJoin karo latest predictions ke liye! 🔥",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]))

    elif query.data == "back_main":
        udata = get_user(user.id); credits = udata["credits"] if udata else 0
        await query.edit_message_text(
            "🤖 <b>Wingo 30 Big/Small Predictor</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎟️ Tumhare Credits: <b>{credits}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "👇 <b>Get Prediction</b> dabao:",
            parse_mode="HTML", reply_markup=main_keyboard(credits))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    if update.message.chat.type != "private":
        return
    if is_banned(user.id):
        await update.message.reply_text("🚫 Aapko ban kar diya gaya hai.")
        return

    if context.user_data.get("waiting_for_digits"):
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            context.user_data["waiting_for_digits"] = False
            await update.message.reply_text("🔒 Pehle sabhi channels join karo!", reply_markup=join_channels_keyboard())
            return
        udata = get_user(user.id)
        if not udata or udata["credits"] <= 0:
            context.user_data["waiting_for_digits"] = False
            refer_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
            await update.message.reply_text("😢 <b>Credits Khatam!</b>\n\nRefer karo ya Admin se lo:", parse_mode="HTML", reply_markup=no_credits_keyboard(refer_link))
            return

        digits = text.replace(" ", "")
        result = predict_wingo(digits)
        if result.get("error"):
            await update.message.reply_text("⚠️ <b>Invalid Input!</b>\n\nSirf 3 digits enter karo.\nExample: <code>456</code>", parse_mode="HTML")
            return

        deduct_credit(user.id)
        context.user_data["waiting_for_digits"] = False
        udata = get_user(user.id)
        remaining = udata["credits"] if udata else 0

        conf = result["confidence"]
        bar_filled = int(conf / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        if conf >= 70: conf_label = "✅ HIGH"
        elif conf >= 55: conf_label = "⚡ MODERATE"
        else: conf_label = "⚠️ LOW"

        response = (
            f"🎯 <b>WINGO 30 RESULT</b>\n\n"
            f"📥 Input: <b>{digits}</b>\n\n"
            f"🔴 BIG  {'█' * 8}░░\n"
            f"🟢 SMALL {'█' * 8}░░\n\n"
            f"🔮 Prediction: {result['result']}\n"
            f"📊 Confidence: {conf}% {conf_label}\n"
            f"<code>[{bar}]</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━

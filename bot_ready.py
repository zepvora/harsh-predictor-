import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ============================================================
#  ⚙️  CONFIG
# ============================================================
import os
BOT_TOKEN     = os.environ.get("BOT_TOKEN", "8846798377:AAH8BKhwy6Z-GpFUDGBk_kCRnVwvSZJAiZw")
BOT_USERNAME  = "predictor_bot"   # without @

ADMIN_IDS = [6896407205]

CHANNELS = [
    {"name": "🔥 Main Channel",       "username": None,                 "invite_link": "https://t.me/+geNHq7jKIiAyYjJl", "id": -1001813666985},
    {"name": "📈 Trade With Sniper",  "username": "snipertradingshort", "invite_link": None,                              "id": -1003750001776},
    {"name": "💎 Premium Group",      "username": None,                 "invite_link": "https://t.me/+i1aDUi_W8bE3ZTVl",  "id": -1003765229156},
    {"name": "💬 Discussions On Top", "username": "disscussionbfx",     "invite_link": None,                              "id": -1003999268364},
]

DM_USERNAME       = "Predictorisdope"
REGISTER_LINK     = "https://www.rajaparty5.com/#/register?invitationCode=365122527807"

NEW_USER_CREDITS  = 7
REFER_CREDITS     = 4
CREDITS_PER_PRED  = 1
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
            user_id      INTEGER PRIMARY KEY,
            username     TEXT,
            first_name   TEXT,
            joined_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified     INTEGER DEFAULT 0,
            credits      INTEGER DEFAULT 0,
            referred_by  INTEGER DEFAULT NULL,
            refer_count  INTEGER DEFAULT 0
        )
    """)
    for col, definition in [
        ("credits",     "INTEGER DEFAULT 7"),
        ("referred_by", "INTEGER DEFAULT NULL"),
        ("refer_count", "INTEGER DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
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
        conn.commit()
        is_new = True
    else:
        is_new = False
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
    c.execute("SELECT user_id, username, first_name, verified, credits, referred_by, refer_count FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "username": row[1], "first_name": row[2],
                "verified": row[3], "credits": row[4], "referred_by": row[5], "refer_count": row[6]}
    return None

def deduct_credit(user_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits - 1 WHERE user_id=? AND credits > 0", (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def add_credits(user_id, amount):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def increment_refer_count(referrer_id):
    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET refer_count = refer_count + 1, credits = credits + ? WHERE user_id=?",
              (REFER_CREDITS, referrer_id))
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
        result     = "BIG 🔴"
        confidence = round((big_score / total) * 100)
        color      = "🔴"
        trend      = "📈"
    else:
        result     = "SMALL 🟢"
        confidence = round((small_score / total) * 100)
        color      = "🟢"
        trend      = "📉"

    return {
        "error": False,
        "result": result,
        "confidence": confidence,
        "color": color,
        "trend": trend,
        "digit_sum": digit_sum,
        "big_score": big_score,
        "small_score": small_score,
    }

# ──────────────────────────────────────────────
# KEYBOARDS
# ──────────────────────────────────────────────
def join_channels_keyboard():
    buttons = []
    for ch in CHANNELS:
        link = ch["invite_link"] if ch.get("invite_link") else f"https://t.me/{ch['username']}"
        buttons.append([InlineKeyboardButton(f"📢 {ch['name']}", url=link)])
    buttons.append([InlineKeyboardButton("✅ Verify Karo", callback_data="verify")])
    return InlineKeyboardMarkup(buttons)

def main_keyboard(credits=0):
    credit_label = f"🎯 Get Prediction  [{credits} 🎟️]"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(credit_label, callback_data="predict")],
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
# CHANNEL CHECK
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
            await context.bot.send_message(
                referred_by,
                f"🎉 <b>+{REFER_CREDITS} Credits Mile!</b>\n\n"
                f"✅ <b>{user.first_name}</b> ne tumhara refer link use kiya!\n"
                f"🎟️ Tumhare account mein <b>{REFER_CREDITS} credits</b> add ho gaye!",
                parse_mode="HTML"
            )
        except Exception:
            pass

    not_joined = await check_all_channels(user.id, context.bot)

    if not_joined:
        text = (
            f"👋 Welcome <b>{user.first_name}</b>!\n\n"
            "🔒 <b>Bot Access Locked</b>\n\n"
            "Sabhi channels join karo, phir\n"
            "<b>✅ Verify Karo</b> button dabao!\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎟️ Join karne ke baad milenge: <b>{NEW_USER_CREDITS} Free Credits!</b>\n"
            f"   (5 Base + 2 Bonus 🎁)"
        )
        await update.message.reply_text(text, parse_mode="HTML",
                                        reply_markup=join_channels_keyboard())
    else:
        set_verified(user.id)
        udata = get_user(user.id)
        credits = udata["credits"] if udata else NEW_USER_CREDITS
        text = (
            f"✅ <b>Welcome {user.first_name}!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 <b>Wingo 30 Big/Small Predictor</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎟️ Tumhare Credits: <b>{credits}</b>\n\n"
            "👇 <b>Get Prediction</b> dabao:"
        )
        await update.message.reply_text(text, parse_mode="HTML",
                                        reply_markup=main_keyboard(credits))

# ──────────────────────────────────────────────
# ADMIN COMMANDS (proper CommandHandlers)
# ──────────────────────────────────────────────
async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Tum admin nahi ho!")
        return

    if len(context.args) == 2:
        try:
            target_id = int(context.args[0])
            amount    = int(context.args[1])
            add_credits(target_id, amount)

            # Target user ko bhi notify karo
            try:
                udata = get_user(target_id)
                new_credits = udata["credits"] if udata else amount
                await context.bot.send_message(
                    target_id,
                    f"🎉 <b>Credits Mile!</b>\n\n"
                    f"🎟️ Admin ne <b>{amount} credits</b> add kiye!\n"
                    f"💰 Ab tumhare total credits: <b>{new_credits}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass  # User ne bot block kiya hoga

            await update.message.reply_text(
                f"✅ <b>Done!</b>\n\n"
                f"👤 User ID: <code>{target_id}</code>\n"
                f"🎟️ Credits Added: <b>{amount}</b>",
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ <b>Format galat hai!</b>\n\nSahi format:\n<code>/addcredits USER_ID AMOUNT</code>\n\nExample:\n<code>/addcredits 6896407205 10</code>",
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text(
            "❌ <b>Format galat hai!</b>\n\nSahi format:\n<code>/addcredits USER_ID AMOUNT</code>\n\nExample:\n<code>/addcredits 6896407205 10</code>",
            parse_mode="HTML"
        )

async def removecredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Tum admin nahi ho!")
        return

    if len(context.args) == 2:
        try:
            target_id = int(context.args[0])
            amount    = int(context.args[1])
            conn = sqlite3.connect("bot_users.db")
            c = conn.cursor()
            c.execute("UPDATE users SET credits = MAX(0, credits - ?) WHERE user_id=?", (amount, target_id))
            conn.commit()
            conn.close()
            await update.message.reply_text(
                f"✅ <b>Done!</b>\n\n"
                f"👤 User ID: <code>{target_id}</code>\n"
                f"🎟️ Credits Removed: <b>{amount}</b>",
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text("❌ Format: /removecredits USER_ID AMOUNT")
    else:
        await update.message.reply_text("❌ Format: /removecredits USER_ID AMOUNT")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    total = get_total_users()
    await update.message.reply_text(
        f"📊 <b>Bot Stats</b>\n\n"
        f"👥 Total Users: <b>{total}</b>",
        parse_mode="HTML"
    )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /broadcast MESSAGE")
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
    await update.message.reply_text(
        f"📢 <b>Broadcast Done!</b>\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
        parse_mode="HTML"
    )

async def checkuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: kisi bhi user ki info dekho"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    if len(context.args) == 1:
        try:
            target_id = int(context.args[0])
            udata = get_user(target_id)
            if udata:
                await update.message.reply_text(
                    f"👤 <b>User Info</b>\n\n"
                    f"🆔 ID: <code>{udata['user_id']}</code>\n"
                    f"📛 Name: {udata['first_name']}\n"
                    f"🎟️ Credits: <b>{udata['credits']}</b>\n"
                    f"👥 Refers: {udata['refer_count']}\n"
                    f"✅ Verified: {'Yes' if udata['verified'] else 'No'}",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ User nahi mila database mein!")
        except ValueError:
            await update.message.reply_text("❌ Format: /checkuser USER_ID")
    else:
        await update.message.reply_text("❌ Format: /checkuser USER_ID")

# ──────────────────────────────────────────────
# BUTTON HANDLER
# ──────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    await query.answer()

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
                f"⚠️ <b>Abhi bhi join nahi kiya:</b>\n\n{names}\n\n"
                "Sabhi channels join karo phir verify karo! 👆",
                parse_mode="HTML",
                reply_markup=join_channels_keyboard()
            )
        else:
            set_verified(user.id)
            udata = get_user(user.id)
            credits = udata["credits"]
            await query.edit_message_text(
                f"🎉 <b>Verified! Welcome {user.first_name}!</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🎟️ Tumhare Credits: <b>{credits}</b>\n"
                f"   (5 Base + 2 Bonus 🎁)\n\n"
                "Ek prediction = 1 credit\n"
                "Refer karo = 4 credits kamao! 🔗\n\n"
                "👇 Prediction lene ke liye button dabao:",
                parse_mode="HTML",
                reply_markup=main_keyboard(credits)
            )

    elif query.data == "predict":
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            await query.edit_message_text(
                "🔒 <b>Access Denied!</b>\n\nPehle sabhi channels join karo:",
                parse_mode="HTML",
                reply_markup=join_channels_keyboard()
            )
            return

        if credits <= 0:
            refer_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
            await query.edit_message_text(
                "😢 <b>Credits Khatam Ho Gaye!</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🎟️ Credits pane ke 2 tarike:\n\n"
                f"🔗 <b>Refer karo</b> → +{REFER_CREDITS} credits per refer\n"
                f"🎰 <b>Register karo</b> → Bonus earn karo\n\n"
                f"📎 Tera Refer Link:\n<code>{refer_link}</code>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💬 Ya Admin se contact karo:",
                parse_mode="HTML",
                reply_markup=no_credits_keyboard(refer_link)
            )
            return

        context.user_data["waiting_for_digits"] = True
        await query.edit_message_text(
            "🎯 <b>Wingo 30 Predictor</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎟️ Credits: <b>{credits}</b> (1 credit use hoga)\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 <b>Last 3 digits enter karo:</b>\n\n"
            "Example: <code>456</code> ya <code>789</code>\n\n"
            "⬇️ Neeche type karo:",
            parse_mode="HTML"
        )

    elif query.data == "refer":
        refer_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
        refer_count = udata.get("refer_count", 0)
        await query.edit_message_text(
            "🔗 <b>Refer & Earn System</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Har successful refer pe: <b>+{REFER_CREDITS} Credits</b>\n"
            f"👥 Tumhare total refers: <b>{refer_count}</b>\n"
            f"🎟️ Tumhare credits: <b>{credits}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📎 <b>Tera Unique Refer Link:</b>\n"
            f"<code>{refer_link}</code>\n\n"
            "👆 Copy karo aur dosto ko bhejo!\n"
            "Jab woh join karenge, tumhe automatic credit milega! 🎉",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={refer_link}&text=🎯+Wingo+30+Predictor+Bot+-+Free+Predictions!")],
                [InlineKeyboardButton("🏠 Back", callback_data="back_main")],
            ])
        )

    elif query.data == "howto":
        await query.edit_message_text(
            "📊 <b>Kaise Kaam Karta Hai?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Wingo 30 ka last result dekho\n"
            "2️⃣ Last 3 digits copy karo\n"
            "3️⃣ Bot mein enter karo\n\n"
            "🧠 <b>Algorithm Factors:</b>\n"
            "  • Digit Sum Pattern\n"
            "  • Modulo Analysis (÷3, ÷7)\n"
            "  • Even/Odd Distribution\n"
            "  • Range Calculation\n"
            "  • Last Digit Weight\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎟️ <b>Credit System:</b>\n"
            f"  • New user: {NEW_USER_CREDITS} free credits\n"
            f"  • Refer karo: +{REFER_CREDITS} credits\n"
            "  • 1 prediction = 1 credit\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ <i>Sirf entertainment ke liye hai</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )

    elif query.data == "channels":
        ch_lines = []
        for ch in CHANNELS:
            if ch.get("username"):
                ch_lines.append(f"📢 @{ch['username']}")
            else:
                ch_lines.append(f"🔒 {ch['name']} (Private)")
        ch_list = "\n".join(ch_lines)
        await query.edit_message_text(
            f"📢 <b>Humare Channels:</b>\n\n{ch_list}\n\n"
            "Join karo latest predictions ke liye! 🔥",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )

    elif query.data == "back_main":
        udata = get_user(user.id)
        credits = udata["credits"] if udata else 0
        await query.edit_message_text(
            "🤖 <b>Wingo 30 Big/Small Predictor</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎟️ Tumhare Credits: <b>{credits}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "👇 <b>Get Prediction</b> dabao:",
            parse_mode="HTML",
            reply_markup=main_keyboard(credits)
        )

# ──────────────────────────────────────────────
# MESSAGE HANDLER
# ──────────────────────────────────────────────
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if context.user_data.get("waiting_for_digits"):
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            context.user_data["waiting_for_digits"] = False
            await update.message.reply_text(
                "🔒 Pehle sabhi channels join karo!",
                reply_markup=join_channels_keyboard()
            )
            return

        udata = get_user(user.id)
        if not udata or udata["credits"] <= 0:
            context.user_data["waiting_for_digits"] = False
            refer_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
            await update.message.reply_text(
                "😢 <b>Credits Khatam!</b>\n\nRefer karo ya register karo credits pane ke liye:",
                parse_mode="HTML",
                reply_markup=no_credits_keyboard(refer_link)
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

        success = deduct_credit(user.id)
        context.user_data["waiting_for_digits"] = False

        udata = get_user(user.id)
        remaining = udata["credits"] if udata else 0

        conf       = result["confidence"]
        bar_filled = int(conf / 10)
        bar        = "█" * bar_filled + "░" * (10 - bar_filled)

        if conf >= 70:
            conf_label = "🔥 HIGH"
        elif conf >= 55:
            conf_label = "⚡ MEDIUM"
        else:
            conf_label = "⚠️ LOW"

        response = (
            "╔══════════════════════╗\n"
            "  🤖 <b>WINGO 30 PREDICTION</b>\n"
            "╚══════════════════════╝\n\n"
            f"📥 <b>Input:</b> <code>{digits}</code>\n\n"
            f"{result['color']} <b>Result: {result['result']}</b>\n\n"
            f"📊 <b>Confidence:</b> {conf}% {conf_label}\n"
            f"<code>[{bar}]</code>\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📈 <b>Analysis:</b>\n"
            f"  {result['trend']} Digit Sum: <b>{result['digit_sum']}</b>\n"
            f"  🔴 BIG Score:   <b>{result['big_score']}/8</b>\n"
            f"  🟢 SMALL Score: <b>{result['small_score']}/8</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🎟️ Baaki Credits: <b>{remaining}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚠️ <i>Sirf entertainment ke liye</i>"
        )

        kb_buttons = [
            [InlineKeyboardButton("🔄 Predict Again", callback_data="predict")],
        ]
        if remaining <= 1:
            refer_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
            kb_buttons.append([InlineKeyboardButton("🔗 Refer & Earn Credits", url=refer_link)])
        kb_buttons.append([
            InlineKeyboardButton("💬 DM Admin", url=f"https://t.me/{DM_USERNAME}"),
            InlineKeyboardButton("🎰 Register", url=REGISTER_LINK)
        ])
        kb_buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")])

        await update.message.reply_text(
            response,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb_buttons)
        )
    else:
        not_joined = await check_all_channels(user.id, context.bot)
        if not_joined:
            await update.message.reply_text(
                "🔒 Pehle channels join karo!",
                reply_markup=join_channels_keyboard()
            )
        else:
            udata = get_user(user.id)
            credits = udata["credits"] if udata else 0
            await update.message.reply_text(
                f"🎟️ Tumhare Credits: <b>{credits}</b>\n\n👇 Menu use karo:",
                parse_mode="HTML",
                reply_markup=main_keyboard(credits)
            )

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Start
    app.add_handler(CommandHandler("start", start))

    # ✅ Admin Commands (properly registered)
    app.add_handler(CommandHandler("addcredits", addcredits_command))
    app.add_handler(CommandHandler("removecredits", removecredits_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("checkuser", checkuser_command))

    # Buttons & Messages
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("✅ Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

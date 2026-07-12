import logging

    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /removecredits <user_id> <amount>")
        return
    try:
        uid = int(context.args[0]); amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Sahi values daalo.")
        return
    remove_credits(uid, amount)
    await update.message.reply_text(f"✅ Done!\n👤 User: <code>{uid}</code>\n🎟️ Removed: <b>{amount}</b>", parse_mode="HTML")


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
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
    await update.message.reply_text(f"🚫 User <code>{uid}</code> ban kar diya!", parse_mode="HTML")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
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
    await update.message.reply_text(f"✅ User <code>{uid}</code> unban kar diya!", parse_mode="HTML")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
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
    await update.message.reply_text(f"📢 Broadcast Done!\n✅ Sent: {sent}\n❌ Failed: {failed}")


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
    app.add_handler(CommandHandler("checkuser", cmd_checkuser))
    app.add_handler(CommandHandler("addcredits", cmd_addcredits))
    app.add_handler(CommandHandler("removecredits", cmd_removecredits))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("✅ Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

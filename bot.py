import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from database import Database
from ai_engine import (
    chat, get_intro, generate_caption,
    get_feedback_prompt, detect_language, clear_session
)
from scraper import fetch_memes
from config import (
    BOT_TOKEN, ADMIN_ID, CHANNEL_USERNAME,
    OWNER_USERNAME, BOT_USERNAME, MEMES_PER_BATCH
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('memebot.log')]
)
logger = logging.getLogger(__name__)

db = Database()

# User state tracking
user_states: dict = {}
# {user_id: {'state': 'idle/awaiting_format/awaiting_quality/awaiting_feedback',
#             'query': str, 'style': str, 'format': str, 'lang': str}}


def get_state(uid): return user_states.get(uid, {'state': 'idle', 'lang': 'hinglish'})
def set_state(uid, **kwargs):
    current = get_state(uid)
    current.update(kwargs)
    user_states[uid] = current


def is_admin(uid): return str(uid) == str(ADMIN_ID)


# ─────────────────────────────────────────
# CHANNEL CHECK
# ─────────────────────────────────────────
async def check_member(bot, uid) -> bool:
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ["member", "administrator", "creator"]
    except Exception:
        return False


async def send_join_prompt(update: Update):
    keyboard = [[
        InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"),
        InlineKeyboardButton("✅ Verify", callback_data="verify_join")
    ]]
    await update.message.reply_text(
        "⛔ <b>Ruk ja bhai!</b>\n\n"
        "Pehle humara channel join kar,\n"
        "tab memes milenge! 😤\n\n"
        "👇 Join kar aur Verify dabao:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─────────────────────────────────────────
# /start
# ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    # Register user
    db.add_or_update_user(uid, user.username or "", user.first_name or "User")

    # Check ban
    if db.is_banned(uid):
        await update.message.reply_text("🚫 Tu banned hai. Contact @ethicalrobo.")
        return

    # Check membership
    if not await check_member(context.bot, uid):
        await send_join_prompt(update)
        return

    # Detect language
    sample = user.first_name or ""
    lang = detect_language(sample)
    set_state(uid, state='idle', lang=lang)

    # Generate AI intro
    intro_text = get_intro(user.first_name or "Bhai", lang)

    keyboard = [
        [
            InlineKeyboardButton("👑 Admin", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}"),
            InlineKeyboardButton("❓ Help", callback_data="show_help")
        ]
    ]

    await update.message.reply_text(
        intro_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# VERIFY CALLBACK
# ─────────────────────────────────────────
async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Checking...")
    uid = query.from_user.id

    if await check_member(context.bot, uid):
        user = query.from_user
        db.add_or_update_user(uid, user.username or "", user.first_name or "User")
        lang = detect_language(user.first_name or "")
        set_state(uid, state='idle', lang=lang)

        intro_text = get_intro(user.first_name or "Bhai", lang)
        keyboard = [[
            InlineKeyboardButton("👑 Admin", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}"),
            InlineKeyboardButton("❓ Help", callback_data="show_help")
        ]]
        await query.edit_message_text(intro_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        keyboard = [[
            InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"),
            InlineKeyboardButton("✅ Verify Again", callback_data="verify_join")
        ]]
        await query.edit_message_text(
            "❌ <b>Abhi tak join nahi kiya!</b>\n\nJoin kar phir verify kar. 😤",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ─────────────────────────────────────────
# HELP CALLBACK
# ─────────────────────────────────────────
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]
    await query.edit_message_text(
        "❓ <b>InstasMeme Bot — Full Guide</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 <b>Bot kaise kaam karta hai:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ Kuch bhi likh — AI baat karega\n"
        "2️⃣ Meme maango — AI samjhega\n"
        "3️⃣ Format chuno: Photo/Video/Sound\n"
        "4️⃣ 4 memes ek saath milenge\n"
        "5️⃣ AI feedback lega — aur do ya alag?\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💬 <b>Examples:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "• \"israel iran war meme do\"\n"
        "• \"funny cat memes chahiye\"\n"
        "• \"modi ji meme video\"\n"
        "• \"dark humor sound effect\"\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌐 <b>Sources:</b>\n"
        "Pinterest → Reddit → Instagram → YouTube\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔧 <b>Commands:</b>\n"
        "/start — Bot restart karo\n"
        "/reset — Conversation reset karo\n\n"
        "👑 Support: @ethicalrobo",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    lang = get_state(uid).get('lang', 'hinglish')
    intro_text = get_intro(query.from_user.first_name or "Bhai", lang)
    keyboard = [[
        InlineKeyboardButton("👑 Admin", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}"),
        InlineKeyboardButton("❓ Help", callback_data="show_help")
    ]]
    await query.edit_message_text(intro_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ─────────────────────────────────────────
# FORMAT SELECTION
# ─────────────────────────────────────────
async def ask_format(message, query_text: str, style: str, uid: int):
    set_state(uid, state='awaiting_format', query=query_text, style=style)
    keyboard = [[
        InlineKeyboardButton("📷 Photo", callback_data="format_photo"),
        InlineKeyboardButton("🎬 Video", callback_data="format_video"),
        InlineKeyboardButton("🔊 Sound", callback_data="format_sound"),
    ]]
    lang = get_state(uid).get('lang', 'hinglish')
    texts = {
        'hindi': "Kaunsa format chahiye? 🤔",
        'english': "What format do you want? 🤔",
        'hinglish': "Kaunsa format chahiye bhai? 🤔"
    }
    await message.reply_text(
        texts.get(lang, texts['hinglish']),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def format_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    fmt = query.data.replace("format_", "")
    set_state(uid, format=fmt, state='fetching')

    lang = get_state(uid).get('lang', 'hinglish')
    loading_texts = {
        'hindi': f"{'📷' if fmt == 'photo' else '🎬' if fmt == 'video' else '🔊'} Dhundh raha hun...",
        'english': f"{'📷' if fmt == 'photo' else '🎬' if fmt == 'video' else '🔊'} Searching...",
        'hinglish': f"{'📷' if fmt == 'photo' else '🎬' if fmt == 'video' else '🔊'} Dhundh raha hun bhai..."
    }

    await query.edit_message_text(loading_texts.get(lang, loading_texts['hinglish']))
    await send_memes(query.message, uid, context)


# ─────────────────────────────────────────
# SEND MEMES
# ─────────────────────────────────────────
async def send_memes(message, uid: int, context):
    state = get_state(uid)
    query_text = state.get('query', 'funny meme')
    style = state.get('style', 'funny')
    fmt = state.get('format', 'photo')
    lang = state.get('lang', 'hinglish')

    # Fetch memes
    result = fetch_memes(f"{query_text} {style}", media_type=fmt, count=MEMES_PER_BATCH)
    memes = result['results']
    source = result['source']

    if not memes:
        no_result_texts = {
            'hindi': "😔 Kuch nahi mila yaar. Alag query try karo!",
            'english': "😔 Nothing found. Try a different query!",
            'hinglish': "😔 Kuch nahi mila bhai. Alag try karo!"
        }
        await message.reply_text(no_result_texts.get(lang, no_result_texts['hinglish']))
        set_state(uid, state='idle')
        return

    # Generate caption
    caption = generate_caption(query_text, style, lang)

    # Send memes
    sent_count = 0
    for i, meme in enumerate(memes[:MEMES_PER_BATCH]):
        try:
            meme_caption = f"{caption}\n\n🔍 <i>{source}</i>" if i == 0 else None
            if fmt == 'photo':
                await context.bot.send_photo(
                    uid, meme['url'],
                    caption=meme_caption,
                    parse_mode="HTML"
                )
            elif fmt == 'video':
                await context.bot.send_video(
                    uid, meme['url'],
                    caption=meme_caption,
                    parse_mode="HTML",
                    supports_streaming=True
                )
            elif fmt == 'sound':
                await context.bot.send_audio(
                    uid, meme['url'],
                    caption=meme_caption,
                    parse_mode="HTML",
                    title=meme.get('title', query_text)
                )
            sent_count += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"Failed to send meme: {e}")
            continue

    db.log_search(uid, query_text, source, sent_count)

    if sent_count == 0:
        await message.reply_text("😬 Memes load nahi ho paaye. Dobara try karo!")
        set_state(uid, state='idle')
        return

    # AI Feedback
    feedback_text = get_feedback_prompt(query_text, sent_count, lang)
    keyboard = [
        [
            InlineKeyboardButton("🔁 Aur Do", callback_data="more_memes"),
            InlineKeyboardButton("🔀 Alag Type", callback_data="change_type"),
        ],
        [InlineKeyboardButton("✅ Theek Hai", callback_data="done_memes")]
    ]
    await context.bot.send_message(
        uid, feedback_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    set_state(uid, state='awaiting_feedback')


# ─────────────────────────────────────────
# FEEDBACK CALLBACKS
# ─────────────────────────────────────────
async def more_memes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Loading more! 🔥")
    uid = query.from_user.id
    await query.edit_message_text("🔄 Aur dhundh raha hun...")
    await send_memes(query.message, uid, context)


async def change_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    lang = get_state(uid).get('lang', 'hinglish')
    texts = {
        'hindi': "Kya alag chahiye? Batao!",
        'english': "What do you want instead? Tell me!",
        'hinglish': "Bata kya alag chahiye! 🤔"
    }
    await query.edit_message_text(texts.get(lang, texts['hinglish']))
    set_state(uid, state='refining')


async def done_memes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    lang = get_state(uid).get('lang', 'hinglish')
    texts = {
        'hindi': "👍 Achha! Aur chahiye toh bata!",
        'english': "👍 Cool! Ask me anything else!",
        'hinglish': "👍 Done! Aur kuch chahiye toh bol!"
    }
    await query.edit_message_text(texts.get(lang, texts['hinglish']))
    set_state(uid, state='idle')


# ─────────────────────────────────────────
# MAIN MESSAGE HANDLER
# ─────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    text = update.message.text or ""

    # Check ban
    if db.is_banned(uid):
        await update.message.reply_text("🚫 Tu banned hai.")
        return

    # Check membership
    if not await check_member(context.bot, uid):
        await send_join_prompt(update)
        return

    # Register
    db.add_or_update_user(uid, user.username or "", user.first_name or "")

    state = get_state(uid)
    current_state = state.get('state', 'idle')
    lang = state.get('lang', detect_language(text))
    set_state(uid, lang=lang)

    # Handle refinement state
    if current_state == 'refining':
        prev_query = state.get('query', '')
        from ai_engine import refine_query
        new_query = refine_query(text, prev_query, lang)
        set_state(uid, query=new_query, state='awaiting_format')
        await ask_format(update.message, new_query, state.get('style', 'funny'), uid)
        return

    # Send typing action
    await context.bot.send_chat_action(uid, 'typing')

    # AI Chat
    result = chat(uid, text)

    if result['type'] == 'meme_request':
        # AI detected meme request
        query_text = result['query']
        style = result['style']

        # Brief savage ack
        ack_texts = {
            'hindi': f"Aye aye! '{query_text}' ke memes dhundh raha hun... 🔍",
            'english': f"On it! Searching for '{query_text}' memes... 🔍",
            'hinglish': f"Aye aye! '{query_text}' ke memes dhundh raha hun... 🔍"
        }

        set_state(uid, query=query_text, style=style)
        await ask_format(update.message, query_text, style, uid)

    else:
        # Normal chat response
        await update.message.reply_text(result['text'])


# ─────────────────────────────────────────
# /reset
# ─────────────────────────────────────────
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    clear_session(uid)
    set_state(uid, state='idle')
    lang = get_state(uid).get('lang', 'hinglish')
    texts = {
        'hindi': "🔄 Reset! Fresh start karte hain!",
        'english': "🔄 Reset! Fresh start!",
        'hinglish': "🔄 Reset! Fresh start bhai!"
    }
    await update.message.reply_text(texts.get(lang, texts['hinglish']))


# ─────────────────────────────────────────
# ADMIN PANEL
# ─────────────────────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only!")
        return

    stats = db.get_stats()
    keyboard = [
        [InlineKeyboardButton("👥 User List", callback_data="admin_users")],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban")
        ],
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_stats")]
    ]

    top_q = "\n".join([f"  • {q[0]} ({q[1]}x)" for q in stats['top_queries']]) or "  None yet"

    await update.message.reply_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: <b>{stats['total_users']}</b>\n"
        f"✅ Active: <b>{stats['active_users']}</b>\n"
        f"🚫 Banned: <b>{stats['banned_users']}</b>\n"
        f"🆕 New Today: <b>{stats['new_today']}</b>\n"
        f"🔍 Total Searches: <b>{stats['total_searches']}</b>\n\n"
        f"🔥 <b>Top Queries:</b>\n{top_q}\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id

    if not is_admin(uid):
        await query.answer("❌ Admin only!", show_alert=True)
        return

    await query.answer()

    if query.data == "admin_users":
        users = db.get_user_list(limit=20)
        if not users:
            await query.edit_message_text("No users yet.")
            return
        text = "👥 <b>User List (Last 20):</b>\n\n"
        for u in users:
            status = "🚫" if u['is_banned'] else "✅"
            uname = f"@{u['username']}" if u['username'] else "No username"
            text += f"{status} <code>{u['user_id']}</code> — {u['first_name']} ({uname}) | 🔍{u['total_searches']}\n"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "admin_stats":
        stats = db.get_stats()
        top_q = "\n".join([f"  • {q[0]} ({q[1]}x)" for q in stats['top_queries']]) or "  None yet"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(
            f"📊 <b>Refreshed Stats</b>\n\n"
            f"👥 Total: {stats['total_users']} | Active: {stats['active_users']} | Banned: {stats['banned_users']}\n"
            f"🆕 New Today: {stats['new_today']}\n"
            f"🔍 Searches: {stats['total_searches']}\n\n"
            f"🔥 Top Queries:\n{top_q}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "admin_broadcast":
        context.user_data['admin_action'] = 'broadcast'
        await query.edit_message_text(
            "📢 <b>Broadcast Mode</b>\n\nBhejo jo message sabko bhejna hai:",
            parse_mode="HTML"
        )

    elif query.data == "admin_ban":
        context.user_data['admin_action'] = 'ban'
        await query.edit_message_text(
            "🚫 <b>Ban User</b>\n\nUser ID bhejo (space ke baad reason):\n<code>123456789 spam</code>",
            parse_mode="HTML"
        )

    elif query.data == "admin_back":
        stats = db.get_stats()
        keyboard = [
            [InlineKeyboardButton("👥 User List", callback_data="admin_users")],
            [
                InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
                InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban")
            ],
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_stats")]
        ]
        await query.edit_message_text(
            f"👑 <b>Admin Panel</b>\n\n👥 Users: {stats['total_users']} | Searches: {stats['total_searches']}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin broadcast and ban messages."""
    uid = update.effective_user.id
    if not is_admin(uid):
        return

    action = context.user_data.get('admin_action')
    if not action:
        return

    text = update.message.text

    if action == 'broadcast':
        users = db.get_all_users()
        success = 0
        for user in users:
            try:
                await context.bot.send_message(
                    user['user_id'],
                    f"📢 <b>Announcement</b>\n\n{text}",
                    parse_mode="HTML"
                )
                success += 1
            except Exception:
                pass
        await update.message.reply_text(f"✅ Sent to {success}/{len(users)} users.")
        context.user_data['admin_action'] = None

    elif action == 'ban':
        parts = text.split(' ', 1)
        try:
            ban_uid = int(parts[0])
            reason = parts[1] if len(parts) > 1 else "No reason"
            db.ban_user(ban_uid, reason)
            await update.message.reply_text(f"🚫 User {ban_uid} banned! Reason: {reason}")
        except Exception:
            await update.message.reply_text("❌ Format galat hai. Use: `123456789 reason`")
        context.user_data['admin_action'] = None


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        ban_uid = int(context.args[0])
        db.unban_user(ban_uid)
        await update.message.reply_text(f"✅ User {ban_uid} unbanned!")
    except Exception:
        await update.message.reply_text("❌ Invalid user ID")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("unban", unban_cmd))

    # Callbacks
    app.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^show_help$"))
    app.add_handler(CallbackQueryHandler(back_start, pattern="^back_start$"))
    app.add_handler(CallbackQueryHandler(format_selected, pattern="^format_"))
    app.add_handler(CallbackQueryHandler(more_memes, pattern="^more_memes$"))
    app.add_handler(CallbackQueryHandler(change_type, pattern="^change_type$"))
    app.add_handler(CallbackQueryHandler(done_memes, pattern="^done_memes$"))
    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern="^admin_"))

    # Admin text handler (before main message handler)
    app.add_handler(MessageHandler(
        filters.TEXT & filters.User(user_id=int(ADMIN_ID)),
        admin_message_handler
    ), group=0)

    # Main message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message), group=1)

    logger.info("🤖 InstasMeme Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

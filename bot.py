import logging
import sqlite3
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8645998745:AAE2B3GFipL6NCU9H2oc5mUKU5NZUN_Q6uE")

QUIZ_REWARD = 10
AD_REWARD = 5
REFERRAL_REWARD = 20
MIN_WITHDRAWAL = 500

QUESTIONS = [
    {"q": "Capital of Nigeria?", "options": ["Lagos", "Abuja", "Kano", "Ibadan"], "answer": 1},
    {"q": "15 x 15?", "options": ["200", "215", "225", "230"], "answer": 2},
    {"q": "Closest planet to sun?", "options": ["Venus", "Earth", "Mercury", "Mars"], "answer": 2},
    {"q": "How many days in a week?", "options": ["5", "6", "7", "8"], "answer": 2},
    {"q": "Largest ocean?", "options": ["Atlantic", "Indian", "Arctic", "Pacific"], "answer": 3},
]

logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        coins INTEGER DEFAULT 0,
        referral_code TEXT,
        referred_by INTEGER,
        ads_watched INTEGER DEFAULT 0,
        quizzes_done INTEGER DEFAULT 0,
        btc_address TEXT
    )""")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username, referred_by=None):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    ref_code = f"REF{user_id}"
    c.execute("INSERT OR IGNORE INTO users (user_id, username, referral_code, referred_by) VALUES (?,?,?,?)",
              (user_id, username, ref_code, referred_by))
    if referred_by:
        c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (REFERRAL_REWARD, referred_by))
    conn.commit()
    conn.close()

def get_coins(user_id):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_coins(user_id, amount):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def get_ref_code(user_id):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("SELECT referral_code FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else f"REF{user_id}"

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎮 Play Quiz & Earn", callback_data="quiz")],
        [InlineKeyboardButton("📺 Watch Ad & Earn", callback_data="watch_ad")],
        [InlineKeyboardButton("👥 Referral System", callback_data="referral")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("🏆 Withdraw BTC", callback_data="withdraw")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referred_by = None
    if args and args[0].startswith("REF"):
        try:
            referred_by = int(args[0][3:])
            if referred_by == user.id:
                referred_by = None
        except:
            referred_by = None
    if not get_user(user.id):
        add_user(user.id, user.username or user.first_name, referred_by)
        if referred_by:
            try:
                await context.bot.send_message(referred_by, f"🎉 Someone joined using your referral!\n+{REFERRAL_REWARD} coins added!")
            except:
                pass
    await update.message.reply_text(
        f"🎉 *Welcome to GozzyBot!*\n\n"
        f"🎮 Quiz → +{QUIZ_REWARD} coins\n"
        f"📺 Watch Ads → +{AD_REWARD} coins\n"
        f"👥 Referrals → +{REFERRAL_REWARD} coins\n\n"
        f"💸 Withdraw via Bitcoin!\nMinimum: {MIN_WITHDRAWAL} coins",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    if not get_user(user_id):
        add_user(user_id, query.from_user.username or query.from_user.first_name)

    if data == "menu":
        await query.edit_message_text("🏠 *Main Menu*", parse_mode="Markdown", reply_markup=main_menu())

    elif data == "balance":
        coins = get_coins(user_id)
        usd = round(coins / 100, 2)
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="menu")]]
        await query.edit_message_text(
            f"💰 *Your Balance*\n\n🪙 Coins: *{coins}*\n💵 Value: *${usd}*\n\n"
            f"{'✅ Ready to withdraw!' if coins >= MIN_WITHDRAWAL else f'Need {MIN_WITHDRAWAL - coins} more coins'}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "quiz":
        q = random.choice(QUESTIONS)
        context.user_data["current_question"] = q
        keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer_{i}")] for i, opt in enumerate(q["options"])]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
        await query.edit_message_text(f"🎮 *Quiz Time!*\n\n❓ {q['q']}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("answer_"):
        q = context.user_data.get("current_question")
        if not q:
            await query.edit_message_text("❌ Expired. Try again.", reply_markup=main_menu())
            return
        selected = int(data.split("_")[1])
        kb = [[InlineKeyboardButton("🎮 Play Again", callback_data="quiz")], [InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
        if selected == q["answer"]:
            update_coins(user_id, QUIZ_REWARD)
            await query.edit_message_text(f"✅ *Correct!* +{QUIZ_REWARD} coins!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await query.edit_message_text(f"❌ *Wrong!* Answer: *{q['options'][q['answer']]}*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "watch_ad":
        kb = [[InlineKeyboardButton("✅ I Watched It!", callback_data="ad_done")], [InlineKeyboardButton("🔙 Back", callback_data="menu")]]
        await query.edit_message_text(f"📺 *Watch Ad & Earn*\n\nWatch the ad and click done!\nEarn +{AD_REWARD} coins!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "ad_done":
        update_coins(user_id, AD_REWARD)
        kb = [[InlineKeyboardButton("📺 Watch Another", callback_data="watch_ad")], [InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
        await query.edit_message_text(f"✅ +{AD_REWARD} coins added!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "referral":
        ref_code = get_ref_code(user_id)
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={ref_code}"
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="menu")]]
        await query.edit_message_text(f"👥 *Referral*\n\nYour link:\n`{ref_link}`\n\nEarn +{REFERRAL_REWARD} coins per referral!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "withdraw":
        coins = get_coins(user_id)
        if coins < MIN_WITHDRAWAL:
            kb = [[InlineKeyboardButton("🔙 Back", callback_data="menu")]]
            await query.edit_message_text(f"❌ Need {MIN_WITHDRAWAL - coins} more coins!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        else:
            context.user_data["withdrawing"] = True
            kb = [[InlineKeyboardButton("❌ Cancel", callback_data="menu")]]
            await query.edit_message_text("🏆 Send your *Bitcoin wallet address*:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("withdrawing"):
        context.user_data["withdrawing"] = False
        user_id = update.effective_user.id
        coins = get_coins(user_id)
        await update.message.reply_text(
            f"✅ *Withdrawal Submitted!*\n\nAmount: {coins} coins\nBTC: `{update.message.text}`\n\nProcessed in 24-48hrs.",
            parse_mode="Markdown", reply_markup=main_menu())

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ GozzyBot Running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

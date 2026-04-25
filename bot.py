import logging
import sqlite3
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Configuration
BOT_TOKEN = "8645998745:AAE2B3GFipL6NCU9H2oc5mUKU5NZUN_Q6uE"
ADMIN_ID = None  # Set your Telegram user ID here

# Rewards
QUIZ_REWARD = 10
AD_REWARD = 5
REFERRAL_REWARD = 20
MIN_WITHDRAWAL = 500  # coins equivalent to $5

# Quiz questions
QUESTIONS = [
    {"q": "What is the capital of Nigeria?", "options": ["Lagos", "Abuja", "Kano", "Ibadan"], "answer": 1},
    {"q": "What is 15 x 15?", "options": ["200", "215", "225", "230"], "answer": 2},
    {"q": "Which planet is closest to the sun?", "options": ["Venus", "Earth", "Mercury", "Mars"], "answer": 2},
    {"q": "What color is the sky on a clear day?", "options": ["Green", "Blue", "Red", "Yellow"], "answer": 1},
    {"q": "How many days are in a week?", "options": ["5", "6", "7", "8"], "answer": 2},
    {"q": "What is the largest ocean?", "options": ["Atlantic", "Indian", "Arctic", "Pacific"], "answer": 3},
    {"q": "Who invented the telephone?", "options": ["Edison", "Bell", "Tesla", "Newton"], "answer": 1},
    {"q": "What is 100 divided by 4?", "options": ["20", "25", "30", "40"], "answer": 1},
    {"q": "Which animal is known as man's best friend?", "options": ["Cat", "Dog", "Horse", "Bird"], "answer": 1},
    {"q": "How many hours are in a day?", "options": ["12", "20", "24", "48"], "answer": 2},
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

def update_coins(user_id, amount):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def get_coins(user_id):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_ref_code(user_id):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("SELECT referral_code FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else f"REF{user_id}"

def save_btc_address(user_id, address):
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET btc_address=? WHERE user_id=?", (address, user_id))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect("gozzybot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(coins), SUM(ads_watched), SUM(quizzes_done) FROM users")
    result = c.fetchone()
    conn.close()
    return result

# Main menu
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

    existing = get_user(user.id)
    if not existing:
        add_user(user.id, user.username or user.first_name, referred_by)
        if referred_by:
            try:
                await context.bot.send_message(referred_by,
                    f"🎉 Someone joined using your referral link!\n+{REFERRAL_REWARD} coins added to your balance!")
            except:
                pass

    await update.message.reply_text(
        f"🎉 *Welcome to GozzyBot!*\n\n"
        f"Earn coins by:\n"
        f"🎮 Playing quizzes → +{QUIZ_REWARD} coins\n"
        f"📺 Watching ads → +{AD_REWARD} coins\n"
        f"👥 Referring friends → +{REFERRAL_REWARD} coins\n\n"
        f"💸 Withdraw via *Bitcoin (BTC)*\n"
        f"Minimum: {MIN_WITHDRAWAL} coins ($5)\n\n"
        f"Let's get started! 👇",
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
        await query.edit_message_text("🏠 *Main Menu*\nChoose an option:", parse_mode="Markdown", reply_markup=main_menu())

    elif data == "balance":
        coins = get_coins(user_id)
        usd = round(coins / 100, 2)
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu")]]
        await query.edit_message_text(
            f"💰 *Your Balance*\n\n"
            f"🪙 Coins: *{coins}*\n"
            f"💵 Value: *${usd}*\n\n"
            f"Minimum withdrawal: {MIN_WITHDRAWAL} coins ($5)\n"
            f"{'✅ Ready to withdraw!' if coins >= MIN_WITHDRAWAL else f'❌ Need {MIN_WITHDRAWAL - coins} more coins'}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "quiz":
        q = random.choice(QUESTIONS)
        context.user_data["current_question"] = q
        keyboard = []
        for i, opt in enumerate(q["options"]):
            keyboard.append([InlineKeyboardButton(opt, callback_data=f"answer_{i}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
        await query.edit_message_text(
            f"🎮 *Quiz Time!*\n\n❓ {q['q']}\n\nChoose the correct answer:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("answer_"):
        q = context.user_data.get("current_question")
        if not q:
            await query.edit_message_text("❌ Question expired. Please try again.", reply_markup=main_menu())
            return
        selected = int(data.split("_")[1])
        correct = q["answer"]
        keyboard = [
            [InlineKeyboardButton("🎮 Play Again", callback_data="quiz")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")]
        ]
        if selected == correct:
            update_coins(user_id, QUIZ_REWARD)
            conn = sqlite3.connect("gozzybot.db")
            conn.execute("UPDATE users SET quizzes_done=quizzes_done+1 WHERE user_id=?", (user_id,))
            conn.commit()
            conn.close()
            await query.edit_message_text(
                f"✅ *Correct!*\n\n+{QUIZ_REWARD} coins added!\n🪙 Keep playing to earn more!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                f"❌ *Wrong!*\n\nCorrect answer was: *{q['options'][correct]}*\n\nTry again!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data == "watch_ad":
        keyboard = [
            [InlineKeyboardButton("✅ I Watched the Ad!", callback_data="ad_done")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu")]
        ]
        await query.edit_message_text(
            f"📺 *Watch Ad & Earn*\n\n"
            f"1. Watch the short ad below\n"
            f"2. Click the button when done\n"
            f"3. Earn +{AD_REWARD} coins!\n\n"
            f"🔗 Ad Link: https://go.monetag.com/?bid=your_zone_id\n\n"
            f"_(Replace with your Monetag zone link)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "ad_done":
        conn = sqlite3.connect("gozzybot.db")
        c = conn.cursor()
        c.execute("SELECT ads_watched FROM users WHERE user_id=?", (user_id,))
        result = c.fetchone()
        ads_today = result[0] if result else 0

        if ads_today >= 10:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu")]]
            await query.edit_message_text(
                "⚠️ *Daily limit reached!*\n\nYou can watch max 10 ads per day.\nCome back tomorrow!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            conn.execute("UPDATE users SET ads_watched=ads_watched+1, coins=coins+? WHERE user_id=?", (AD_REWARD, user_id))
            conn.commit()
            keyboard = [
                [InlineKeyboardButton("📺 Watch Another", callback_data="watch_ad")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")]
            ]
            await query.edit_message_text(
                f"✅ *Ad Watched!*\n\n+{AD_REWARD} coins added!\n"
                f"Ads watched today: {ads_today + 1}/10",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        conn.close()

    elif data == "referral":
        ref_code = get_ref_code(user_id)
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={ref_code}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu")]]
        await query.edit_message_text(
            f"👥 *Referral System*\n\n"
            f"Invite friends and earn *+{REFERRAL_REWARD} coins* per referral!\n\n"
            f"🔗 Your referral link:\n`{ref_link}`\n\n"
            f"Share this link with friends!\n"
            f"When they join, you both benefit! 🎉",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "withdraw":
        coins = get_coins(user_id)
        if coins < MIN_WITHDRAWAL:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu")]]
            await query.edit_message_text(
                f"❌ *Insufficient Balance*\n\n"
                f"You have: *{coins} coins*\n"
                f"Minimum: *{MIN_WITHDRAWAL} coins ($5)*\n\n"
                f"Keep earning and come back!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            context.user_data["withdrawing"] = True
            keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="menu")]]
            await query.edit_message_text(
                f"🏆 *Withdraw Bitcoin*\n\n"
                f"Your balance: *{coins} coins (${round(coins/100, 2)})*\n\n"
                f"Please send your *Bitcoin (BTC) wallet address* in the next message:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get("withdrawing"):
        context.user_data["withdrawing"] = False
        save_btc_address(user_id, text)
        coins = get_coins(user_id)
        usd = round(coins / 100, 2)

        # Notify admin
        if ADMIN_ID:
            await context.bot.send_message(
                ADMIN_ID,
                f"💸 WITHDRAWAL REQUEST\n"
                f"User ID: {user_id}\n"
                f"Coins: {coins} (${usd})\n"
                f"BTC Address: {text}"
            )

        await update.message.reply_text(
            f"✅ *Withdrawal Request Submitted!*\n\n"
            f"Amount: *{coins} coins (${usd})*\n"
            f"BTC Address: `{text}`\n\n"
            f"Your request will be processed within 24-48 hours.",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ GozzyBot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()

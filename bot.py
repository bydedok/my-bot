import json
import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# 🔑 ТВОЙ ТОКЕН и ID группы
TOKEN = "8205652665:AAGqfXfMPI0FmJ-ya7Gdl33xAb2TzcW8QUg"
ADMIN_CHAT_ID = -4870640506

# 📂 Файл для хранения сообщений
DATA_FILE = "pending.json"
pending_messages = {}
uid_counter = 0


# ======= Работа с файлами =======
def save_data():
    """Безопасное сохранение данных (через .tmp)."""
    global pending_messages, uid_counter
    tmp_file = DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump({"pending": pending_messages, "uid_counter": uid_counter}, f, ensure_ascii=False)
    os.replace(tmp_file, DATA_FILE)


def load_data():
    """Загрузка данных из файла (если есть)."""
    global pending_messages, uid_counter
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            pending_messages = data.get("pending", {})
            uid_counter = data.get("uid_counter", 0)


# ======= Команды =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["📝 Хочу задать вопрос!", "ℹ️ Информация обо мне"]]
    await update.message.reply_text(
        "Привет! 👋 Я школьный бот-президент.\nВыбери действие:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✍️ Напиши сюда свои пожелания президенту школы:")


async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приём сообщения от ученика."""
    global uid_counter
    user = update.message.from_user
    text = update.message.text

    existing_uid = None
    for uid, msg in pending_messages.items():
        if msg["user_id"] == user.id:
            existing_uid = uid
            break

    if existing_uid:
        pending_messages[existing_uid]["texts"].append(text)
        uid = existing_uid
    else:
        uid_counter += 1
        pending_messages[str(uid_counter)] = {
            "user_id": user.id,
            "name": user.first_name,
            "texts": [text],
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        uid = str(uid_counter)

    save_data()
    await update.message.reply_text("✅ Спасибо за твоё сообщение!")

    # Отправка админу
    keyboard = [[InlineKeyboardButton("Ответить этому ученику", callback_data=f"reply_{uid}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    all_texts = "\n---\n".join(pending_messages[uid]["texts"])
    msg = (
        f"📩 Сообщение (UID: {uid}) от {user.first_name} (ID: {user.id})\n"
        f"🕒 {pending_messages[uid]['timestamp']}\n\n{all_texts}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("reply_"):
        uid = query.data.split("_")[1]
        if uid in pending_messages:
            await query.message.reply_text(
                f"✍️ Чтобы ответить, напиши:\n`/reply {uid} твой текст`",
                parse_mode="Markdown"
            )


async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ отвечает ученику."""
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Используй: /reply <UID> <текст>")
        return

    uid = context.args[0]
    reply_text = " ".join(context.args[1:])

    if uid not in pending_messages:
        await update.message.reply_text("⚠️ UID не найден.")
        return

    user_id = pending_messages[uid]["user_id"]

    try:
        await context.bot.send_message(chat_id=user_id, text=f"📢 Ответ от президента:\n\n{reply_text}")
        await update.message.reply_text("✅ Ответ отправлен ученику.")
        del pending_messages[uid]
        save_data()
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {e}")


async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список непрочитанных сообщений."""
    if not pending_messages:
        await update.message.reply_text("🎉 Нет непрочитанных сообщений.")
    else:
        text = "📋 Непрочитанные сообщения:\n\n"
        for uid, msg in pending_messages.items():
            all_texts = "\n---\n".join(msg["texts"])
            text += (
                f"UID: {uid}\n"
                f"От: {msg['name']} (ID: {msg['user_id']})\n"
                f"🕒 {msg['timestamp']}\n"
                f"{all_texts}\n\n"
            )
        # разбиваем на куски по 4000 символов
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i:i + 4000])


async def about_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👤 Президент школы: Иван Иванов\n"
        "📚 Класс: 10А\n"
        "✨ Хочу сделать школу лучше!"
    )


# ======= Запуск =======
def main():
    load_data()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reply", reply_command))
    app.add_handler(CommandHandler("pending", pending_command))
    app.add_handler(MessageHandler(filters.Regex("^📝 Хочу задать вопрос!$"), ask_question))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^ℹ️ Информация обо мне$"), receive_question))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ Информация обо мне$"), about_me))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

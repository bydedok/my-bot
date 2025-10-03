import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# === Настройки ===
TOKEN = "8205652665:AAGqfXfMPI0FmJ-ya7Gdl33xAb2TzcW8QUg"
ADMIN_CHAT_ID = -4870640506

# === Логирование ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Хранилище сообщений
unread_messages = {}

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Напиши своё сообщение, и его увидит школьный президент.")

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    # Сохраняем сообщение
    if user_id not in unread_messages:
        unread_messages[user_id] = []
    unread_messages[user_id].append(text)

    # Уведомляем админа
    keyboard = [[InlineKeyboardButton("Ответить этому ученику", callback_data=f"reply_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"📩 Новое сообщение от {update.message.from_user.full_name} (ID: {user_id}):\n{text}",
        reply_markup=reply_markup
    )

async def reply_command(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /reply <user_id> <текст>")
        return

    user_id = int(context.args[0])
    reply_text = " ".join(context.args[1:])

    try:
        await context.bot.send_message(chat_id=user_id, text=f"Ответ: {reply_text}")
        if user_id in unread_messages:
            unread_messages.pop(user_id)
        await update.message.reply_text("✅ Ответ отправлен!")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("reply_"):
        user_id = query.data.split("_")[1]
        await query.edit_message_text(text=f"Введите команду: /reply {user_id} <ваш ответ>")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reply", reply_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()

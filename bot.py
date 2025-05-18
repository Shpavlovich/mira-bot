import os
import logging
import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Настройки
openai.api_key = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

user_data = {}

# Промт для Таро
PROMPT_TAROT = """
Ты — Мира, 42 года. Женщина с эзотерическим даром, профессиональный таролог и ясновидящая с более чем 20-летним опытом...

ДАННЫЕ КЛИЕНТА:
{input_text}
"""

# Промт для Матрицы судьбы
PROMPT_MATRIX = """
Ты — Мира, 42 года. Эзотерик, ясновидящая, мастер матрицы судьбы...

ДАННЫЕ КЛИЕНТА:
{input_text}
"""

WELCOME_TEXT = """Здравствуйте!

Первый расклад на Таро или разбор по матрице судьбы — бесплатно, при условии, что после вы оставите отзыв на Авито ✨

⸻

Как оставить заявку:

1️⃣ Нажмите /start
2️⃣ Выберите расклад или матрицу
3️⃣ Пришлите данные
4️⃣ Нажмите «✅ Подтвердить предысторию»
"""

INSTRUCTION_TAROT = (
    "Для расклада пришлите:\n"
    "— Имя и дату рождения\n"
    "— Имена и возраст участников\n"
    "— Предысторию\n"
    "— Чёткий вопрос\n\n"
    "Затем нажмите «✅ Подтвердить предысторию»."
)

INSTRUCTION_MATRIX = (
    "Для разбора по матрице судьбы пришлите:\n"
    "— Дату рождения (ДД.ММ.ГГГГ)\n"
    "— Имя\n\n"
    "Затем нажмите «✅ Подтвердить предысторию»."
)

RESPONSE_WAIT = "Спасибо, всё получила. Запрос отправлен. Ответ готовится..."
REVIEW_TEXT = "Для энергообмена обязательно оставьте отзыв на Авито."

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 Расклад Таро", callback_data="tarot")],
        [InlineKeyboardButton("🌌 Матрица судьбы", callback_data="matrix")]
    ])

def get_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить предысторию", callback_data="confirm")]
    ])

async def ask_gpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=3500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Ошибка OpenAI: {e}")
        return "Произошла ошибка при генерации ответа. Попробуйте позже."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    user_data[chat_id] = {"type": None, "text": ""}
    await update.message.reply_text(WELCOME_TEXT, reply_markup=get_main_keyboard())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    if query.data == "tarot":
        user_data[chat_id] = {"type": "tarot", "text": ""}
        await query.message.reply_text(INSTRUCTION_TAROT, reply_markup=get_confirm_keyboard())

    elif query.data == "matrix":
        user_data[chat_id] = {"type": "matrix", "text": ""}
        await query.message.reply_text(INSTRUCTION_MATRIX, reply_markup=get_confirm_keyboard())

    elif query.data == "confirm":
        data = user_data.get(chat_id)
        if not data or not data["text"].strip():
            await query.message.reply_text("Вы ещё ничего не написали.")
            return

        await query.message.reply_text(RESPONSE_WAIT)

        prompt = PROMPT_TAROT.format(input_text=data["text"]) if data["type"] == "tarot" else PROMPT_MATRIX.format(input_text=data["text"])
        result = await ask_gpt(prompt)

        await context.bot.send_message(chat_id=chat_id, text=result)
        await context.bot.send_message(chat_id=chat_id, text=REVIEW_TEXT)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id in user_data:
        user_data[chat_id]["text"] += "\n" + update.message.text.strip()

# Запуск
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
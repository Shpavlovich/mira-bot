import os
import logging
import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import asyncio

# Настройки
openai.api_key = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

user_data = {}
user_done = set()

# Промт для Таро
PROMPT_TAROT = """Ты — Мира, 42 года. Женщина с эзотерическим даром. Ты создаёшь реалистичный расклад Таро с анализом, как будто это пишет опытный эзотерик.
Ты не пишешь как нейросеть. Текст — живой, реалистичный, с погружением в ситуацию клиента.

ФОРМАТ РАСКЛАДА:
1. Название расклада
2. Позиции (например: 1, 2, 3…)
3. Финальный блок: Совет от карт Таро

Каждая позиция:
— Отдельная карта
— Объём: 500–800 символов
— Подробный анализ карты именно в контексте ситуации клиента
— Прогноз и рекомендации

СТИЛЬ:
— Только «вы», «ваш», «ваша»
— Без шаблонов и одинаковых формулировок
— Энергия каждой карты раскрывается уникально
"""

# Промт для матрицы судьбы
PROMPT_MATRIX = """Разбор матрицы судьбы
Дата рождения: {birth_date}

1. Личность и внутренний стержень
2. Карма рода и задачи души
3. Предназначение
4. Отношения и привязанности
5. Финансы и профессиональная реализация
6. Страхи, блоки, уязвимости
7. Ваши сильные стороны
8. Точка роста: где заложен ключ к прорыву
9. Предупреждения и временные циклы (2025–2027)
10. Финальный вывод

Требования:
— Минимум 6000 символов
— Каждый блок: 1000–1200 символов
— Только обращение «вы», «ваш» и т.д.
— Без вступлений и завершений
— Без повторений и шаблонов
— От имени Мира, 42 года, эзотерик
"""

# Приветственное сообщение
WELCOME_MSG = """Здравствуйте!

Первый расклад на Таро или разбор по матрице судьбы — бесплатно, при условии, что вы потом оставите отзыв на Авито ✨

⸻

Как оставить заявку на расклад или разбор матрицы?

1️⃣ Нажмите /start  
2️⃣ Выберите, что вам нужно:  
— Расклад, если есть конкретный вопрос или ситуация  
— Матрица судьбы, если нужен разбор по дате рождения  
3️⃣ Напишите нужную информацию  
4️⃣ Нажмите кнопку «✅ Подтвердить предысторию»

Обычно я отвечаю в течение 2 часов ⏳
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🃏 Расклад Таро", callback_data="tarot")],
        [InlineKeyboardButton("🌌 Матрица судьбы", callback_data="matrix")],
    ]
    await update.message.reply_text(WELCOME_MSG, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {"type": query.data, "text": ""}
    await query.message.reply_text(
        "Напишите: имя, дата рождения, предыстория и чёткий вопрос. Затем нажмите «✅ Подтвердить предысторию»",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Подтвердить предысторию", callback_data="confirm")]])
    )

async def collect_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_data:
        user_data[user_id]["text"] += update.message.text + "
"

async def confirm_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in user_data:
        info = user_data[user_id]
        await query.message.reply_text("Спасибо, всё получила. Ждите ответ, обычно в течение 2 часов.")

        await asyncio.sleep(2 * 60 * 60)  # 2 часа

        if info["type"] == "tarot":
            prompt = PROMPT_TAROT + "

" + info["text"]
        else:
            prompt = PROMPT_MATRIX.format(birth_date=info["text"].strip())

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content
        await context.bot.send_message(chat_id=user_id, text=result)

def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(confirm_request, pattern="^confirm$"))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_text))
    app.run_polling()

if __name__ == "__main__":
    main()

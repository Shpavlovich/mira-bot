import os
import logging
import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Настройки
openai.api_key = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

user_data = {}
user_done = set()

# Промт для Таро
PROMPT_TAROT = """
Ты — Мира, 42 года. Женщина с эзотерическим даром, профессиональный таролог и ясновидящая с более чем 20-летним опытом. Ты делаешь расклады по имени, дате рождения, фото и конкретным вопросам клиента. Все расклады делаешь вручную, с глубокой проработкой.

Ты не пишешь как нейросеть. Текст — живой, реалистичный, внятный, словно ты лично пишешь клиенту. Без клише, без шаблонов, без фраз, которые выдают ИИ.

ФОРМАТ РАСКЛАДА:
1. Название расклада
2. Позиции (например: 1️⃣, 2️⃣, 3️⃣...)
3. Финальный блок: Совет от карт Таро

Каждая позиция:
— Отдельная карта
— Объём: 500–800 символов
— Подробный анализ карты именно в контексте ситуации клиента
— Карты выбираются случайно, а не по смыслу
— Повторы и выдуманные карты запрещены

Общий объём — минимум 4000 символов

СТРОГОЕ ТРЕБОВАНИЕ:
— Никаких приветствий и вступлений.
— Расклад начинается с названия
— В конце запрещено писать «обратитесь снова» и т.п.
— Последний блок — только «Совет от карт Таро»

ДАННЫЕ КЛИЕНТА:
{input_text}
"""

# Промт для Матрицы судьбы
PROMPT_MATRIX = """
Ты — Мира, 42 года. Эзотерик, ясновидящая, мастер матрицы судьбы. Пишешь как человек с 20-летним опытом, уверенно и глубоко. Работаешь по дате рождения.

СТРУКТУРА:
1. Разбор матрицы судьбы
2. Дата рождения клиента
3. 10 разделов по 1000–1200 символов каждый:
— Личность
— Карма рода
— Предназначение
— Отношения
— Финансы
— Блоки
— Сильные стороны
— Точка роста
— Предупреждения (2025–2027)
— Финальный вывод

ОГРАНИЧЕНИЯ:
— Никаких вступлений и завершений
— Только уникальный текст
— Объём: не менее 6000 символов

ДАННЫЕ КЛИЕНТА:
{input_text}
"""

# Приветственное сообщение
WELCOME_TEXT = """Здравствуйте!

Я сделала этот бот, чтобы вам было проще и быстрее оставить заявку — без ожидания и лишней переписки.

Первый расклад на Таро или разбор по матрице судьбы — бесплатно, при условии, что после вы оставите отзыв на Авито ✨

⸻

Как оставить заявку на расклад или разбор матрицы?

1️⃣ Нажмите /start, если ещё не нажимали.
2️⃣ Выберите, что вам нужно — расклад или матрица судьбы.
3️⃣ Бот напишет, какие данные нужны. Просто ответьте и пришлите всё, что требуется.
4️⃣ Пожалуйста, не расписывайте «вокруг» — без конкретного запроса я не работаю.
5️⃣ Всё, что вы напишете, автоматически пересылается мне в личные сообщения.
Никаких автоответов — я читаю всё сама и делаю каждый разбор вручную.
6️⃣ После этого просто ожидайте. Обычно отвечаю в течение 2–3 часов.

Бот создан только для того, чтобы ускорить обработку заявок и сэкономить ваше время.

Спасибо за доверие и понимание! 🔮"""

INSTRUCTION_TAROT = """Для расклада пришлите:

— Ваше имя и дату рождения
— Имена и возраст участников
— Предысторию
— Чёткий вопрос

Затем нажмите «✅ Подтвердить предысторию»."""

INSTRUCTION_MATRIX = """Для разбора по матрице судьбы пришлите:

— Дату рождения (ДД.ММ.ГГГГ)
— Имя

Затем нажмите «✅ Подтвердить предысторию»."""

RESPONSE_WAIT = "Спасибо, всё получила. Запрос отправлен. Ответ готовится..."
REVIEW_TEXT = "Для энергообмена обязательно оставьте отзыв на авито."

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
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=3500
    )
    return response.choices[0].message.content.strip()

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
        await query.message.reply_text(result)
        await query.message.reply_text(REVIEW_TEXT)

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

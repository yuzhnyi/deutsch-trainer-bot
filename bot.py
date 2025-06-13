# bot.py — Telegram-бот для тренировки перевода слов

import os
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ----------------- Настройки -----------------
TOKEN = "7876094199:AAEursuAwoRiLR_Byvb5O2lGkvqHlf3zMxU"  # Токен явно указан, как просил
WORDS_DIR = "words"  # все CSV-файлы лежат в корне проекта

# ----------------- Помощники -----------------
def list_csv_files():
    files = [f for f in os.listdir(WORDS_DIR) if f.lower().endswith('.csv')]
    return sorted(files)  # сортировка по алфавиту

# ----------------- Обработчики -----------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    files = list_csv_files()
    if not files:
        await update.message.reply_text("❗ Нет CSV-файлов для тестирования.")
        return

    buttons = [
        [InlineKeyboardButton(f"{i+1}. {fname}", callback_data=f"test_{i}")]
        for i, fname in enumerate(files)
    ]
    await update.message.reply_text("Выбери тест (набор слов):",
                                    reply_markup=InlineKeyboardMarkup(buttons))

async def choose_test(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("test_"):
        await query.edit_message_text("❗ Неверный выбор.")
        return

    idx = int(query.data.replace("test_", ""))
    files = list_csv_files()
    if not (0 <= idx < len(files)):
        await query.edit_message_text("❗ Некорректный выбор.")
        return

    fname = files[idx]
    path = os.path.join(WORDS_DIR, fname)

    words = []
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                words.append((row[0].strip(), row[1].strip()))

    if not words:
        await query.edit_message_text(f"❗ Файл {fname} пуст или некорректен.")
        return

    ctx.user_data["words"] = words
    ctx.user_data["pos"] = 0

    await query.edit_message_text(f"Начинаем тест: {fname}")
    await ask_word(update.effective_chat.id, ctx)

async def ask_word(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    pos = ctx.user_data.get("pos", 0)
    words = ctx.user_data.get("words", [])
    if pos >= len(words):
        await ctx.bot.send_message(chat_id, "🏋️ Тест завершён!")
        return

    word = words[pos][0]
    await ctx.bot.send_message(chat_id, f"Переведи: *{word}*", parse_mode="Markdown")

async def check_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    pos = ctx.user_data.get("pos", 0)
    words = ctx.user_data.get("words", [])
    if pos >= len(words):
        return

    correct = words[pos][1]
    if text.lower() == correct.lower():
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неверно. Верный ответ: *{correct}*",
                                        parse_mode="Markdown")

    ctx.user_data["pos"] = pos + 1
    await ask_word(update.message.chat_id, ctx)

# ----------------- Запуск -----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(choose_test))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))

    app.run_polling()

if __name__ == "__main__":
    main()

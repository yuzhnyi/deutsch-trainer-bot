import os
import random
import pandas as pd
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

WORDS_DIR = "words"  # Папка с файлами слов

def list_tests():
    return [f for f in os.listdir(WORDS_DIR) if f.endswith('.csv')]

def load_words(filename):
    df = pd.read_csv(os.path.join(WORDS_DIR, filename), sep=';')
    return df[['Wort', 'Перевод']].to_dict(orient='records')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tests = list_tests()
    buttons = [
        [InlineKeyboardButton(f"{i+1}. {name}", callback_data=f"choose_{name}")]
        for i, name in enumerate(tests)
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "Выбери тест (набор слов):",
        reply_markup=reply_markup
    )

async def choose_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    test_name = query.data.replace('choose_', '')
    words = load_words(test_name)
    selection = random.sample(words, min(10, len(words)))
    context.user_data['current_test'] = test_name
    context.user_data['to_learn'] = selection
    context.user_data['test_words'] = random.sample(selection, len(selection))
    context.user_data['score'] = 0
    context.user_data['current'] = 0

    msg = "Изучи эти слова:\n"
    for w in selection:
        msg += f"{w['Wort']} – {w['Перевод']}\n"
    msg += "\nКогда будешь готов(а), напиши /start_test"
    await query.message.reply_text(msg)

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'test_words' not in context.user_data:
        await update.message.reply_text("Сначала выбери тест (/start)!")
        return
    context.user_data['current'] = 0
    await ask_word(update, context)

async def ask_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'test_words' not in context.user_data:
        target = update.message if update.message else update.callback_query.message
        await target.reply_text("Сессия устарела. Пожалуйста, начни заново с /start.")
        return

    idx = context.user_data.get('current', 0)
    test_words = context.user_data['test_words']
    if idx >= len(test_words):
        score = context.user_data['score']
        total = len(test_words)
        keyboard = [
            [
                InlineKeyboardButton("Повторить эти слова", callback_data='repeat'),
                InlineKeyboardButton("Новые 10 слов", callback_data='new')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        target = update.message if update.message else update.callback_query.message
        await target.reply_text(
            f"Тест окончен!\nВерных ответов: {score} из {total}",
            reply_markup=reply_markup
        )
        return

    word = test_words[idx]['Wort']
    target = update.message if update.message else update.callback_query.message
    await target.reply_text(f"Переведи: {word}")

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'test_words' not in context.user_data:
        await update.message.reply_text("Сначала выбери тест (/start)!")
        return

    answer = update.message.text.strip().lower()
    idx = context.user_data.get('current', 0)
    test_words = context.user_data['test_words']

    if idx >= len(test_words):
        return

    correct = test_words[idx]['Перевод'].strip().lower()
    if answer == correct:
        await update.message.reply_text("Верно!")
        context.user_data['score'] += 1
    else:
        await update.message.reply_text(f"Неверно! Правильный перевод: {correct}")
    context.user_data['current'] += 1
    await ask_word(update, context)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'repeat':
        if 'test_words' not in context.user_data:
            await query.message.reply_text("Сессия устарела. Начни заново с /start.")
            return
        fake_update = Update(update.update_id, message=query.message)
        await ask_word(fake_update, context)

    elif data == 'new':
        test_name = context.user_data.get('current_test')
        if not test_name:
            await query.message.reply_text("Сначала выбери тест заново с /start.")
            return
        words = load_words(test_name)
        selection = random.sample(words, min(10, len(words)))
        context.user_data['to_learn'] = selection
        context.user_data['test_words'] = random.sample(selection, len(selection))
        context.user_data['score'] = 0
        context.user_data['current'] = 0
        msg = "Изучи эти слова:\n"
        for w in selection:
            msg += f"{w['Wort']} – {w['Перевод']}\n"
        msg += "\nКогда будешь готов(а), напиши /start_test"
        await query.message.reply_text(msg)

    elif data.startswith('choose_'):
        await choose_test(update, context)

def main():
    token = "7876094199:AAEursuAwoRiLR_Byvb5O2lGkvqHlf3zMxU"
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_test", start_test))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_answer))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

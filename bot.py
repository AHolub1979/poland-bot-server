import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Состояния опроса
(Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q_DATES, Q_DATES_MORE, FINAL, QUESTION) = range(11)

# ID чата для заявок
ADMIN_CHAT_ID = -1002562481191

# Телефон для консультаций (замени на нужный, если потребуется)
CONSULT_PHONE = "+48 123 456 789"

# --- База пользователей ---
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            city TEXT,
            tags TEXT,
            first_seen TEXT,
            last_seen TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user(user, tags=""):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, city, tags, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user.id, user.username, user.first_name, user.last_name, "", tags,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    c.execute('''
        UPDATE users SET last_seen=?, tags=?
        WHERE user_id=?
    ''', (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        tags,
        user.id
    ))
    conn.commit()
    conn.close()

def update_user_city(user_id, city):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('UPDATE users SET city=? WHERE user_id=?', (city, user_id))
    conn.commit()
    conn.close()

def update_user_tags(user_id, tags):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('UPDATE users SET tags=? WHERE user_id=?', (tags, user_id))
    conn.commit()
    conn.close()

# --- Опросник ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    await update.message.reply_text(
        "👋 Привет! Я помогу тебе узнать, можешь ли ты подать на карту резидента ЕС в Польше. Давай начнём!\n\n"
        "Сколько лет ты живёшь в Польше?",
        reply_markup=ReplyKeyboardMarkup([["Меньше 5 лет", "5 лет и более"]], one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data.clear()
    context.user_data["tags"] = []
    return Q1

async def q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    user = update.effective_user
    if answer == "Меньше 5 лет":
        context.user_data["tags"].append("early")
        save_user(user, ",".join(context.user_data["tags"]))
        await update.message.reply_text(
            "😔 Пока рано подаваться на карту резидента. Если хочешь узнать требования заранее — напиши мне!\n"
            f"Если остались вопросы — пиши или звони: {CONSULT_PHONE} 📞",
            reply_markup=ReplyKeyboardRemove()
        )
        return FINAL
    else:
        context.user_data["tags"].append("ok_stay_years")
        await update.message.reply_text(
            "📅 За последние 5 лет ты был(-а) за пределами Польши?\n"
            "Если да — введи периоды выезда в формате:\n"
            "дд.мм.гггг - дд.мм.гггг\n"
            "Например:\n01.01.2021 - 15.01.2021\n"
            "Если выездов несколько — отправляй по одному периоду за раз.\n"
            "Когда закончишь — напиши 'Готово'.\n"
            "Если не было выездов — напиши 'Не было'.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data["dates"] = []
        return Q_DATES

async def q_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "не было":
        context.user_data["tags"].append("ok_stay")
        return await after_dates(update, context)
    elif text.lower() == "готово":
        if not context.user_data.get("dates"):
            await update.message.reply_text("Пожалуйста, введите хотя бы один период или напишите 'Не было'.")
            return Q_DATES
        return await after_dates(update, context)
    else:
        try:
            period = text.replace(" ", "").split("-")
            start = datetime.strptime(period[0], "%d.%m.%Y")
            end = datetime.strptime(period[1], "%d.%m.%Y")
            if end < start:
                await update.message.reply_text("Дата окончания раньше даты начала. Попробуй ещё раз.")
                return Q_DATES
            context.user_data.setdefault("dates", []).append((start, end))
            await update.message.reply_text("Период добавлен! Если есть ещё выезды — введи следующий. Если всё — напиши 'Готово'.")
            return Q_DATES
        except Exception:
            await update.message.reply_text("Неверный формат. Введи даты так: дд.мм.гггг - дд.мм.гггг")
            return Q_DATES

async def after_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    periods = context.user_data.get("dates", [])
    total_days = 0
    max_trip = 0
    for start, end in periods:
        days = (end - start).days + 1
        total_days += days
        if days > max_trip:
            max_trip = days
    # Критерии: не более 304 дней всего, не более 183 дней за раз
    if total_days > 304 or max_trip > 183:
        context.user_data["tags"].append("fail_stay")
        save_user(update.effective_user, ",".join(context.user_data["tags"]))
        await update.message.reply_text(
            f"😔 К сожалению, по количеству дней вне Польши ты пока не подходишь.\n"
            f"Всего дней вне Польши: {total_days}\n"
            f"Максимальный один выезд: {max_trip} дней\n"
            f"Если есть вопросы — пиши или звони: {CONSULT_PHONE} 📞"
        )
        return FINAL
    else:
        context.user_data["tags"].append("ok_stay")
        await update.message.reply_text(
            "💼 За последние 3 года у тебя был стабильный и официальный доход (работа или бизнес)?",
            reply_markup=ReplyKeyboardMarkup([["Да", "Нет", "Были перерывы"]], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q3

async def q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer == "Да":
        context.user_data["tags"].append("ok_income")
        await update.message.reply_text(
            "🗣️ Есть ли у тебя подтверждение знания польского языка на уровне не ниже B1?",
            reply_markup=ReplyKeyboardMarkup([
                ["Сертификат B1 или выше"],
                ["Окончил ВУЗ в Польше на польском"],
                ["Окончил другое учебное заведение в Польше"],
                ["Нет подтверждения"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q4
    elif answer == "Нет":
        context.user_data["tags"].append("fail_income")
        await update.message.reply_text(
            "Как долго не было дохода?",
            reply_markup=ReplyKeyboardMarkup([
                ["Несколько месяцев"], ["Полгода"], ["Год"], ["Вообще не было дохода"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q5
    else:  # Были перерывы
        context.user_data["tags"].append("fail_income")
        await update.message.reply_text(
            "Как долго длились перерывы?",
            reply_markup=ReplyKeyboardMarkup([
                ["Несколько месяцев"], ["Полгода"], ["Год"], ["Вообще не было дохода"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q5

async def q5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer == "Несколько месяцев":
        await update.message.reply_text(
            "🗣️ Есть ли у тебя подтверждение знания польского языка на уровне не ниже B1?",
            reply_markup=ReplyKeyboardMarkup([
                ["Сертификат B1 или выше"],
                ["Окончил ВУЗ в Польше на польском"],
                ["Окончил другое учебное заведение в Польше"],
                ["Нет подтверждения"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q4
    else:
        await update.message.reply_text(
            "😔 К сожалению, при длительных перерывах с доходом могут быть сложности. Рекомендуем проконсультироваться с экспертом.\n"
            f"Пиши или звони: {CONSULT_PHONE} 📞"
        )
        return FINAL

async def q4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer in [
        "Сертификат B1 или выше",
        "Окончил ВУЗ в Польше на польском",
        "Окончил другое учебное заведение в Польше"
    ]:
        context.user_data["tags"].append("ok_language")
        await update.message.reply_text(
            "🏠 У тебя есть жильё в собственности или официальная аренда?",
            reply_markup=ReplyKeyboardMarkup([
                ["Жильё в собственности"], ["Аренда жилья"], ["Ничего нет"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q6
    else:
        context.user_data["tags"].append("fail_language")
        await update.message.reply_text(
            "Быстрее и эффективнее всего будет сдать государственный экзамен. Вот ссылка на официальный сайт госэкзамена: https://certyfikatpolski.pl/ 🇵🇱",
            reply_markup=ReplyKeyboardRemove()
        )
        return FINAL

async def q6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer in ["Жильё в собственности", "Аренда жилья"]:
        context.user_data["tags"].append("ok_housing")
        await update.message.reply_text(
            "🛡️ У тебя есть страховка?",
            reply_markup=ReplyKeyboardMarkup([
                ["Да, я официально работаю"],
                ["Да, я предприниматель"],
                ["Зарегистрирован в ЗУС к члену семьи"],
                ["Есть частная страховка"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q7
    else:
        context.user_data["tags"].append("fail_housing")
        await update.message.reply_text(
            "Вам нужна официальная аренда жилья с договором. Рекомендуем проконсультироваться с экспертом.\n"
            f"Пиши или звони: {CONSULT_PHONE} 📞"
        )
        return FINAL

async def q7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏙️ Из какого ты города? Напиши название города."
    )
    return FINAL

async def final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    city = update.message.text if update.message else ""
    if city and not city.startswith("/"):
        update_user_city(user.id, city)
    tags = context.user_data.get("tags", [])
    save_user(user, ",".join(tags))
    if "early" in tags or "fail_stay" in tags or "fail_income" in tags or "fail_language" in tags or "fail_housing" in tags:
        await update.message.reply_text(
            f"Спасибо за обращение! Если появятся вопросы — пиши или звони: {CONSULT_PHONE} 📞"
        )
    else:
        await update.message.reply_text(
            f"🎉 Поздравляю! Ты можешь подаваться на карту резидента ЕС.\n"
            f"Если нужна помощь с документами или консультация — пиши или звони: {CONSULT_PHONE} 📞"
        )
    return ConversationHandler.END

# --- Автоответчик и пересылка вопросов в чат ---
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    save_user(user)
    # Переслать вопрос в админ-чат
    msg = (
        f"❓ Вопрос вне сценария!\n"
        f"От: @{user.username or '-'} (ID: {user.id})\n"
        f"Имя: {user.first_name or ''} {user.last_name or ''}\n"
        f"Вопрос: {text}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)
    await update.message.reply_text(
        "Спасибо за вопрос! Мы получили его и скоро свяжемся с вами. ☎️"
    )
    return ConversationHandler.END

# --- Команда /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я помогу тебе узнать, можешь ли ты подать на карту резидента ЕС в Польше 🇵🇱\n"
        "Просто напиши /start, чтобы пройти опрос.\n"
        "Если у тебя есть вопрос — просто напиши его, и мы обязательно ответим!"
    )

def main():
    init_db()
    app = ApplicationBuilder().token("7950791928:AAFvhWZMlthDlOB2SExxzhiu0M2djDrHsME").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, q1)],
            Q_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_dates)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, q3)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, q4)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, q5)],
            Q6: [MessageHandler(filters.TEXT & ~filters.COMMAND, q6)],
            Q7: [MessageHandler(filters.TEXT & ~filters.COMMAND, q7)],
            FINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, final)],
        },
        fallbacks=[
            MessageHandler(filters.ALL, handle_question)
        ]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('help', help_command))
    app.run_polling()

if __name__ == '__main__':
    main()

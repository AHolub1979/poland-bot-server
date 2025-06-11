import sqlite3
from datetime import datetime
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, InputMediaVideo
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

ADMIN_USERNAMES = ["Anastasia_Kulesh", "belarus79"]
(Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q_DATES, Q_DATES_MORE, FINAL, QUESTION) = range(11)
(BROADCAST_TAGS, BROADCAST_CONTENT, BROADCAST_CONFIRM) = range(100, 103)
ADMIN_CHAT_ID = -1002562481191
CONSULT_PHONE = "+48 791 787 071"

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

def get_users_by_tags(tags=None):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    if not tags or tags == ["всем"]:
        c.execute("SELECT user_id FROM users")
        users = [row[0] for row in c.fetchall()]
        conn.close()
        return users
    else:
        query = "SELECT user_id, tags FROM users"
        c.execute(query)
        users = []
        for user_id, user_tags in c.fetchall():
            if user_tags:
                user_tag_set = set(user_tags.split(","))
                if any(tag in user_tag_set for tag in tags):
                    users.append(user_id)
        conn.close()
        return users

def export_users_csv():
    import csv
    filename = "users_export.csv"
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, last_name, city, tags, first_seen, last_seen FROM users")
    rows = c.fetchall()
    conn.close()
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "username", "first_name", "last_name", "city", "tags", "first_seen", "last_seen"])
        writer.writerows(rows)
    return filename

def get_tag_stats():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT tags FROM users")
    tag_counts = {}
    for (tags,) in c.fetchall():
        if tags:
            for tag in tags.split(","):
                tag = tag.strip()
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
    conn.close()
    return tag_counts

def is_admin(user):
    return (user.username in ADMIN_USERNAMES)

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user):
        await update.message.reply_text("Нет доступа.")
        return
    await update.message.reply_text(
        "👑 Админ-панель:\n"
        "/broadcast — рассылка\n"
        "/export_users — выгрузка базы\n"
        "/stats — статистика по тегам"
    )

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user):
        await update.message.reply_text("Нет доступа.")
        return ConversationHandler.END
    await update.message.reply_text(
        "Введи теги через запятую (например: ok_stay,fail_income) или напиши 'всем' для рассылки всем пользователям."
    )
    context.user_data.clear()
    return BROADCAST_TAGS

async def broadcast_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tags = [t.strip() for t in update.message.text.lower().split(",")]
    context.user_data["broadcast_tags"] = tags
    await update.message.reply_text(
        "Отправь текст, фото или видео для рассылки. Можно отправить только текст, только фото/видео или всё вместе.\n"
        "Если хочешь добавить подпись к фото/видео — сначала отправь медиа, потом подпись отдельным сообщением.\n"
        "Когда всё готово — напиши 'Готово'."
    )
    context.user_data["broadcast_media"] = []
    context.user_data["broadcast_text"] = ""
    return BROADCAST_CONTENT

async def broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data["broadcast_media"].append(("photo", file_id))
    elif update.message.video:
        file_id = update.message.video.file_id
        context.user_data["broadcast_media"].append(("video", file_id))
    elif update.message.text and update.message.text.lower() != "готово":
        context.user_data["broadcast_text"] += update.message.text + "\n"
    elif update.message.text and update.message.text.lower() == "готово":
        text = context.user_data.get("broadcast_text", "").strip()
        media = context.user_data.get("broadcast_media", [])
        preview = "📢 Предпросмотр рассылки:\n"
        if text:
            preview += f"\n{text}\n"
        if media:
            preview += f"\n[Медиа: {len(media)} файла(ов)]"
        await update.message.reply_text(preview)
        await update.message.reply_text("Отправить рассылку? (Да/Нет)")
        return BROADCAST_CONFIRM
    else:
        await update.message.reply_text("Пожалуйста, отправь текст, фото или видео.")
        return BROADCAST_CONTENT

    return BROADCAST_CONTENT

async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "да":
        await update.message.reply_text("Рассылка отменена.")
        return ConversationHandler.END

    tags = context.user_data.get("broadcast_tags", [])
    users = get_users_by_tags(tags)
    text = context.user_data.get("broadcast_text", "").strip()
    media = context.user_data.get("broadcast_media", [])

    count = 0
    for user_id in users:
        try:
            if media:
                if len(media) == 1:
                    mtype, file_id = media[0]
                    if mtype == "photo":
                        await context.bot.send_photo(chat_id=user_id, photo=file_id, caption=text or None)
                    elif mtype == "video":
                        await context.bot.send_video(chat_id=user_id, video=file_id, caption=text or None)
                else:
                    media_group = []
                    for mtype, file_id in media:
                        if mtype == "photo":
                            media_group.append(InputMediaPhoto(file_id))
                        elif mtype == "video":
                            media_group.append(InputMediaVideo(file_id))
                    await context.bot.send_media_group(chat_id=user_id, media=media_group)
                    if text:
                        await context.bot.send_message(chat_id=user_id, text=text)
            else:
                await context.bot.send_message(chat_id=user_id, text=text)
            count += 1
        except Exception as e:
            continue
    await update.message.reply_text(f"Рассылка завершена. Отправлено {count} пользователям.")
    return ConversationHandler.END

async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user):
        await update.message.reply_text("Нет доступа.")
        return
    filename = export_users_csv()
    await update.message.reply_document(open(filename, "rb"))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user):
        await update.message.reply_text("Нет доступа.")
        return
    stats = get_tag_stats()
    if not stats:
        await update.message.reply_text("Пока нет данных по тегам.")
        return
    msg = "📊 Статистика по тегам:\n"
    for tag, count in stats.items():
        msg += f"{tag}: {count}\n"
    await update.message.reply_text(msg)

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
    elif answer == "5 лет и более":
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
    else:
        return await handle_question(update, context)

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
            return await handle_question(update, context)

async def after_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    periods = context.user_data.get("dates", [])
    total_days = 0
    max_trip = 0
    for start, end in periods:
        days = (end - start).days + 1
        total_days += days
        if days > max_trip:
            max_trip = days
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
                ["Окончил полицеальную школу"],
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
    elif answer == "Были перерывы":
        context.user_data["tags"].append("fail_income")
        await update.message.reply_text(
            "Как долго длились перерывы?",
            reply_markup=ReplyKeyboardMarkup([
                ["Несколько месяцев"], ["Полгода"], ["Год"], ["Вообще не было дохода"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q5
    else:
        return await handle_question(update, context)

async def q5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer == "Несколько месяцев":
        await update.message.reply_text(
            "🗣️ Есть ли у тебя подтверждение знания польского языка на уровне не ниже B1?",
            reply_markup=ReplyKeyboardMarkup([
                ["Сертификат B1 или выше"],
                ["Окончил ВУЗ в Польше на польском"],
                ["Окончил полицеальную школу"],
                ["Нет подтверждения"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q4
    elif answer in ["Полгода", "Год", "Вообще не было дохода"]:
        await update.message.reply_text(
            f"😔 К сожалению, при длительных перерывах с доходом могут быть сложности. Рекомендуем проконсультироваться с экспертом.\n"
            f"Пиши или звони: {CONSULT_PHONE} 📞"
        )
        return FINAL
    else:
        return await handle_question(update, context)

async def q4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer in [
        "Сертификат B1 или выше",
        "Окончил ВУЗ в Польше на польском"
    ]:
        context.user_data["tags"].append("ok_language")
        await update.message.reply_text(
            "🏠 У тебя есть жильё в собственности или официальная аренда?",
            reply_markup=ReplyKeyboardMarkup([
                ["Жильё в собственности"], ["Аренда жилья"], ["Ничего нет"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q6
    elif answer == "Окончил полицеальную школу":
        context.user_data["tags"].append("ok_language")
        await update.message.reply_text(
            "❗️ Важно: свидетельство об окончании полицеальной школы принимается только если оно выдано до 30.06.2025 г. Податься на карту резидента нужно до 30.06.2026 г. Если не успеваешь — потребуется сдать экзамен B1.\n\n"
            "🏠 У тебя есть жильё в собственности или официальная аренда?",
            reply_markup=ReplyKeyboardMarkup([
                ["Жильё в собственности"], ["Аренда жилья"], ["Ничего нет"]
            ], one_time_keyboard=True, resize_keyboard=True)
        )
        return Q6
    elif answer == "Нет подтверждения":
        context.user_data["tags"].append("fail_language")
        await update.message.reply_text(
            "Быстрее и эффективнее всего будет сдать государственный экзамен. Вот ссылка на официальный сайт госэкзамена: https://certyfikatpolski.pl/ 🇵🇱",
            reply_markup=ReplyKeyboardRemove()
        )
        return FINAL
    else:
        return await handle_question(update, context)

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
    elif answer == "Ничего нет":
        context.user_data["tags"].append("fail_housing")
        await update.message.reply_text(
            f"Вам нужна официальная аренда жилья с договором. Рекомендуем проконсультироваться с экспертом.\n"
            f"Пиши или звони: {CONSULT_PHONE} 📞"
        )
        return FINAL
    else:
        return await handle_question(update, context)

async def q7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer in [
        "Да, я официально работаю",
        "Да, я предприниматель",
        "Зарегистрирован в ЗУС к члену семьи",
        "Есть частная страховка"
    ]:
        await update.message.reply_text(
            "🏙️ Из какого ты города? Напиши название города."
        )
        return FINAL
    else:
        return await handle_question(update, context)

async def final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    city = update.message.text if update.message else ""
    if city and not city.startswith("/") and len(city) > 1 and all(x.isalpha() or x in " -'" for x in city):
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
    else:
        return await handle_question(update, context)

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    save_user(user)
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

    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            BROADCAST_TAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_tags)],
            BROADCAST_CONTENT: [
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.TEXT & ~filters.COMMAND, broadcast_content),
            ],
            BROADCAST_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_confirm)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(broadcast_conv)
    app.add_handler(CommandHandler("export_users", export_users))
    app.add_handler(CommandHandler("stats", stats))
    app.run_polling()

if __name__ == '__main__':
    main()

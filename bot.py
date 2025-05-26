from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Состояния опроса
(
    Q1, Q2, Q3, Q4, Q5, Q6, Q7, FINAL
) = range(8)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу вам проверить, можете ли вы подать на карту резидента ЕС в Польше.\n"
        "Сколько лет вы живёте в Польше?",
        reply_markup=ReplyKeyboardMarkup([["Меньше 5 лет", "5 лет и более"]], one_time_keyboard=True)
    )
    return Q1

async def q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer == "5 лет и более":
        await update.message.reply_text(
            "Ваше пребывание за последние 5 лет должно быть непрерывным. "
            "За 5 лет вы должны находиться за пределами Польши не более чем 10 месяцев в сумме, "
            "а один выезд не должен превышать 6 месяцев. Это условие соблюдено?",
            reply_markup=ReplyKeyboardMarkup([["Да", "Нет", "Не могу разобраться"]], one_time_keyboard=True)
        )
        return Q2
    else:
        await update.message.reply_text(
            "Вам пока рано подаваться на карту резидента. Хотите всё равно ознакомиться с требованиями заранее?",
            reply_markup=ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True)
        )
        return FINAL

async def q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer == "Да":
        await update.message.reply_text(
            "Следующий критерий — 3 года стабильного и регулярного источника дохода. "
            "За последние 3 года вы постоянно официально работали или вели бизнес?",
            reply_markup=ReplyKeyboardMarkup([["Да", "Нет", "Есть вопросы"]], one_time_keyboard=True)
        )
        return Q3
    elif answer == "Нет":
        await update.message.reply_text(
            "Ваши выезды были связаны с выполнением работы для польского работодателя?",
            reply_markup=ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True)
        )
        return FINAL
    else:  # "Не могу разобраться"
        await update.message.reply_text(
            "Рекомендуем воспользоваться калькулятором расчёта дней пребывания или записаться на консультацию.\n"
            "Ссылка на калькулятор: https://docs.google.com/spreadsheets/d/1Qw8Qw8Qw8Qw8Qw8Qw8Qw8Qw8Qw8Qw8Qw8Qw8Qw8Qw8/edit\n"
            "Для консультации напишите нам.",
            reply_markup=ReplyKeyboardRemove()
        )
        return FINAL

async def q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer == "Да":
        await update.message.reply_text(
            "Следующий критерий — подтверждение знания польского языка на уровне не ниже B1.\n"
            "Есть ли у вас одно из следующих подтверждений?",
            reply_markup=ReplyKeyboardMarkup([
                ["Сдан сертифицированный экзамен B1 или выше"],
                ["Окончил ВУЗ в Польше на польском"],
                ["Окончил другое учебное заведение в Польше"],
                ["Нет подтверждения"]
            ], one_time_keyboard=True)
        )
        return Q4
    elif answer == "Нет":
        await update.message.reply_text(
            "Как долго вы не работали?",
            reply_markup=ReplyKeyboardMarkup([
                ["Несколько месяцев"],
                ["Полгода"],
                ["Год"],
                ["Вообще не было источника дохода"]
            ], one_time_keyboard=True)
        )
        return FINAL
    else:  # "Есть вопросы"
        await update.message.reply_text(
            "Запишитесь на консультацию, чтобы мы помогли вам разобраться с этим вопросом.",
            reply_markup=ReplyKeyboardRemove()
        )
        return FINAL

async def q4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer in [
        "Сдан сертифицированный экзамен B1 или выше",
        "Окончил ВУЗ в Польше на польском",
        "Окончил другое учебное заведение в Польше"
    ]:
        await update.message.reply_text(
            "Теперь проверим ещё два важных момента. При подаче на карту резидента нужно обязательно иметь юридическое право собственности на жилое помещение. У вас есть:",
            reply_markup=ReplyKeyboardMarkup([
                ["Жильё в собственности (akt notarialny)"],
                ["Аренда жилья (umowa najmu)"],
                ["Ничего нет"]
            ], one_time_keyboard=True)
        )
        return Q5
    else:
        await update.message.reply_text(
            "Быстрее и эффективнее всего будет сдать государственный экзамен. Вот ссылка на официальный сайт госэкзамена: https://certyfikatpolski.pl/",
            reply_markup=ReplyKeyboardRemove()
        )
        return FINAL

async def q5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if answer in [
        "Жильё в собственности (akt notarialny)",
        "Аренда жилья (umowa najmu)"
    ]:
        await update.message.reply_text(
            "На данный момент у вас есть страховка?",
            reply_markup=ReplyKeyboardMarkup([
                ["Да, я официально работаю"],
                ["Да, я предприниматель"],
                ["Зарегистрирован в ЗУС к члену семьи"],
                ["Есть частная страховка"]
            ], one_time_keyboard=True)
        )
        return Q6
    else:
        await update.message.reply_text(
            "Вам нужна официальная аренда жилья с договором. Запишитесь на консультацию, чтобы мы помогли вам с этим вопросом.",
            reply_markup=ReplyKeyboardRemove()
        )
        return FINAL

async def q6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Из какого вы города? Пожалуйста, напишите название города.",
        reply_markup=ReplyKeyboardRemove()
    )
    return Q7

async def q7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    await update.message.reply_text(
        f"Спасибо! Вы можете подаваться на карту резидента. Если нужна помощь в ведении дела, подготовке документов или консультация — напишите нам свой номер телефона, и мы свяжемся с вами."
    )
    return FINAL

async def final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Спасибо за обращение! Если появятся вопросы — пишите, мы всегда на связи."
    )
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token("7950791928:AAFvhWZMlthDlOB2SExxzhiu0M2djDrHsME").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, q1)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, q2)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, q3)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, q4)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, q5)],
            Q6: [MessageHandler(filters.TEXT & ~filters.COMMAND, q6)],
            Q7: [MessageHandler(filters.TEXT & ~filters.COMMAND, q7)],
            FINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, final)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()

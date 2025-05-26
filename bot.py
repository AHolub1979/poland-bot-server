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

def main():
    app = ApplicationBuilder().token("7972507271:AAFbXmlHfqH5x-LXR0TUDHVrDJerv3Cx4t4").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, q1)],
            # Здесь будут следующие шаги
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()

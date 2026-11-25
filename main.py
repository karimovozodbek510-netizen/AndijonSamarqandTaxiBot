
import os
import sqlite3
import logging
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5921026197

DRIVER_NAME = "Ulug‘bek"
DRIVER_PHONE = "+998 94 234 87 87"
CAR = "Chevrolet Cobalt"
PLATE = "60 L 899 FB"

ROUTE, DATE, TIME, PASSENGERS, PHONE = range(5)
DB_NAME = "taxi.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                route TEXT,
                travel_date TEXT,
                travel_time TEXT,
                passengers INTEGER,
                phone TEXT,
                created_at TEXT
            )
        """)


def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["🚕 Taxi buyurtma berish"],
            ["🚘 Haydovchi ma'lumotlari"],
        ],
        resize_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Assalomu alaykum!\n"
        "Andijon ↔ Samarqand taxi xizmatiga xush kelibsiz.",
        reply_markup=main_menu(),
    )


async def driver_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🚘 Haydovchi: {DRIVER_NAME}\n"
        f"📞 Telefon: {DRIVER_PHONE}\n"
        f"🚗 Mashina: {CAR}\n"
        f"🔢 Davlat raqami: {PLATE}",
        reply_markup=main_menu(),
    )


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        ["Andijon ➡️ Samarqand"],
        ["Samarqand ➡️ Andijon"],
    ]
    await update.message.reply_text(
        "🛣 Yo‘nalishni tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return ROUTE


async def choose_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    route = update.message.text.strip()
    if route not in ["Andijon ➡️ Samarqand", "Samarqand ➡️ Andijon"]:
        await update.message.reply_text("Yo‘nalishni tugmadan tanlang.")
        return ROUTE

    context.user_data["route"] = route
    await update.message.reply_text("📅 Sanani kiriting (masalan: 30.12.2026):")
    return DATE


async def choose_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    try:
        travel_date = datetime.strptime(value, "%d.%m.%Y")
        if travel_date.date() < datetime.now().date():
            raise ValueError
    except ValueError:
        await update.message.reply_text("Sanani KK.OO.YYYY shaklida kiriting.")
        return DATE

    context.user_data["date"] = value
    await update.message.reply_text("🕒 Jo‘nash vaqtini kiriting (masalan: 08:30):")
    return TIME


async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError:
        await update.message.reply_text("Vaqtni 08:30 shaklida kiriting.")
        return TIME

    context.user_data["time"] = value
    await update.message.reply_text(
        "👥 Nechta yo‘lovchi bor?",
        reply_markup=ReplyKeyboardMarkup(
            [["1", "2", "3", "4"]], resize_keyboard=True
        ),
    )
    return PASSENGERS


async def choose_passengers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    if value not in ["1", "2", "3", "4"]:
        await update.message.reply_text("1 dan 4 gacha tanlang.")
        return PASSENGERS

    context.user_data["passengers"] = int(value)
    keyboard = [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]]
    await update.message.reply_text(
        "📞 Telefon raqamingizni yuboring yoki yozing (+998901234567):",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return PHONE


async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    if not phone or len(phone) < 9:
        await update.message.reply_text("Telefon raqamini to‘g‘ri kiriting.")
        return PHONE

    data = context.user_data
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("""
            INSERT INTO orders (
                user_id, route, travel_date, travel_time,
                passengers, phone, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            update.effective_user.id,
            data["route"],
            data["date"],
            data["time"],
            data["passengers"],
            phone,
            datetime.now().strftime("%d.%m.%Y %H:%M"),
        ))
        order_id = cursor.lastrowid

    order_text = (
        f"🚕 YANGI TAXI BUYURTMASI\n\n"
        f"🆔 Buyurtma: #{order_id}\n"
        f"🛣 Yo‘nalish: {data['route']}\n"
        f"📅 Sana: {data['date']}\n"
        f"🕒 Vaqt: {data['time']}\n"
        f"👥 Yo‘lovchilar: {data['passengers']} ta\n"
        f"📞 Telefon: {phone}\n"
        f"👤 Mijoz: {update.effective_user.full_name}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=order_text)
    except Exception:
        logger.exception("Admin xabarini yuborishda xato")

    await update.message.reply_text(
        "✅ Buyurtmangiz qabul qilindi!\n\n"
        f"👤 Haydovchi: {DRIVER_NAME}\n"
        f"📞 Telefon: {DRIVER_PHONE}\n"
        f"🚗 Mashina: {CAR}\n"
        f"🔢 Raqami: {PLATE}",
        reply_markup=main_menu(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Buyurtma bekor qilindi.", reply_markup=main_menu())
    return ConversationHandler.END


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    with sqlite3.connect(DB_NAME) as conn:
        total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        passengers = conn.execute(
            "SELECT COALESCE(SUM(passengers), 0) FROM orders"
        ).fetchone()[0]

    await update.message.reply_text(
        f"📊 TAXI STATISTIKASI\n\n🚕 Jami buyurtmalar: {total}\n"
        f"👥 Jami yo‘lovchilar: {passengers}"
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi! Environment Variables ga kiriting.")

    init_db()
    app = Application.builder().token(TOKEN).build()

    booking = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🚕 Taxi buyurtma berish$"), start_booking)
        ],
        states={
            ROUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_route)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_time)],
            PASSENGERS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_passengers)
            ],
            PHONE: [
                MessageHandler(
                    (filters.TEXT | filters.CONTACT) & ~filters.COMMAND,
                    save_phone,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(booking)
    app.add_handler(
        MessageHandler(filters.Regex("^🚘 Haydovchi ma'lumotlari$"), driver_info)
    )

    logger.info("Taxi bot ishga tushdi.")
    app.run_polling()


if __name__ == "__main__":
    main()

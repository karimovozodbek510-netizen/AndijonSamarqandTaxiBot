
import os
import sqlite3
import logging
from datetime import datetime

from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5921026197

DRIVER_NAME = "Ulug‘bek"
DRIVER_PHONE = "+998942348787"
CAR = "Chevrolet Cobalt"
PLATE = "60 L 899 FB"

logging.basicConfig(level=logging.INFO)

def database():
    con = sqlite3.connect("taxi.db")
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            route TEXT,
            date TEXT,
            time TEXT,
            passengers INTEGER,
            phone TEXT
        )
    """)
    return con

def menu():
    return ReplyKeyboardMarkup([
        ["🚕 Taxi buyurtma berish"],
        ["🚖 Haydovchi haqida"],
        ["📋 Mening buyurtmalarim"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Assalomu alaykum! 🚕\n"
        "Andijon ↔ Samarqand Taxi botiga xush kelibsiz!",
        reply_markup=menu()
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    stage = context.user_data.get("stage")

    if text == "🚕 Taxi buyurtma berish":
        context.user_data.clear()
        context.user_data["stage"] = "route"
        await update.message.reply_text(
            "Yo‘nalishni tanlang:",
            reply_markup=ReplyKeyboardMarkup([
                ["Andijon ➡️ Samarqand"],
                ["Samarqand ➡️ Andijon"],
                ["❌ Bekor qilish"]
            ], resize_keyboard=True)
        )
        return

    if text == "🚖 Haydovchi haqida":
        await update.message.reply_text(
            f"🚘 Mashina: {CAR}\n"
            f"🔢 Raqami: {PLATE}\n"
            f"👤 Haydovchi: {DRIVER_NAME}\n"
            f"📞 Telefon: {DRIVER_PHONE}",
            reply_markup=menu()
        )
        return

    if text == "📋 Mening buyurtmalarim":
        with database() as con:
            rows = con.execute(
                "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",
                (update.effective_user.id,)
            ).fetchall()

        if not rows:
            await update.message.reply_text("Buyurtmalaringiz yo‘q.", reply_markup=menu())
        else:
            result = "📋 BUYURTMALARINGIZ\n"
            for r in rows:
                result += (
                    f"\n🚕 №{r[0]}\n🛣 {r[3]}\n"
                    f"📅 {r[4]} | {r[5]}\n"
                    f"👥 {r[6]} kishi\n"
                )
            await update.message.reply_text(result, reply_markup=menu())
        return

    if text == "❌ Bekor qilish":
        context.user_data.clear()
        await update.message.reply_text("Bekor qilindi.", reply_markup=menu())
        return

    if stage == "route":
        if text not in ["Andijon ➡️ Samarqand", "Samarqand ➡️ Andijon"]:
            await update.message.reply_text("Yo‘nalishni tugma orqali tanlang.")
            return
        context.user_data["route"] = text
        context.user_data["stage"] = "date"
        await update.message.reply_text("Safar sanasini yozing (30.12.2026):")
        return

    if stage == "date":
        try:
            datetime.strptime(text, "%d.%m.%Y")
        except ValueError:
            await update.message.reply_text("Sanani 30.12.2026 shaklida yozing.")
            return
        context.user_data["date"] = text
        context.user_data["stage"] = "time"
        await update.message.reply_text("Ketish vaqtini yozing (masalan 08:00):")
        return

    if stage == "time":
        try:
            datetime.strptime(text, "%H:%M")
        except ValueError:
            await update.message.reply_text("Vaqtni 08:00 shaklida yozing.")
            return
        context.user_data["time"] = text
        context.user_data["stage"] = "passengers"
        await update.message.reply_text("Nechta yo‘lovchi? (1-4)")
        return

    if stage == "passengers":
        if text not in ["1", "2", "3", "4"]:
            await update.message.reply_text("1 dan 4 gacha son kiriting.")
            return
        context.user_data["passengers"] = int(text)
        context.user_data["stage"] = "phone"
        await update.message.reply_text(
            "Telefon raqamingizni yuboring yoki yozing:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("📱 Telefonni yuborish", request_contact=True)],
                ["❌ Bekor qilish"]
            ], resize_keyboard=True)
        )
        return

    if stage == "phone":
        contact = update.message.contact
        phone = contact.phone_number if contact else text.strip()
        if len(phone) < 7:
            await update.message.reply_text("Telefon raqamini to‘g‘ri kiriting.")
            return

        user = update.effective_user
        name = user.full_name
        data = context.user_data

        with database() as con:
            cur = con.execute("""
                INSERT INTO orders
                (user_id,name,route,date,time,passengers,phone)
                VALUES (?,?,?,?,?,?,?)
            """, (
                user.id, name, data["route"], data["date"],
                data["time"], data["passengers"], phone
            ))
            order_id = cur.lastrowid

        summary = (
            f"🚕 YANGI BUYURTMA №{order_id}\n\n"
            f"👤 {name}\n"
            f"🛣 {data['route']}\n"
            f"📅 {data['date']}\n"
            f"🕒 {data['time']}\n"
            f"👥 {data['passengers']} kishi\n"
            f"📞 {phone}\n"
            f"🆔 {user.id}"
        )

        try:
            await context.bot.send_message(ADMIN_ID, summary)
        except Exception:
            logging.exception("Admin xabari yuborilmadi")

        await update.message.reply_text(
            "✅ Buyurtmangiz qabul qilindi!\n\n"
            + summary +
            f"\n\n🚘 {CAR}\n🔢 {PLATE}\n"
            f"👤 Haydovchi: {DRIVER_NAME}\n"
            f"📞 {DRIVER_PHONE}",
            reply_markup=menu()
        )
        context.user_data.clear()
        return

    await update.message.reply_text("Menyudan tanlang.", reply_markup=menu())

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    with database() as con:
        total = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        people = con.execute("SELECT COALESCE(SUM(passengers),0) FROM orders").fetchone()[0]

    await update.message.reply_text(
        f"📊 TAXI STATISTIKASI\n\n"
        f"🚕 Buyurtmalar: {total}\n"
        f"👥 Yo‘lovchilar: {people}"
    )

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN kiritilmagan!")

    database().close()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

import asyncio
import mysql.connector
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- SOZLAMALAR ---
API_TOKEN = os.getenv('API_TOKEN', '8512126860:AAEvguhPUtgmua8Z8WitHXi5_35l2dQfH2U')
ADMIN_ID = int(os.getenv('ADMIN_ID', '5670469794'))
LOYIHA_LINKI = "https://openbudget.uz/uz/boards/view/123456"

# Railway MySQL ulanishi
DB_HOST = os.getenv('MYSQLHOST')
DB_USER = os.getenv('MYSQLUSER')
DB_PASSWORD = os.getenv('MYSQLPASSWORD')
DB_NAME = os.getenv('MYSQLDATABASE')
DB_PORT = os.getenv('MYSQLPORT')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, port=DB_PORT
    )

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id BIGINT PRIMARY KEY, full_name TEXT, referrer_id BIGINT, 
                       points INT DEFAULT 0, verified_photos INT DEFAULT 0)''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🗳 Ovoz berish")
    builder.button(text="👤 Mening profilim")
    builder.button(text="📢 Taklifnoma")
    builder.button(text="🏆 Reyting")
    builder.button(text="❓ Yordam") # Yangi tugma
    builder.adjust(2, 2, 1) # Tugmalar joylashuvi: 2ta, 2ta va 1ta pastda
    return builder.as_markup(resize_keyboard=True)

@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    args = message.text.split()
    ref_id = args[1] if len(args) > 1 else None
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, full_name, referrer_id) VALUES (%s, %s, %s)", (user_id, name, ref_id))
        if ref_id and ref_id.isdigit() and int(ref_id) != user_id:
            cursor.execute("UPDATE users SET points = points + 1 WHERE user_id=%s", (int(ref_id),))
        conn.commit()
    cursor.close()
    conn.close()
    await message.answer(f"👋 Salom, {name}!", reply_markup=main_menu())

@dp.message(F.text == "❓ Yordam")
async def help_command(message: types.Message):
    # Admin foydalanuvchi nomi bilan yordam xabari
    help_text = (
        "❓ **Yordam bo'limi**\n\n"
        "Bot bo'yicha savollaringiz yoki muammolar bo'lsa, adminga murojaat qiling:\n"
        "👤 **Admin:** @Erkin_Akramov\n\n"
        "Iltimos, skrinshot yuborishda rasmda ovoz berilgani aniq ko'rinishiga e'tibor bering!"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(F.text == "🗳 Ovoz berish")
async def vote(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Ovoz berish sahifasi 🌐", url=LOYIHA_LINKI))
    await message.answer("Ovoz bering va skrinshot yuboring!", reply_markup=kb.as_markup())

@dp.message(F.text == "🏆 Reyting")
async def show_rating(message: types.Message):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT full_name, points FROM users ORDER BY points DESC LIMIT 50")
    top_users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not top_users:
        return await message.answer("Hozircha reyting bo'sh.")
    
    text = "🏆 **TOP 50 FOYDALANUVCHILAR:**\n\n"
    for i, user in enumerate(top_users, 1):
        text += f"{i}. {user['full_name']} — {user['points']} ball\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "👤 Mening profilim")
async def profile(message: types.Message):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT points, verified_photos FROM users WHERE user_id=%s", (message.from_user.id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        await message.answer(f"👤 Ism: {message.from_user.full_name}\n💰 Ballar: {user['points']}\n✅ Tasdiqlanganlar: {user['verified_photos']}")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await message.reply("✅ Qabul qilindi! Admin tasdiqlashini kuting.")
    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="Tasdiqlash ✅", callback_data=f"verify_{message.from_user.id}"),
        types.InlineKeyboardButton(text="Rad etish ❌", callback_data=f"reject_{message.from_user.id}")
    )
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"ID: {message.from_user.id}\nIsm: {message.from_user.full_name}", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("verify_"))
async def approve(callback: types.CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        uid = int(callback.data.split("_")[1])
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + 1, verified_photos = verified_photos + 1 WHERE user_id=%s", (uid,))
        conn.commit()
        cursor.close()
        conn.close()
        await bot.send_message(uid, "🎉 Skrinshotingiz tasdiqlandi! Sizga 1 ball berildi.")
        await callback.message.edit_caption(caption=f"✅ Tasdiqlandi (ID: {uid})")
        await callback.answer("Tasdiqlandi!")

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        uid = int(callback.data.split("_")[1])
        await bot.send_message(uid, "❌ Skrinshotingiz rad etildi. Iltimos, qaytadan to'g'ri rasm yuboring.")
        await callback.message.edit_caption(caption=f"❌ Rad etildi (ID: {uid})")
        await callback.answer("Rad etildi!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
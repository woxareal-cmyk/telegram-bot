import asyncio
import logging
import sqlite3
import os
import random
import json
from datetime import date, datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile,
    CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from deep_translator import GoogleTranslator

# gTTS uchun xavfsiz import
try:
    from gTTS import gTTS # type: ignore
except ImportError:
    gTTS = None

import g4f

# API Tokenlar
BOT_TOKEN = "8633962524:AAEY7hxR2_bCmdE7SDM7hT58KvYCpJ3Gbto"
# BotFather'dan olingan Click provider tokeni (Masalan: 398061625:TEST:...)
PAYMENT_PROVIDER_TOKEN = "YOUR_CLICK_PROVIDER_TOKEN"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Foydalanuvchilar rejimini saqlash
ai_chat_mode = {}
ielts_mode = {}

# --- DATABASE SETUP ---
conn = sqlite3.connect("bot_user_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    coins INTEGER DEFAULT 0,
    days_count INTEGER DEFAULT 0,
    last_active DATE,
    last_quiz_date DATE,
    quiz_today_count INTEGER DEFAULT 0,
    referred_by INTEGER,
    is_pro INTEGER DEFAULT 0,
    pro_expires DATE
)
""")

# Migration
for col_name, col_type in [
    ("full_name", "TEXT"),
    ("referred_by", "INTEGER"),
    ("quiz_today_count", "INTEGER DEFAULT 0"),
    ("last_quiz_date", "DATE"),
    ("is_pro", "INTEGER DEFAULT 0"),
    ("pro_expires", "DATE")
]:
    try:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
    except sqlite3.OperationalError:
        pass

conn.commit()

def get_or_create_user(user_id: int, full_name: str, referrer_id: int = None):
    today = date.today().isoformat()
    cursor.execute("SELECT coins, days_count, last_active, is_pro FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            "INSERT INTO users (user_id, full_name, coins, days_count, last_active, last_quiz_date, quiz_today_count, referred_by, is_pro) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, full_name, 0, 1, today, None, 0, referrer_id, 0)
        )
        if referrer_id:
            cursor.execute("UPDATE users SET coins = coins + 50 WHERE user_id = ?", (referrer_id,))
        conn.commit()
        return 0, 1, referrer_id, 0
    else:
        coins, days_count, last_active, is_pro = row
        if last_active != today:
            days_count += 1
            cursor.execute("UPDATE users SET days_count = ?, last_active = ?, quiz_today_count = 0, full_name = ? WHERE user_id = ?", (days_count, today, full_name, user_id))
            conn.commit()
        return coins, days_count, None, is_pro

# --- SAVOLLAR BAZASI (QUIZ) ---
QUIZ_QUESTIONS = [
    {"q": "'Apple' so'zining tarjimasi nima?", "options": ["Olma", "Banan", "Uzum", "Nok"], "correct": "Olma"},
    {"q": "'Book' so'zining tarjimasi nima?", "options": ["Rochka", "Kitob", "Daftar", "Stol"], "correct": "Kitob"},
    {"q": "'Water' so'zining tarjimasi nima?", "options": ["Olov", "Suv", "Havo", "Yer"], "correct": "Suv"},
    {"q": "'I ___ a student.' bo'shliqni to'ldiring.", "options": ["is", "am", "are", "be"], "correct": "am"},
    {"q": "'They ___ playing football.' bo'shliqni to'ldiring.", "options": ["is", "am", "are", "was"], "correct": "are"}
]

# --- KEYBOARDS ---
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤖 AI Chat (Suhbat)"), KeyboardButton(text="📚 Kunlik 10 so'z")],
        [KeyboardButton(text="📖 Grammatika"), KeyboardButton(text="🎯 Kunlik Quiz")],
        [KeyboardButton(text="✍️ IELTS Insho (AI)"), KeyboardButton(text="🛒 Do'kon")],
        [KeyboardButton(text="🏆 Reyting"), KeyboardButton(text="👥 Taklif qilish")],
        [KeyboardButton(text="👤 Profil")]
    ],
    resize_keyboard=True
)

ai_exit_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ AI Muloqotni yakunlash")]
    ],
    resize_keyboard=True
)

# --- START HANDLER ---
@dp.message(Command("start"))
async def command_start_handler(message: Message):
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    get_or_create_user(message.from_user.id, message.from_user.full_name, referrer_id)
    ai_chat_mode[message.from_user.id] = False
    ielts_mode[message.from_user.id] = False

    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        f"Botga xush kelibsiz! Men sizga ingliz tilini o'rganishda yordam beraman.\n\n"
        f"💡 <b>Ixtiyoriy inglizcha yoki o'zbekcha so'z/gap yozsangiz, uni avtomatik tarjima qilib beraman!</b>",
        reply_markup=main_keyboard,
        parse_mode="HTML"
    )

# --- ✍️ AI IELTS INSHO TEKSHIRISH BO'LIMI ---
@dp.message(F.text == "✍️ IELTS Insho (AI)")
async def start_ielts_check(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT is_pro, coins FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    is_pro = row[0] if row else 0
    coins = row[1] if row else 0

    if not is_pro and coins < 30:
        await message.answer(
            "🔒 <b>IELTS Insho tekshirish funksiyasi uchun kamida 30 tanga kerak!</b>\n\n"
            "Sizda yetarli tanga yo'q. Test yechib tanga yig'ing yoki <b>🛒 Do'kon</b> bo'limidan PRO obunasini xarid qiling (PRO a'zolarga bepul!).",
            parse_mode="HTML"
        )
        return

    ielts_mode[user_id] = True
    ai_chat_mode[user_id] = False
    await message.answer(
        "✍️ <b>IELTS Writing Task 1 yoki Task 2 Inshoyingizni yuboring:</b>\n\n"
        "Matningizni shu yerga yozib yuboring. AI uni quyidagi mezonlar bo'yicha tahlil qiladi:\n"
        "• 📊 Estimated Band Score (Taxminiy ball)\n"
        "• ❌ Grammatik va imlo xatolar\n"
        "• 💡 Yaxshilash bo'yicha tavsiyalar\n\n"
        "<i>💡 Masalan: 'Some people think that university education should be free...'</i>",
        parse_mode="HTML"
    )

# --- 🤖 AI CHAT BO'LIMI ---
@dp.message(F.text == "🤖 AI Chat (Suhbat)")
async def start_ai_chat(message: Message):
    ai_chat_mode[message.from_user.id] = True
    ielts_mode[message.from_user.id] = False
    await message.answer(
        "🤖 <b>AI Ingliz tili ustozingiz xizmatingizda!</b>\n\n"
        "Menga ingliz tilida ixtiyoriy xabar yozing (Masalan: <i>'Hello, how are you?'</i>).\n"
        "Men siz bilan muloqot qilaman va xatolaringizni to'g'rilab boraman!\n\n"
        "<i>Chiqish uchun pastdagi '❌ AI Muloqotni yakunlash' tugmasini bosing.</i>",
        reply_markup=ai_exit_keyboard,
        parse_mode="HTML"
    )

@dp.message(F.text == "❌ AI Muloqotni yakunlash")
async def stop_ai_chat(message: Message):
    ai_chat_mode[message.from_user.id] = False
    ielts_mode[message.from_user.id] = False
    await message.answer("✅ AI muloqot rejimidan chiqdingiz. Asosiy menyu tiklandi!", reply_markup=main_keyboard)

# --- 🎯 QUIZ (TEST) TIZIMI ---
@dp.message(F.text == "🎯 Kunlik Quiz")
async def start_quiz(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT days_count, quiz_today_count, is_pro FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    days = row[0] if row else 1
    quiz_count = row[1] if row and row[1] is not None else 0
    is_pro = row[2] if row else 0

    if days < 5 and not is_pro:
        await message.answer(
            f"🔒 <b>Kunlik Quiz hali yopiq!</b>\n\n"
            f"Quizda qatnashish uchun botdan kamida <b>5 kun</b> foydalanishingiz kerak.\n"
            f"Sizning hozirgi faolligingiz: <b>{days}/5 kun</b>\n\n"
            f"💡 <i>PRO a'zolar uchun testlar birinchi kundanoq ochiq!</i>",
            parse_mode="HTML"
        )
        return

    if quiz_count >= 15 and not is_pro:
        await message.answer(
            "🛑 <b>Bugungi test limitingiz tugadi (15/15)!</b>\n\n"
            "Cheksiz test yechish va 2x ko'p tanga ishlash uchun <b>🛒 Do'kon</b> bo'limidan PRO statusini faollashtiring!",
            parse_mode="HTML"
        )
        return

    q_data = random.choice(QUIZ_QUESTIONS)
    options = q_data["options"].copy()
    random.shuffle(options)

    buttons = []
    for opt in options:
        is_correct = "1" if opt == q_data["correct"] else "0"
        buttons.append([InlineKeyboardButton(text=opt, callback_data=f"quiz_{is_correct}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    reward = 20 if is_pro else 10
    pro_bonus_text = " (💎 PRO 2x bonus!)" if is_pro else ""

    await message.answer(
        f"❓ <b>Savol:</b>\n{q_data['q']}\n\n"
        f"💡 <i>To'g'ri javob uchun +{reward} tanga beriladi{pro_bonus_text}!</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("quiz_"))
async def handle_quiz_answer(callback: CallbackQuery):
    is_correct = callback.data.split("_")[1]
    user_id = callback.from_user.id

    cursor.execute("SELECT quiz_today_count, is_pro FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    quiz_count = row[0] if row and row[0] is not None else 0
    is_pro = row[1] if row else 0
    new_count = quiz_count + 1

    reward = 20 if is_pro else 10

    if is_correct == "1":
        cursor.execute("UPDATE users SET coins = coins + ?, quiz_today_count = ? WHERE user_id = ?", (reward, new_count, user_id))
        conn.commit()
        await callback.answer(f"🎉 To'g'ri javob! +{reward} tanga berildi!", show_alert=True)
        await callback.message.edit_text(f"✅ <b>Barakalla, to'g'ri javob berdingiz! (+{reward} tanga)</b>\n\nBugungi yechilgan testlar: {new_count} ta", parse_mode="HTML")
    else:
        cursor.execute("UPDATE users SET quiz_today_count = ? WHERE user_id = ?", (new_count, user_id))
        conn.commit()
        await callback.answer("❌ Noto'g'ri javob!", show_alert=True)
        await callback.message.edit_text(f"❌ <b>Afsuski, javob noto'g'ri edi.</b>\n\nBugungi yechilgan testlar: {new_count} ta", parse_mode="HTML")

# --- 📚 KUNLIK 10 SO'Z ---
def load_words_from_json():
    json_path = "words.json"
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@dp.message(F.text == "📚 Kunlik 10 so'z")
async def show_daily_words(message: Message):
    all_words = load_words_from_json()

    if not all_words:
        await message.answer("⚠️ So'zlar bazasi (words.json) topilmadi yoki bo'sh!")
        return

    day_of_year = datetime.now().timetuple().tm_yday
    start_idx = ((day_of_year - 1) * 10) % len(all_words)
    today_words = all_words[start_idx : start_idx + 10]

    if len(today_words) < 10:
        today_words += all_words[: 10 - len(today_words)]

    today_date_str = datetime.now().strftime("%d.%m.%Y")
    text = f"📚 <b>Bugungi ({today_date_str}) yodlash uchun 10 ta so'z:</b>\n\n"
    words_audio_text = ""

    for i, w in enumerate(today_words, 1):
        text += f"{i}. <b>{w['word']}</b> — {w['trans']}\n<i>Misol:</i> {w['example']}\n\n"
        words_audio_text += f"{w['word']}. "

    await message.answer(text, parse_mode="HTML")

    if gTTS:
        try:
            tts = gTTS(text=words_audio_text, lang='en')
            audio_path = f"words_{message.from_user.id}.mp3"
            tts.save(audio_path)

            audio_file = FSInputFile(audio_path)
            await message.answer_voice(voice=audio_file, caption="🔊 <b>Bugungi so'zlarning inglizcha talaffuzi</b>", parse_mode="HTML")

            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            logging.error(f"Audio xatosi: {e}")

# --- 📖 GRAMMATIKA BO'LIMI ---
@dp.message(F.text == "📖 Grammatika")
async def show_grammar(message: Message):
    grammar_text = (
        "📖 <b>Ingliz tili Grammatikasi: Boshlang'ich Darslar</b>\n\n"
        "1️⃣ <b>To be (am / is / are)</b>\n"
        "• I am a student. (Men talabaman)\n"
        "• He / She / It is fast. (U tez)\n"
        "• We / You / They are ready. (Biz/Siz/Ular tayyor)\n\n"
        "2️⃣ <b>Present Simple (Hozirgi oddiy zamon)</b>\n"
        "• Odatda takrorlanadigan ish-harakatlar uchun ishlatiladi.\n"
        "• <i>Formula:</i> Subject + Verb(s/es)\n"
        "• <i>Misol:</i> I study coding every day."
    )
    await message.answer(grammar_text, parse_mode="HTML")

# --- 👤 PROFIL ---
@dp.message(F.text == "👤 Profil")
async def show_profile(message: Message):
    cursor.execute("SELECT coins, days_count, is_pro FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    coins = row[0] if row else 0
    days = row[1] if row else 1
    is_pro = row[2] if row else 0

    status = "💎 PRO A'zo" if is_pro else "FREE (Oddiy)"

    profile_text = (
        f"👤 <b>Foydalanuvchi:</b> {message.from_user.full_name}\n"
        f"✨ <b>Status:</b> {status}\n"
        f"🪙 <b>Tangalar (Coins):</b> {coins} ta\n"
        f"🔥 <b>Faol kunlar (Streak):</b> {days} kun"
    )
    await message.answer(profile_text, parse_mode="HTML")

# --- 🏆 REYTING ---
@dp.message(F.text == "🏆 Reyting")
async def show_leaderboard(message: Message):
    cursor.execute("SELECT full_name, coins, is_pro FROM users ORDER BY coins DESC LIMIT 10")
    top_users = cursor.fetchall()

    text = "🏆 <b>Eng ko'p tanga yig'gan top-10 foydalanuvchi:</b>\n\n"
    for i, user in enumerate(top_users, 1):
        name = user[0] if user[0] else "Foydalanuvchi"
        badge = " 💎" if user[2] else ""
        text += f"{i}. <b>{name}</b>{badge} — {user[1]} tanga\n"

    await message.answer(text, parse_mode="HTML")

# --- 👥 TAKLIF QILISH ---
@dp.message(F.text == "👥 Taklif qilish")
async def show_referral(message: Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"

    await message.answer(
        f"👥 <b>Do'stlaringizni taklif qiling va tanga ishlang!</b>\n\n"
        f"Sizning taklif havolangiz:\n<code>{ref_link}</code>\n\n"
        f"🎁 Har bir yangi kelgan do'stingiz uchun <b>50 tanga</b> beriladi!",
        parse_mode="HTML"
    )

# --- 🛒 DO'KON BO'LIMI VA REAL PULGA CLICK TO'LOV ---
@dp.message(F.text == "🛒 Do'kon")
async def show_shop(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT is_pro, coins FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    is_pro = row[0] if row else 0
    coins = row[1] if row else 0

    status = "💎 PRO A'zo" if is_pro else "FREE (Oddiy)"

    text = (
        f"🛒 <b>Bot Do'koni & VIP Status</b>\n\n"
        f"Sizning hozirgi statusingiz: <b>{status}</b>\n"
        f"Hisobingizdagi tangalar: <b>{coins} 🪙</b>\n\n"
        f"💎 <b>PRO Obuna afzalliklari:</b>\n"
        f"• ✍️ IELTS Insho tekshirish — Bepul va cheksiz!\n"
        f"• Testlarda 2x ko'p tanga ishlash (+20 tanga) 🪙\n"
        f"• Kunlik testlar soni va limitlar cheksiz 🎯\n"
        f"• Profil va Reytingda 💎 PRO nishoni\n\n"
        f"Tariflar:\n"
        f"• <b>PRO Status (O'yin tangasiga):</b> 500 tanga 🪙\n"
        f"• <b>PRO Status (Click / Karta orqali):</b> 15,000 so'm 💳"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Tangaga xarid qilish (500 coins)", callback_data="buy_pro_coins")],
        [InlineKeyboardButton(text="💳 Click orqali xarid (15,000 so'm)", callback_data="buy_pro_click")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# Tangaga PRO olish
@dp.callback_query(F.data == "buy_pro_coins")
async def process_buy_pro_coins(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT coins, is_pro FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    coins = row[0] if row else 0
    is_pro = row[1] if row else 0

    if is_pro:
        await callback.answer("Sizda allaqachon PRO status mavjud! ✨", show_alert=True)
        return

    if coins < 500:
        await callback.answer(f"❌ Tangalaringiz yetarli emas! Sizda {coins} tanga bor, 500 tanga kerak.", show_alert=True)
        return

    cursor.execute("UPDATE users SET coins = coins - 500, is_pro = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

    await callback.answer("🎉 Tassanoqlar! PRO status muvaffaqiyatli faollashtirildi!", show_alert=True)
    await callback.message.edit_text(
        "💎 <b>Xaridingiz uchun rahmat!</b>\n\nSiz endi PRO a'zosiz. Barcha imkoniyatlar ochildi!",
        parse_mode="HTML"
    )

# Click / Karta orqali Invoys yuborish
@dp.callback_query(F.data == "buy_pro_click")
async def process_buy_pro_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT is_pro FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        await callback.answer("Sizda allaqachon PRO status mavjud! ✨", show_alert=True)
        return

    await callback.answer()

    # Narx tiyinlarda ko'rsatiladi (1500000 tiyin = 15000 so'm)
    prices = [LabeledPrice(label="PRO Obuna (1 Oylik)", amount=1500000)]

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="💎 PRO Obuna Xaridi",
        description="Botdagi barcha imkoniyatlar (AI IELTS insho va cheksiz quiz)ni ochish uchun 1 oylik PRO status.",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="UZS",
        prices=prices,
        start_parameter="pro-subscription",
        payload="pro_status_purchase"
    )

# Pre-checkout (To'lovdan oldingi tekshiruv)
@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Muvaffaqiyatli to'lov qabul qilinganda
@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    user_id = message.from_user.id
    cursor.execute("UPDATE users SET is_pro = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

    await message.answer(
        "🎉 <b>To'lovingiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        "Sizga 💎 <b>PRO Status</b> taqdim etildi. Endi siz IELTS Insho tekshirishdan cheksiz foydalanishingiz va quizlarda 2x ko'p tanga ishlashingiz mumkin!",
        parse_mode="HTML"
    )

# --- ODDIY MATNLAR VA AI MULOQOT ---
@dp.message()
async def general_message_handler(message: Message):
    user_id = message.from_user.id

    # 1. IELTS Insho tekshirish rejimi
    if ielts_mode.get(user_id, False):
        ielts_mode[user_id] = False

        cursor.execute("SELECT is_pro, coins FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        is_pro = row[0] if row else 0
        coins = row[1] if row else 0

        if not is_pro:
            cursor.execute("UPDATE users SET coins = coins - 30 WHERE user_id = ?", (user_id,))
            conn.commit()

        wait_msg = await message.answer("📝 <i>AI Inshoyingizni IELTS mezonlari bo'yicha tahlil qilmoqda (30-60 soniya)...</i>", parse_mode="HTML")

        try:
            prompt = (
                "You are an expert IELTS Writing Examiner. Evaluate the following essay:\n\n"
                f"\"{message.text}\"\n\n"
                "Provide detailed feedback in the following format (use simple Uzbek for explanations where helpful):\n"
                "1. Overall Estimated Band Score (e.g. 6.5)\n"
                "2. Scores for Task Achievement, Coherence & Cohesion, Lexical Resource, Grammatical Range & Accuracy\n"
                "3. Key Mistakes & Corrections\n"
                "4. Suggestions for Improvement to reach Band 7.0+"
            )

            response = await asyncio.to_thread(
                g4f.ChatCompletion.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )

            await wait_msg.delete()
            pro_badge = "💎 PRO (Bepul)" if is_pro else "🪙 -30 Tanga yechildi"
            await message.answer(
                f"📊 <b>IELTS Writing Tahlil Natijasi:</b> ({pro_badge})\n\n{response}",
                parse_mode="HTML"
            )
        except Exception as e:
            await wait_msg.delete()
            logging.error(f"IELTS AI error: {e}")
            await message.answer("❌ Inshoni tahlil qilishda xatolik yuz berdi. Qayta urinib ko'ring.")

    # 2. Oddiy AI Chat rejimi
    elif ai_chat_mode.get(user_id, False):
        wait_msg = await message.answer("🤖 <i>AI o'ylanmoqda...</i>", parse_mode="HTML")
        try:
            prompt = f"You are an English teacher. Reply in short, simple English to practice: {message.text}"

            response = await asyncio.to_thread(
                g4f.ChatCompletion.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )

            await wait_msg.delete()
            await message.answer(f"🤖 <b>AI Teacher:</b>\n\n{response}", parse_mode="HTML")
        except Exception:
            await wait_msg.delete()
            await message.answer("❌ AI javob bera olmadi, qayta urinib ko'ring.")

    # 3. Oddiy tarjimon rejimi
    else:
        user_text = message.text.strip()
        wait_msg = await message.answer("🔄 <i>Tarjima qilinmoqda...</i>", parse_mode="HTML")

        try:
            translated_text = GoogleTranslator(source='auto', target='uz').translate(user_text)
            if translated_text.lower() == user_text.lower():
                translated_text = GoogleTranslator(source='auto', target='en').translate(user_text)
                to_lang = "🇬🇧 Inglizcha"
            else:
                to_lang = "🇺🇿 O'zbekcha"

            await wait_msg.delete()
            await message.answer(f"🔤 <b>Matn:</b> {user_text}\n\n🎯 <b>Tarjima ({to_lang}):</b> {translated_text}", parse_mode="HTML")
        except Exception:
            await wait_msg.delete()
            await message.answer("❌ Tarjimada xatolik yuz berdi.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
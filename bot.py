from fastapi import FastAPI
import asyncio
import uvicorn
from threading import Thread

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ربات ۲۴ ساعته روشن است"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8080)

# روشن کردن وب‌سایت در پس‌زمینه
Thread(target=run_web).start()



import asyncio
import logging
import aiosqlite
import random
import math
import html
import time

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ============================================================
# SETTINGS
# ============================================================

logging.basicConfig(level=logging.INFO)

TOKEN = "8514097794:AAHkST4CykXv62a3buub0Ch--BcmAlkdxq8"
OWNER_ID = 7545214150
COIN_SELLER = "mehrdad1714"

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
BOT_USERNAME = "@AfghanGapVIP_bot"

DB_PATH = "afghangap_pure_organic.db"

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username_hash TEXT UNIQUE,
            name TEXT DEFAULT 'ناشناس',
            gender TEXT DEFAULT 'unknown',
            age TEXT DEFAULT 'نامشخص',
            province TEXT DEFAULT 'نامشخص',
            city TEXT DEFAULT 'نامشخص',
            photo_id TEXT DEFAULT 'none',
           bio TEXT DEFAULT 'به ربات افغان گپ خوش آمدید',
            likes INTEGER DEFAULT 0,
            status TEXT DEFAULT 'registering',
            partner_id INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 0,
            latitude REAL DEFAULT NULL,
            longitude REAL DEFAULT NULL,
            location_updated INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT 0,
            referral_reward_given INTEGER DEFAULT 0,
            profile_reward_given INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            last_activity INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS chat_requests (
            sender_id INTEGER,
            receiver_id INTEGER,
            PRIMARY KEY (sender_id, receiver_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_likes (
            liker_id INTEGER,
            target_id INTEGER,
            PRIMARY KEY (liker_id, target_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS random_queue (
            user_id INTEGER PRIMARY KEY
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username_hash TEXT,
            role TEXT DEFAULT 'admin',
            added_at INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        INSERT OR IGNORE INTO admins
        (user_id, username_hash, role, added_at)
        VALUES (?, ?, 'owner', ?)
        """, (OWNER_ID, "OWNER", int(time.time())))


        await db.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            sender_id INTEGER,
            receiver_id INTEGER,
            text TEXT,
            timestamp INTEGER
        )
        """)



        await db.commit()

async def add_column_if_missing(table, column, definition):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"PRAGMA table_info({table})") as cursor:
            rows = await cursor.fetchall()
        columns = [row[1] for row in rows]
        if column not in columns:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            await db.commit()

# ============================================================
# PROVINCES & STATES
# ============================================================

AFG_PROVINCES = [
    "کابل", "هرات", "بلخ", "قندهار", "ننگرهار", "کندوز",
    "غزنی", "پکتیا", "بغلان", "بدخشان", "تخار", "فاریاب",
    "جوزجان", "سرپل", "سمنگان", "بامیان", "پروان", "کاپیسا",
    "پنجشیر", "میدان وردک", "لوگر", "خوست", "پکتیکا", "کنر",
    "لغمان", "نورستان", "نیمروز", "فراه", "بادغیس", "غور",
    "دایکندی", "ارزگان", "زابل", "هلمند"
]

class RegisterStates(StatesGroup):
    NAME = State()
    GENDER = State()
    AGE = State()
    PROVINCE = State()
    CITY = State()
    PHOTO = State()

class EditStates(StatesGroup):
    EDIT_NAME = State()
    EDIT_AGE = State()
    EDIT_PROVINCE = State()
    EDIT_CITY = State()
    EDIT_BIO = State()
    EDIT_PHOTO = State()
    FEEDBACK = State()

class AdminStates(StatesGroup):
    ADD_ADMIN = State()
    REMOVE_ADMIN = State()
    ADD_COINS_USER = State()
    ADD_COINS_AMOUNT = State()
    REMOVE_COINS_USER = State()
    REMOVE_COINS_AMOUNT = State()
    WARN_USER = State()
    BAN_USER = State()
    UNBAN_USER = State()
    EDIT_USER = State()
    DELETE_USER = State()
    BROADCAST = State()

# ============================================================
# ASYNC HELPERS
# ============================================================

async def generate_user_hash():
    while True:
        value = "user_" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id FROM users WHERE username_hash=?", (value,)) as cursor:
                if not await cursor.fetchone():
                    return value

def profile_link(user_hash):
    return f"https://t.me{BOT_USERNAME}?start={user_hash}"

def profile_id_html(user_hash):
    return f"🆔 /{html.escape(user_hash)}"


async def get_coins(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_coins(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
        await db.commit()

async def remove_coins(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET coins = CASE WHEN coins >= ? THEN coins - ? ELSE 0 END WHERE user_id=?
        """, (amount, amount, user_id))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, username_hash, name, age, gender, province, city, photo_id, likes, bio, status, partner_id, coins, latitude, longitude
            FROM users WHERE user_id=?
        """, (user_id,)) as cursor:
            return await cursor.fetchone()

async def get_user_by_hash(user_hash):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE username_hash=?", (user_hash,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def is_chatting(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT status, partner_id FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False, 0
            return row[0] == "chatting" and bool(row[1]), row[1]

def distance_km(lat1, lon1, lat2, lon2):
    r = 6371
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ============================================================
# ADMIN HELPERS
# ============================================================

async def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cursor:
            return bool(await cursor.fetchone())

async def add_admin_by_user_hash(user_hash):
    user_hash = user_hash.strip()
    user_id = await get_user_by_hash(user_hash)
    if not user_id:
        return False, "❌ این آیدی اختصاصی در ربات پیدا نشد."
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cursor:
            if await cursor.fetchone():
                return False, "⚠️ این کاربر از قبل ادمین است."
        await db.execute("""
            INSERT INTO admins (user_id, username_hash, role, added_at) VALUES (?, ?, 'admin', ?)
        """, (user_id, user_hash, int(time.time())))
        await db.commit()
    return True, "✅ ادمین با موفقیت اضافه شد."

async def remove_admin_by_hash(user_hash):
    user_hash = user_hash.strip()
    if user_hash == "OWNER":
        return False, "❌ ادمین اصلی قابل حذف نیست."
    user_id = await get_user_by_hash(user_hash)
    if not user_id:
        return False, "❌ کاربر پیدا نشد."
    if user_id == OWNER_ID:
        return False, "❌ ادمین اصلی قابل حذف نیست."
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()
    return True, "✅ ادمین حذف شد."

# ============================================================
# LAST ACTIVITY MIDDLEWARE
# ============================================================

@dp.update.outer_middleware()
async def update_last_activity_middleware(handler, event, data):
    user = data.get("event_from_user")
    if user:
        current_time = int(time.time())
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET last_activity=? WHERE user_id=?", (current_time, user.id))
            await db.commit()
    return await handler(event, data)

# ============================================================


#KEYBOARDS**

# ============================================================


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬 به یه ناشناس وصلم کن!")],
            [KeyboardButton(text="🌀 جستجوی کاربران"), KeyboardButton(text="📍 افراد نزدیک من")],
            [KeyboardButton(text="💰 سکه"), KeyboardButton(text="👤 پروفایل"), KeyboardButton(text="❓ راهنما")],
            [KeyboardButton(text="📬 انتقادات و پیشنهادات"), KeyboardButton(text="✉️ لینک ناشناس من")]
        ],
        resize_keyboard=True
    )


def get_chat_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ قطع گفتگو"), KeyboardButton(text="👤 مشاهده پروفایل")]
        ],
        resize_keyboard=True
    )


def get_searching_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ لغو جستجو")]
        ],
        resize_keyboard=True
    )


def get_end_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ بله، قطع کن",
                callback_data="confirm_end_chat"
            ),
            InlineKeyboardButton(
                text="❌ خیر",
                callback_data="cancel_end_chat"
            )
        ]]
    )


def get_profile_buttons(target_id, likes):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"❤️ Like {likes}",
                    callback_data=f"like_{target_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 درخواست چت",
                    callback_data=f"req_chat_{target_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 گزارش تخلف کاربر",
                    callback_data=f"report_menu_{target_id}"  # فعال شد
                )
            ]
        ]
    )




def get_my_profile_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ ویرایش نام",
                    callback_data="edit_my_name"
                ),
                InlineKeyboardButton(
                    text="🎂 ویرایش سن",
                    callback_data="edit_my_age"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📍 ویرایش ولایت",
                    callback_data="edit_my_province"
                ),
                InlineKeyboardButton(
                    text="🏠 ویرایش شهر",
                    callback_data="edit_my_city"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 ویرایش بیو",
                    callback_data="edit_my_bio"
                ),
                InlineKeyboardButton(
                    text="📸 تغییر عکس",
                    callback_data="edit_my_photo"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📍 بروزرسانی موقعیت",
                    callback_data="update_location"
                )
            ]
        ]
    )


def get_accept_reject_buttons(sender_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ قبول گفتگو",
                callback_data=f"accept_c_{sender_id}"
            ),
            InlineKeyboardButton(
                text="❌ رد درخواست",
                callback_data=f"reject_c_{sender_id}"
            )
        ]]
    )


# ============================================================


# QUEUE MECHANISM**

# ============================================================


async def random_queue_add(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO random_queue(user_id) VALUES(?)",
            (user_id,)
        )
        await db.commit()


async def random_queue_remove(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM random_queue WHERE user_id=?",
            (user_id,)
        )
        await db.commit()


async def random_queue_find(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM random_queue WHERE user_id != ? LIMIT 1",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    return row[0] if row else None


# ============================================================


# ADMIN PANEL HANDLERS**

# ============================================================


def admin_panel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 آمار",
                    callback_data="admin_stats"
                ),
                InlineKeyboardButton(
                    text="👥 کاربران",
                    callback_data="admin_users"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 افزودن سکه",
                    callback_data="admin_addcoins"
                ),
                InlineKeyboardButton(
                    text="💸 کم کردن سکه",
                    callback_data="admin_removecoins"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ اخطار",
                    callback_data="admin_warn"
                ),
                InlineKeyboardButton(
                    text="🚫 محروم",
                    callback_data="admin_ban"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ رفع محرومیت",
                    callback_data="admin_unban"
                ),
                InlineKeyboardButton(
                    text="✏️ ویرایش پروفایل",
                    callback_data="admin_edit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 حذف کاربر",
                    callback_data="admin_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👑 افزودن ادمین",
                    callback_data="admin_add_admin"
                ),
                InlineKeyboardButton(
                    text="❌ حذف ادمین",
                    callback_data="admin_remove_admin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👑 لیست ادمین‌ها",
                    callback_data="admin_list_admins"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 پیام همگانی",
                    callback_data="admin_broadcast"
                )
            ]
        ]
    )


@dp.message(Command("admin"))
async def admin_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی مدیریت ندارید.")
        return

    await message.answer(
        "👑 **پنل مدیریت افغان چت**\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=admin_panel_keyboard()
    )


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users"
        ) as c1:
            total = (await c1.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE status='chatting'"
        ) as c2:
            chatting = (await c2.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE banned=1"
        ) as c3:
            banned = (await c3.fetchone())[0]

        async with db.execute(
            "SELECT COALESCE(SUM(coins),0) FROM users"
        ) as c4:
            coins = (await c4.fetchone())[0]

    await call.message.answer(
        f"📊 **آمار ربات**\n\n"
        f"👥 کل کاربران: **{total}**\n"
        f"💬 در حال چت: **{chatting}**\n"
        f"🚫 محروم: **{banned}**\n"
        f"💰 مجموع سکه‌ها: **{coins}**"
    )

    await call.answer()


@dp.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT username_hash, name, age, gender, coins, banned
            FROM users
            ORDER BY user_id DESC
            LIMIT 30
            """
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await call.answer(
            "کاربری وجود ندارد.",
            show_alert=True
        )
        return

    text = "👥 **آخرین کاربران**\n\n"

    for row in rows:
        u_hash, name, age, gender, coins, banned = row

        state = "🚫 محروم" if banned else "✅ فعال"

        text += (
            f"🆔 {html.escape(u_hash or 'نامشخص')}\n"
            f"👤 {html.escape(name or 'نامشخص')} | "
            f"{html.escape(str(age or 'نامشخص'))} سال\n"
            f"⚧ {html.escape(gender or 'نامشخص')}\n"
            f"💰 {coins} سکه | {state}\n"
            f"────────────\n"
        )

    await call.message.answer(text)
    await call.answer()


@dp.callback_query(F.data == "admin_addcoins")
async def admin_addcoins(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "💰 **افزودن سکه**\n\n"
        "آیدی اختصاصی کاربر را ارسال کنید:\n\n"
        "مثال:\n"
        "user_A7K92P"
    )

    await state.set_state(AdminStates.ADD_COINS_USER)
    await call.answer()


@dp.message(AdminStates.ADD_COINS_USER)
async def admin_addcoins_user(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()
    user_id = await get_user_by_hash(user_hash)

    if not user_id:
        await message.answer(
            "❌ کاربر پیدا نشد.\n"
            "فرمت صحیح: user_XXXXXX"
        )
        return

    await state.update_data(
        target_user_id=user_id,
        target_hash=user_hash
    )

    await message.answer("💰 مقدار سکه را وارد کنید:")
    await state.set_state(AdminStates.ADD_COINS_AMOUNT)


@dp.message(AdminStates.ADD_COINS_AMOUNT)
async def admin_addcoins_amount(
    message: Message,
    state: FSMContext
):
    try:
        amount = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ فقط عدد وارد کنید.")
        return

    if amount <= 0:
        await message.answer(
            "❌ مقدار باید بیشتر از صفر باشد."
        )
        return

    data = await state.get_data()
    user_id = data["target_user_id"]

    await add_coins(user_id, amount)
    new_coins = await get_coins(user_id)

    await state.clear()

    await message.answer(
        f"✅ **{amount} سکه** اضافه شد.\n\n"
        f"🆔 {html.escape(data['target_hash'])}\n"
        f"💰 موجودی جدید: {new_coins}"
    )

    try:
        await bot.send_message(
            user_id,
            f"🎁 **{amount} سکه** توسط مدیریت به حساب شما اضافه شد."
        )
    except Exception:
        pass


@dp.callback_query(F.data == "admin_removecoins")
async def admin_removecoins(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "💸 آیدی اختصاصی کاربر را ارسال کنید:"
    )

    await state.set_state(
        AdminStates.REMOVE_COINS_USER
    )

    await call.answer()


@dp.message(AdminStates.REMOVE_COINS_USER)
async def admin_removecoins_user(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()
    user_id = await get_user_by_hash(user_hash)

    if not user_id:
        await message.answer("❌ کاربر پیدا نشد.")
        return

    await state.update_data(
        target_user_id=user_id,
        target_hash=user_hash
    )

    await message.answer(
        "💸 مقدار سکه‌ای که باید کم شود:"
    )

    await state.set_state(
        AdminStates.REMOVE_COINS_AMOUNT
    )


@dp.message(AdminStates.REMOVE_COINS_AMOUNT)
async def admin_removecoins_amount(
    message: Message,
    state: FSMContext
):
    try:
        amount = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ فقط عدد وارد کنید.")
        return

    if amount <= 0:
        await message.answer("❌ مقدار نامعتبر است.")
        return

    data = await state.get_data()
    user_id = data["target_user_id"]

    await remove_coins(user_id, amount)
    new_coins = await get_coins(user_id)

    await state.clear()

    await message.answer(
        f"✅ {amount} سکه کم شد.\n\n"
        f"💰 موجودی جدید: {new_coins}"
    )


@dp.callback_query(F.data == "admin_add_admin")
async def admin_add_admin(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "👑 **افزودن ادمین**\n\n"
        "آیدی اختصاصی کاربر را ارسال کنید.\n\n"
        "مثال:\n"
        "user_A7K92P"
    )

    await state.set_state(AdminStates.ADD_ADMIN)
    await call.answer()


@dp.message(AdminStates.ADD_ADMIN)
async def admin_add_admin_save(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()

    success, result = await add_admin_by_user_hash(
        user_hash
    )

    await state.clear()
    await message.answer(result)


@dp.callback_query(F.data == "admin_remove_admin")
async def admin_remove_admin(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "❌ آیدی اختصاصی ادمین را ارسال کنید:"
    )

    await state.set_state(
        AdminStates.REMOVE_ADMIN
    )

    await call.answer()


@dp.message(AdminStates.REMOVE_ADMIN)
async def admin_remove_admin_save(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()

    success, result = await remove_admin_by_hash(
        user_hash
    )

    await state.clear()
    await message.answer(result)


@dp.callback_query(F.data == "admin_list_admins")
async def admin_list_admins(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT user_id, username_hash, role
            FROM admins
            ORDER BY added_at ASC
            """
        ) as cursor:
            rows = await cursor.fetchall()

    text = "👑 **لیست ادمین‌ها**\n\n"

    for uid, u_hash, role in rows:
        if uid == OWNER_ID:
            text += (
                f"👑 **ادمین اصلی**\n"
                f"ID: {uid}\n\n"
            )
        else:
            text += (
                f"👤 {html.escape(u_hash or 'نامشخص')}\n"
                f"نقش: {html.escape(role or 'نامشخص')}\n\n"
            )

    await call.message.answer(text)
    await call.answer()


@dp.callback_query(F.data == "admin_warn")
async def admin_warn(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "⚠️ آیدی اختصاصی کاربر را ارسال کنید:"
    )

    await state.set_state(
        AdminStates.WARN_USER
    )

    await call.answer()


@dp.message(AdminStates.WARN_USER)
async def admin_warn_save(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()
    user_id = await get_user_by_hash(user_hash)

    if not user_id:
        await message.answer("❌ کاربر پیدا نشد.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET warnings = warnings + 1
            WHERE user_id=?
            """,
            (user_id,)
        )
        await db.commit()

        async with db.execute(
            "SELECT warnings FROM users WHERE user_id=?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    warnings = row[0] if row else 0

    await state.clear()

    await message.answer(
        f"⚠️ اخطار ثبت شد.\n\n"
        f"🆔 {html.escape(user_hash)}\n"
        f"تعداد اخطار: {warnings}"
    )

    try:
        await bot.send_message(
            user_id,
            f"⚠️ **هشدار مدیریت**\n\n"
            f"شما یک اخطار دریافت کردید.\n"
            f"تعداد اخطارهای شما: {warnings}"
        )
    except Exception:
        pass


@dp.callback_query(F.data == "admin_ban")
async def admin_ban(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "🚫 آیدی اختصاصی کاربر را ارسال کنید:"
    )

    await state.set_state(
        AdminStates.BAN_USER
    )

    await call.answer()


@dp.message(AdminStates.BAN_USER)
async def admin_ban_save(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()
    user_id = await get_user_by_hash(user_hash)

    if not user_id:
        await message.answer("❌ کاربر پیدا نشد.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET banned=1,
                status='banned',
                partner_id=0
            WHERE user_id=?
            """,
            (user_id,)
        )
        await db.commit()

    await random_queue_remove(user_id)
    await state.clear()

    await message.answer(
        f"🚫 کاربر {html.escape(user_hash)} محروم شد."
    )

    try:
        await bot.send_message(
            user_id,
            "🚫 **حساب شما توسط مدیریت محروم شد.**"
        )
    except Exception:
        pass


@dp.callback_query(F.data == "admin_unban")
async def admin_unban(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "✅ آیدی اختصاصی کاربر را ارسال کنید:"
    )

    await state.set_state(
        AdminStates.UNBAN_USER
    )

    await call.answer()


@dp.message(AdminStates.UNBAN_USER)
async def admin_unban_save(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()
    user_id = await get_user_by_hash(user_hash)

    if not user_id:
        await message.answer("❌ کاربر پیدا نشد.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET banned=0,
                status='main_menu',
                partner_id=0
            WHERE user_id=?
            """,
            (user_id,)
        )
        await db.commit()

    await state.clear()

    await message.answer(
        f"✅ محرومیت {html.escape(user_hash)} برداشته شد."
    )

    try:
        await bot.send_message(
            user_id,
            "✅ **محرومیت حساب شما توسط مدیریت برداشته شد.**"
        )
    except Exception:
        pass


@dp.callback_query(F.data == "admin_edit")
async def admin_edit(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "✏️ آیدی اختصاصی کاربر را ارسال کنید:"
    )

    await state.set_state(
        AdminStates.EDIT_USER
    )

    await call.answer()


@dp.message(AdminStates.EDIT_USER)
async def admin_edit_user(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()
    user_id = await get_user_by_hash(user_hash)

    if not user_id:
        await message.answer("❌ کاربر پیدا نشد.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT name, age, gender, province, city,
                   bio, coins, warnings, banned
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        await message.answer("❌ اطلاعات پیدا نشد.")
        return

    (
        name,
        age,
        gender,
        province,
        city,
        bio,
        coins,
        warnings,
        banned
    ) = row

    await state.clear()

    await message.answer(
        f"✏️ **پروفایل کاربر**\n\n"
        f"🆔 {html.escape(user_hash)}\n"
        f"👤 نام: {html.escape(name or 'نامشخص')}\n"
        f"🎂 سن: {html.escape(str(age or 'نامشخص'))}\n"
        f"⚧ جنسیت: {html.escape(gender or 'نامشخص')}\n"
        f"📍 ولایت: {html.escape(province or 'نامشخص')}\n"
        f"🏠 شهر: {html.escape(city or 'نامشخص')}\n"
        f"📝 بیو: {html.escape(bio or 'ندارد')}\n"
        f"💰 سکه: {coins}\n"
        f"⚠️ اخطار: {warnings}\n"
        f"🚫 محروم: {'بله' if banned else 'خیر'}"
    )


@dp.callback_query(F.data == "admin_delete")
async def admin_delete(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    await call.message.answer(
        "🗑 آیدی اختصاصی کاربر را ارسال کنید:"
    )

    await state.set_state(
        AdminStates.DELETE_USER
    )

    await call.answer()


@dp.message(AdminStates.DELETE_USER)
async def admin_delete_save(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    user_hash = message.text.strip()
    user_id = await get_user_by_hash(user_hash)

    if not user_id:
        await message.answer("❌ کاربر پیدا نشد.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            DELETE FROM user_likes
            WHERE liker_id=? OR target_id=?
            """,
            (user_id, user_id)
        )

        await db.execute(
            """
            DELETE FROM chat_requests
            WHERE sender_id=? OR receiver_id=?
            """,
            (user_id, user_id)
        )

        await db.execute(
            "DELETE FROM random_queue WHERE user_id=?",
            (user_id,)
        )

        await db.execute(
            """
            DELETE FROM admins
            WHERE user_id=? AND user_id != ?
            """,
            (user_id, OWNER_ID)
        )

        await db.execute(
            "DELETE FROM users WHERE user_id=?",
            (user_id,)
        )

        await db.commit()

    await state.clear()

    await message.answer(
        f"🗑 کاربر {html.escape(user_hash)} حذف شد."
    )


@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(
    call: CallbackQuery,
    state: FSMContext
):
    if not await is_admin(call.from_user.id):
        return

    # ایجاد کیبورد برگشت مخصوص برای ادمین
    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 برگشت از پیام همگانی")]
        ],
        resize_keyboard=True
    )

    await call.message.answer(
        "📢 **پیام همگانی را ارسال کنید.**\n\n"
        "متن، عکس، ویدیو، استیکر یا پیام معمولی می‌توانید ارسال کنید.\n"
        "برای لغو عملیات، دکمه‌ی زیر را بزنید:",
        reply_markup=cancel_kb
    )

    await state.set_state(
        AdminStates.BROADCAST
    )

    await call.answer()



@dp.message(AdminStates.BROADCAST)
async def admin_broadcast_send(
    message: Message,
    state: FSMContext
):
    # بررسی دکمه‌ی برگشت
    if message.text == "🔙 برگشت از پیام همگانی":
        await state.clear()
        await message.answer(
            "❌ **عملیات ارسال پیام همگانی لغو شد.**",
            reply_markup=get_main_keyboard()
        )
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE banned=0"
        ) as cursor:
            users = await cursor.fetchall()

    sent = 0

    # نمایش وضعیت شروع ارسال به ادمین
    status_msg = await message.answer("⏳ در حال ارسال پیام به کاربران... لطفاً منتظر بمانید.")

    for row in users:
        target_id = row[0]

        # پیام به خود ادمین فرستاده نشود
        if target_id == message.from_user.id:
            continue

        try:
            await message.copy_to(chat_id=target_id)
            sent += 1
        except Exception:
            pass

        await asyncio.sleep(0.03)

    await state.clear()

    # حذف پیام وضعیت قبلی
    try:
        await status_msg.delete()
    except Exception:
        pass

    await message.answer(
        f"📢 **پیام همگانی ارسال شد.**\n\n"
        f"✅ ارسال موفق: {sent}\n"
        f"👥 کل کاربران فعال: {len(users)}",
        reply_markup=get_main_keyboard()
    )



# ============================================================


# START & REGISTERING HANDLERS**

# ============================================================


@dp.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext
):
    await state.clear()

    user_id = message.chat.id

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT banned, status
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if row and row[0] == 1:
        await message.answer(
            "🚫 حساب شما توسط مدیریت محروم شده است."
        )
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) == 2:
        target_hash = parts[1].strip()
        target_id = await get_user_by_hash(target_hash)

        if target_id:
            existing_me = await get_user(user_id)

            if existing_me and existing_me[10] != "registering":
                await send_profile(
                    chat_id=user_id,
                    target_id=target_id,
                    own=(target_id == user_id)
                )
                return

            elif not existing_me:
                my_hash = await generate_user_hash()

                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        """
                        INSERT INTO users
                        (
                            user_id,
                            username_hash,
                            status,
                            coins,
                            referred_by
                        )
                        VALUES (?, ?, 'registering', 0, ?)
                        """,
                        (
                            user_id,
                            my_hash,
                            target_id
                        )
                    )
                    await db.commit()

                await message.answer(
                    "🌟 **به افغان چت خوش آمدید!**\n\n"
                    "لطفاً نام یا نام مستعار خود را ارسال کنید:"
                )

                await state.set_state(
                    RegisterStates.NAME
                )
                return

    if not row or row[1] == "registering":

        if not row:
            my_hash = await generate_user_hash()

            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """
                    INSERT INTO users
                    (
                        user_id,
                        username_hash,
                        status,
                        coins
                    )
                    VALUES (?, ?, 'registering', 0)
                    """,
                    (
                        user_id,
                        my_hash
                    )
                )
                await db.commit()

            await message.answer(
                "🌟 **به افغان چت خوش آمدید!**\n\n"
                "لطفاً نام یا نام مستعار خود را ارسال کنید:"
            )

            await state.set_state(
                RegisterStates.NAME
            )
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                UPDATE users
                SET status='main_menu'
                WHERE user_id=?
                """,
                (user_id,)
            )
            await db.commit()

        await message.answer(
            "👋 دوباره خوش آمدید!",
            reply_markup=get_main_keyboard()
        )


@dp.message(RegisterStates.NAME)
async def process_name(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    name = message.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET name=?
            WHERE user_id=?
            """,
            (name, message.chat.id)
        )
        await db.commit()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="👨 پسرم",
                callback_data="set_g_boy"
            ),
            InlineKeyboardButton(
                text="👩 دخترم",
                callback_data="set_g_girl"
            )
        ]]
    )

    await message.answer(
        f"تشکر {html.escape(name)}! 🌟\n\n"
        "جنسیت خود را انتخاب کنید:",
        reply_markup=kb
    )

    await state.set_state(
        RegisterStates.GENDER
    )


@dp.callback_query(RegisterStates.GENDER)
async def process_gender(
    call: CallbackQuery,
    state: FSMContext
):
    if call.data not in (
        "set_g_boy",
        "set_g_girl"
    ):
        await call.answer()
        return

    gender = (
        "پسر 👨"
        if call.data == "set_g_boy"
        else "دختر 👩"
    )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET gender=?
            WHERE user_id=?
            """,
            (
                gender,
                call.from_user.id
            )
        )
        await db.commit()

    kb = []
    row_buttons = []

    for age in range(10, 61):
        row_buttons.append(
            InlineKeyboardButton(
                text=str(age),
                callback_data=f"set_a_{age}"
            )
        )

        if len(row_buttons) == 5:
            kb.append(row_buttons)
            row_buttons = []

    if row_buttons:
        kb.append(row_buttons)

    await call.message.edit_text(
        "🎂 سن خود را انتخاب کنید:\n⚠️ <i>(لطفاً فقط از دکمه‌های زیر استفاده کنید)</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=kb
        )
    )

    await state.set_state(
        RegisterStates.AGE
    )

    await call.answer()


# جلوگیری از قفل شدن فرآیند ثبت‌نام در صورت ارسال متن اشتباه به جای سن
@dp.message(RegisterStates.AGE)
async def invalid_age_text(message: Message):
    await message.answer(
        "❌ <b>خطا!</b> لطفاً سن خود را فقط با <u>کلیک روی دکمه‌های شیشه‌ای بالا</u> انتخاب کنید."
    )


@dp.callback_query(RegisterStates.AGE)
async def process_age(
    call: CallbackQuery,
    state: FSMContext
):
    if not call.data.startswith("set_a_"):
        await call.answer()
        return

    age = call.data.replace(
        "set_a_",
        "",
        1
    )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET age=?
            WHERE user_id=?
            """,
            (
                age,
                call.from_user.id
            )
        )
        await db.commit()

    kb = []

    for i in range(0, len(AFG_PROVINCES), 2):
        row = [
            InlineKeyboardButton(
                text=AFG_PROVINCES[i],
                callback_data=f"set_p_{AFG_PROVINCES[i]}"
            )
        ]

        if i + 1 < len(AFG_PROVINCES):
            row.append(
                InlineKeyboardButton(
                    text=AFG_PROVINCES[i + 1],
                    callback_data=f"set_p_{AFG_PROVINCES[i + 1]}"
                )
            )

        kb.append(row)

    await call.message.edit_text(
        "📍 از کدام ولایت افغانستان هستید؟\n⚠️ <i>(لطفاً فقط از دکمه‌های زیر استفاده کنید)</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=kb
        )
    )

    await state.set_state(
        RegisterStates.PROVINCE
    )

    await call.answer()


# جلوگیری از قفل شدن فرآیند ثبت‌نام در صورت ارسال متن اشتباه به جای ولایت
@dp.message(RegisterStates.PROVINCE)
async def invalid_province_text(message: Message):
    await message.answer(
        "❌ <b>خطا!</b> لطفاً ولایت خود را فقط با <u>کلیک روی دکمه‌های شیشه‌ای بالا</u> انتخاب کنید."
    )


@dp.callback_query(RegisterStates.PROVINCE)
async def process_province(
    call: CallbackQuery,
    state: FSMContext
):
    if not call.data.startswith("set_p_"):
        await call.answer()
        return

    province = call.data.replace(
        "set_p_",
        "",
        1
    )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET province=?
            WHERE user_id=?
            """,
            (
                province,
                call.from_user.id
            )
        )
        await db.commit()

    await call.message.edit_text(
        f"📍 ولایت: **{html.escape(province)}**\n\n"
        "🏠 نام شهر خود را ارسال کنید:"
    )

    await state.set_state(
        RegisterStates.CITY
    )

    await call.answer()


@dp.message(RegisterStates.CITY)
async def process_city(
    message: Message,
    state: FSMContext
):
    if not message.text:
        return

    city = message.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET city=?
            WHERE user_id=?
            """,
            (
                city,
                message.chat.id
            )
        )
        await db.commit()

    await message.answer(
        "📸 حالا یک عکس برای پروفایل خود ارسال کنید:"
    )

    await state.set_state(
        RegisterStates.PHOTO
    )


@dp.message(RegisterStates.PHOTO, F.photo)
async def process_photo(
    message: Message,
    state: FSMContext
):
    user_id = message.chat.id
    photo_id = message.photo[-1].file_id

    referred_by = 0
    reward_given = 0
    is_already_rewarded = 0

    async with aiosqlite.connect(DB_PATH) as db:
        # بررسی وضعیت قبلی برای جلوگیری از واریز مجدد پاداش
        async with db.execute(
            """
            SELECT referred_by, referral_reward_given, profile_reward_given
            FROM users WHERE user_id=?
            """,
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            referred_by = row[0] or 0
            reward_given = row[1] or 0
            is_already_rewarded = row[2] or 0

        # به روز رسانی اطلاعات پروفایل و افزودن سکه‌های اولیه ثبت‌نام
        await db.execute(
            """
            UPDATE users
            SET photo_id=?,
                status='main_menu',
                coins=coins + (CASE WHEN profile_reward_given=0 THEN 15 ELSE 0 END),
                profile_reward_given=1
            WHERE user_id=?
            """,
            (photo_id, user_id)
        )
        await db.commit()

    # اگر کاربر قبلاً ثبت‌نامش را نهایی نکرده بود و معرف داشت
    if referred_by and reward_given == 0 and is_already_rewarded == 0:
        await add_coins(referred_by, 10)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                UPDATE users
                SET referral_reward_given=1
                WHERE user_id=?
                """,
                (user_id,)
            )
            await db.commit()

        try:
            await bot.send_message(
                referred_by,
                "🎉 **تبریک!**\n\n"
                "کاربری که با لینک اختصاصی شما وارد شده بود، "
                "پروفایلش را تکمیل کرد.\n\n"
                "💰 +10 سکه"
            )
        except Exception:
            pass

    await state.clear()

    await message.answer(
        "🎉 **پروفایل شما تکمیل شد!**\n\n"
        "🎁 15 سکه هدیه ثبت‌نام دریافت کردید.\n\n"
        "به افغان چت خوش آمدید! 🇦🇫",
        reply_markup=get_main_keyboard()
    )




@dp.message(RegisterStates.PHOTO)
async def invalid_registration_photo(
    message: Message
):
    await message.answer(
        "📸 لطفاً یک عکس ارسال کنید."
    )
# ============================================================


# PROFILE MECHANISM**

# ============================================================


async def send_profile(chat_id, target_id, own=False):
    row = await get_user(target_id)
    if not row:
        return

    (
        uid,
        u_hash,
        name,
        age,
        gender,
        province,
        city,
        photo_id,
        likes,
        bio,
        status,
        partner_id,
        coins,
        latitude,
        longitude
    ) = row

    text = (
        f"👤 **کارت پروفایل**\n\n"
        f"• نام: {html.escape(name or 'نامشخص')}\n"
        f"• سن: {html.escape(str(age or 'نامشخص'))} سال\n"
        f"• جنسیت: {html.escape(gender or 'نامشخص')}\n"
        f"• ولایت: {html.escape(province or 'نامشخص')}\n"
        f"• شهر: {html.escape(city or 'نامشخص')}\n\n"
        f"📝 بیوگرافی: {html.escape(bio or 'ندارد')}\n\n"
        f"❤️ لایک: {likes}\n"
    )

    if own:
        text += (
            f"💰 سکه‌های شما: **{coins}**\n\n"
            f"{profile_id_html(u_hash)}"
        )
        markup = get_my_profile_buttons()
    else:
        text += (
            f"👀 هم اکنون آنلاین\n"
            f"{profile_id_html(u_hash)}"
        )
        markup = get_profile_buttons(uid, likes)

    if photo_id and photo_id != "none":
        await bot.send_photo(
            chat_id,
            photo=photo_id,
            caption=text,
            reply_markup=markup
        )
    else:
        await bot.send_message(
            chat_id,
            text,
            reply_markup=markup
        )


@dp.message(F.text == "👤 پروفایل")
async def my_profile(message: Message):
    if not await get_user(message.chat.id):
        await message.answer("❌ ابتدا ثبت‌نام کنید.")
        return

    await send_profile(
        message.chat.id,
        message.chat.id,
        own=True
    )


# ============================================================


# COINS & REFERRAL**

# ============================================================


@dp.message(F.text == "💰 سکه")
async def coin_menu(message: Message):
    coins = await get_coins(message.chat.id)

    await message.answer(
        f"💰 **کیف پول سکه**\n\n"
        f"موجودی شما: **{coins} سکه**\n\n"
        f"🎁 با دعوت کاربران می‌توانید سکه رایگان بگیرید.\n"
        f"💳 همچنین امکان خرید سکه وجود دارد.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎁 لینک دعوت من",
                        callback_data="my_referral"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💳 خرید سکه",
                        callback_data="buy_coins"
                    )
                ]
            ]
        )
    )


async def send_referral(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT username_hash
            FROM users
            WHERE user_id=?
            """,
            (message.chat.id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return

    link = profile_link(row[0])

    await message.answer(
        f"🎁 **لینک اختصاصی شما**\n\n"
        f"این لینک را برای دوستان خود ارسال کنید.\n\n"
        f"{html.escape(link)}\n\n"
        f"👤 با ورود هر کاربر از لینک شما:\n"
        f"💰 +10 سکه\n\n"
        f"✅ اگر همان کاربر پروفایل خود را تکمیل کند:\n"
        f"💰 +10 سکه دیگر"
    )


@dp.callback_query(F.data == "my_referral")
async def my_referral_callback(call: CallbackQuery):
    await send_referral(call.message)
    await call.answer()


@dp.message(F.text == "✉️ لینک ناشناس من")
async def referral_button(message: Message):
    await send_referral(message)


@dp.callback_query(F.data == "buy_coins")
async def buy_coins(call: CallbackQuery):
    await call.message.answer(
        f"💳 **خرید سکه**\n\n"
        f"🪙 500 سکه = 50 افغانی\n\n"
        f"برای خرید سکه به پیوی @{COIN_SELLER} پیام دهید.\n\n"
        f"بعد از پرداخت، ادمین سکه‌ها را به حساب شما اضافه می‌کند."
    )

    await call.answer()


# ============================================================


# SEARCH & LIKE HANDLERS**

# ============================================================


def search_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 کاربران آنلاین (فعال)",
                    callback_data="show_list_online"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 همه کاربران",
                    callback_data="show_list_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👨 کاربران آقا",
                    callback_data="show_list_male"
                ),
                InlineKeyboardButton(
                    text="👩 کاربران خانم",
                    callback_data="show_list_female"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 هم‌سن‌ها",
                    callback_data="show_list_age"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗺 هم‌استانی‌ها",
                    callback_data="show_list_province"
                ),
                InlineKeyboardButton(
                    text="🏠 هم‌شهری‌ها",
                    callback_data="show_list_city"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🆕 کاربران جدید",
                    callback_data="show_list_new"
                ),
                InlineKeyboardButton(
                    text="💝 محبوب",
                    callback_data="show_list_popular"
                )
            ]
        ]
    )


@dp.message(F.text == "🌀 جستجوی کاربران")
async def search_users(message: Message):
    await message.answer(
        "👥 **جستجوی کاربران**\n\n"
        "نوع جستجو را انتخاب کنید:",
        reply_markup=search_menu()
    )


@dp.callback_query(F.data.startswith("show_list_"))
async def show_search_results(call: CallbackQuery):
    user_id = call.from_user.id

    kind = call.data.replace(
        "show_list_",
        "",
        1
    )

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT age, province, city
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        ) as cursor:
            me = await cursor.fetchone()

    if not me:
        await call.answer(
            "❌ ابتدا ثبت‌نام کنید.",
            show_alert=True
        )
        return

    my_age, my_province, my_city = me

    online_threshold = int(time.time()) - 300

    base = """
        SELECT user_id,
               username_hash,
               age,
               province,
               city,
               name,
               likes,
               gender,
               last_activity
        FROM users
        WHERE status != 'registering'
          AND banned=0
          AND user_id != ?
    """

    params = [user_id]

    if kind == "online":
        base += " AND last_activity >= ?"
        params.append(online_threshold)

    elif kind == "male":
        base += " AND gender LIKE '%پسر%'"

    elif kind == "female":
        base += " AND gender LIKE '%دختر%'"

    elif kind == "age":
        base += " AND age=?"
        params.append(my_age)

    elif kind == "province":
        base += " AND province=?"
        params.append(my_province)

    elif kind == "city":
        base += " AND city=?"
        params.append(my_city)

    elif kind == "popular":
        base += " ORDER BY likes DESC"

    elif kind == "new":
        base += " ORDER BY user_id DESC"

    elif kind == "all":
        base += " ORDER BY user_id DESC"

    base += " LIMIT 10"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            base,
            tuple(params)
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await call.answer(
            "⏳ کاربری پیدا نشد.",
            show_alert=True
        )
        return

    output = "👥 **لیست کاربران**\n\n"

    for row in rows:
        (
            uid,
            u_hash,
            age,
            province,
            city,
            name,
            likes,
            gender,
            last_act
        ) = row

        emoji = (
            "👩"
            if "دختر" in (gender or "")
            else "👨"
        )

        online_status = (
            "🟢 آنلاین"
            if last_act and last_act >= online_threshold
            else "⚪ آفلاین"
        )

        output += (
            f"{emoji} **{html.escape(name or 'نامشخص')}** "
            f"({online_status})\n"
            f"🎂 {html.escape(str(age or 'نامشخص'))} سال\n"
            f"📍 {html.escape(city or 'نامشخص')} "
            f"({html.escape(province or 'نامشخص')})\n"
            f"❤️ {likes}\n"
            f"{profile_id_html(u_hash)}\n"
            f"────────────\n"
        )

    try:
        await call.message.edit_text(output)
    except Exception:
        await call.message.answer(output)

    await call.answer()


@dp.message(F.text.startswith("/user_"))
async def profile_by_id(message: Message):
    target_hash = message.text.strip().replace(
        "/",
        ""
    )

    target_id = await get_user_by_hash(target_hash)

    if not target_id:
        await message.answer(
            "❌ این آیدی یافت نشد."
        )
        return

    await send_profile(
        message.chat.id,
        target_id,
        own=(target_id == message.chat.id)
    )


@dp.callback_query(F.data.startswith("like_"))
async def like_user(call: CallbackQuery):
    try:
        target_id = int(call.data.split("_")[1])
    except (IndexError, ValueError):
        return
        
    sender_id = call.from_user.id

    if target_id == sender_id:
        await call.answer("❌ شما نمی‌توانید پروفایل خودتان را لایک کنید!", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM user_likes WHERE liker_id=? AND target_id=?", 
            (sender_id, target_id)
        ) as cursor:
            already_liked = await cursor.fetchone()

        if already_liked:
            await call.answer("❤️ شما قبلاً این پروفایل را لایک کرده‌اید!", show_alert=True)
            return

        await db.execute(
            "INSERT INTO user_likes (liker_id, target_id) VALUES (?, ?)", 
            (sender_id, target_id)
        )
        await db.execute(
            "UPDATE users SET likes=likes+1 WHERE user_id=?", 
            (target_id,)
        )
        await db.commit()

        async with db.execute("SELECT likes FROM users WHERE user_id=?", (target_id,)) as cursor:
            row = await cursor.fetchone()
            new_likes_count = row[0] if row else 0  # اصلاح شد

    await call.answer("🎉 پروفایل با موفقیت لایک شد!")

    current_markup = call.message.reply_markup
    if current_markup and current_markup.inline_keyboard:
        new_keyboard = []
        for row_btn in current_markup.inline_keyboard:
            new_row = []
            for btn in row_btn:
                if btn.callback_data == f"like_{target_id}":
                    new_row.append(InlineKeyboardButton(text=f"❤️ لایک ({new_likes_count})", callback_data=btn.callback_data))
                else:
                    new_row.append(btn)
            new_keyboard.append(new_row)
        
        try:
            await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_keyboard))
        except Exception:
            pass


# ============================================================
# گام 4: سیستم گزارش تخلفات هوشمند همراه با ۵۰ پیام اخیر چت
# ============================================================

# ۱. منوی انتخاب دلیل گزارش برای کاربر
@dp.callback_query(F.data.startswith("report_menu_"))
async def show_report_reasons(call: CallbackQuery):
    try:
        target_id = int(call.data.split("_")[2])
    except (IndexError, ValueError):
        return

    if call.from_user.id == target_id:
        await call.answer("❌ شما نمی‌توانید خودتان را گزارش کنید!", show_alert=True)
        return

    reasons_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🤬 فحاشی و لحن نامناسب", callback_data=f"send_rep_{target_id}_abuse"),
                InlineKeyboardButton(text="🔞 محتوای غیراخلاقی", callback_data=f"send_rep_{target_id}_insult")
            ],
            [
                InlineKeyboardButton(text="💵 کلاهبرداری یا تبلیغات", callback_data=f"send_rep_{target_id}_scam"),
                InlineKeyboardButton(text="🪪 اکانت فیک و دروغین", callback_data=f"send_rep_{target_id}_fake")
            ],
            [
                InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_report")
            ]
        ]
    )

    # 🛠 ارور در این خط اصلاح شد: reply_text به answer تغییر یافت
    await call.message.answer(
        "⚠️ **لطفاً دلیل گزارش این کاربر را انتخاب کنید:**\n"
        "🚨 توجه: ۵۰ پیام اخیر چت شما جهت بررسی صحت گزارش برای مدیریت ارسال می‌شود.",
        reply_markup=reasons_kb
    )
    await call.answer()


@dp.callback_query(F.data == "cancel_report")
async def cancel_report_callback(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer("عملکرد لغو شد.")


# ۲. استخراج ۵۰ چت اخیر و ارسال گزارش نهایی به ادمین اصلی (Owner)
@dp.callback_query(F.data.startswith("send_rep_"))
async def submit_report_to_admin(call: CallbackQuery):
    reporter_id = call.from_user.id
    parts = call.data.split("_")
    
    try:
        target_id = int(parts[2])
        reason_key = parts[3]
    except (IndexError, ValueError):
        return

    reasons_map = {
        "abuse": "🤬 فحاشی و لحن نامناسب",
        "insult": "🔞 ارسال محتوای غیراخلاقی",
        "scam": "💵 کلاهبرداری یا تبلیغات",
        "fake": "🪪 اکانت فیک و دروغین"
    }
    chosen_reason = reasons_map.get(reason_key, "نامشخص")

    target_user = await get_user(target_id)
    reporter_user = await get_user(reporter_id)
    
    if not target_user:
        await call.answer("❌ کاربر یافت نشد.", show_alert=True)
        return

    target_hash = target_user[1]
    target_name = target_user[2]
    reporter_hash = reporter_user[1] if reporter_user else "ناشناس"
    reporter_name = reporter_user[2] if reporter_user else "ناشناس"

    chat_history_text = "💬 **متن ۵۰ پیام اخیر این گفتگو:**\n"
    chat_history_text += "🔻 (از قدیم به جدید تنظیم شده است)\n\n"
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT sender_id, text, timestamp FROM chat_logs 
            WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
            ORDER BY timestamp DESC LIMIT 50
        """, (reporter_id, target_id, target_id, reporter_id)) as cursor:
            logs = await cursor.fetchall()
            
    if logs:
        logs.reverse()
        for s_id, msg_text, t_stamp in logs:
            sender_label = "👤 متهم" if s_id == target_id else "📢 گزارش‌دهنده"
            msg_time = time.strftime('%H:%M', time.localtime(t_stamp))
            chat_history_text += f"⏰ {msg_time} **[{sender_label}]:** {html.escape(msg_text)}\n"
    else:
        chat_history_text += "❌ پیامی متنی در حافظه یافت نشد."

    admin_text = (
        "🚨 **گزارش تخلف جدید (نیاز به قضاوت ادمین)**\n\n"
        f"👤 **کاربر متخلف (گزارش شده):** {html.escape(target_name)}\n"
        f"🆔 آیدی اختصاصی متخلف: /{target_hash}\n"
        f"🔹 شناسه عددی متخلف: `{target_id}`\n\n"
        f"⚠️ **علت گزارش:** {chosen_reason}\n\n"
        f"{chat_history_text}\n"
        f"📢 **گزارش دهنده:** {html.escape(reporter_name)} (/{reporter_hash} | `{reporter_id}`)\n"
    )

    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🚫 مسدود کردن متخلف", callback_data=f"qban_{target_id}"),
            InlineKeyboardButton(text="⚠️ جریمه گزارش‌دهنده الکی", callback_data=f"warn_rep_{reporter_id}")
        ]]
    )

    try:
        await bot.send_message(chat_id=OWNER_ID, text=admin_text, reply_markup=admin_kb)
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.answer("✅ گزارش شما همراه با مدارک چت به مدیریت ارسال شد.", show_alert=True)
    except Exception as e:
        logging.error(f"Error sending report to admin: {e}")
        await call.answer("❌ خطایی رخ داد.", show_alert=True)


# ۳. عملکرد دکمه مسدود کردن متخلف واقعی
@dp.callback_query(F.data.startswith("qban_"))
async def quick_ban_from_report(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ شما دسترسی مدیریت ندارید.", show_alert=True)
        return

    target_id = int(call.data.split("_")[1])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned=1, status='banned', partner_id=0 WHERE user_id=?", (target_id,))
        await db.commit()

    await random_queue_remove(target_id)

    try:
        await bot.send_message(target_id, "🚫 **حساب شما به دلیل گزارش تخلفات توسط مدیریت محروم شد.**")
    except Exception:
        pass

    await call.message.edit_text(f"{call.message.text}\n\n🛑 **نتیجه: متخلف با موفقیت مسدود شد.**")
    await call.answer("✅ کاربر مسدود شد.")


# ۴. عملکرد دکمه جریمه کردن کاربر گزارش‌دهنده دروغگو
@dp.callback_query(F.data.startswith("warn_rep_"))
async def warn_fake_reporter(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ شما دسترسی مدیریت ندارید.", show_alert=True)
        return

    reporter_id = int(call.data.split("_")[2])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET warnings = warnings + 1, coins = CASE WHEN coins >= 5 THEN coins - 5 ELSE 0 END WHERE user_id=?", (reporter_id,))
        await db.commit()

    try:
        await bot.send_message(
            reporter_id, 
            "⚠️ **اخطار جدی مدیریت!**\n\n"
            "گزارش تخلفی که ارسال کرده بودید توسط ادمین بررسی و **دروغین** تشخیص داده شد!\n"
            "❌ به دلیل گزارش الکی، یک اخطار دریافت کردید و ۵ سکه از شما کسر شد."
        )
    except Exception:
        pass

    await call.message.edit_text(f"{call.message.text}\n\n⚠️ **نتیجه: گزارش‌دهنده به دلیل گزارش دروغین جریمه شد (+۱ اخطار / -۵ سکه).**")
    await call.answer("✅ گزارش‌دهنده الکی جریمه شد.")



# ============================================================


# CHAT REQUESTS & ACCEPTANCE**

# ============================================================


@dp.callback_query(F.data.startswith("req_chat_"))
async def request_chat(call: CallbackQuery):
    sender_id = call.from_user.id

    try:
        receiver_id = int(
            call.data.replace(
                "req_chat_",
                "",
                1
            )
        )
    except ValueError:
        return

    if sender_id == receiver_id:
        await call.answer(
            "❌ نمی‌توانید به خودتان درخواست بدهید.",
            show_alert=True
        )
        return

    chatting, _ = await is_chatting(sender_id)

    if chatting:
        await call.answer(
            "❌ ابتدا گفتگوی فعلی خود را قطع کنید.",
            show_alert=True
        )
        return

    coins = await get_coins(sender_id)

    if coins < 2:
        await call.answer(
            "❌ برای ارسال درخواست حداقل 2 سکه لازم دارید.",
            show_alert=True
        )
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT status, banned
            FROM users
            WHERE user_id=?
            """,
            (receiver_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        await call.answer(
            "❌ کاربر پیدا نشد.",
            show_alert=True
        )
        return

    if row[1]:
        await call.answer(
            "❌ این کاربر محروم است.",
            show_alert=True
        )
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT 1
            FROM chat_requests
            WHERE sender_id=? AND receiver_id=?
            """,
            (
                sender_id,
                receiver_id
            )
        ) as cursor:
            if await cursor.fetchone():
                await call.answer(
                    "⚠️ قبلاً درخواست داده‌اید."
                )
                return

        await db.execute(
            """
            INSERT INTO chat_requests
            (sender_id, receiver_id)
            VALUES (?, ?)
            """,
            (
                sender_id,
                receiver_id
            )
        )

        await db.commit()

    sender = await get_user(sender_id)

    if not sender:
        return

    (
        _uid,
        u_hash,
        name,
        age,
        gender,
        province,
        city,
        photo_id,
        _likes,
        _bio,
        *_rest
    ) = sender

    text = (
        f"🔔 **درخواست چت جدید!**\n\n"
        f"• نام: {html.escape(name or 'نامشخص')}\n"
        f"• سن: {html.escape(str(age or 'نامشخص'))} سال\n"
        f"• جنسیت: {html.escape(gender or 'نامشخص')}\n"
        f"• ولایت: {html.escape(province or 'نامشخص')}\n"
        f"• شهر: {html.escape(city or 'نامشخص')}\n\n"
        f"{profile_id_html(u_hash)}\n\n"
        f"آیا گفتگو را می‌پذیرید؟"
    )

    try:
        if photo_id and photo_id != "none":
            await bot.send_photo(
                receiver_id,
                photo=photo_id,
                caption=text,
                reply_markup=get_accept_reject_buttons(
                    sender_id
                )
            )
        else:
            await bot.send_message(
                receiver_id,
                text,
                reply_markup=get_accept_reject_buttons(
                    sender_id
                )
            )

        await call.answer(
            "💌 درخواست ارسال شد."
        )

    except Exception:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                DELETE FROM chat_requests
                WHERE sender_id=? AND receiver_id=?
                """,
                (
                    sender_id,
                    receiver_id
                )
            )
            await db.commit()

        await call.answer(
            "❌ ارسال درخواست ممکن نشد.",
            show_alert=True
        )


@dp.callback_query(F.data.startswith("accept_c_"))
async def accept_chat(call: CallbackQuery):
    receiver_id = call.from_user.id

    try:
        sender_id = int(
            call.data.replace(
                "accept_c_",
                "",
                1
            )
        )
    except ValueError:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT 1
            FROM chat_requests
            WHERE sender_id=? AND receiver_id=?
            """,
            (
                sender_id,
                receiver_id
            )
        ) as cursor:
            if not await cursor.fetchone():
                await call.answer(
                    "❌ درخواست دیگر معتبر نیست.",
                    show_alert=True
                )
                return

    s_chat, _ = await is_chatting(sender_id)
    r_chat, _ = await is_chatting(receiver_id)

    if s_chat or r_chat:
        await call.answer(
            "❌ یکی از کاربران در حال گفتگو است.",
            show_alert=True
        )
        return

    if await get_coins(sender_id) < 2:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                DELETE FROM chat_requests
                WHERE sender_id=? AND receiver_id=?
                """,
                (
                    sender_id,
                    receiver_id
                )
            )
            await db.commit()

        await call.answer(
            "❌ درخواست‌دهنده دیگر 2 سکه ندارد.",
            show_alert=True
        )
        return

    await remove_coins(
        sender_id,
        2
    )

    await random_queue_remove(sender_id)
    await random_queue_remove(receiver_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET status='chatting',
                partner_id=?
            WHERE user_id=?
            """,
            (
                receiver_id,
                sender_id
            )
        )

        await db.execute(
            """
            UPDATE users
            SET status='chatting',
                partner_id=?
            WHERE user_id=?
            """,
            (
                sender_id,
                receiver_id
            )
        )

        await db.execute(
            """
            DELETE FROM chat_requests
            WHERE sender_id=? AND receiver_id=?
            """,
            (
                sender_id,
                receiver_id
            )
        )

        await db.commit()

    try:
        await call.message.delete()
    except Exception:
        pass

    await bot.send_message(
        sender_id,
        "🎉 **درخواست شما قبول شد!**\n\n"
        "گفتگو آغاز شد.",
        reply_markup=get_chat_keyboard()
    )

    await bot.send_message(
        receiver_id,
        "🎉 **گفتگو متصل شد!**\n\n"
        "گفتگو آغاز شد.",
        reply_markup=get_chat_keyboard()
    )

    await call.answer()


@dp.callback_query(F.data.startswith("reject_c_"))
async def reject_chat(call: CallbackQuery):
    try:
        sender_id = int(
            call.data.replace(
                "reject_c_",
                "",
                1
            )
        )
    except ValueError:
        return

    receiver_id = call.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            DELETE FROM chat_requests
            WHERE sender_id=? AND receiver_id=?
            """,
            (
                sender_id,
                receiver_id
            )
        )
        await db.commit()

    try:
        await call.message.delete()
    except Exception:
        pass

    await call.answer(
        "درخواست رد شد."
    )


# ============================================================


# RANDOM CHAT MECHANISM**

# ============================================================


@dp.message(F.text == "💬 به یه ناشناس وصلم کن!")
async def random_chat(message: Message):
    user_id = message.chat.id

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT banned, status
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if row and row[0]:
        await message.answer(
            "🚫 حساب شما محروم است."
        )
        return

    chatting, _ = await is_chatting(user_id)

    if chatting:
        await message.answer(
            "❌ شما در حال حاضر در یک گفتگو هستید.\n\n"
            "ابتدا «❌ قطع گفتگو» را بزنید."
        )
        return

    if not row or row[1] == "registering":
        await message.answer(
            "❌ ابتدا ثبت‌نام خود را کامل کنید."
        )
        return

    existing = await random_queue_find(user_id)

    if existing:
        await random_queue_remove(existing)
        await random_queue_remove(user_id)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                UPDATE users
                SET status='chatting',
                    partner_id=?
                WHERE user_id=?
                """,
                (
                    existing,
                    user_id
                )
            )

            await db.execute(
                """
                UPDATE users
                SET status='chatting',
                    partner_id=?
                WHERE user_id=?
                """,
                (
                    user_id,
                    existing
                )
            )

            await db.commit()

        await bot.send_message(
            user_id,
            "🎉 **یک ناشناس برای شما پیدا شد!**\n\n"
            "گفتگو شروع شد.",
            reply_markup=get_chat_keyboard()
        )

        await bot.send_message(
            existing,
            "🎉 **یک ناشناس برای شما پیدا شد!**\n\n"
            "گفتگو شروع شد.",
            reply_markup=get_chat_keyboard()
        )

        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT user_id
            FROM random_queue
            WHERE user_id=?
            """,
            (user_id,)
        ) as cursor:
            if await cursor.fetchone():
                await message.answer(
                    "🔎 شما در صف جستجو هستید.",
                    reply_markup=get_searching_keyboard()
                )
                return

        await db.execute(
            """
            INSERT OR IGNORE INTO random_queue(user_id)
            VALUES(?)
            """,
            (user_id,)
        )

        await db.execute(
            """
            UPDATE users
            SET status='searching'
            WHERE user_id=?
            """,
            (user_id,)
        )

        await db.commit()

    await message.answer(
        "🔎 **در حال جستجوی یک ناشناس...**\n\n"
        "لطفاً منتظر بمانید. بعد از ۱ دقیقه خودکار خارج می‌شوید.",
        reply_markup=get_searching_keyboard()
    )

    asyncio.create_task(
        auto_remove_from_queue(user_id)
    )


# ============================================================
# AUTO REMOVE FROM QUEUE TASK
# ============================================================

async def auto_remove_from_queue(user_id):
    """
    این تابع پس از ۶۰ ثانیه کاربر را به صورت خودکار از صف جستجو حذف می‌کند
    تا دیتابیس سنگین نشود و کاربر بیهوده منتظر نماند.
    """
    await asyncio.sleep(60) # ۱ دقیقه انتظار
    
    async with aiosqlite.connect(DB_PATH) as db:
        # ابتدا چک می‌کنیم که کاربر هنوز در وضعیت جستجو باشد (وسط کار چت وصل نشده باشد)
        async with db.execute("SELECT status FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
        if row and row[0] == "searching":
            # وضعیت کاربر را به منوی اصلی برمی‌گردانیم
            await db.execute("""
                UPDATE users
                SET status='main_menu'
                WHERE user_id=?
            """, (user_id,))
            await db.commit()
            
            # از جدول صف تصادفی حذفش می‌کنیم
            await random_queue_remove(user_id)
            
            # به کاربر اطلاع می‌دهیم که کسی پیدا نشد
            try:
                await bot.send_message(
                    user_id,
                    "⏳ <b>کسی برای گفتگو پیدا نشد!</b>\n\n"
                    "صفحه شلوغ نیست یا در این لحظه کاربری آنلاین نیست. لطفاً دوباره تلاش کنید.",
                    reply_markup=get_main_keyboard()
                )
            except Exception:
                pass




# ============================================================
# CANCEL SEARCH (اصلاح شده و امن)
# ============================================================

@dp.message(F.text == "❌ لغو جستجو")
async def cancel_search(message: Message):
    user_id = message.chat.id

    async with aiosqlite.connect(DB_PATH) as db:
        # ابتدا وضعیت دقیق کاربر را چک می‌کنیم
        async with db.execute("SELECT status FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
        if not row:
            return
            
        current_status = row[0]

        # اگر در همین لحظه چت وصل شده باشد، جلوی لغو را می‌گیریم
        if current_status == "chatting":
            await message.answer(
                "🎉 <b>لغو نشد!</b> دقیقاً در همین لحظه یک ناشناس به شما متصل شد.\n گفتگو را شروع کنید!", 
                reply_markup=get_chat_keyboard()
            )
            return

        # اگر هنوز در حال جستجو بود، با خیال راحت لغو می‌کنیم
        if current_status == "searching":
            await db.execute("DELETE FROM random_queue WHERE user_id=?", (user_id,))
            await db.execute("UPDATE users SET status='main_menu' WHERE user_id=?", (user_id,))
            await db.commit()
            
            await message.answer("❌ جستجو با موفقیت لغو شد.", reply_markup=get_main_keyboard())
        else:
            await message.answer("❌ شما در صف جستجو نیستید.", reply_markup=get_main_keyboard())


# ============================================================
# END CHAT
# ============================================================

@dp.message(F.text == "❌ قطع گفتگو")
async def end_chat_button(message: Message):
    chatting, _ = await is_chatting(message.chat.id)
    if not chatting:
        await message.answer("❌ شما در حال گفتگو نیستید.", reply_markup=get_main_keyboard())
        return

    await message.answer("⚠️ <b>آیا مطمئن هستید که می‌خواهید گفتگو را پایان دهید؟</b>", reply_markup=get_end_confirm_keyboard())


@dp.callback_query(F.data == "cancel_end_chat")
async def cancel_end_chat(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer("گفتگو ادامه دارد.")


@dp.callback_query(F.data == "confirm_end_chat")
async def confirm_end_chat(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await end_chat(call.from_user.id)
    await call.answer()


async def end_chat(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT partner_id, status FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            partner_id, status = row

        if status != "chatting" or not partner_id:
            return

        await db.execute("UPDATE users SET status='main_menu', partner_id=0 WHERE user_id=?", (user_id,))
        await db.execute("UPDATE users SET status='main_menu', partner_id=0 WHERE user_id=?", (partner_id,))
        await db.commit()

    await bot.send_message(user_id, "❌ <b>گفتگو پایان یافت.</b>", reply_markup=get_main_keyboard())
    try:
        await bot.send_message(partner_id, "❌ <b>هم‌صحبت شما گفتگو را قطع کرد.</b>", reply_markup=get_main_keyboard())
    except Exception:
        pass


# ============================================================
# PARTNER PROFILE
# ============================================================

@dp.message(F.text == "👤 مشاهده پروفایل")
async def view_partner_profile(message: Message):
    chatting, partner_id = await is_chatting(message.chat.id)
    if not chatting:
        await message.answer("❌ شما در حال گفتگو نیستید.")
        return
    await send_profile(message.chat.id, partner_id, own=False)


# ============================================================
# NEARBY
# ============================================================

def nearby_gender_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👩 کاربران خانم", callback_data="near_female")],
        [InlineKeyboardButton(text="👨 کاربران آقا", callback_data="near_male")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="near_back")]
    ])


def request_location_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 ارسال موقعیت فعلی من", request_location=True)],
        [KeyboardButton(text="🔙 برگشت")]
    ], resize_keyboard=True, one_time_keyboard=True)


@dp.message(F.text == "📍 افراد نزدیک من")
async def nearby_start(message: Message):
    user_id = message.chat.id
    
    # بررسی ثبت‌نام کاربر برای جلوگیری از ارور دیتابیس
    if not await get_user(user_id):
        await message.answer("❌ <b>ابتدا باید ثبت‌نام خود را کامل کنید!</b>\n\nلطفاً ابتدا دستور /start را ارسال کنید.")
        return

    # بررسی اینکه کاربر در حال چت نباشد
    chatting, _ = await is_chatting(user_id)
    if chatting:
        await message.answer(
            "⚠️ شما در حال حاضر در یک گفتگو هستید!\n"
            "ابتدا باید گفتگو را قطع کنید تا بتوانید از این بخش استفاده کنید.",
            reply_markup=get_chat_keyboard()
        )
        return

    await message.answer("📍 <b>افراد نزدیک من</b>\n\nبرای پیدا کردن کاربران نزدیک، موقعیت خود را از طریق GPS تلگرام ارسال کنید.", reply_markup=request_location_keyboard())

@dp.message(F.location)
async def receive_location(message: Message):
    user_id = message.chat.id
    lat = message.location.latitude
    lon = message.location.longitude

    # بررسی اینکه کاربر در حال چت است یا خیر
    chatting, _ = await is_chatting(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET latitude=?, longitude=?, location_updated=?
            WHERE user_id=?
        """, (lat, lon, int(time.time()), user_id))
        await db.commit()

    # اگر کاربر در حال چت بود، فقط لوکیشن را ثبت کن و کیبورد چت را نگه دار
    if chatting:
        await message.answer("✅ موقعیت شما بروزرسانی شد.", reply_markup=get_chat_keyboard())
        return

    # اگر چت نبود، منوی عادی افراد نزدیک را نشان بده
    await message.answer("✅ <b>موقعیت شما ثبت شد.</b>", reply_markup=get_main_keyboard())
    await message.answer("👥 نوع کاربران نزدیک:", reply_markup=nearby_gender_menu())


async def show_nearby(call: CallbackQuery, gender_type):
    user_id = call.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT latitude, longitude FROM users WHERE user_id=?", (user_id,)) as cursor:
            me = await cursor.fetchone()

    if not me or me[0] is None or me[1] is None:
        await call.answer("❌ ابتدا موقعیت خود را ارسال کنید.", show_alert=True)
        return

    my_lat, my_lon = me
    gender_filter = "دختر" if gender_type == "female" else "پسر"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, username_hash, name, age, gender, province, city, photo_id, likes, bio, status, latitude, longitude
            FROM users
            WHERE user_id != ? AND status != 'registering' AND banned=0 AND gender LIKE ? AND latitude IS NOT NULL AND longitude IS NOT NULL
        """, (user_id, f"%{gender_filter}%")) as cursor:
            rows = await cursor.fetchall()

    results = []
    for row in rows:
        uid, u_hash, name, age, gender, province, city, photo_id, likes, bio, status, lat, lon = row
        distance = distance_km(my_lat, my_lon, lat, lon)
        results.append((0 if status == "chatting" else 1, distance, row))

    results.sort(key=lambda x: (x[0], x[1]))
    results = results[:20]

    if not results:
        await call.message.edit_text("⏳ کاربر نزدیکی با موقعیت ثبت‌شده پیدا نشد.")
        await call.answer()
        return

    text = "📍 <b>کاربران نزدیک شما</b>\n\n"
    for priority, distance, row in results:
        uid, u_hash, name, age, gender, province, city, photo_id, likes, bio, status, lat, lon = row
        online = "🟢 آنلاین" if status in ("chatting", "searching") else "⚪ آفلاین"
        text += (
            f"{'👩' if 'دختر' in gender else '👨'} <b>{html.escape(name)}</b>\n"
            f"🎂 {html.escape(age)} سال\n📍 {html.escape(city)}\n📏 {distance:.1f} کیلومتر\n"
            f"{online}\n❤️ {likes}\n{profile_id_html(u_hash)}\n────────────\n"
        )

    await call.message.edit_text(text)
    await call.answer()


@dp.callback_query(F.data == "near_female")
async def nearby_female(call: CallbackQuery):
    await show_nearby(call, "female")


@dp.callback_query(F.data == "near_male")
async def nearby_male(call: CallbackQuery):
    await show_nearby(call, "male")


@dp.callback_query(F.data == "near_back")
async def nearby_back(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer("منوی اصلی:", reply_markup=get_main_keyboard())
    await call.answer()


# ============================================================
# EDIT OWN PROFILE
# ============================================================

@dp.callback_query(F.data == "edit_my_name")
async def edit_name(call: CallbackQuery, state: FSMContext):
    await call.message.answer("✏️ نام جدید را ارسال کنید:")
    await state.set_state(EditStates.EDIT_NAME)
    await call.answer()


@dp.message(EditStates.EDIT_NAME)
async def save_name(message: Message, state: FSMContext):
    if not message.text:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET name=? WHERE user_id=?", (message.text.strip(), message.chat.id))
        await db.commit()
    await state.clear()
    await message.answer("✅ نام شما تغییر کرد.", reply_markup=get_main_keyboard())


@dp.callback_query(F.data == "edit_my_age")
async def edit_age(call: CallbackQuery, state: FSMContext):
    kb = []
    row = []
    for age in range(10, 61):
        row.append(InlineKeyboardButton(text=str(age), callback_data=f"edit_age_{age}"))
        if len(row) == 5:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    await call.message.answer("🎂 سن جدید را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(EditStates.EDIT_AGE)
    await call.answer()


@dp.callback_query(EditStates.EDIT_AGE, F.data.startswith("edit_age_"))
async def save_age(call: CallbackQuery, state: FSMContext):
    age = call.data.replace("edit_age_", "")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET age=? WHERE user_id=?", (age, call.from_user.id))
        await db.commit()
    await state.clear()
    await call.message.edit_text(f"✅ سن شما به <b>{age}</b> سال تغییر کرد.")
    await call.answer()


@dp.callback_query(F.data == "edit_my_province")
async def edit_province(call: CallbackQuery, state: FSMContext):
    kb = []
    for i in range(0, len(AFG_PROVINCES), 2):
        row = [InlineKeyboardButton(text=AFG_PROVINCES[i], callback_data=f"edit_prov_{AFG_PROVINCES[i]}")]
        if i + 1 < len(AFG_PROVINCES):
            row.append(InlineKeyboardButton(text=AFG_PROVINCES[i + 1], callback_data=f"edit_prov_{AFG_PROVINCES[i + 1]}"))
        kb.append(row)
    await call.message.answer("📍 ولایت جدید را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(EditStates.EDIT_PROVINCE)
    await call.answer()


@dp.callback_query(EditStates.EDIT_PROVINCE, F.data.startswith("edit_prov_"))
async def save_province(call: CallbackQuery, state: FSMContext):
    province = call.data.replace("edit_prov_", "")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET province=? WHERE user_id=?", (province, call.from_user.id))
        await db.commit()
    await state.clear()
    await call.message.edit_text(f"✅ ولایت به <b>{html.escape(province)}</b> تغییر کرد.")
    await call.answer()


@dp.callback_query(F.data == "edit_my_city")
async def edit_city(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🏠 نام شهر جدید را ارسال کنید:")
    await state.set_state(EditStates.EDIT_CITY)
    await call.answer()

@dp.message(EditStates.EDIT_CITY)
async def save_city(message: Message, state: FSMContext):
    if not message.text:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET city=? WHERE user_id=?",
            (message.text.strip(), message.chat.id)
        )
        await db.commit()

    await state.clear()
    await message.answer(
        "✅ شهر شما تغییر کرد.",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "edit_my_bio")
async def edit_bio(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📝 بیوگرافی جدید را ارسال کنید:")
    await state.set_state(EditStates.EDIT_BIO)
    await call.answer()


@dp.message(EditStates.EDIT_BIO)
async def save_bio(message: Message, state: FSMContext):
    if not message.text:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET bio=? WHERE user_id=?",
            (message.text.strip(), message.chat.id)
        )
        await db.commit()

    await state.clear()
    await message.answer(
        "✅ بیوگرافی تغییر کرد.",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "edit_my_photo")
async def edit_photo(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📸 عکس جدید را ارسال کنید:")
    await state.set_state(EditStates.EDIT_PHOTO)
    await call.answer()


@dp.message(EditStates.EDIT_PHOTO, F.photo)
async def save_photo(message: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET photo_id=? WHERE user_id=?",
            (message.photo[-1].file_id, message.chat.id)
        )
        await db.commit()

    await state.clear()
    await message.answer(
        "✅ عکس پروفایل تغییر کرد.",
        reply_markup=get_main_keyboard()
    )


# ============================================================
# UPDATE LOCATION & GUIDE & BACK
# ============================================================

@dp.callback_query(F.data == "update_location")
async def update_location(call: CallbackQuery):
    await call.message.answer(
        "📍 برای بروزرسانی موقعیت، دکمه زیر را بزنید.",
        reply_markup=request_location_keyboard()
    )
    await call.answer()


@dp.message(F.text == "❓ راهنما")
async def help_menu(message: Message):
    text = (
        "❓ **راهنمای افغان چت**\n\n"
        "💬 **به یه ناشناس وصلم کن!**\n"
        "برای پیدا کردن تصادفی یک کاربر استفاده می‌شود.\n\n"
        "🌀 **جستجوی کاربران**\n"
        "جستجو بر اساس جنسیت، سن، ولایت، شهر، جدید و محبوب.\n\n"
        "📍 **افراد نزدیک من**\n"
        "نمایش کاربران بر اساس فاصله.\n\n"
        "💰 **سکه**\n"
        "موجودی، دعوت و خرید سکه.\n\n"
        "👤 **پروفایل**\n"
        "مشاهده و ویرایش پروفایل.\n\n"
        "❌ **قطع گفتگو**\n"
        "قبل از پایان گفتگو تأیید دریافت می‌شود.\n\n"
        "👤 **مشاهده پروفایل**\n"
        "در زمان چت می‌توانید پروفایل طرف مقابل را مشاهده کنید."
    )

    await message.answer(
        text,
        reply_markup=get_main_keyboard()
    )


@dp.message(F.text == "📬 انتقادات و پیشنهادات")
async def feedback(message: Message, state: FSMContext):
    # بررسی ثبت‌نام کاربر برای جلوگیری از ارور دیتابیس
    if not await get_user(message.chat.id):
        await message.answer("❌ <b>ابتدا باید ثبت‌نام خود را کامل کنید!</b>\n\nلطفاً ابتدا دستور /start را ارسال کنید.")
        return

    await message.answer(
        "📬 **بخش انتقادات و پیشنهادات**\n\n"
        "لطفاً متن پیام، پیشنهاد یا انتقاد خود را در یک پیام ارسال کنید:\n"
        "*(برای لغو می‌توانید دکمه برگشت را بزنید)*",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔙 برگشت")]
            ],
            resize_keyboard=True
        )
    )

    await state.set_state(EditStates.FEEDBACK)



@dp.message(EditStates.FEEDBACK)
async def receive_feedback(message: Message, state: FSMContext):
    if message.text == "🔙 برگشت":
        await state.clear()
        await message.answer(
            "به منوی اصلی برگشتید.",
            reply_markup=get_main_keyboard()
        )
        return

    if not message.text:
        await message.answer(
            "❌ لطفاً پیام خود را به صورت متن ارسال کنید."
        )
        return

    user_id = message.chat.id

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT username_hash, name FROM users WHERE user_id=?",
            (user_id,)
        ) as cursor:
            user_row = await cursor.fetchone()

    u_hash = user_row[0] if user_row else "ناشناس"
    u_name = user_row[1] if user_row else "ناشناس"

    admin_report = (
        "📬 **یک انتقاد یا پیشنهاد جدید دریافت شد!**\n\n"
        f"👤 فرستنده: {html.escape(u_name)}\n"
        f"🆔 آیدی اختصاصی: {u_hash}\n"
        f"🔹 شناسه عددی: {user_id}\n\n"
        f"📝 **متن پیام:**\n{html.escape(message.text)}"
    )

    try:
        await bot.send_message(
            chat_id=OWNER_ID,
            text=admin_report
        )

        await message.answer(
            "✅ **پیام شما با موفقیت به مدیریت ارسال شد.**\n"
            "از اینکه به بهبود ربات کمک می‌کنید، سپاسگزاریم! 🙏",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        await message.answer(
            "❌ متأسفانه در ارسال پیام خطایی رخ داد. "
            "لطفاً بعداً تلاش کنید.",
            reply_markup=get_main_keyboard()
        )
        logging.error(f"Error sending feedback to admin: {e}")

    await state.clear()


@dp.message(F.text == "🔙 برگشت")
async def location_back(message: Message):
    await message.answer(
        "به منوی اصلی برگشتید.",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "locked")
async def locked(call: CallbackQuery):
    await call.answer(
        "🎯 این قابلیت در آپدیت بعدی فعال می‌شود.",
        show_alert=True
    )


@dp.message()
async def chat_router(message: Message):
    user_id = message.chat.id

    excluded = {
        "💬 به یه ناشناس وصلم کن!",
        "🌀 جستجوی کاربران",
        "📍 افراد نزدیک من",
        "💰 سکه",
        "👤 پروفایل",
        "❓ راهنما",
        "📬 انتقادات و پیشنهادات",
        "✉️ لینک ناشناس من",
        "❌ قطع گفتگو",
        "👤 مشاهده پروفایل",
        "🔙 برگشت",
        "📍 ارسال موقعیت فعلی من",
        "❌ لغو جستجو"
    }

    if message.text in excluded:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT partner_id, status, banned FROM users WHERE user_id=?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return

    partner_id, status, banned = row

    if banned:
        return

    # ارسال هوشمند و امن انواع رسانه (متن، عکس، استیکر، وویس، ویدیو و فایل)
    if status == "chatting" and partner_id:
        # 🛑 بررسی زنده بودن و بلاک نبودن ربات توسط طرف مقابل
        try:
            # ارسال وضعیت "در حال نوشتن..." برای تست آنلاین بودن مخاطب
            await bot.send_chat_action(chat_id=partner_id, action="typing")
        except Exception:
            # اگر خطایی رخ دهد یعنی طرف مقابل ربات را بلاک کرده است؛ پس چت فوراً قطع می‌شود
            await message.answer("⚠️ <b>ارتباط قطع شد!</b> هم‌صحبت شما ربات را مسدود (بلاک) کرده است.")
            await end_chat(user_id)
            return

        # 📥 ذخیره موقت پیام متنی در دیتابیس برای بخش بررسی تخلفات ادمین
        if message.text:
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "INSERT INTO chat_logs (sender_id, receiver_id, text, timestamp) VALUES (?, ?, ?, ?)",
                        (user_id, partner_id, message.text, int(time.time()))
                    )
                    await db.commit()
            except Exception as e:
                logging.error(f"Error saving chat log: {e}")

        # اگر طرف مقابل ربات را بلاک نکرده بود، پیام برایش ارسال می‌شود
        try:
            await message.send_copy(chat_id=partner_id)
        except Exception as e:
            logging.error(f"Chat message error: {e}")
            # اگر پیام به هر دلیل دیگری ارسال نشد، چت را دوطرفه قطع کن
            await end_chat(user_id)


async def main():
    global BOT_USERNAME

    if TOKEN == "YOUR_BOT_TOKEN":
        raise RuntimeError("TOKEN را در ابتدای فایل وارد کنید.")

    await init_db()
       # کد اختصاصی برای ریست کردن بیوگرافی‌های حاوی لینک‌های تبلیغاتی
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET bio='؟' WHERE bio LIKE '%t.me/%'")
        await db.commit()


    try:
        me = await bot.get_me()
        BOT_USERNAME = me.username or ""
        logging.info(
            f"Bot started successfully: @{BOT_USERNAME}"
        )

    except Exception as e:
        logging.error(
            f"Failed to connect to Telegram API: {e}"
        )
        return

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped by user.")

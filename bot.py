import os
import sqlite3
import logging
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "seradj_store.db")
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "213671629818")
STORE_NAME = "SERADJ STORE"
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

CANCEL_WORDS = {
    "إلغاء", "الغاء", "❌ إلغاء", "/cancel"
}

MAIN_MENU = [
    ["🛍️ المتجر", "📦 طلباتي"],
    ["👤 حسابي", "📞 اتصل بالإدارة"],
]

ADMIN_MAIN_MENU = [
    ["🛠️ لوحة التحكم"],
    ["🛍️ المتجر", "📦 طلباتي"],
    ["👤 حسابي", "📞 اتصل بالإدارة"],
]

ADMIN_PANEL_MENU = [
["🎮 إدارة الألعاب", "➕ إضافة لعبة"],
["📦 إدارة العروض", "➕ إضافة عرض"],
["💰 تعديل سعر عرض", "📋 كل الطلبات"],
["📊 الإحصائيات", "💳 إعدادات الدفع"],
["📝 إدارة النصوص", "📨 إرسال إشعار"],
["🔙 القائمة الرئيسية"],
]

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_setting(key, default=""):
    with db() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()

    return row["value"] if row else default


def set_setting(key, value):
    with db() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def is_admin(user_id):
    return user_id == ADMIN_ID and ADMIN_ID != 0


def main_keyboard(user_id):
    keyboard = (
        ADMIN_MAIN_MENU
        if is_admin(user_id)
        else MAIN_MENU
    )
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

async def admin_command(update, context):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.effective_message.reply_text(
            "⛔ هذا الأمر خاص بالإدارة."
        )
        return

    await update.effective_message.reply_text(
        "👑 لوحة تحكم SERADJ STORE",
        reply_markup=admin_keyboard()
    )
    
def admin_keyboard():
    return ReplyKeyboardMarkup(
        ADMIN_PANEL_MENU,
        resize_keyboard=True
    )

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [["❌ إلغاء"]],
        resize_keyboard=True
    )


def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🎮',
            active INTEGER DEFAULT 1,
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price_baridi INTEGER DEFAULT 0,
            price_flexy INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_id INTEGER,
            offer_id INTEGER,
            player_id TEXT DEFAULT '',
            payment_method TEXT DEFAULT '',
            price INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        );
        """)
#تحديث قاعدة البيانات القديمة دون حذف البيانات

    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(orders)"
        ).fetchall()
    }

    required_columns = {
        "game_id": "INTEGER",
        "offer_id": "INTEGER",
        "player_id": "TEXT DEFAULT ''",
        "payment_method": "TEXT DEFAULT ''",
        "price": "INTEGER DEFAULT 0",
        "status": "TEXT DEFAULT 'pending'",
        "created_at": "TEXT",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in columns:
            conn.execute(
                f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}"
            )

    # التحقق من أعمدة جدول الألعاب وإضافة الناقص فقط
    game_columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(games)"
        ).fetchall()
    }

    if "description" not in game_columns:
        conn.execute(
            "ALTER TABLE games ADD COLUMN description TEXT DEFAULT ''"
        )

    if "player_prompt" not in game_columns:
        conn.execute(
            "ALTER TABLE games ADD COLUMN player_prompt TEXT DEFAULT ''"
        )
        default_games = [
            ("Free Fire", "🔥"),
            ("PUBG Mobile", "🎯"),
            ("eFootball", "⚽"),
            ("FC Mobile", "⚽"),
            ("Call of Duty Mobile", "🎮"),
            ("Brawl Stars", "⭐"),
            ("Roblox", "🧱"),
            ("One State", "🚘"),
            ("TikTok", "🎵"),
            ("Blood Strike", "💥"),
            ("Snapchat+", "👻"),
            ("Netflix", "🎬"),
            ("Azar", "📹"),
            ("App Store", "🍎"),
        ]

        for name, emoji in default_games:
            conn.execute(
                """
                INSERT INTO games (name, emoji)
                SELECT ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM games WHERE name = ?
                )
                """,
                (name, emoji, name),
            )

        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("baridi_details", "تواصل مع الإدارة لمعرفة معلومات الدفع."),
        )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("flexy_details", "تواصل مع الإدارة لمعرفة معلومات Flexy."),
        )

        game = conn.execute(
            "SELECT id FROM games WHERE name = 'eFootball'"
        ).fetchone()

        if game:
            offers = [
                ("300 Coins", 750, 900),
                ("550 Coins", 1300, 1550),
                ("750 Coins", 1700, 2050),
                ("1040 Coins", 2300, 2750),
                ("2130 Coins", 4600, 5500),
                ("3250 Coins", 6600, 7900),
                ("5700 Coins", 11500, 13500),
                ("12800 Coins", 22000, 25500),
            ]

            for name, baridi, flexy in offers:
                conn.execute(
                    """
                    INSERT INTO offers
                    (game_id, name, price_baridi, price_flexy)
                    SELECT ?, ?, ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1 FROM offers
                        WHERE game_id = ? AND name = ?
                    )
                    """,
                    (
                        game["id"], name, baridi, flexy,
                        game["id"], name,
                    ),
                )


def get_setting(key, default=""):
    with db() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()

    return row["value"] if row else default


def set_setting(key, value):
    with db() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key)
            DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )


def get_games(active_only=True):
    with db() as conn:
        if active_only:
            return conn.execute(
                "SELECT * FROM games WHERE active = 1 ORDER BY id"
            ).fetchall()

        return conn.execute(
            "SELECT * FROM games ORDER BY id"
        ).fetchall()


def get_game(game_id):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM games WHERE id = ?",
            (game_id,),
        ).fetchone()


def get_offers(game_id, active_only=True):
    with db() as conn:
        if active_only:
            return conn.execute(
                """
                SELECT * FROM offers
                WHERE game_id = ? AND active = 1
                ORDER BY id
                """,
                (game_id,),
            ).fetchall()

        return conn.execute(
            """
            SELECT * FROM offers
            WHERE game_id = ?
            ORDER BY id
            """,
            (game_id,),
        ).fetchall()


def status_label(status):
    labels = {
        "pending": "⏳ قيد الانتظار",
        "processing": "🔄 قيد التنفيذ",
        "completed": "✅ مكتمل",
        "rejected": "❌ مرفوض",
    }
    return labels.get(status, status)

# ====== أوامر البداية ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    with db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users
            (user_id, username, full_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user.id,
                user.username or "",
                user.full_name or "",
                now_text(),
            ),
        )

    context.user_data.clear()

    welcome_text = get_setting(
        "welcome_message",
        f"🎮 مرحباً بك في {STORE_NAME}!\n\n"
        "🛍️ شحن الألعاب والخدمات الرقمية\n"
        "💳 الدفع عبر BaridiMob / CCP أو Flexy\n\n"
        "اختر الخدمة من القائمة بالأسفل 👇",
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=main_keyboard(user.id),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ تم إلغاء العملية.",
        reply_markup=main_keyboard(update.effective_user.id),
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Telegram ID تاعك:\n{update.effective_user.id}"
    )


# ====== عرض المتجر ======

async def show_store(message, user_id):
    games = get_games(active_only=True)

    if not games:
        await message.reply_text(
            "😕 لا توجد ألعاب متاحة حالياً.",
            reply_markup=main_keyboard(user_id),
        )
        return

    buttons = []

    for game in games:
        buttons.append([
            InlineKeyboardButton(
                f"{game['emoji']} {game['name']}",
                callback_data=f"game:{game['id']}",
            )
        ])

    await message.reply_text(
        "🛍️ مرحباً بك في متجر SERADJ STORE!\n\n"
        "اختر اللعبة أو الخدمة:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ====== حساب الزبون ======

async def show_account(message, user_id):
    with db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        total = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

    if not user:
        await message.reply_text(
            "أرسل /start لتسجيل حسابك.",
            reply_markup=main_keyboard(user_id),
        )
        return

    username = (
        f"@{user['username']}"
        if user["username"]
        else "غير متوفر"
    )

    await message.reply_text(
        "👤 حسابك في SERADJ STORE\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 الاسم: {user['full_name']}\n"
        f"🔗 Username: {username}\n"
        f"📦 عدد الطلبات: {total}\n"
        f"📅 التسجيل: {user['created_at']}",
        reply_markup=main_keyboard(user_id),
        )

# ====== عرض عروض اللعبة ======

async def open_game(query, game_id):
    game = get_game(game_id)

    if not game or not game["active"]:
        await query.edit_message_text(
            "❌ هذه الخدمة غير متاحة حالياً."
        )
        return

    offers = get_offers(game_id)
    description = (game["description"] or "").strip()

    if not offers:
        await query.edit_message_text(
            f"{game['emoji']} {game['name']}\n\n"
            f"{description + chr(10) + chr(10) if description else ''}"
            "لا توجد عروض حالياً.\n"
            "تواصل مع الإدارة للمزيد من المعلومات."
        )
        return

    buttons = []

    for offer in offers:
        buttons.append([
            InlineKeyboardButton(
                f"{offer['name']} | "
                f"{offer['price_baridi']} دج",
                callback_data=(
                    f"offer:{game_id}:{offer['id']}"
                ),
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 رجوع للمتجر",
            callback_data="store",
        )
    ])

    await query.edit_message_text(
        f"{game['emoji']} {game['name']}\n\n"
        f"{description + chr(10) + chr(10) if description else ''}"
        "اختر العرض المناسب:\n"
        "💳 الأسعار المعروضة هي أسعار BaridiMob / CCP.",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ====== تفاصيل العرض ======

async def open_offer(query, game_id, offer_id):
    game = get_game(game_id)
    offers = get_offers(game_id)

    offer = next(
        (item for item in offers if item["id"] == offer_id),
        None,
    )

    if not game or not offer:
        await query.edit_message_text(
            "❌ هذا العرض غير متاح."
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"💳 BaridiMob / CCP — "
                f"{offer['price_baridi']} دج",
                callback_data=(
                    f"pay:{game_id}:{offer_id}:baridi"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                f"📱 Flexy — {offer['price_flexy']} دج",
                callback_data=(
                    f"pay:{game_id}:{offer_id}:flexy"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 رجوع",
                callback_data=f"game:{game_id}",
            )
        ],
    ]

    await query.edit_message_text(
        "🛍️ تفاصيل العرض\n\n"
        f"🎮 اللعبة: {game['name']}\n"
        f"📦 العرض: {offer['name']}\n\n"
        f"💳 BaridiMob / CCP: "
        f"{offer['price_baridi']} دج\n"
        f"📱 Flexy: {offer['price_flexy']} دج\n\n"
        "اختر طريقة الدفع:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ====== اختيار طريقة الدفع ======

async def select_payment(
    query,
    context,
    game_id,
    offer_id,
    method,
):
    game = get_game(game_id)
    offers = get_offers(game_id)

    offer = next(
        (item for item in offers if item["id"] == offer_id),
        None,
    )

    if not game or not offer:
        await query.edit_message_text(
            "❌ العرض لم يعد متاحاً."
        )
        return

    if method == "baridi":
        price = offer["price_baridi"]
        method_name = "BaridiMob / CCP"
        details = get_setting(
            "baridi_details",
            "تواصل مع الإدارة لمعرفة معلومات الدفع.",
        )
    elif method == "flexy":
        price = offer["price_flexy"]
        method_name = "Flexy"
        details = get_setting(
            "flexy_details",
            "تواصل مع الإدارة لمعرفة معلومات الدفع.",
        )
    else:
        await query.edit_message_text(
            "❌ طريقة الدفع غير صحيحة."
        )
        return

    context.user_data["order_draft"] = {
        "game_id": game_id,
        "offer_id": offer_id,
        "game_name": game["name"],
        "offer_name": offer["name"],
        "method": method_name,
        "price": price,
    }

    context.user_data["awaiting_player_id"] = True

    await query.edit_message_text(
        "✅ اخترت العرض بنجاح!\n\n"
        f"🎮 اللعبة: {game['name']}\n"
        f"📦 العرض: {offer['name']}\n"
        f"💳 الدفع: {method_name}\n"
        f"💰 السعر: {price} دج\n\n"
        f"💳 معلومات الدفع:\n{details}\n\n"
        "🆔 أرسل الآن معرف اللاعب (Player ID).\n"
        "إذا ما تحتاجش الخدمة معرف، أرسل: بدون\n\n"
        "للإلغاء أرسل /cancel"
    )


# ====== إنشاء الطلب ======

async def create_order(update, context):
    user = update.effective_user
    player_id = update.message.text.strip()
    draft = context.user_data.get("order_draft")

    if not draft:
        context.user_data.pop("awaiting_player_id", None)
        return

    if not player_id:
        await update.message.reply_text(
            "❌ أرسل معرف اللاعب أو اكتب: بدون"
        )
        return

    # حفظ معلومات الشحن مؤقتًا حتى يرسل الزبون الوصل
    context.user_data["pending_player_id"] = player_id
    context.user_data["awaiting_payment_receipt"] = True
    context.user_data.pop("awaiting_player_id", None)

    await update.message.reply_text(
        "✅ تم استلام معلومات الشحن!\n\n"
        f"🎮 اللعبة: {draft['game_name']}\n"
        f"📦 العرض: {draft['offer_name']}\n"
        f"🆔 معرف اللاعب: {player_id}\n"
        f"💳 طريقة الدفع: {draft['method']}\n"
        f"💰 المبلغ: {draft['price']} دج\n\n"
        "📸 الآن أرسل صورة وصل الدفع لإتمام الطلب.\n\n"
        "⚠️ تأكد أن الصورة واضحة وتظهر معلومات العملية.\n"
        "لإلغاء العملية أرسل /cancel"
    )
async def photo_handler(update, context):
    user = update.effective_user
    message = update.effective_message

    if not context.user_data.get("awaiting_payment_receipt"):
        return

    draft = context.user_data.get("order_draft")
    player_id = context.user_data.get("pending_player_id")

    if not draft or player_id is None:
        context.user_data.pop("awaiting_payment_receipt", None)
        await message.reply_text(
            "❌ انتهت جلسة الطلب. ابدأ طلبًا جديدًا."
        )
        return

    # الحصول على صورة الوصل
    photo = message.photo[-1]

    # إنشاء الطلب بعد استلام صورة الوصل
    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO orders (
                user_id, game_id, offer_id, player_id,
                payment_method, price, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                draft["game_id"],
                draft["offer_id"],
                player_id,
                draft["method"],
                draft["price"],
                "pending",
                now_text(),
            ),
        )
        order_id = cursor.lastrowid

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔄 قيد التنفيذ",
                callback_data=f"status:{order_id}:processing",
            ),
            InlineKeyboardButton(
                "✅ مكتمل",
                callback_data=f"status:{order_id}:completed",
            ),
        ],
        [
            InlineKeyboardButton(
                "❌ رفض الطلب",
                callback_data=f"status:{order_id}:rejected",
            ),
        ],
    ])

    # إرسال صورة الوصل مع معلومات الطلب إلى الأدمن
    if ADMIN_ID:
        try:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo.file_id,
                caption=(
                    f"🆕 طلب جديد #{order_id}\n\n"
                    f"👤 الزبون: {user.full_name}\n"
                    f"🆔 Telegram ID: {user.id}\n"
                    f"🎮 الخدمة: {draft['game_name']}\n"
                    f"📦 العرض: {draft['offer_name']}\n"
                    f"🆔 معرف اللاعب: {player_id}\n"
                    f"💳 الدفع: {draft['method']}\n"
                    f"💰 السعر: {draft['price']} دج\n"
                    f"🧾 وصل الدفع: مرفق أعلاه\n"
                    f"📌 الحالة: قيد الانتظار\n"
                    f"🕒 الوقت: {now_text()}"
                ),
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.exception(
                "تعذر إرسال وصل الدفع إلى الإدارة"
            )
            await message.reply_text(
                "❌ تعذر إرسال وصل الدفع إلى الإدارة.\n"
                f"سبب الخطأ: {str(e)[:300]}\n\n"
                "لم يتم تأكيد الطلب. تواصل مع الإدارة."
            )
            return

    # إنهاء حالة الطلب المؤقتة
    context.user_data.pop("order_draft", None)
    context.user_data.pop("pending_player_id", None)
    context.user_data.pop("awaiting_payment_receipt", None)

    await message.reply_text(
        "✅ تم استلام صورة وصل الدفع وتسجيل طلبك!\n\n"
        f"🧾 رقم الطلب: #{order_id}\n"
        f"🎮 الخدمة: {draft['game_name']}\n"
        f"📦 العرض: {draft['offer_name']}\n"
        f"🆔 معرف اللاعب: {player_id}\n"
        f"💳 طريقة الدفع: {draft['method']}\n"
        f"💰 المبلغ: {draft['price']} دج\n"
        "📌 الحالة: قيد الانتظار\n\n"
        "ستتحقق الإدارة من الوصل قبل معالجة طلبك.",
        reply_markup=main_keyboard(user.id),
    )
# =========================
# عرض طلبات الزبون
# =========================

async def show_my_orders(update, context):
    user_id = update.effective_user.id

    with db() as conn:
        orders = conn.execute(
            """
            SELECT id, game_id, offer_id, player_id,
                   payment_method, price, status, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (user_id,),
        ).fetchall()

        games = {
            row["id"]: row["name"]
            for row in conn.execute("SELECT id, name FROM games").fetchall()
        }

        offers = {
            row["id"]: row["name"]
            for row in conn.execute("SELECT id, name FROM offers").fetchall()
        }

    if not orders:
        await update.message.reply_text(
            "📦 ما عندك حتى طلب حاليا.",
            reply_markup=main_keyboard(user_id),
        )
        return

    lines = ["📦 <b>آخر طلباتك:</b>\n"]

    for order in orders:
        game_name = games.get(order["game_id"], "لعبة محذوفة")
        offer_name = offers.get(order["offer_id"], "عرض محذوف")

        lines.append(
            f"🧾 <b>الطلب #{order['id']}</b>\n"
            f"🎮 اللعبة: {game_name}\n"
            f"📦 العرض: {offer_name}\n"
            f"🆔 المعرّف: {order['player_id'] or 'غير محدد'}\n"
            f"💳 الدفع: {order['payment_method'] or 'غير محدد'}\n"
            f"💰 السعر: {order['price']} دج\n"
            f"📌 الحالة: {status_label(order['status'])}\n"
            f"🕒 التاريخ: {order['created_at']}\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=main_keyboard(user_id),
    )


# =========================
# زر التواصل عبر واتساب
# =========================

def wa_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 التواصل عبر WhatsApp",
                url=f"https://wa.me/{WHATSAPP_NUMBER}",
            )
        ]
    ])


# =========================
# لوحة تحكم الإدارة
# =========================

async def show_admin_panel(update, context):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.effective_message.reply_text(
            "⛔ هذه القائمة خاصة بالإدارة.",
            reply_markup=main_keyboard(user_id),
        )
        return

    await update.effective_message.reply_text(
        "🛠️ <b>لوحة تحكم SERADJ STORE</b>\n\n"
        "اختار العملية لي حاب تديرها من الأزرار لي تحت.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            ADMIN_PANEL_MENU,
            resize_keyboard=True,
        ),
    )


#=========================

#إدارة الألعاب

#=========================


# =========================
# اختيار لعبة لإضافة عرض
# =========================

async def admin_choose_offer_game(query):
    with db() as conn:
        games = conn.execute(
            "SELECT id, name, emoji FROM games ORDER BY id"
        ).fetchall()

    buttons = [
        [
            InlineKeyboardButton(
                f"{game['emoji']} {game['name']}",
                callback_data=f"add_offer_game:{game['id']}",
            )
        ]
        for game in games
    ]

    buttons.append([
        InlineKeyboardButton(
            "🔙 رجوع",
            callback_data="adm_home",
        )
    ])

    await query.edit_message_text(
        "🎮 اختار اللعبة لي حاب تزيدلها عرض:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================
# إدارة الألعاب
# =========================

async def admin_games(query):
    with db() as conn:
        games = conn.execute(
            "SELECT id, name, emoji, active FROM games ORDER BY id"
        ).fetchall()

    buttons = []

    for game in games:
        state = "🟢" if game["active"] else "🔴"

        buttons.append([
            InlineKeyboardButton(
                f"{state} {game['emoji']} {game['name']}",
                callback_data=f"game_toggle:{game['id']}",
            ),
            InlineKeyboardButton(
                "🗑️",
                callback_data=f"game_delete:{game['id']}",
            ),
        ])

        buttons.append([
            InlineKeyboardButton(
                "📝 تعديل الوصف",
                callback_data=f"game_desc:{game['id']}",
            ),
            InlineKeyboardButton(
                "✏️ تعديل رسالة طلب المعلومات",
                callback_data=f"game_prompt:{game['id']}",
            ),
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔄 تحديث",
            callback_data="adm_games",
        )
    ])

    await query.edit_message_text(
        "🎮 <b>إدارة الألعاب</b>\n\n"
        "🟢 / 🔴 اضغط على اسم اللعبة لتفعيلها أو إيقافها.\n"
        "📝 تعديل وصف اللعبة.\n"
        "✏️ تعديل رسالة طلب المعلومات.\n"
        "🗑️ حذف اللعبة والعروض التابعة لها.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )



# =========================
# عرض عروض لعبة معينة
# =========================

async def admin_offers(query, game_id):
    with db() as conn:
        game = conn.execute(
            "SELECT name, emoji FROM games WHERE id = ?",
            (game_id,),
        ).fetchone()

        offers = conn.execute(
            """
            SELECT id, name, price_baridi, price_flexy, active
            FROM offers
            WHERE game_id = ?
            ORDER BY id
            """,
            (game_id,),
        ).fetchall()

    if not game:
        await query.edit_message_text("❌ اللعبة غير موجودة.")
        return

    buttons = []

    for offer in offers:
        state = "🟢" if offer["active"] else "🔴"

        buttons.append([
            InlineKeyboardButton(
                f"{state} {offer['name']}",
                callback_data=f"offer_toggle:{offer['id']}",
            ),
            InlineKeyboardButton(
                "💰 تعديل السعر",
                callback_data=f"edit_offer:{offer['id']}",
            ),
            InlineKeyboardButton(
                "🗑️",
                callback_data=f"offer_delete:{offer['id']}",
            ),
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 اختيار لعبة أخرى",
            callback_data="adm_offers",
        )
    ])

    text = (
        f"{game['emoji']} <b>عروض {game['name']}</b>\n\n"
        "🟢 العرض مفعّل\n"
        "🔴 العرض متوقف\n\n"
        "اضغط على اسم العرض لتفعيله أو إيقافه."
    )

    if not offers:
        text += "\n\nما كاين حتى عرض لهذه اللعبة حاليا."

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================
# اختيار لعبة لإدارة عروضها
# =========================

async def admin_choose_manage_game(query):
    with db() as conn:
        games = conn.execute(
            "SELECT id, name, emoji FROM games ORDER BY id"
        ).fetchall()

    buttons = [
        [
            InlineKeyboardButton(
                f"{game['emoji']} {game['name']}",
                callback_data=f"offers_game:{game['id']}",
            )
        ]
        for game in games
    ]

    buttons.append([
        InlineKeyboardButton(
            "🔙 رجوع",
            callback_data="adm_home",
        )
    ])

    await query.edit_message_text(
        "📦 اختار اللعبة باش تشوف عروضها وتتحكم فيها:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# =========================
# عرض جميع الطلبات للإدارة
# =========================

async def admin_all_orders(query):
    with db() as conn:
        orders = conn.execute(
            """
            SELECT o.id, o.user_id, o.game_id, o.offer_id,
                   o.player_id, o.payment_method, o.price,
                   o.status, o.created_at,
                   g.name AS game_name,
                   f.name AS offer_name
            FROM orders o
            LEFT JOIN games g ON g.id = o.game_id
            LEFT JOIN offers f ON f.id = o.offer_id
            ORDER BY o.id DESC
            LIMIT 15
            """
        ).fetchall()

    if not orders:
        await query.edit_message_text(
            "📦 ما كاين حتى طلب في المتجر حاليا.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")]
            ]),
        )
        return

    buttons = []

    for order in orders:
        buttons.append([
            InlineKeyboardButton(
                f"#{order['id']} | {status_label(order['status'])}",
                callback_data=f"order_view:{order['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔄 تحديث",
            callback_data="adm_orders",
        ),
        InlineKeyboardButton(
            "🔙 رجوع",
            callback_data="adm_home",
        ),
    ])

    await query.edit_message_text(
        "📋 <b>آخر 15 طلب</b>\n\n"
        "اختار طلب باش تشوف التفاصيل وتبدل حالته.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================
# تفاصيل طلب للإدارة
# =========================

async def admin_order_details(query, order_id):
    with db() as conn:
        order = conn.execute(
            """
            SELECT o.*, g.name AS game_name,
                   f.name AS offer_name
            FROM orders o
            LEFT JOIN games g ON g.id = o.game_id
            LEFT JOIN offers f ON f.id = o.offer_id
            WHERE o.id = ?
            """,
            (order_id,),
        ).fetchone()

    if not order:
        await query.edit_message_text("❌ الطلب غير موجود.")
        return

    text = (
        f"🧾 <b>تفاصيل الطلب #{order['id']}</b>\n\n"
        f"👤 المستخدم: <code>{order['user_id']}</code>\n"
        f"🎮 اللعبة: {order['game_name'] or 'غير موجودة'}\n"
        f"📦 العرض: {order['offer_name'] or 'غير موجود'}\n"
        f"🆔 معرّف اللاعب: {order['player_id'] or 'غير محدد'}\n"
        f"💳 طريقة الدفع: {order['payment_method'] or 'غير محددة'}\n"
        f"💰 السعر: {order['price']} دج\n"
        f"📌 الحالة: {status_label(order['status'])}\n"
        f"🕒 التاريخ: {order['created_at']}"
    )

    buttons = [
        [
            InlineKeyboardButton(
                "🔄 قيد التنفيذ",
                callback_data=f"status:{order_id}:processing",
            ),
            InlineKeyboardButton(
                "✅ مكتمل",
                callback_data=f"status:{order_id}:completed",
            ),
        ],
        [
            InlineKeyboardButton(
                "❌ رفض الطلب",
                callback_data=f"status:{order_id}:rejected",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 جميع الطلبات",
                callback_data="adm_orders",
            )
        ],
    ]

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================
# إحصائيات المتجر
# =========================

async def show_stats(query):
    with db() as conn:
        total_orders = conn.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        pending_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
        ).fetchone()[0]

        processing_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'processing'"
        ).fetchone()[0]

        completed_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
        ).fetchone()[0]

        rejected_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'rejected'"
        ).fetchone()[0]

        total_users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        completed_revenue = conn.execute(
            """
            SELECT COALESCE(SUM(price), 0)
            FROM orders
            WHERE status = 'completed'
            """
        ).fetchone()[0]

        active_games = conn.execute(
            "SELECT COUNT(*) FROM games WHERE active = 1"
        ).fetchone()[0]

        active_offers = conn.execute(
            "SELECT COUNT(*) FROM offers WHERE active = 1"
        ).fetchone()[0]

    text = (
        "📊 <b>إحصائيات SERADJ STORE</b>\n\n"
        f"👥 عدد المستخدمين: {total_users}\n"
        f"🎮 الألعاب المفعلة: {active_games}\n"
        f"📦 العروض المفعلة: {active_offers}\n\n"
        f"🧾 مجموع الطلبات: {total_orders}\n"
        f"⏳ طلبات جديدة: {pending_orders}\n"
        f"🔄 قيد التنفيذ: {processing_orders}\n"
        f"✅ طلبات مكتملة: {completed_orders}\n"
        f"❌ طلبات مرفوضة: {rejected_orders}\n\n"
        f"💰 قيمة الطلبات المكتملة: {completed_revenue} دج"
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔄 تحديث",
                    callback_data="adm_stats",
                ),
                InlineKeyboardButton(
                    "🔙 رجوع",
                    callback_data="adm_home",
                ),
            ]
        ]),
    )


# =========================
# إعدادات الدفع
# =========================

async def admin_payment_settings(query):
    baridi = get_setting("baridi_details", "غير محددة")
    flexy = get_setting("flexy_details", "غير محددة")

    text = (
        "💳 <b>إعدادات الدفع</b>\n\n"
        f"🏦 <b>BaridiMob / CCP:</b>\n{baridi}\n\n"
        f"📱 <b>Flexy:</b>\n{flexy}\n\n"
        "اختار طريقة الدفع لي حاب تبدل معلوماتها."
    )

    buttons = [
        [
            InlineKeyboardButton(
                "🏦 تعديل BaridiMob / CCP",
                callback_data="pay_settings:baridi",
            )
        ],
        [
            InlineKeyboardButton(
                "📱 تعديل Flexy",
                callback_data="pay_settings:flexy",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 رجوع",
                callback_data="adm_home",
            )
        ],
    ]

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
        )


# =========================
# معالجة أزرار لوحة التحكم
# =========================

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    user_id = query.from_user.id

    # التحقق من صلاحيات الإدارة
    admin_actions = (
        "adm_",
        "game_toggle:",
        "game_delete:",
        "game_desc:",
        "game_prompt:",
        "offers_game:",
        "offer_toggle:",
        "offer_delete:",
        "add_offer_game:",
        "edit_offer:",
        "order_view:",
        "status:",
        "pay_settings:",
        "text_edit:",
        "notify_",
    )

    if data.startswith(admin_actions) and not is_admin(user_id):
        await query.answer("⛔ غير مسموح لك.", show_alert=True)
        return

    # العودة إلى لوحة الإدارة
    if data == "adm_home":
        await query.edit_message_text(
            "⚙️ لوحة الإدارة",
            reply_markup=ADMIN_PANEL_MENU,
        )

    # عرض الطلبات
    elif data == "adm_orders":
        await admin_all_orders(query)

    # الإحصائيات
    elif data == "adm_stats":
        await show_stats(query)

    # إدارة الألعاب
    elif data == "adm_games":
        await admin_games(query)

    # إدارة العروض
    elif data == "adm_offers":
        await admin_choose_manage_game(query)

    # إعدادات الدفع
    elif data == "adm_payment":
        await admin_payment_settings(query)

    # اختيار لعبة لإضافة عرض
    elif data == "adm_add_offer":
        await admin_choose_offer_game(query)

    # تعديل وصف اللعبة
    elif data.startswith("game_desc:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف اللعبة غير صالح."
            )
            return

        with db() as conn:
            game = conn.execute(
                "SELECT id, name FROM games WHERE id = ?",
                (game_id,),
            ).fetchone()

        if not game:
            await query.message.reply_text(
                "❌ اللعبة غير موجودة."
            )
            return

        context.user_data["editing_game_description"] = game_id

        await query.message.reply_text(
            f"📝 أرسل الوصف الجديد للعبة: {game['name']}\n\n"
            "أرسل الوصف في رسالة واحدة."
        )

    # تعديل رسالة طلب معلومات الشحن
    elif data.startswith("game_prompt:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف اللعبة غير صالح."
            )
            return

        with db() as conn:
            game = conn.execute(
                "SELECT id, name FROM games WHERE id = ?",
                (game_id,),
            ).fetchone()

        if not game:
            await query.message.reply_text(
                "❌ اللعبة غير موجودة."
            )
            return

        context.user_data["editing_game_prompt"] = game_id

        await query.message.reply_text(
            f"✏️ أرسل الرسالة الجديدة للزبون عند اختيار لعبة {game['name']}.\n\n"
            "يمكنك كتابة الرسالة على عدة أسطر."
        )

    # عرض تفاصيل الطلب
    elif data.startswith("order_view:"):
        try:
            order_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ رقم الطلب غير صالح."
            )
            return

        await admin_order_details(query, order_id)

    # تفعيل أو إيقاف لعبة
    elif data.startswith("game_toggle:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف اللعبة غير صالح."
            )
            return

        with db() as conn:
            conn.execute(
                """
                UPDATE games
                SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END
                WHERE id = ?
                """,
                (game_id,),
            )

        await admin_games(query)

    # حذف لعبة وعروضها
    elif data.startswith("game_delete:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف اللعبة غير صالح."
            )
            return

        with db() as conn:
            conn.execute(
                "DELETE FROM offers WHERE game_id = ?",
                (game_id,),
            )
            conn.execute(
                "DELETE FROM games WHERE id = ?",
                (game_id,),
            )

        await admin_games(query)

    # فتح عروض لعبة
    elif data.startswith("offers_game:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف اللعبة غير صالح."
            )
            return

        await admin_offers(query, game_id)

    # تفعيل أو إيقاف عرض
    elif data.startswith("offer_toggle:"):
        try:
            offer_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف العرض غير صالح."
            )
            return

        with db() as conn:
            conn.execute(
                """
                UPDATE offers
                SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END
                WHERE id = ?
                """,
                (offer_id,),
            )

            row = conn.execute(
                "SELECT game_id FROM offers WHERE id = ?",
                (offer_id,),
            ).fetchone()

        if row:
            await admin_offers(query, row["game_id"])
        else:
            await query.edit_message_text(
                "❌ العرض غير موجود."
            )

    # حذف عرض
    elif data.startswith("offer_delete:"):
        try:
            offer_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف العرض غير صالح."
            )
            return

        with db() as conn:
            row = conn.execute(
                "SELECT game_id FROM offers WHERE id = ?",
                (offer_id,),
            ).fetchone()

            if row:
                game_id = row["game_id"]
                conn.execute(
                    "DELETE FROM offers WHERE id = ?",
                    (offer_id,),
                )

        if row:
            await admin_offers(query, game_id)
        else:
            await query.edit_message_text(
                "❌ العرض غير موجود."
            )

    # اختيار لعبة لإضافة عرض
    elif data.startswith("add_offer_game:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف اللعبة غير صالح."
            )
            return

        context.user_data["admin_step"] = "add_offer_data"
        context.user_data["pending_game_id"] = game_id

        await query.message.reply_text(
            "➕ ابعث معلومات العرض بهذا الشكل:\n\n"
            "اسم العرض | سعر BaridiMob/CCP | سعر Flexy\n\n"
            "مثال:\n"
            "100 Coins | 250 | 300\n\n"
            "ابعث /cancel للإلغاء."
        )

    # اختيار عرض لتعديل أسعاره
    elif data.startswith("edit_offer:"):
        try:
            offer_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text(
                "❌ معرّف العرض غير صالح."
            )
            return

        with db() as conn:
            offer = conn.execute(
                "SELECT name FROM offers WHERE id = ?",
                (offer_id,),
            ).fetchone()

        if not offer:
            await query.edit_message_text(
                "❌ العرض غير موجود."
            )
            return

        context.user_data["admin_step"] = "edit_price_data"
        context.user_data["pending_offer_id"] = offer_id

        await query.message.reply_text(
            f"💰 تعديل أسعار العرض: {offer['name']}\n\n"
            "ابعث السعرين بهذا الشكل:\n"
            "سعر BaridiMob/CCP | سعر Flexy\n\n"
            "مثال:\n"
            "750 | 900\n\n"
            "ابعث /cancel للإلغاء."
        )

    # اختيار طريقة الدفع لتعديل معلوماتها
    elif data.startswith("pay_settings:"):
        method = data.split(":", 1)[1]

        if method not in ("baridi", "flexy"):
            return

        context.user_data["admin_step"] = "set_payment"
        context.user_data["pending_payment_method"] = method

        if method == "baridi":
            message = (
                "🏦 ابعث معلومات BaridiMob / CCP الجديدة.\n"
                "مثال: الاسم ورقم الحساب أو RIP."
            )
        else:
            message = (
                "📱 ابعث معلومات Flexy الجديدة، "
                "مثل رقم الهاتف والتعليمات."
            )

        await query.message.reply_text(
            message + "\n\nابعث /cancel للإلغاء."
        )

    # تغيير حالة الطلب وإخبار الزبون
    elif data.startswith("status:"):
        parts = data.split(":")

        if len(parts) != 3:
            return

        try:
            order_id = int(parts[1])
        except ValueError:
            return

        new_status = parts[2]

        allowed_statuses = {
            "processing",
            "completed",
            "rejected",
        }

        if new_status not in allowed_statuses:
            return

        with db() as conn:
            order = conn.execute(
                "SELECT user_id FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()

            if not order:
                await query.edit_message_text(
                    "❌ الطلب غير موجود."
                )
                return

            conn.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (new_status, order_id),
            )

            customer_id = order["user_id"]

        status_text = status_label(new_status)

        try:
            await context.bot.send_message(
                chat_id=customer_id,
                text=(
                    f"📦 تحديث الطلب #{order_id}\n\n"
                    f"📌 الحالة الجديدة: {status_text}"
                ),
                reply_markup=main_keyboard(customer_id),
            )
        except Exception:
            logger.exception(
                "تعذر إرسال تحديث الطلب إلى الزبون"
            )

        await admin_order_details(query, order_id)

    # فتح لعبة للزبون
    elif data.startswith("game:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            return

        await open_game(query, game_id)

    # فتح عرض للزبون
    elif data.startswith("offer:"):
        parts = data.split(":")

        if len(parts) != 3:
            return

        try:
            game_id = int(parts[1])
            offer_id = int(parts[2])
        except ValueError:
            return

        await open_offer(query, game_id, offer_id)

    # اختيار طريقة الدفع
    elif data.startswith("pay:"):
        parts = data.split(":")

        if len(parts) != 4:
            return

        try:
            game_id = int(parts[1])
            offer_id = int(parts[2])
        except ValueError:
            return

        method = parts[3]

        await select_payment(
            query, context, game_id, offer_id, method
        )

    # تعديل نص من قاعدة البيانات
    elif data.startswith("text_edit:"):
        key = data.split(":", 1)[1]

        editable_texts = {
            "welcome_message": "رسالة الترحيب",
            "store_description": "وصف المتجر",
            "no_offers_message": "رسالة عدم وجود عروض",
            "contact_message": "رسالة التواصل مع الإدارة",
        }

        if key not in editable_texts:
            await query.message.reply_text(
                "❌ النص المطلوب غير موجود."
            )
            return

        context.user_data["admin_step"] = "edit_setting_value"
        context.user_data["pending_setting_key"] = key

        current_text = get_setting(key, "")

        await query.message.reply_text(
            f"📝 تعديل: {editable_texts[key]}\n\n"
            f"النص الحالي:\n{current_text or 'غير محدد'}\n\n"
            "ابعث النص الجديد.\n"
            "ابعث /cancel للإلغاء."
        )

    # تأكيد إرسال إشعار
    elif data == "notify_confirm":
        target_id = context.user_data.get(
            "pending_notify_user_id"
        )
        notify_text = context.user_data.get(
            "pending_notify_text"
        )

        if not target_id or not notify_text:
            await query.message.reply_text(
                "❌ انتهت صلاحية عملية الإرسال. أعد المحاولة."
            )
            return

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=notify_text,
            )

            await query.edit_message_text(
                "✅ تم إرسال الإشعار إلى الزبون بنجاح."
            )

        except Exception:
            logger.exception(
                "فشل إرسال إشعار الزبون"
            )

            await query.edit_message_text(
                "❌ تعذر إرسال الإشعار. تأكد من Telegram ID "
                "وأن الزبون يستطيع استقبال رسائل البوت."
            )

        context.user_data.pop(
            "pending_notify_user_id", None
        )
        context.user_data.pop(
            "pending_notify_text", None
        )
        context.user_data.pop("admin_step", None)

    # إلغاء إرسال الإشعار
    elif data == "notify_cancel":
        context.user_data.pop(
            "pending_notify_user_id", None
        )
        context.user_data.pop(
            "pending_notify_text", None
        )
        context.user_data.pop("admin_step", None)

        await query.edit_message_text(
            "❌ تم إلغاء إرسال الإشعار."
        )

    # المتجر للزبائن
    elif data == "store":
        await query.edit_message_text(
            "🛍️ افتح المتجر من زر 🛍️ المتجر الموجود أسفل الشاشة."
        )

    # إلغاء أو رجوع عام
    elif data == "cancel":
        context.user_data.pop("admin_step", None)
        context.user_data.pop("pending_game_id", None)
        context.user_data.pop("pending_offer_id", None)
        context.user_data.pop(
            "pending_payment_method", None
        )

        await query.edit_message_text(
            "تم إلغاء العملية."
        )

# =========================
# معالجة رسائل الإدارة والزبائن
# =========================

async def text_handler(update, context):
    message = update.effective_message
    user_id = update.effective_user.id
    text = (message.text or "").strip()

    if text in ("🛠️ لوحة التحكم", "لوحة التحكم", "الإدارة"):
        await show_admin_panel(update, context)
        return

    # إلغاء العملية الحالية
    if text in CANCEL_WORDS:
        context.user_data.pop("admin_step", None)
        context.user_data.pop("pending_game_id", None)
        context.user_data.pop("pending_offer_id", None)
        context.user_data.pop("pending_payment_method", None)
        context.user_data.pop("awaiting_player_id", None)
        context.user_data.pop("editing_game_description", None)
        context.user_data.pop("editing_game_prompt", None)

        await message.reply_text(
            "❌ تم إلغاء العملية.",
            reply_markup=main_keyboard(user_id),
        )
        return

    # تعديل وصف اللعبة
    if is_admin(user_id):
        game_id = context.user_data.get("editing_game_description")

        if game_id is not None:
            try:
                with db() as conn:
                    conn.execute(
                        "UPDATE games SET description = ? WHERE id = ?",
                        (text, int(game_id)),
                    )

                context.user_data.pop("editing_game_description", None)

                await message.reply_text(
                    "✅ تم حفظ وصف اللعبة بنجاح."
                )
            except Exception:
                logger.exception("فشل حفظ وصف اللعبة")
                await message.reply_text(
                    "❌ حدث خطأ أثناء حفظ الوصف."
                )
            return

    #=========================
    # خطوات الإدارة
    # =========================

    if is_admin(user_id):
        step = context.user_data.get("admin_step")

        # إضافة لعبة
        if step == "add_game":
            parts = [part.strip() for part in text.split("|", 1)]

            if not parts[0]:
                await message.reply_text(
                    "❌ اكتب اسم اللعبة."
                )
                return

            game_name = parts[0]
            emoji = parts[1] if len(parts) > 1 and parts[1] else "🎮"

            with db() as conn:
                existing = conn.execute(
                    "SELECT id FROM games WHERE name = ?",
                    (game_name,),
                ).fetchone()

                if existing:
                    await message.reply_text(
                        "⚠️ هذه اللعبة موجودة من قبل."
                    )
                    return

                conn.execute(
                    """
                    INSERT INTO games (name, emoji, active)
                    VALUES (?, ?, 1)
                    """,
                    (game_name, emoji),
                )

            context.user_data.pop("admin_step", None)

            await message.reply_text(
                f"✅ تمت إضافة اللعبة: {emoji} {game_name}",
                reply_markup=ReplyKeyboardMarkup(
                    ADMIN_PANEL_MENU,
                    resize_keyboard=True,
                ),
            )
            return
        
        # إضافة عرض
        if step == "add_offer_data":
            parts = [part.strip() for part in text.split("|")]

            if len(parts) != 3:
                await message.reply_text(
                    "❌ الصيغة غير صحيحة.\n\n"
                    "استعمل:\n"
                    "اسم العرض | سعر BaridiMob/CCP | سعر Flexy\n\n"
                    "مثال:\n100 Coins | 250 | 300"
                )
                return

            offer_name = parts[0]

            try:
                price_baridi = int(parts[1])
                price_flexy = int(parts[2])

                if (
                    not offer_name
                    or price_baridi < 0
                    or price_flexy < 0
                ):
                    raise ValueError
            except ValueError:
                await message.reply_text(
                    "❌ تأكد من اسم العرض والأسعار. "
                    "الأسعار لازم تكون أرقامًا موجبة أو صفرًا."
                )
                return

            game_id = context.user_data.get("pending_game_id")

            with db() as conn:
                game = conn.execute(
                    "SELECT id FROM games WHERE id = ?",
                    (game_id,),
                ).fetchone()

                if not game:
                    await message.reply_text(
                        "❌ اللعبة غير موجودة. أعد المحاولة."
                    )
                    context.user_data.pop("admin_step", None)
                    context.user_data.pop("pending_game_id", None)
                    return

                conn.execute(
                    """
                    INSERT INTO offers
                    (game_id, name, price_baridi, price_flexy, active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (
                        game_id,
                        offer_name,
                        price_baridi,
                        price_flexy,
                    ),
                )

            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_game_id", None)

            await message.reply_text(
                f"✅ تمت إضافة العرض: {offer_name}\n\n"
                f"🏦 BaridiMob/CCP: {price_baridi} دج\n"
                f"📱 Flexy: {price_flexy} دج",
                reply_markup=ReplyKeyboardMarkup(
                    ADMIN_PANEL_MENU,
                    resize_keyboard=True,
                ),
            )
            return

        # تعديل أسعار عرض
        if step == "edit_price_data":
            parts = [part.strip() for part in text.split("|")]

            if len(parts) != 2:
                await message.reply_text(
                    "❌ الصيغة غير صحيحة.\n\n"
                    "ابعث:\n"
                    "سعر BaridiMob/CCP | سعر Flexy\n\n"
                    "مثال:\n750 | 900"
                )
                return

            try:
                price_baridi = int(parts[0])
                price_flexy = int(parts[1])

                if price_baridi < 0 or price_flexy < 0:
                    raise ValueError
            except ValueError:
                await message.reply_text(
                    "❌ الأسعار لازم تكون أرقامًا موجبة أو صفرًا."
                )
                return

            offer_id = context.user_data.get("pending_offer_id")

            with db() as conn:
                result = conn.execute(
                    """
                    UPDATE offers
                    SET price_baridi = ?, price_flexy = ?
                    WHERE id = ?
                    """,
                    (price_baridi, price_flexy, offer_id),
                )

                if result.rowcount == 0:
                    await message.reply_text(
                        "❌ العرض غير موجود."
                    )
                    return

            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_offer_id", None)

            await message.reply_text(
                "✅ تم تعديل الأسعار بنجاح.\n\n"
                f"🏦 BaridiMob/CCP: {price_baridi} دج\n"
                f"📱 Flexy: {price_flexy} دج",
                reply_markup=ReplyKeyboardMarkup(
                    ADMIN_PANEL_MENU,
                    resize_keyboard=True,
                ),
            )
            return

        # تعديل معلومات الدفع
        if step == "set_payment":
            method = context.user_data.get(
                "pending_payment_method"
            )

            if method not in ("baridi", "flexy"):
                context.user_data.pop("admin_step", None)
                await message.reply_text(
                    "❌ تعذر تحديد طريقة الدفع."
                )
                return

            setting_key = (
                "baridi_details"
                if method == "baridi"
                else "flexy_details"
            )

            set_setting(setting_key, text)

            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_payment_method", None)

            await message.reply_text(
                "✅ تم حفظ معلومات الدفع بنجاح.",
                reply_markup=ReplyKeyboardMarkup(
                    ADMIN_PANEL_MENU,
                    resize_keyboard=True,
                ),
            )
            return
            
# تعديل النصوص وإرسال الإشعارات
    if is_admin(user_id):
        step = context.user_data.get("admin_step")

        # حفظ النص الجديد
        if step == "edit_setting_value":
            key = context.user_data.get("pending_setting_key")

            allowed_keys = {
                "welcome_message",
                "store_description",
                "no_offers_message",
                "contact_message",
            }

            if key not in allowed_keys:
                context.user_data.pop("admin_step", None)
                context.user_data.pop("pending_setting_key", None)
                await message.reply_text("❌ النص المطلوب غير محدد.")
                return

            set_setting(key, text)

            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_setting_key", None)

            await message.reply_text(
                "✅ تم حفظ النص الجديد بنجاح.",
                reply_markup=ReplyKeyboardMarkup(
                    ADMIN_PANEL_MENU,
                    resize_keyboard=True,
                ),
            )
            return

        # استقبال Telegram ID للزبون
        if step == "notify_user_id":
            try:
                target_id = int(text)
                if target_id <= 0:
                    raise ValueError
            except ValueError:
                await message.reply_text(
                    "❌ Telegram ID غير صحيح. ابعث رقمًا صحيحًا."
                )
                return

            with db() as conn:
                customer = conn.execute(
                    "SELECT user_id FROM users WHERE user_id = ?",
                    (target_id,),
                ).fetchone()

            if not customer:
                await message.reply_text(
                    "❌ هذا الزبون غير موجود في قاعدة بيانات البوت."
                )
                return

            context.user_data["pending_notify_user_id"] = target_id
            context.user_data["admin_step"] = "notify_message"

            await message.reply_text(
                "✉️ ابعث نص الإشعار الذي تريد إرساله للزبون.\n"
                "ابعث /cancel للإلغاء."
            )
            return

        # استقبال نص الإشعار وعرض المعاينة
        if step == "notify_message":
            target_id = context.user_data.get("pending_notify_user_id")

            if not target_id:
                context.user_data.pop("admin_step", None)
                await message.reply_text(
                    "❌ أعد بدء عملية الإشعار."
                )
                return

            context.user_data["pending_notify_text"] = text
            context.user_data["admin_step"] = "notify_confirm"

            await message.reply_text(
                f"👤 الزبون: {target_id}\n\n"
                "📨 معاينة الإشعار:\n\n"
                f"{text}\n\n"
                "هل تريد إرسال هذه الرسالة؟",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ تأكيد الإرسال",
                            callback_data="notify_confirm",
                        ),
                        InlineKeyboardButton(
                            "❌ إلغاء",
                            callback_data="notify_cancel",
                        ),
                    ]
                ]),
            )
            return

    # =========================
    # إكمال طلب الزبون
    # =========================

    if context.user_data.get("awaiting_player_id"):
        await create_order(update, context)
        return

    # =========================
    # أزرار القائمة الرئيسية
    # =========================

    if text == "🛍️ المتجر":
        await show_store(update.effective_message, update.effective_user.id)
        return

    if text == "📦 طلباتي":
        await show_my_orders(update, context)
        return

    if text == "👤 حسابي":
        await show_account(update.effective_message, update.effective_user.id)
        return

    if text == "📞 اتصل بالإدارة":
        await message.reply_text(
            "📞 تقدر تتواصل مع الإدارة عبر واتساب:",
            reply_markup=wa_keyboard(),
        )
        return

    # =========================
    # أزرار لوحة الإدارة
    # =========================

    if is_admin(user_id):
        if text == "🛠️ لوحة التحكم":
            await show_admin_panel(update, context)
            return

        if text == "🎮 إدارة الألعاب":
            await message.reply_text(
                "🎮 إدارة الألعاب:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "فتح إدارة الألعاب",
                            callback_data="adm_games",
                        )
                    ]
                ]),
            )
            return

        if text == "➕ إضافة لعبة":
            context.user_data["admin_step"] = "add_game"

            await message.reply_text(
                "➕ ابعث اسم اللعبة والإيموجي بهذا الشكل:\n\n"
                "Free Fire | 🔥\n\n"
                "ابعث /cancel للإلغاء."
            )
            return

        if text == "📦 إدارة العروض":
            await message.reply_text(
                "📦 إدارة العروض:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "اختيار لعبة",
                            callback_data="adm_offers",
                        )
                    ]
                ]),
            )
            return

        if text == "➕ إضافة عرض":
            await message.reply_text(
                "➕ اختار اللعبة:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "اختيار اللعبة",
                            callback_data="adm_add_offer",
                        )
                    ]
                ]),
            )
            return

        if text == "💰 تعديل سعر عرض":
            await message.reply_text(
                "💰 اختار اللعبة التي تريد تعديل عروضها:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "اختيار اللعبة",
                            callback_data="adm_offers",
                        )
                    ]
                ]),
            )
            return

        if text == "📋 كل الطلبات":
            await message.reply_text(
                "📋 إدارة الطلبات:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "عرض جميع الطلبات",
                            callback_data="adm_orders",
                        )
                    ]
                ]),
            )
            return

        if text == "📊 الإحصائيات":
            await message.reply_text(
                "📊 إحصائيات المتجر:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "عرض الإحصائيات",
                            callback_data="adm_stats",
                        )
                    ]
                ]),
            )
            return

        if text == "💳 إعدادات الدفع":
            await message.reply_text(
                "💳 إعدادات الدفع:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "فتح إعدادات الدفع",
                            callback_data="adm_payment",
                        )
                    ]
                ]),
            )
            return
        if text == "📝 إدارة النصوص":
            await message.reply_text(
                "📝 اختر النص الذي تريد تعديله:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "رسالة الترحيب",
                            callback_data="text_edit:welcome_message",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "وصف المتجر",
                            callback_data="text_edit:store_description",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "رسالة عدم وجود عروض",
                            callback_data="text_edit:no_offers_message",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "رسالة التواصل مع الإدارة",
                            callback_data="text_edit:contact_message",
                        )
                    ],
                ]),
            )
            return

        if text == "📨 إرسال إشعار":
            context.user_data["admin_step"] = "notify_user_id"
            await message.reply_text(
                "📨 ابعث Telegram ID تاع الزبون.\n\n"
                "ابعث /cancel للإلغاء."
            )
            return

        if text == "🔙 القائمة الرئيسية":
            await message.reply_text(
                "🏠 القائمة الرئيسية.",
                reply_markup=main_keyboard(user_id),
            )
            return


    await message.reply_text(
        "ما فهمتش طلبك. استعمل الأزرار الموجودة أسفل الشاشة.",
        reply_markup=main_keyboard(user_id),
    )


# =========================
# تشغيل البوت
# =========================

def main():
    if not TOKEN:
        raise RuntimeError(
            "❌ BOT_TOKEN غير موجود في إعدادات السيرفر."
        )

    if ADMIN_ID == 0:
        raise RuntimeError(
            "❌ ADMIN_ID غير موجود في إعدادات السيرفر."
        )

    # إنشاء قاعدة البيانات وتجهيزها
    init_db()

    # إنشاء التطبيق
    app = Application.builder().token(TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("admin", admin_command))

    # أزرار Inline
    app.add_handler(CallbackQueryHandler(callback_handler))

    # استقبال صور وصل الدفع
    app.add_handler(
        MessageHandler(filters.PHOTO, photo_handler)
    )
    
    # الرسائل النصية
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    logger.info("SERADJ STORE bot is starting...")

    # تشغيل البوت
    app.run_polling()


if __name__ == "__main__":
    main()

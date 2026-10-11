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
    ["👤 حسابي", "💰 تعبئة الرصيد"],
    ["📞 اتصل بالإدارة", "🏪 طلب حساب تاجر"],
]

ADMIN_MAIN_MENU = [
    ["🛠️ لوحة التحكم"],
    ["🛍️ المتجر", "📦 طلباتي"],
    ["👤 حسابي", "💰 تعبئة الرصيد"],
    ["📞 اتصل بالإدارة"],
]

ADMIN_PANEL_MENU = [
["🎮 إدارة الألعاب", "➕ إضافة لعبة"],
["📦 إدارة العروض", "➕ إضافة عرض"],
["💰 تعديل سعر عرض", "📋 كل الطلبات"],
["📊 الإحصائيات", "💳 إعدادات الدفع"],
["📝 إدارة النصوص", "📨 إرسال إشعار"],
["💬 مراسلة زبون"],
["👥 إدارة التجار", "💳 قروض التجار"],
["🔄 تحويل نوع الحساب"],
["👤 طلبات حسب الزبون"],
["🧹 تصفير الحسابات والطلبات"],
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
    if is_admin(user_id):
        keyboard = ADMIN_MAIN_MENU
    else:
        keyboard = [row[:] for row in MAIN_MENU]
        if is_trader(user_id):
            keyboard.insert(2, ["💳 تسديد القرض"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
    """Create tables and migrate existing data without deleting it."""
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            created_at TEXT,
            account_type TEXT DEFAULT 'customer',
            trader_requested INTEGER DEFAULT 0,
            balance INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            credit_limit INTEGER DEFAULT 0,
            credit_debt INTEGER DEFAULT 0,
            credit_term_days INTEGER DEFAULT 0,
            credit_due_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🎮',
            active INTEGER DEFAULT 1,
            description TEXT DEFAULT '',
            player_prompt TEXT DEFAULT '',
            recharge_method TEXT DEFAULT 'id',
            platform_mode TEXT DEFAULT 'none'
        );
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price_baridi INTEGER DEFAULT 0,
            price_flexy INTEGER DEFAULT 0,
            price_baridi_trader INTEGER DEFAULT 0,
            price_flexy_trader INTEGER DEFAULT 0,
            reward_points INTEGER DEFAULT 0,
            android_active INTEGER DEFAULT 1,
            ios_active INTEGER DEFAULT 1,
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
            created_at TEXT,
            points_awarded INTEGER DEFAULT 0,
            points_used INTEGER DEFAULT 0,
            platform TEXT DEFAULT '',
            credit_charged INTEGER DEFAULT 0,
            credit_refunded INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS wallet_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            payment_method TEXT DEFAULT '',
            receipt_file_id TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS credit_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            payment_method TEXT DEFAULT '',
            receipt_file_id TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS customer_chats (
            user_id INTEGER PRIMARY KEY,
            is_open INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS monthly_stats_archive (
            month TEXT PRIMARY KEY,
            users_count INTEGER DEFAULT 0,
            total_orders INTEGER DEFAULT 0,
            pending_orders INTEGER DEFAULT 0,
            processing_orders INTEGER DEFAULT 0,
            completed_orders INTEGER DEFAULT 0,
            rejected_orders INTEGER DEFAULT 0,
            completed_revenue INTEGER DEFAULT 0,
            archived_at TEXT DEFAULT ''
        );
        """)

        # Safe migrations for older databases.
        migrations = {
            "users": {
                "account_type": "TEXT DEFAULT 'customer'",
                "trader_requested": "INTEGER DEFAULT 0",
                "balance": "INTEGER DEFAULT 0",
                "points": "INTEGER DEFAULT 0",
                "credit_limit": "INTEGER DEFAULT 0",
                "credit_debt": "INTEGER DEFAULT 0",
                "credit_term_days": "INTEGER DEFAULT 0",
                "credit_due_at": "TEXT DEFAULT ''",
            },
            "games": {
                "description": "TEXT DEFAULT ''",
                "player_prompt": "TEXT DEFAULT ''",
                "recharge_method": "TEXT DEFAULT 'id'",
                "platform_mode": "TEXT DEFAULT 'none'",
            },
            "offers": {
                "price_baridi_trader": "INTEGER DEFAULT 0",
                "price_flexy_trader": "INTEGER DEFAULT 0",
                "reward_points": "INTEGER DEFAULT 0",
                "android_active": "INTEGER DEFAULT 1",
                "ios_active": "INTEGER DEFAULT 1",
            },
            "orders": {
                "game_id": "INTEGER", "offer_id": "INTEGER",
                "player_id": "TEXT DEFAULT ''", "payment_method": "TEXT DEFAULT ''",
                "price": "INTEGER DEFAULT 0", "status": "TEXT DEFAULT 'pending'",
                "created_at": "TEXT", "points_awarded": "INTEGER DEFAULT 0",
                "points_used": "INTEGER DEFAULT 0", "platform": "TEXT DEFAULT ''",
                "wallet_charged": "INTEGER DEFAULT 0", "wallet_refunded": "INTEGER DEFAULT 0",
                "credit_charged": "INTEGER DEFAULT 0", "credit_refunded": "INTEGER DEFAULT 0",
            },
        }
        for table, needed in migrations.items():
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for col, typ in needed.items():
                if col not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
                    # Preserve old retail prices as the initial trader prices.
                    if table == "offers" and col == "price_baridi_trader":
                        conn.execute("UPDATE offers SET price_baridi_trader = price_baridi")
                    elif table == "offers" and col == "price_flexy_trader":
                        conn.execute("UPDATE offers SET price_flexy_trader = price_flexy")

        # Defaults for an empty database only; never overwrite existing offers.
        default_games = [
            ("Free Fire", "🔥"), ("PUBG Mobile", "🎯"), ("eFootball", "⚽"),
            ("FC Mobile", "⚽"), ("Call of Duty Mobile", "🎮"),
            ("Brawl Stars", "⭐"), ("Roblox", "🧱"), ("One State", "🚘"),
            ("TikTok", "🎵"), ("Blood Strike", "💥"), ("Snapchat+", "👻"),
            ("Netflix", "🎬"), ("Azar", "📹"), ("App Store", "🍎"),
        ]
        for name, emoji in default_games:
            conn.execute("INSERT INTO games (name, emoji) SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM games WHERE name = ?)", (name, emoji, name))
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('baridi_details', 'تواصل مع الإدارة لمعرفة معلومات الدفع.')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('flexy_details', 'تواصل مع الإدارة لمعرفة معلومات Flexy.')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('points_value', '1')")

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


def is_trader(user_id):
    if is_admin(user_id):
        return True
    with db() as conn:
        row = conn.execute("SELECT account_type FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return bool(row and row["account_type"] == "trader")


def get_trader_credit(user_id):
    with db() as conn:
        row = conn.execute("SELECT credit_limit, credit_debt, credit_term_days, credit_due_at FROM users WHERE user_id = ? AND account_type = 'trader'", (user_id,)).fetchone()
    if not row:
        return (0, 0, 0, "")
    return (int(row["credit_limit"] or 0), int(row["credit_debt"] or 0), int(row["credit_term_days"] or 0), row["credit_due_at"] or "")


def parse_datetime(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def offer_price(offer, method, user_id):
    trader = is_trader(user_id)
    if method == "baridi":
        return int(offer["price_baridi_trader"] if trader else offer["price_baridi"])
    return int(offer["price_flexy_trader"] if trader else offer["price_flexy"])


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
        f"🏷️ نوع الحساب: {'تاجر معتمد' if user['account_type'] == 'trader' else 'زبون عادي'}\n"
        f"💰 رصيد المحفظة: {int(user['balance'] or 0)} دج\n"
        f"📉 الدين الحالي: {int(user['credit_debt'] or 0)} دج\n"
        f"📅 آخر أجل للتسديد: {user['credit_due_at'] or 'لا يوجد'}\n"
        f"🎁 نقاط المكافآت: {int(user['points'] or 0)} نقطة\n"
        f"📅 التسجيل: {user['created_at']}",
        reply_markup=main_keyboard(user_id),
        )

# ====== عرض عروض اللعبة ======

async def open_game(query, game_id, platform=None):
    user_id = query.from_user.id
    game = get_game(game_id)

    if not game or not game["active"]:
        await query.edit_message_text(
            "❌ هذه الخدمة غير متاحة حالياً."
        )
        return

    mode = game["platform_mode"] if "platform_mode" in game.keys() else "none"
    if mode == "both" and platform is None:
        await query.edit_message_text(
            f"📱 اختر نوع الهاتف لخدمة {game['name']}: ",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Android", callback_data=f"platform:{game_id}:android")],
                [InlineKeyboardButton("🍎 iPhone (iOS)", callback_data=f"platform:{game_id}:ios")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="store")],
            ]),
        )
        return
    if mode in ("android", "ios"):
        platform = mode
    if mode == "none":
        platform = None

    offers = get_offers(game_id)
    if platform == "android":
        offers = [o for o in offers if int(o["android_active"] or 0)]
    elif platform == "ios":
        offers = [o for o in offers if int(o["ios_active"] or 0)]
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
                f"{offer_price(offer, 'baridi', user_id)} دج",
                callback_data=(
                    f"offer:{game_id}:{offer['id']}:{platform or 'none'}"
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
        f"📱 الجهاز: {'Android' if platform == 'android' else 'iPhone (iOS)' if platform == 'ios' else 'غير مطلوب'}\n"
        "اختر العرض المناسب:\n"
        f"💳 الأسعار المعروضة هي أسعار BaridiMob / CCP ({'تاجر' if is_trader(user_id) else 'زبون عادي'}).",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ====== تفاصيل العرض ======

async def open_offer(query, game_id, offer_id, platform=None, context=None):
    user_id = query.from_user.id
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
    if platform == "android" and not int(offer["android_active"] or 0):
        await query.edit_message_text("❌ هذا العرض غير متوفر على Android.")
        return
    if platform == "ios" and not int(offer["ios_active"] or 0):
        await query.edit_message_text("❌ هذا العرض غير متوفر على iPhone.")
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"💳 BaridiMob / CCP — "
                f"{offer_price(offer, 'baridi', user_id)} دج",
                callback_data=(
                    f"pay:{game_id}:{offer_id}:baridi"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                f"📱 Flexy — {offer_price(offer, 'flexy', user_id)} دج",
                callback_data=(
                    f"pay:{game_id}:{offer_id}:flexy"
                ),
            )
        ],
        [InlineKeyboardButton(
            f"🎁 استخدام النقاط: {'مفعّل' if context and context.user_data.get('use_points_for_order') else 'غير مفعّل'}",
            callback_data=f"points_toggle:{game_id}:{offer_id}:{platform or 'none'}",
        )],
        [InlineKeyboardButton("💰 الدفع من رصيد المحفظة", callback_data=f"pay:{game_id}:{offer_id}:balance")],
        *([[InlineKeyboardButton("🧾 الشراء بالقرض", callback_data=f"pay:{game_id}:{offer_id}:credit")]] if is_trader(user_id) and get_trader_credit(user_id)[0] > 0 else []),
        [
            InlineKeyboardButton(
                "🔙 رجوع",
                callback_data=(f"platform:{game_id}:{platform}" if platform in ("android", "ios") else f"game:{game_id}"),
            )
        ],
    ]

    await query.edit_message_text(
        "🛍️ تفاصيل العرض\n\n"
        f"🎮 اللعبة: {game['name']}\n"
        f"📦 العرض: {offer['name']}\n"
        f"📱 الجهاز: {'Android' if platform == 'android' else 'iPhone (iOS)' if platform == 'ios' else 'غير مطلوب'}\n\n"
        f"💳 BaridiMob / CCP: "
        f"{offer_price(offer, 'baridi', user_id)} دج\n"
        f"📱 Flexy: {offer_price(offer, 'flexy', user_id)} دج\n"
        f"🏷️ فئة السعر: {'تاجر' if is_trader(user_id) else 'زبون عادي'}\n\n"
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
        price = offer_price(offer, "baridi", query.from_user.id)
        method_name = "BaridiMob / CCP"
        details = get_setting(
            "baridi_details",
            "تواصل مع الإدارة لمعرفة معلومات الدفع.",
        )
    elif method == "flexy":
        price = offer_price(offer, "flexy", query.from_user.id)
        method_name = "Flexy"
        details = get_setting(
            "flexy_details",
            "تواصل مع الإدارة لمعرفة معلومات الدفع.",
        )
    elif method == "credit":
        limit_amount, debt, term_days, due_at = get_trader_credit(query.from_user.id)
        if not is_trader(query.from_user.id) or limit_amount <= 0:
            await query.edit_message_text("❌ القرض غير مفعّل لحسابك. تواصل مع الإدارة.")
            return
        price = offer_price(offer, "baridi", query.from_user.id)
        if debt + price > limit_amount:
            await query.edit_message_text(f"❌ سقف القرض لا يكفي لهذا الطلب.\nسقف القرض: {limit_amount} دج\nالدين الحالي: {debt} دج\nالسعر: {price} دج\nالمتاح: {max(0, limit_amount-debt)} دج")
            return
        method_name = "قرض التاجر"
        details = f"الدين الحالي: {debt} دج\nالمتاح من سقف القرض: {limit_amount-debt} دج\nأجل التسديد: {term_days} يومًا"
    elif method == "balance":
        with db() as conn:
            row = conn.execute("SELECT balance FROM users WHERE user_id = ?", (query.from_user.id,)).fetchone()
        balance = int(row["balance"] or 0) if row else 0
        price = offer_price(offer, "baridi", query.from_user.id)
        points_row = None
        if context.user_data.get("use_points_for_order"):
            with db() as conn:
                points_row = conn.execute("SELECT points FROM users WHERE user_id = ?", (query.from_user.id,)).fetchone()
        available_points = int(points_row["points"] or 0) if points_row else 0
        if balance + (available_points if context.user_data.get("use_points_for_order") else 0) < price:
            await query.edit_message_text(
                f"❌ رصيدك غير كافٍ.\nالسعر: {price} دج\nرصيد المحفظة: {balance} دج\nالنقاط: {available_points}\n\nاضغط تعبئة الرصيد من القائمة الرئيسية ثم أعد الطلب."
            )
            return
        method_name = "رصيد المحفظة"
        details = "سيُخصم المبلغ من محفظتك عند تأكيد الطلب."
    else:
        await query.edit_message_text(
            "❌ طريقة الدفع غير صحيحة."
        )
        return

    base_price = price
    points_used = 0
    if context.user_data.get("use_points_for_order"):
        with db() as conn:
            points_row = conn.execute("SELECT points FROM users WHERE user_id = ?", (query.from_user.id,)).fetchone()
        available_points = int(points_row["points"] or 0) if points_row else 0
        points_used = min(available_points, base_price)
        price = max(0, base_price - points_used)
        if points_used:
            details += f"\n🎁 خصم النقاط: {points_used} دج"

    context.user_data["order_draft"] = {
        "game_id": game_id,
        "offer_id": offer_id,
        "game_name": game["name"],
        "offer_name": offer["name"],
        "method": method_name,
        "price": price,
        "base_price": base_price,
        "points_used": points_used,
        "payment_type": method,
        "platform": context.user_data.get("selected_platform", ""),
    }

    custom_prompt = (game["player_prompt"] or "").strip()
    recharge_method = game["recharge_method"] if "recharge_method" in game.keys() else "id"
    if recharge_method == "login":
        context.user_data["awaiting_login_email"] = True
        prompt = "🔐 أرسل إيميل الحساب المراد شحنه.\nبعدها سيطلب منك كلمة السر.\n\n⚠️ أدخل بيانات الحساب المطلوب شحنه فقط، ولا ترسل بيانات حسابات أخرى."
    elif recharge_method == "none":
        # Some products (e.g. Netflix subscriptions) require no player ID or login.
        context.user_data["pending_player_id"] = ""
        context.user_data.pop("awaiting_player_id", None)
        if method == "balance":
            await create_wallet_order(query.message, context, "", user=query.from_user)
            return
        if method == "credit":
            await create_credit_order(query.message, context, "", user=query.from_user)
            return
        context.user_data["awaiting_payment_receipt"] = True
        prompt = "🧾 هذا العرض لا يحتاج ID أو بيانات دخول. أرسل صورة وصل الدفع مباشرة لإتمام الطلب."
    else:
        context.user_data["awaiting_player_id"] = True
        prompt = custom_prompt or "🆔 أرسل الآن معرف اللاعب (Player ID).\nإذا ما تحتاجش الخدمة معرف، أرسل: بدون"

    await query.edit_message_text(
        "✅ اخترت العرض بنجاح!\n\n"
        f"🎮 اللعبة: {game['name']}\n"
        f"📦 العرض: {offer['name']}\n"
        f"💳 الدفع: {method_name}\n"
        f"💰 السعر: {price} دج\n\n"
        f"💳 معلومات الدفع:\n{details}\n\n"
        f"{prompt}\n\nللإلغاء أرسل /cancel"
    )


# ====== إنشاء طلب مدفوع من المحفظة ======
async def create_wallet_order(message, context, player_id, user=None):
    user = user or message.from_user
    draft = context.user_data.get("order_draft")
    if not draft:
        await message.reply_text("❌ انتهت جلسة الطلب. ابدأ من جديد.")
        return
    price = int(draft["price"])
    points_used = int(draft.get("points_used", 0))
    with db() as conn:
        row = conn.execute("SELECT balance, points FROM users WHERE user_id = ?", (user.id,)).fetchone()
        if not row or int(row["balance"] or 0) < price or int(row["points"] or 0) < points_used:
            await message.reply_text("❌ رصيد المحفظة أو النقاط تغيّر ولم يعد كافيًا. راجع حسابك وأعد الطلب.")
            return
        conn.execute("UPDATE users SET balance = balance - ?, points = points - ? WHERE user_id = ?", (price, points_used, user.id))
        cursor = conn.execute(
            "INSERT INTO orders (user_id, game_id, offer_id, player_id, payment_method, price, status, created_at, points_used, platform, wallet_charged) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, 1)",
            (user.id, draft["game_id"], draft["offer_id"], player_id, "رصيد المحفظة", price, now_text(), points_used, draft.get("platform", "")),
        )
        order_id = cursor.lastrowid
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 قيد التنفيذ", callback_data=f"status:{order_id}:processing"), InlineKeyboardButton("✅ مكتمل", callback_data=f"status:{order_id}:completed")],
        [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"status:{order_id}:rejected")],
    ])
    if ADMIN_ID:
        try:
            await context.bot.send_message(ADMIN_ID,
                f"🆕 طلب جديد #{order_id} (محفظة)\n\nالزبون: {user.full_name}\nTelegram ID: {user.id}\nالخدمة: {draft['game_name']}\nالعرض: {draft['offer_name']}\nمعلومات الشحن: {player_id}\nالجهاز: {draft.get('platform') or 'غير محدد'}\nالسعر بعد الخصم: {price} دج\nالنقاط المستخدمة: {points_used}\nالدفع: رصيد المحفظة\nالحالة: قيد الانتظار",
                reply_markup=keyboard)
        except Exception:
            logger.exception("تعذر إرسال طلب المحفظة للإدارة")
    context.user_data.pop("order_draft", None)
    context.user_data.pop("pending_player_id", None)
    context.user_data.pop("awaiting_player_id", None)
    await message.reply_text(f"✅ تم تسجيل طلبك #{order_id}.\n💰 المبلغ المخصوم: {price} دج\n🎁 النقاط المستخدمة: {points_used}\nسيتم إعلامك عند تحديث الحالة.", reply_markup=main_keyboard(user.id))


async def create_credit_order(message, context, player_id, user=None):
    user = user or message.from_user
    draft = context.user_data.get("order_draft")
    if not draft:
        await message.reply_text("❌ انتهت جلسة الطلب. ابدأ من جديد.")
        return
    price = int(draft["price"])
    points_used = int(draft.get("points_used", 0))
    with db() as conn:
        row = conn.execute("SELECT account_type, credit_limit, credit_debt, credit_term_days, credit_due_at, points FROM users WHERE user_id = ?", (user.id,)).fetchone()
        if not row or row["account_type"] != "trader" or int(row["credit_limit"] or 0) <= 0:
            await message.reply_text("❌ القرض غير مفعّل لحسابك.")
            return
        limit_amount = int(row["credit_limit"] or 0)
        debt = int(row["credit_debt"] or 0)
        if debt + price > limit_amount:
            await message.reply_text(f"❌ سقف القرض لا يكفي. المتاح: {max(0, limit_amount-debt)} دج، والسعر: {price} دج.")
            return
        if int(row["points"] or 0) < points_used:
            await message.reply_text("❌ نقاطك لم تعد كافية. أعد الطلب.")
            return
        due_at = row["credit_due_at"] or ""
        if debt == 0:
            from datetime import timedelta
            term = max(1, int(row["credit_term_days"] or 0))
            due_at = (datetime.now() + timedelta(days=term)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE users SET credit_debt = credit_debt + ?, credit_due_at = ?, points = points - ? WHERE user_id = ?", (price, due_at, points_used, user.id))
        cur = conn.execute("INSERT INTO orders (user_id, game_id, offer_id, player_id, payment_method, price, status, created_at, points_used, platform, credit_charged) VALUES (?, ?, ?, ?, 'قرض التاجر', ?, 'pending', ?, ?, ?, 1)", (user.id, draft["game_id"], draft["offer_id"], player_id, price, now_text(), points_used, draft.get("platform", "")))
        order_id = cur.lastrowid
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 قيد التنفيذ", callback_data=f"status:{order_id}:processing"), InlineKeyboardButton("✅ مكتمل", callback_data=f"status:{order_id}:completed")], [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"status:{order_id}:rejected")]])
    if ADMIN_ID:
        try:
            await context.bot.send_message(ADMIN_ID, f"🆕 طلب بالقرض #{order_id}\nالزبون: {user.full_name}\nTelegram ID: {user.id}\nالخدمة: {draft['game_name']}\nالعرض: {draft['offer_name']}\nمعلومات الشحن: {player_id or 'لا يتطلب'}\nالسعر: {price} دج\nالدين بعد الطلب: {debt+price} دج\nأجل التسديد: {due_at or 'غير محدد'}", reply_markup=keyboard)
        except Exception:
            logger.exception("تعذر إرسال طلب القرض للإدارة")
    context.user_data.pop("order_draft", None)
    context.user_data.pop("pending_player_id", None)
    context.user_data.pop("awaiting_player_id", None)
    context.user_data.pop("awaiting_payment_receipt", None)
    await message.reply_text(f"✅ تم تسجيل طلبك #{order_id} بالقرض.\n💰 المبلغ المضاف للدين: {price} دج\n📊 الدين الحالي: {debt+price} دج\n📅 آخر أجل للتسديد: {due_at}", reply_markup=main_keyboard(user.id))


# ====== إنشاء الطلب ======

async def create_order(update, context):
    user = update.effective_user
    player_id = update.message.text.strip()
    draft = context.user_data.get("order_draft")

    if not draft:
        context.user_data.pop("awaiting_player_id", None)
        context.user_data.pop("awaiting_credit_repay_amount", None)
        context.user_data.pop("awaiting_credit_receipt", None)
        context.user_data.pop("credit_repay_amount", None)
        context.user_data.pop("credit_repay_method", None)
        context.user_data.pop("awaiting_login_email", None)
        context.user_data.pop("awaiting_login_password", None)
        context.user_data.pop("pending_login_email", None)
        return

    if not player_id:
        await update.message.reply_text(
            "❌ أرسل معرف اللاعب أو اكتب: بدون"
        )
        return

    if draft.get("payment_type") == "balance":
        await create_wallet_order(update.effective_message, context, player_id)
        return
    if draft.get("payment_type") == "credit":
        await create_credit_order(update.effective_message, context, player_id)
        return

    # حفظ معلومات الشحن مؤقتًا حتى يرسل الزبون الوصل
    context.user_data["pending_player_id"] = player_id
    context.user_data["awaiting_payment_receipt"] = True
    context.user_data.pop("awaiting_player_id", None)

    await update.message.reply_text(
        "✅ تم استلام معلومات الشحن!\n\n"
        f"🎮 اللعبة: {draft['game_name']}\n"
        f"📦 العرض: {draft['offer_name']}\n"
        f"{('🆔 معرف اللاعب: ' + player_id + chr(10)) if not draft.get('login_mode') else '🔐 تم استلام بيانات الحساب.' + chr(10)}"
        f"💳 طريقة الدفع: {draft['method']}\n"
        f"💰 المبلغ: {draft['price']} دج\n\n"
        "📸 الآن أرسل صورة وصل الدفع لإتمام الطلب.\n\n"
        "⚠️ تأكد أن الصورة واضحة وتظهر معلومات العملية.\n"
        "لإلغاء العملية أرسل /cancel"
    )
async def forward_customer_attachment_to_admin(update, context, kind):
    """Forward a customer's image/PDF to admin only while the admin-opened chat is active."""
    user = update.effective_user
    message = update.effective_message
    if not user or is_admin(user.id) or not ADMIN_ID:
        return False

    with db() as conn:
        chat = conn.execute(
            "SELECT is_open FROM customer_chats WHERE user_id = ?", (user.id,)
        ).fetchone()
    if not chat or int(chat["is_open"] or 0) != 1:
        return False

    caption = (
        f"📎 مرفق من زبون عبر محادثة الدعم\n"
        f"👤 الاسم: {user.full_name}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"📄 النوع: {'صورة' if kind == 'photo' else 'ملف'}"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ رد على الزبون", callback_data=f"chat_reply:{user.id}")
    ]])
    try:
        if kind == "photo":
            media = message.photo[-1]
            await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=media.file_id, caption=caption,
                reply_markup=keyboard,
            )
        else:
            document = message.document
            filename = document.file_name or "ملف بدون اسم"
            caption += f"\n📁 اسم الملف: {filename}"
            await context.bot.send_document(
                chat_id=ADMIN_ID, document=document.file_id, caption=caption,
                reply_markup=keyboard,
            )
        await message.reply_text("✅ تم إرسال المرفق إلى الإدارة.")
    except Exception:
        logger.exception("تعذر تحويل مرفق الزبون إلى الإدارة")
        await message.reply_text("❌ تعذر إرسال المرفق. حاول مرة أخرى لاحقًا.")
    return True


async def document_handler(update, context):
    """Handle customer PDFs/files in an active admin-initiated support chat."""
    message = update.effective_message
    if not message or not message.document:
        return
    user = update.effective_user

    # وصل الطلب المالي يبقى ضمن مسار الطلب؛ ملفات المحادثة العادية تُحوّل للإدارة.
    if context.user_data.get("awaiting_payment_receipt"):
        await message.reply_text("📸 لإتمام الطلب، أرسل صورة واضحة لوصل الدفع. أما ملفات PDF فتقدر تبعثها داخل محادثة الدعم بعد ما تراسلك الإدارة.")
        return
    handled = await forward_customer_attachment_to_admin(update, context, "document")
    if not handled and user and not is_admin(user.id):
        await message.reply_text("لا يمكنك إرسال ملفات للإدارة إلا بعد أن تبدأ الإدارة محادثة معك.")


async def photo_handler(update, context):
    user = update.effective_user
    message = update.effective_message

    if context.user_data.get("awaiting_credit_receipt"):
        amount = int(context.user_data.get("credit_repay_amount", 0))
        method = context.user_data.get("credit_repay_method", "")
        with db() as conn:
            debt_row = conn.execute("SELECT credit_debt FROM users WHERE user_id=?", (user.id,)).fetchone()
        debt = int(debt_row["credit_debt"] or 0) if debt_row else 0
        if amount <= 0 or amount > debt or not method:
            context.user_data.pop("awaiting_credit_receipt", None)
            await message.reply_text("❌ مبلغ التسديد غير صحيح أو أكبر من الدين الحالي. ابدأ من جديد.")
            return
        photo = message.photo[-1]
        with db() as conn:
            cur = conn.execute("INSERT INTO credit_payments (user_id, amount, payment_method, receipt_file_id, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", (user.id, amount, method, photo.file_id, now_text()))
            payment_id = cur.lastrowid
        if ADMIN_ID:
            await context.bot.send_photo(ADMIN_ID, photo.file_id, caption=f"💳 طلب تسديد قرض #{payment_id}\nالتاجر: {user.full_name}\nTelegram ID: {user.id}\nالمبلغ: {amount} دج\nطريقة الدفع: {method}\nالدين الحالي: {debt} دج", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ قبول التسديد", callback_data=f"creditpay_approve:{payment_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"creditpay_reject:{payment_id}")]]))
        context.user_data.pop("awaiting_credit_receipt", None)
        context.user_data.pop("credit_repay_amount", None)
        context.user_data.pop("credit_repay_method", None)
        await message.reply_text(f"✅ استلمنا وصل تسديد الدين #{payment_id}. سيتم تحديث الدين بعد موافقة الإدارة.", reply_markup=main_keyboard(user.id))
        return

    if context.user_data.get("awaiting_deposit_receipt"):
        amount = int(context.user_data.get("deposit_amount", 0))
        method = context.user_data.get("deposit_method", "")
        if amount < 100 or not method:
            context.user_data.pop("awaiting_deposit_receipt", None)
            await message.reply_text("❌ انتهت جلسة التعبئة. ابدأ من جديد.")
            return
        photo = message.photo[-1]
        with db() as conn:
            cur = conn.execute("INSERT INTO wallet_deposits (user_id, amount, payment_method, receipt_file_id, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", (user.id, amount, method, photo.file_id, now_text()))
            deposit_id = cur.lastrowid
        if ADMIN_ID:
            try:
                await context.bot.send_photo(ADMIN_ID, photo.file_id,
                    caption=f"💰 طلب تعبئة رصيد #{deposit_id}\nالزبون: {user.full_name}\nTelegram ID: {user.id}\nالمبلغ: {amount} دج\nطريقة الدفع: {method}\nالحالة: قيد المراجعة",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ قبول التعبئة", callback_data=f"deposit_approve:{deposit_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"deposit_reject:{deposit_id}")]]))
            except Exception:
                logger.exception("تعذر إرسال طلب تعبئة الرصيد للإدارة")
        context.user_data.pop("awaiting_deposit_receipt", None)
        context.user_data.pop("deposit_amount", None)
        context.user_data.pop("deposit_method", None)
        await message.reply_text(f"✅ استلمنا وصل التعبئة #{deposit_id}. سيضاف الرصيد بعد تأكيد الإدارة.", reply_markup=main_keyboard(user.id))
        return

    if not context.user_data.get("awaiting_payment_receipt"):
        handled = await forward_customer_attachment_to_admin(update, context, "photo")
        if not handled and user and not is_admin(user.id):
            # لا نمنع بقية وظائف البوت؛ نرد فقط إذا كانت الصورة محاولة مراسلة خارج محادثة الدعم.
            with db() as conn:
                chat = conn.execute("SELECT is_open FROM customer_chats WHERE user_id = ?", (user.id,)).fetchone()
            if chat and int(chat["is_open"] or 0) == 1:
                return
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
                payment_method, price, status, created_at, points_used, platform
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                int(draft.get("points_used", 0)),
                draft.get("platform", ""),
            ),
        )
        order_id = cursor.lastrowid
        points_used = int(draft.get("points_used", 0))
        if points_used:
            conn.execute("UPDATE users SET points = MAX(0, points - ?) WHERE user_id = ?", (points_used, user.id))

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
                    f"📋 معلومات الشحن: {player_id or 'لا تتطلب الخدمة معلومات شحن'}\n"
                    f"📱 الجهاز: {draft.get('platform') or 'غير محدد'}\n"
                    f"🎁 النقاط المستخدمة: {draft.get('points_used', 0)}\n"
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
    context.user_data.pop("use_points_for_order", None)

    await message.reply_text(
        "✅ تم استلام صورة وصل الدفع وتسجيل طلبك!\n\n"
        f"🧾 رقم الطلب: #{order_id}\n"
        f"🎮 الخدمة: {draft['game_name']}\n"
        f"📦 العرض: {draft['offer_name']}\n"
        f"{('🆔 معرف اللاعب: ' + player_id + chr(10)) if player_id else '📋 لا يتطلب هذا العرض ID أو بيانات دخول.' + chr(10)}"
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
            "SELECT * FROM games ORDER BY id"
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

        method = game["recharge_method"] if "recharge_method" in game.keys() else "id"
        method_label = {"id": "ID اللاعب", "login": "إيميل وكلمة سر", "none": "بدون معلومات شحن"}.get(method, "ID اللاعب")
        buttons.append([
            InlineKeyboardButton(
                f"🔑 طريقة الشحن: {method_label} (تغيير)",
                callback_data=f"game_method:{game['id']}",
            ),
            InlineKeyboardButton(
                f"📱 الأجهزة: {game['platform_mode'] if 'platform_mode' in game.keys() else 'none'} (تغيير)",
                callback_data=f"game_platform:{game['id']}",
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
            SELECT id, name, price_baridi, price_flexy, active, android_active, ios_active, reward_points
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
            InlineKeyboardButton(f"🤖 Android: {'متاح' if offer['android_active'] else 'موقوف'}", callback_data=f"offer_platform:{offer['id']}:android"),
            InlineKeyboardButton(f"🍎 iPhone: {'متاح' if offer['ios_active'] else 'موقوف'}", callback_data=f"offer_platform:{offer['id']}:ios"),
            InlineKeyboardButton("🎁 نقاط المكافأة", callback_data=f"edit_reward:{offer['id']}"),
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


async def admin_customer_orders(query, target_id):
    with db() as conn:
        user = conn.execute("SELECT user_id, username, full_name, account_type, credit_limit, credit_debt, credit_due_at FROM users WHERE user_id = ?", (target_id,)).fetchone()
        orders = conn.execute("SELECT o.id, o.price, o.status, o.created_at, o.payment_method, o.player_id, g.name AS game_name, f.name AS offer_name FROM orders o LEFT JOIN games g ON g.id=o.game_id LEFT JOIN offers f ON f.id=o.offer_id WHERE o.user_id = ? ORDER BY o.id DESC LIMIT 50", (target_id,)).fetchall()
        totals = conn.execute("SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN status != 'rejected' THEN price ELSE 0 END),0) AS all_total, COALESCE(SUM(CASE WHEN status='completed' THEN price ELSE 0 END),0) AS completed_total, COALESCE(SUM(CASE WHEN status IN ('pending','processing') THEN price ELSE 0 END),0) AS active_total FROM orders WHERE user_id = ?", (target_id,)).fetchone()
    if not user:
        await query.edit_message_text("❌ الزبون غير موجود.")
        return
    lines = [f"👤 <b>{user['full_name'] or user['username'] or target_id}</b>", f"🆔 ID: <code>{target_id}</code>", f"🏷️ نوع الحساب: {'تاجر' if user['account_type']=='trader' else 'زبون عادي'}", f"🧾 عدد الطلبات: {totals['n']}", f"💰 مجموع الطلبات غير المرفوضة: {totals['all_total']} دج", f"✅ مجموع المكتمل: {totals['completed_total']} دج", f"⏳ مجموع المعلّق/قيد التنفيذ: {totals['active_total']} دج"]
    if user['account_type'] == 'trader':
        lines += [f"💳 سقف القرض: {user['credit_limit']} دج", f"📉 الدين الحالي: {user['credit_debt']} دج", f"📅 الاستحقاق: {user['credit_due_at'] or 'لا يوجد'}"]
    lines.append("\n<b>آخر الطلبات:</b>")
    for order in orders:
        lines.append(f"\n🧾 #{order['id']} — {order['game_name'] or 'خدمة محذوفة'} / {order['offer_name'] or 'عرض محذوف'}\n💰 {order['price']} دج | {status_label(order['status'])}\n💳 {order['payment_method'] or 'غير محدد'} | {order['created_at'] or ''}")
    await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 قائمة الزبائن", callback_data="adm_customers")]]))


# =========================
# تصفير بيانات الحسابات مع حفظ ملخص إحصائي لشهرين
# =========================

def reset_customer_data_preserving_stats():
    """Archive monthly order aggregates for the last two months, then clear transactional/user data.
    Products, prices and settings are deliberately preserved.
    """
    with db() as conn:
        # Archive monthly summaries from the last two months before deleting detailed records.
        conn.execute("""
            INSERT INTO monthly_stats_archive
                (month, users_count, total_orders, pending_orders, processing_orders,
                 completed_orders, rejected_orders, completed_revenue, archived_at)
            SELECT substr(created_at, 1, 7) AS month,
                   COUNT(DISTINCT user_id), COUNT(*),
                   SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='processing' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='completed' THEN price ELSE 0 END), ?
            FROM orders
            WHERE created_at >= datetime('now', '-2 months')
              AND created_at IS NOT NULL AND created_at != ''
            GROUP BY substr(created_at, 1, 7)
            ON CONFLICT(month) DO UPDATE SET
                users_count=excluded.users_count,
                total_orders=excluded.total_orders,
                pending_orders=excluded.pending_orders,
                processing_orders=excluded.processing_orders,
                completed_orders=excluded.completed_orders,
                rejected_orders=excluded.rejected_orders,
                completed_revenue=excluded.completed_revenue,
                archived_at=excluded.archived_at
        """, (now_text(),))
        # Keep only the two most recent calendar-month summaries.
        conn.execute("DELETE FROM monthly_stats_archive WHERE month < strftime('%Y-%m', date('now', 'start of month', '-1 month'))")
        # Reset user accounts, orders, wallet transactions and customer support sessions.
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM wallet_deposits")
        conn.execute("DELETE FROM credit_payments")
        conn.execute("DELETE FROM customer_chats")
        conn.execute("DELETE FROM users")
        # Reset auto-increment counters for the cleared transaction tables.
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('orders','wallet_deposits','credit_payments')")


async def show_archived_stats(query):
    with db() as conn:
        rows = conn.execute("SELECT * FROM monthly_stats_archive ORDER BY month DESC LIMIT 2").fetchall()
    if not rows:
        await query.edit_message_text(
            "📊 ما كاين حتى إحصائيات محفوظة للشهرين الأخيرين.\n\nالإحصائيات المحفوظة هي ملخصات شهرية فقط، ماشي تفاصيل طلبات أو حسابات.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_stats")]])
        )
        return
    lines = ["🗂️ <b>الإحصائيات المحفوظة للشهرين الأخيرين</b>", "<i>ملخصات شهرية؛ تفاصيل الحسابات والطلبات القديمة لا تبقى بعد التصفير.</i>"]
    for r in rows:
        lines.append(
            f"\n📅 <b>{r['month']}</b>\n"
            f"👥 مستخدمون لديهم طلبات: {r['users_count']}\n"
            f"🧾 مجموع الطلبات: {r['total_orders']}\n"
            f"⏳ معلقة: {r['pending_orders']} | 🔄 قيد التنفيذ: {r['processing_orders']}\n"
            f"✅ مكتملة: {r['completed_orders']} | ❌ مرفوضة: {r['rejected_orders']}\n"
            f"💰 قيمة الطلبات المكتملة: {r['completed_revenue']} دج"
        )
    await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_stats")]]))


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
                    "🗂️ إحصائيات الشهرين الماضيين",
                    callback_data="adm_archived_stats",
                ),
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")]
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
        "game_method:",
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
        "trader_approve:",
        "trader_reject:",
        "game_platform:",
        "offer_platform:",
        "edit_reward:",
        "deposit_approve:",
        "deposit_reject:",
        "chat_reply:",
        "loan_", "customer_orders:", "creditpay_", "account_type_set:", "reset_data", "reset_confirm", "adm_archived_stats",
    )

    if data.startswith(admin_actions) and not is_admin(user_id):
        await query.answer("⛔ غير مسموح لك.", show_alert=True)
        return

    if data.startswith("account_type_set:"):
        parts = data.split(":")
        if len(parts) != 3 or parts[1] not in ("customer", "trader"):
            await query.answer("طلب غير صالح.", show_alert=True)
            return
        new_type, target_id = parts[1], int(parts[2])
        with db() as conn:
            target = conn.execute("SELECT user_id, full_name, username, account_type, credit_debt FROM users WHERE user_id=?", (target_id,)).fetchone()
            if not target:
                await query.answer("الحساب غير موجود.", show_alert=True)
                return
            if target["account_type"] == "trader" and new_type == "customer" and int(target["credit_debt"] or 0) > 0:
                await query.answer("لا يمكن تحويل التاجر إلى زبون قبل تسديد الدين.", show_alert=True)
                return
            conn.execute("UPDATE users SET account_type=?, trader_requested=0 WHERE user_id=?", (new_type, target_id))
        label = "تاجر" if new_type == "trader" else "زبون عادي"
        try:
            await context.bot.send_message(target_id, f"ℹ️ تم تغيير نوع حسابك في {STORE_NAME} إلى: {label}.")
        except Exception:
            logger.exception("تعذر إشعار المستخدم بتغيير نوع الحساب")
        await query.edit_message_text(f"✅ تم تغيير نوع الحساب إلى {label}.\nID: {target_id}\n" + ("يمكنك الآن ضبط سقف القرض وأجل التسديد من قائمة قروض التجار." if new_type == "trader" else "تم إيقاف صلاحيات التاجر. أي دين قائم يجب تسويته قبل التحويل."))
        return

    if data.startswith("loan_manage:"):
        target_id = int(data.split(":", 1)[1])
        with db() as conn:
            trader = conn.execute("SELECT user_id, username, full_name, credit_limit, credit_debt, credit_term_days, credit_due_at FROM users WHERE user_id = ? AND account_type = 'trader'", (target_id,)).fetchone()
        if not trader:
            await query.edit_message_text("❌ التاجر غير موجود أو حسابه غير معتمد.")
            return
        context.user_data["admin_step"] = "loan_config"
        context.user_data["loan_target_id"] = target_id
        await query.message.reply_text(f"💳 إعداد قرض التاجر {trader['full_name'] or trader['username'] or target_id} (ID: {target_id})\nالسقف الحالي: {trader['credit_limit']} دج\nالدين الحالي: {trader['credit_debt']} دج\nالأجل: {trader['credit_term_days']} يوم\nالاستحقاق: {trader['credit_due_at'] or 'لا يوجد'}\n\nأرسل: السقف | عدد الأيام\nمثال: 10000 | 30\nلإيقاف القرض أرسل: 0 | 0")
        return

    if data.startswith("customer_orders:"):
        target_id = int(data.split(":", 1)[1])
        await admin_customer_orders(query, target_id)
        return

    if data.startswith("creditpay_approve:") or data.startswith("creditpay_reject:"):
        payment_id = int(data.split(":", 1)[1])
        approve = data.startswith("creditpay_approve:")
        with db() as conn:
            pay = conn.execute("SELECT * FROM credit_payments WHERE id = ?", (payment_id,)).fetchone()
            if not pay or pay["status"] != "pending":
                await query.answer("تمت معالجة هذا الوصل مسبقاً.", show_alert=True)
                return
            debtor = conn.execute("SELECT credit_debt FROM users WHERE user_id = ?", (pay["user_id"],)).fetchone()
            debt_before = int(debtor["credit_debt"] or 0) if debtor else 0
            if approve:
                amount = min(int(pay["amount"]), debt_before)
                conn.execute("UPDATE users SET credit_debt = MAX(0, credit_debt - ?), credit_due_at = CASE WHEN MAX(0, credit_debt - ?) = 0 THEN '' ELSE credit_due_at END WHERE user_id = ?", (amount, amount, pay["user_id"]))
                conn.execute("UPDATE credit_payments SET status = 'approved', processed_at = ? WHERE id = ? AND status = 'pending'", (now_text(), payment_id))
            else:
                amount = int(pay["amount"])
                conn.execute("UPDATE credit_payments SET status = 'rejected', processed_at = ? WHERE id = ? AND status = 'pending'", (now_text(), payment_id))
        try:
            await context.bot.send_message(pay["user_id"], f"{'✅ تم قبول' if approve else '❌ تم رفض'} تسديد القرض #{payment_id}.\nالمبلغ: {amount} دج\nالدين الحالي: {max(0, debt_before-amount) if approve else debt_before} دج")
        except Exception:
            logger.exception("تعذر إشعار التاجر بتسديد القرض")
        await query.edit_message_caption(caption=f"{'✅ تم قبول' if approve else '❌ تم رفض'} تسديد القرض #{payment_id}\nالتاجر: {pay['user_id']}\nالمبلغ: {amount} دج", reply_markup=None)
        return

    if data.startswith("chat_reply:"):
        try:
            target_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        context.user_data["admin_step"] = "chat_reply_message"
        context.user_data["chat_target_id"] = target_id
        await query.message.reply_text(f"💬 أرسل ردك للزبون {target_id}.\nأرسل /cancel للإلغاء.")
        return

    if data.startswith("deposit_method:"):
        method = data.split(":", 1)[1]
        if method not in ("baridi", "flexy"):
            return
        context.user_data["deposit_method"] = "BaridiMob / CCP" if method == "baridi" else "Flexy"
        context.user_data["awaiting_deposit_receipt"] = True
        details = get_setting("baridi_details" if method == "baridi" else "flexy_details", "تواصل مع الإدارة لمعرفة معلومات الدفع.")
        await query.edit_message_text(f"💳 معلومات الدفع:\n{details}\n\n📸 بعد الدفع، أرسل صورة وصل الدفع هنا لتعبئة رصيدك.\nلا يُضاف الرصيد إلا بعد مراجعة الإدارة.")
        return

    if data.startswith("deposit_approve:") or data.startswith("deposit_reject:"):
        try:
            deposit_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        approve = data.startswith("deposit_approve:")
        with db() as conn:
            dep = conn.execute("SELECT * FROM wallet_deposits WHERE id = ?", (deposit_id,)).fetchone()
            if not dep or dep["status"] != "pending":
                await query.answer("تمت معالجة هذا الطلب مسبقًا.", show_alert=True)
                return
            conn.execute("UPDATE wallet_deposits SET status = ?, processed_at = ? WHERE id = ?", ("approved" if approve else "rejected", now_text(), deposit_id))
            if approve:
                conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (dep["amount"], dep["user_id"]))
        try:
            await context.bot.send_message(dep["user_id"], (f"✅ تمت الموافقة على تعبئة #{deposit_id}. أضيف {dep['amount']} دج إلى محفظتك." if approve else f"❌ تم رفض تعبئة الرصيد #{deposit_id}. إذا كان هناك خطأ، تواصل مع الإدارة."))
        except Exception:
            logger.exception("تعذر إشعار الزبون بنتيجة التعبئة")
        await query.edit_message_caption(caption=f"{'✅ تمت الموافقة' if approve else '❌ تم الرفض'} على تعبئة الرصيد #{deposit_id}\nالمبلغ: {dep['amount']} دج\nالزبون: {dep['user_id']}", reply_markup=None)
        return

    if data.startswith("trader_approve:") or data.startswith("trader_reject:"):
        try:
            target_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        approved = data.startswith("trader_approve:")
        with db() as conn:
            conn.execute("UPDATE users SET account_type = ?, trader_requested = 0 WHERE user_id = ?", ("trader" if approved else "customer", target_id))
        try:
            await context.bot.send_message(target_id, "✅ تمت الموافقة على حسابك كتاجر. ستظهر لك أسعار التجار." if approved else "❌ لم تتم الموافقة على طلب حساب التاجر حالياً.")
        except Exception:
            logger.exception("تعذر إشعار صاحب طلب التاجر")
        await query.edit_message_text("✅ تم تفعيل حساب التاجر." if approved else "تم رفض طلب التاجر.")
        return

    # عرض إحصائيات الشهرين المحفوظة
    if data == "adm_archived_stats":
        await show_archived_stats(query)
        return

    # تصفير البيانات مع تأكيد مزدوج
    if data == "reset_data":
        await query.edit_message_text(
            "⚠️ <b>تأكيد تصفير البيانات</b>\n\nسيتم حذف حسابات الزبائن والتجار، الطلبات، الأرصدة، نقاط الولاء، الديون، وصولات تعبئة الرصيد وتسديد الديون.\n\nستبقى الألعاب والعروض والأسعار وإعدادات البوت. سيتم حفظ ملخص إحصائي شهري للشهر الحالي والشهر السابق فقط، دون أسماء أو تفاصيل الطلبات.\n\nهل تريد المتابعة؟",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧹 نعم، صفّر البيانات", callback_data="reset_confirm")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="adm_home")],
            ])
        )
        return

    if data == "reset_confirm":
        try:
            reset_customer_data_preserving_stats()
        except Exception:
            logger.exception("فشل تصفير بيانات المتجر")
            await query.edit_message_text("❌ فشل تصفير البيانات. لم نؤكد نجاح العملية؛ راجع سجل السيرفر وقاعدة البيانات.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")]]))
            return
        await query.edit_message_text(
            "✅ تم تصفير حسابات الزبائن والتجار والطلبات والأرصدة والديون ووصولات الدفع.\n\n🎮 الألعاب والعروض والأسعار والإعدادات بقيت كما هي.\n🗂️ تم حفظ ملخصات إحصائية للشهر الحالي والشهر السابق إذا كانت هناك طلبات ضمن هذه الفترة.\n\nخذ نسخة احتياطية من قاعدة البيانات قبل أي تعديل إضافي.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 عرض الإحصائيات المحفوظة", callback_data="adm_archived_stats")], [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")]])
        )
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

    elif data == "adm_customers":
        with db() as conn:
            rows = conn.execute("SELECT u.user_id, u.username, u.full_name, COUNT(o.id) AS order_count, COALESCE(SUM(CASE WHEN o.status != 'rejected' THEN o.price ELSE 0 END), 0) AS total FROM users u JOIN orders o ON o.user_id = u.user_id GROUP BY u.user_id ORDER BY MAX(o.id) DESC LIMIT 50").fetchall()
        buttons = [[InlineKeyboardButton(f"{(r['full_name'] or r['username'] or r['user_id'])} | {r['order_count']} طلب | {r['total']} دج"[:60], callback_data=f"customer_orders:{r['user_id']}")] for r in rows]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
        await query.edit_message_text("👤 اختر زبونًا:", reply_markup=InlineKeyboardMarkup(buttons))

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

    # تحديد الأجهزة المتاحة للعبة: none -> both -> android -> ios -> none
    elif data.startswith("game_platform:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        with db() as conn:
            row = conn.execute("SELECT platform_mode FROM games WHERE id = ?", (game_id,)).fetchone()
            if not row:
                return
            modes = ["none", "both", "android", "ios"]
            current = row["platform_mode"] or "none"
            new_mode = modes[(modes.index(current) + 1) % len(modes)] if current in modes else "both"
            conn.execute("UPDATE games SET platform_mode = ? WHERE id = ?", (new_mode, game_id))
        await admin_games(query)

    elif data.startswith("offer_platform:"):
        parts = data.split(":")
        if len(parts) != 3 or parts[2] not in ("android", "ios"):
            return
        try:
            offer_id = int(parts[1])
        except ValueError:
            return
        col = "android_active" if parts[2] == "android" else "ios_active"
        with db() as conn:
            conn.execute(f"UPDATE offers SET {col} = CASE WHEN {col} = 1 THEN 0 ELSE 1 END WHERE id = ?", (offer_id,))
            row = conn.execute("SELECT game_id FROM offers WHERE id = ?", (offer_id,)).fetchone()
        if row:
            await admin_offers(query, row["game_id"])

    # تغيير طريقة الشحن بالتناوب: ID -> تسجيل الدخول -> بدون معلومات شحن
    elif data.startswith("game_method:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            return
        with db() as conn:
            game = conn.execute("SELECT name, recharge_method FROM games WHERE id = ?", (game_id,)).fetchone()
            if not game:
                await query.message.reply_text("❌ اللعبة غير موجودة.")
                return
            modes = ["id", "login", "none"]
            current = game["recharge_method"] or "id"
            new_method = modes[(modes.index(current) + 1) % len(modes)] if current in modes else "id"
            conn.execute("UPDATE games SET recharge_method = ? WHERE id = ?", (new_method, game_id))
        labels = {"id": "ID اللاعب", "login": "إيميل وكلمة سر", "none": "بدون معلومات شحن (وصل فقط)"}
        await query.answer(f"تم التغيير: {labels[new_method]}")
        await admin_games(query)

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

    elif data.startswith("edit_reward:"):
        try:
            offer_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        with db() as conn:
            offer = conn.execute("SELECT name, reward_points FROM offers WHERE id = ?", (offer_id,)).fetchone()
        if not offer:
            await query.message.reply_text("❌ العرض غير موجود.")
            return
        context.user_data["admin_step"] = "edit_reward_points"
        context.user_data["pending_offer_id"] = offer_id
        await query.message.reply_text(f"🎁 العرض: {offer['name']}\nالنقاط الحالية: {offer['reward_points']}\nأرسل عدد النقاط التي يحصل عليها الزبون بعد اكتمال الشحن (0 لإيقاف المكافأة).")

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
                "SELECT user_id, offer_id, status, points_awarded, points_used, wallet_charged, wallet_refunded, credit_charged, credit_refunded, price FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()

            if not order:
                await query.edit_message_text(
                    "❌ الطلب غير موجود."
                )
                return

            customer_id = order["user_id"]
            # Rewards are granted only once, on the first transition to completed.
            if new_status == "completed" and order["status"] != "completed" and not int(order["points_awarded"] or 0):
                reward = conn.execute("SELECT reward_points FROM offers WHERE id = ?", (order["offer_id"],)).fetchone()
                reward_points = int(reward["reward_points"] or 0) if reward else 0
                if reward_points:
                    conn.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (reward_points, customer_id))
                conn.execute("UPDATE orders SET points_awarded = 1 WHERE id = ?", (order_id,))
            # Refund wallet balance and redeemed points if an order is rejected.
            if new_status == "rejected" and order["status"] != "rejected":
                if int(order["wallet_charged"] or 0) and not int(order["wallet_refunded"] or 0):
                    conn.execute("UPDATE users SET balance = balance + ?, points = points + ? WHERE user_id = ?", (int(conn.execute("SELECT price FROM orders WHERE id = ?", (order_id,)).fetchone()[0]), int(order["points_used"] or 0), customer_id))
                    conn.execute("UPDATE orders SET wallet_refunded = 1 WHERE id = ?", (order_id,))
                elif int(order["points_used"] or 0):
                    conn.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (int(order["points_used"] or 0), customer_id))
                if int(order["credit_charged"] or 0) and not int(order["credit_refunded"] or 0):
                    conn.execute("UPDATE users SET credit_debt = MAX(0, credit_debt - ?), credit_due_at = CASE WHEN MAX(0, credit_debt - ?) = 0 THEN '' ELSE credit_due_at END WHERE user_id = ?", (int(order["price"] or 0), int(order["price"] or 0), customer_id))
                    conn.execute("UPDATE orders SET credit_refunded = 1 WHERE id = ?", (order_id,))
            if new_status in ("completed", "rejected"):
                credential_row = conn.execute("SELECT player_id FROM orders WHERE id = ?", (order_id,)).fetchone()
                if credential_row and str(credential_row["player_id"] or "").startswith("LOGIN EMAIL:"):
                    conn.execute("UPDATE orders SET player_id = '[تم حذف بيانات الدخول بعد المعالجة]' WHERE id = ?", (order_id,))
            conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))

        status_text = status_label(new_status)

        try:
            await context.bot.send_message(
                chat_id=customer_id,
                text=(
                    f"📦 تحديث الطلب #{order_id}\n\n"
                    f"📌 الحالة الجديدة: {status_text}"
                    + (f"\n🎁 تمت إضافة نقاط المكافأة إلى حسابك." if new_status == "completed" else f"\n💰 تم إرجاع المبلغ والنقاط إلى محفظتك إذا كان الطلب مدفوعًا منها." if new_status == "rejected" else "")
                ),
                reply_markup=main_keyboard(customer_id),
            )
        except Exception:
            logger.exception(
                "تعذر إرسال تحديث الطلب إلى الزبون"
            )

        await admin_order_details(query, order_id)

    # اختيار جهاز الهاتف
    elif data.startswith("platform:"):
        parts = data.split(":")
        if len(parts) != 3 or parts[2] not in ("android", "ios"):
            return
        try:
            game_id = int(parts[1])
        except ValueError:
            return
        context.user_data["selected_platform"] = parts[2]
        await open_game(query, game_id, parts[2])

    # فتح لعبة للزبون
    elif data.startswith("game:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            return
        context.user_data.pop("selected_platform", None)
        await open_game(query, game_id)

    # فتح عرض للزبون
    elif data.startswith("offer:"):
        parts = data.split(":")
        if len(parts) not in (3, 4):
            return
        try:
            game_id = int(parts[1])
            offer_id = int(parts[2])
        except ValueError:
            return
        platform = parts[3] if len(parts) == 4 and parts[3] != "none" else None
        context.user_data["selected_platform"] = platform or ""
        await open_offer(query, game_id, offer_id, platform, context)

    elif data.startswith("points_toggle:"):
        parts = data.split(":")
        if len(parts) != 4:
            return
        try:
            game_id, offer_id = int(parts[1]), int(parts[2])
        except ValueError:
            return
        context.user_data["use_points_for_order"] = not context.user_data.get("use_points_for_order", False)
        platform = parts[3] if parts[3] in ("android", "ios") else None
        await open_offer(query, game_id, offer_id, platform, context)

    # اختيار طريقة دفع تسديد القرض
    elif data.startswith("credit_repay_method:"):
        method = data.split(":", 1)[1]
        if method not in ("baridi", "flexy"):
            return
        context.user_data["credit_repay_method"] = "BaridiMob / CCP" if method == "baridi" else "Flexy"
        context.user_data["awaiting_credit_receipt"] = True
        details = get_setting("baridi_details" if method == "baridi" else "flexy_details", "تواصل مع الإدارة لمعرفة معلومات الدفع.")
        await query.edit_message_text(f"💳 معلومات الدفع لتسديد القرض:\n{details}\n\nالمبلغ: {context.user_data.get('credit_repay_amount', 0)} دج\n📸 أرسل صورة وصل الدفع. لن ينقص الدين حتى توافق الإدارة.")

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
        context.user_data.pop("awaiting_credit_repay_amount", None)
        context.user_data.pop("awaiting_login_email", None)
        context.user_data.pop("awaiting_login_password", None)
        context.user_data.pop("pending_login_email", None)
        context.user_data.pop("editing_game_description", None)
        context.user_data.pop("editing_game_prompt", None)

        await message.reply_text(
            "❌ تم إلغاء العملية.",
            reply_markup=main_keyboard(user_id),
        )
        return

    if context.user_data.get("awaiting_credit_repay_amount"):
        try:
            amount = int(text.replace(" ", "").replace("دج", ""))
            with db() as conn:
                debt_row = conn.execute("SELECT credit_debt FROM users WHERE user_id=?", (user_id,)).fetchone()
            debt = int(debt_row["credit_debt"] or 0) if debt_row else 0
            if amount < 1 or amount > debt:
                raise ValueError
        except ValueError:
            with db() as conn:
                debt_row = conn.execute("SELECT credit_debt FROM users WHERE user_id=?", (user_id,)).fetchone()
            debt = int(debt_row["credit_debt"] or 0) if debt_row else 0
            await message.reply_text(f"❌ أدخل مبلغًا صحيحًا لا يتجاوز الدين الحالي ({debt} دج).")
            return
        context.user_data["credit_repay_amount"] = amount
        context.user_data.pop("awaiting_credit_repay_amount", None)
        await message.reply_text("اختر طريقة الدفع:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BaridiMob / CCP", callback_data="credit_repay_method:baridi")], [InlineKeyboardButton("Flexy", callback_data="credit_repay_method:flexy")]]))
        return

    if context.user_data.get("awaiting_deposit_amount"):
        try:
            amount = int(text.replace(" ", ""))
            if amount < 100:
                raise ValueError
        except ValueError:
            await message.reply_text("❌ أدخل مبلغًا صحيحًا لا يقل عن 100 دج.")
            return
        context.user_data["deposit_amount"] = amount
        context.user_data.pop("awaiting_deposit_amount", None)
        await message.reply_text(
            f"💰 مبلغ التعبئة: {amount} دج\nاختر طريقة الدفع:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("BaridiMob / CCP", callback_data="deposit_method:baridi")],
                [InlineKeyboardButton("Flexy", callback_data="deposit_method:flexy")],
            ]),
        )
        return

    if context.user_data.get("awaiting_login_email"):
        if "@" not in text or len(text) < 5:
            await message.reply_text("❌ أرسل إيميلًا صحيحًا.")
            return
        context.user_data["pending_login_email"] = text
        context.user_data.pop("awaiting_login_email", None)
        context.user_data["awaiting_login_password"] = True
        await message.reply_text("🔑 أرسل كلمة السر الخاصة بالحساب المراد شحنه. لن أعرضها في رسالة التأكيد.")
        return

    if context.user_data.get("awaiting_login_password"):
        if not text:
            await message.reply_text("❌ كلمة السر لا يمكن أن تكون فارغة.")
            return
        email = context.user_data.pop("pending_login_email", "")
        context.user_data.pop("awaiting_login_password", None)
        context.user_data["pending_player_id"] = f"LOGIN EMAIL: {email} | PASSWORD: {text}"
        draft = context.user_data.get("order_draft")
        if not draft:
            context.user_data.pop("pending_player_id", None)
            await message.reply_text("❌ انتهت جلسة الطلب. ابدأ من جديد.")
            return
        draft["login_mode"] = True
        if draft.get("payment_type") == "balance":
            await create_wallet_order(message, context, context.user_data["pending_player_id"])
            return
        if draft.get("payment_type") == "credit":
            await create_credit_order(message, context, context.user_data["pending_player_id"])
            return
        context.user_data["awaiting_payment_receipt"] = True
        await message.reply_text(
            "✅ تم استلام بيانات الحساب.\n\n"
            f"🎮 اللعبة: {draft['game_name']}\n📦 العرض: {draft['offer_name']}\n"
            f"💳 طريقة الدفع: {draft['method']}\n💰 المبلغ: {draft['price']} دج\n\n"
            "📸 الآن أرسل صورة وصل الدفع لإتمام الطلب.\nلإلغاء العملية أرسل /cancel"
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

    if is_admin(user_id):
        game_id = context.user_data.get("editing_game_prompt")
        if game_id is not None:
            with db() as conn:
                conn.execute("UPDATE games SET player_prompt = ? WHERE id = ?", (text, int(game_id)))
            context.user_data.pop("editing_game_prompt", None)
            await message.reply_text("✅ تم حفظ رسالة طلب المعلومات.")
            return

    #=========================
    # خطوات الإدارة
    # =========================

    if is_admin(user_id):
        step = context.user_data.get("admin_step")

        if step == "account_convert_user_id":
            try:
                target_id = int(text.strip())
                if target_id <= 0:
                    raise ValueError
            except ValueError:
                await message.reply_text("❌ أرسل Telegram ID صحيحًا.")
                return
            with db() as conn:
                target = conn.execute("SELECT user_id, username, full_name, account_type, credit_debt FROM users WHERE user_id=?", (target_id,)).fetchone()
            if not target:
                await message.reply_text("❌ الحساب غير موجود في قاعدة البيانات.")
                return
            context.user_data.pop("admin_step", None)
            context.user_data["account_convert_target_id"] = target_id
            current = "تاجر" if target["account_type"] == "trader" else "زبون عادي"
            buttons = [[InlineKeyboardButton("👤 تحويل إلى زبون عادي", callback_data=f"account_type_set:customer:{target_id}")], [InlineKeyboardButton("🏪 تحويل إلى تاجر", callback_data=f"account_type_set:trader:{target_id}")], [InlineKeyboardButton("❌ إلغاء", callback_data="adm_home")]]
            await message.reply_text(f"👤 الحساب: {target['full_name'] or target['username'] or target_id}\nID: {target_id}\nالنوع الحالي: {current}\nالدين الحالي: {target['credit_debt'] or 0} دج\n\nاختر نوع الحساب الجديد. إذا كان عليه دين، لن يُسمح بتحويله من تاجر إلى زبون حتى تسوية الدين.", reply_markup=InlineKeyboardMarkup(buttons))
            return

        if step == "loan_config":
            try:
                parts = [x.strip() for x in text.split("|")]
                if len(parts) != 2:
                    raise ValueError
                limit_amount, term_days = int(parts[0]), int(parts[1])
                target_id = int(context.user_data.get("loan_target_id", 0))
                if limit_amount < 0 or term_days < 0 or (limit_amount > 0 and term_days < 1):
                    raise ValueError
            except ValueError:
                await message.reply_text("❌ الصيغة غير صحيحة. أرسل: السقف | الأيام\nمثال: 10000 | 30 أو 0 | 0 لإيقاف القرض.")
                return
            with db() as conn:
                row = conn.execute("SELECT credit_debt FROM users WHERE user_id = ? AND account_type = 'trader'", (target_id,)).fetchone()
                if not row:
                    await message.reply_text("❌ التاجر غير موجود أو غير معتمد.")
                    context.user_data.pop("admin_step", None)
                    return
                if limit_amount < int(row["credit_debt"] or 0):
                    await message.reply_text(f"❌ لا يمكن جعل سقف القرض أقل من الدين الحالي ({row['credit_debt']} دج).")
                    return
                conn.execute("UPDATE users SET credit_limit = ?, credit_term_days = ?, credit_due_at = CASE WHEN credit_debt = 0 THEN '' ELSE credit_due_at END WHERE user_id = ?", (limit_amount, term_days, target_id))
            context.user_data.pop("admin_step", None)
            context.user_data.pop("loan_target_id", None)
            try:
                await context.bot.send_message(target_id, f"💳 تم تحديث إعدادات القرض الخاصة بك.\nسقف القرض: {limit_amount} دج\nأجل التسديد: {term_days} يومًا" if limit_amount else "⛔ تم إيقاف إمكانية استخدام قرض جديد في حسابك. الدين الحالي يبقى واجب التسديد.")
            except Exception:
                logger.exception("تعذر إشعار التاجر بإعداد القرض")
            await message.reply_text("✅ تم حفظ إعدادات القرض.", reply_markup=admin_keyboard())
            return

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

            if len(parts) not in (3, 5, 6):
                await message.reply_text(
                    "❌ الصيغة غير صحيحة.\n\n"
                    "استعمل:\n"
                    "اسم العرض | سعر BaridiMob/CCP للزبون | سعر Flexy للزبون | سعر BaridiMob/CCP للتاجر | سعر Flexy للتاجر\n\n"
                    "مثال:\n100 Coins | 250 | 300 | 220 | 270\n"
                    "ويمكن إرسال 3 خانات فقط لجعل سعر التاجر مثل سعر الزبون، أو 6 خانات وإضافة نقاط المكافأة في النهاية."
                )
                return

            offer_name = parts[0]

            try:
                price_baridi = int(parts[1])
                price_flexy = int(parts[2])
                price_baridi_trader = int(parts[3]) if len(parts) == 5 else price_baridi
                price_flexy_trader = int(parts[4]) if len(parts) >= 5 else price_flexy
                reward_points = int(parts[5]) if len(parts) == 6 else 0

                if (
                    not offer_name
                    or price_baridi < 0
                    or price_flexy < 0
                    or price_baridi_trader < 0
                    or price_flexy_trader < 0
                    or reward_points < 0
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
                    (game_id, name, price_baridi, price_flexy, price_baridi_trader, price_flexy_trader, reward_points, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        game_id,
                        offer_name,
                        price_baridi,
                        price_flexy,
                        price_baridi_trader,
                        price_flexy_trader,
                        reward_points,
                    ),
                )

            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_game_id", None)

            await message.reply_text(
                f"✅ تمت إضافة العرض: {offer_name}\n\n"
                f"🏦 BaridiMob/CCP: {price_baridi} دج\n"
                f"📱 Flexy: {price_flexy} دج\n"
                f"🏪 أسعار التاجر — BaridiMob/CCP: {price_baridi_trader} دج | Flexy: {price_flexy_trader} دج\n🎁 نقاط المكافأة: {reward_points}",
                reply_markup=ReplyKeyboardMarkup(
                    ADMIN_PANEL_MENU,
                    resize_keyboard=True,
                ),
            )
            return

        if step == "edit_reward_points":
            try:
                reward_points = int(text)
                if reward_points < 0:
                    raise ValueError
            except ValueError:
                await message.reply_text("❌ أرسل عددًا صحيحًا من النقاط (0 أو أكثر).")
                return
            offer_id = context.user_data.get("pending_offer_id")
            with db() as conn:
                conn.execute("UPDATE offers SET reward_points = ? WHERE id = ?", (reward_points, offer_id))
            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_offer_id", None)
            await message.reply_text(f"✅ تم ضبط مكافأة العرض على {reward_points} نقطة.", reply_markup=admin_keyboard())
            return

        # تعديل أسعار عرض
        if step == "edit_price_data":
            parts = [part.strip() for part in text.split("|")]

            if len(parts) not in (2, 4):
                await message.reply_text(
                    "❌ الصيغة غير صحيحة.\n\n"
                    "ابعث سعرين للزبون أو 4 أسعار: الزبون Baridi | الزبون Flexy | التاجر Baridi | التاجر Flexy.\n"
                    "مثال: 750 | 900 | 650 | 800"
                )
                return

            try:
                price_baridi = int(parts[0])
                price_flexy = int(parts[1])
                price_baridi_trader = int(parts[2]) if len(parts) == 4 else price_baridi
                price_flexy_trader = int(parts[3]) if len(parts) == 4 else price_flexy

                if min(price_baridi, price_flexy, price_baridi_trader, price_flexy_trader) < 0:
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
                    SET price_baridi = ?, price_flexy = ?,
                        price_baridi_trader = ?, price_flexy_trader = ?
                    WHERE id = ?
                    """,
                    (price_baridi, price_flexy, price_baridi_trader, price_flexy_trader, offer_id),
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
                f"📱 Flexy: {price_flexy} دج\n"
                f"🏪 للتاجر — BaridiMob/CCP: {price_baridi_trader} دج | Flexy: {price_flexy_trader} دج",
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

        if text == "💬 مراسلة زبون":
            context.user_data["admin_step"] = "chat_user_id"
            await message.reply_text("أرسل Telegram ID للزبون الذي تريد مراسلته.")
            return

        if step == "chat_user_id":
            try:
                target_id = int(text)
                if target_id <= 0:
                    raise ValueError
            except ValueError:
                await message.reply_text("❌ أرسل Telegram ID صحيحًا.")
                return
            with db() as conn:
                found = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,)).fetchone()
            if not found:
                await message.reply_text("❌ لم أجد هذا الزبون في قاعدة البيانات.")
                return
            context.user_data["chat_target_id"] = target_id
            context.user_data["admin_step"] = "chat_first_message"
            await message.reply_text("اكتب الرسالة التي تريد إرسالها. بعد إرسالها سيفتح البوت المحادثة ليتمكن الزبون من الرد.")
            return

        if step in ("chat_first_message", "chat_reply_message"):
            target_id = context.user_data.get("chat_target_id")
            if not target_id:
                context.user_data.pop("admin_step", None)
                await message.reply_text("❌ لم يتم تحديد الزبون.")
                return
            try:
                await context.bot.send_message(target_id, f"💬 رسالة من إدارة SERADJ STORE:\n\n{text}")
                with db() as conn:
                    conn.execute("INSERT INTO customer_chats (user_id, is_open, updated_at) VALUES (?, 1, ?) ON CONFLICT(user_id) DO UPDATE SET is_open = 1, updated_at = excluded.updated_at", (target_id, now_text()))
                await message.reply_text("✅ تم إرسال الرسالة وفتح المحادثة. الزبون يقدر يرد عليك من البوت.")
            except Exception:
                logger.exception("تعذر إرسال رسالة إلى الزبون")
                await message.reply_text("❌ تعذر إرسال الرسالة. تأكد أن الزبون بدأ البوت من قبل.")
            context.user_data.pop("admin_step", None)
            context.user_data.pop("chat_target_id", None)
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

    if text == "💰 تعبئة الرصيد":
        context.user_data["awaiting_deposit_amount"] = True
        await message.reply_text("💰 أرسل مبلغ التعبئة بالدينار الجزائري (مثال: 1000 دج).\nالحد الأدنى 100 دج.\nللإلغاء أرسل /cancel")
        return

    if text == "💳 تسديد القرض":
        if not is_trader(user_id):
            await message.reply_text("خاصية القرض وتسديده مخصصة للتجار المعتمدين فقط.", reply_markup=main_keyboard(user_id))
            return
        with db() as conn:
            row = conn.execute("SELECT credit_debt, credit_limit, credit_due_at, account_type FROM users WHERE user_id = ?", (user_id,)).fetchone()
        debt = int(row["credit_debt"] or 0) if row else 0
        limit_amount = int(row["credit_limit"] or 0) if row else 0
        due_at = row["credit_due_at"] or "" if row else ""
        if debt <= 0:
            await message.reply_text("✅ ما عندك حتى دين حاليًا.")
            return
        context.user_data["awaiting_credit_repay_amount"] = True
        await message.reply_text(f"💳 تسديد القرض\nالدين الحالي: {debt} دج\nتاريخ الاستحقاق: {due_at or 'غير محدد'}\n\nأرسل مبلغ التسديد بالدينار (كلي أو جزئي)، ثم أرسل صورة وصل الدفع. ينقص الدين بعد موافقة الإدارة فقط.\nللإلغاء أرسل /cancel")
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

        if text == "🔄 تحويل نوع الحساب":
            context.user_data["admin_step"] = "account_convert_user_id"
            await message.reply_text("أرسل Telegram ID للحساب الذي تريد تغيير نوعه.\nللإلغاء أرسل /cancel")
            return

        if text == "💳 قروض التجار":
            with db() as conn:
                rows = conn.execute("SELECT user_id, username, full_name, credit_limit, credit_debt, credit_term_days, credit_due_at FROM users WHERE account_type = 'trader' ORDER BY full_name, user_id").fetchall()
            if not rows:
                await message.reply_text("لا توجد حسابات تجار معتمدة.", reply_markup=admin_keyboard())
                return
            buttons = []
            for row in rows:
                label = f"{row['full_name'] or row['username'] or row['user_id']} | دين {row['credit_debt']} / سقف {row['credit_limit']}"
                buttons.append([InlineKeyboardButton(label[:60], callback_data=f"loan_manage:{row['user_id']}")])
            buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
            await message.reply_text("💳 اختر تاجرًا لإعداد سقف القرض وأجل التسديد:", reply_markup=InlineKeyboardMarkup(buttons))
            return

        if text == "🧹 تصفير الحسابات والطلبات":
            await message.reply_text(
                "⚠️ هذا الإجراء يمسح حسابات الزبائن والتجار والطلبات والأرصدة والديون ووصولات الدفع، لكنه يبقي الألعاب والعروض والأسعار. سيحفظ ملخصات شهرية للشهر الحالي والسابق فقط. تابع من الزر التالي إذا كنت متأكدًا.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("متابعة إلى التأكيد", callback_data="reset_data")], [InlineKeyboardButton("إلغاء", callback_data="adm_home")]])
            )
            return

        if text == "👤 طلبات حسب الزبون":
            with db() as conn:
                rows = conn.execute("SELECT u.user_id, u.username, u.full_name, COUNT(o.id) AS order_count, COALESCE(SUM(CASE WHEN o.status != 'rejected' THEN o.price ELSE 0 END), 0) AS total FROM users u JOIN orders o ON o.user_id = u.user_id GROUP BY u.user_id ORDER BY MAX(o.id) DESC LIMIT 50").fetchall()
            if not rows:
                await message.reply_text("لا توجد طلبات مسجلة.", reply_markup=admin_keyboard())
                return
            buttons = []
            for row in rows:
                label = f"{row['full_name'] or row['username'] or row['user_id']} | {row['order_count']} طلب | {row['total']} دج"
                buttons.append([InlineKeyboardButton(label[:60], callback_data=f"customer_orders:{row['user_id']}")])
            buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
            await message.reply_text("👤 الطلبات مجمعة حسب كل زبون (المرفوضة مستثناة من الإجمالي):", reply_markup=InlineKeyboardMarkup(buttons))
            return

        if text == "👥 إدارة التجار":
            with db() as conn:
                rows = conn.execute("SELECT user_id, username, full_name FROM users WHERE trader_requested = 1 AND account_type != 'trader' ORDER BY user_id DESC LIMIT 30").fetchall()
            if not rows:
                await message.reply_text("لا توجد طلبات تاجر معلّقة.", reply_markup=admin_keyboard())
                return
            buttons = []
            for row in rows:
                buttons.append([InlineKeyboardButton(f"{row['full_name'] or row['username'] or row['user_id']} — قبول", callback_data=f"trader_approve:{row['user_id']}"), InlineKeyboardButton("رفض", callback_data=f"trader_reject:{row['user_id']}")])
            await message.reply_text("🏪 طلبات حسابات التجار:", reply_markup=InlineKeyboardMarkup(buttons))
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


    if text == "🏪 طلب حساب تاجر":
        if is_admin(user_id):
            await message.reply_text("أنت الإدارة ولديك صلاحيات كاملة.")
            return
        with db() as conn:
            row = conn.execute("SELECT account_type, trader_requested FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                conn.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?)", (user_id, update.effective_user.username or "", update.effective_user.full_name or "", now_text()))
                row = conn.execute("SELECT account_type, trader_requested FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row["account_type"] == "trader":
                await message.reply_text("✅ حسابك مفعّل كتاجر بالفعل.")
                return
            if row["trader_requested"]:
                await message.reply_text("⏳ طلبك قيد المراجعة من الإدارة.")
                return
            conn.execute("UPDATE users SET trader_requested = 1 WHERE user_id = ?", (user_id,))
        if ADMIN_ID:
            try:
                await context.bot.send_message(ADMIN_ID, f"🏪 طلب حساب تاجر جديد\nالاسم: {update.effective_user.full_name}\nUsername: @{update.effective_user.username or 'غير متوفر'}\nID: {user_id}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ قبول التاجر", callback_data=f"trader_approve:{user_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"trader_reject:{user_id}")]]))
            except Exception:
                logger.exception("تعذر إرسال طلب التاجر للإدارة")
        await message.reply_text("✅ أرسلنا طلبك للإدارة. سيتم تفعيل أسعار التجار بعد الموافقة.")
        return

    if not is_admin(user_id):
        with db() as conn:
            chat = conn.execute("SELECT is_open FROM customer_chats WHERE user_id = ?", (user_id,)).fetchone()
        if chat and int(chat["is_open"] or 0) == 1:
            if ADMIN_ID:
                try:
                    await context.bot.send_message(ADMIN_ID, f"💬 رسالة من زبون\nالاسم: {update.effective_user.full_name}\nTelegram ID: {user_id}\n\n{text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رد على الزبون", callback_data=f"chat_reply:{user_id}")]]))
                    await message.reply_text("✅ وصلت رسالتك للإدارة. يمكنك متابعة المحادثة هنا.")
                except Exception:
                    logger.exception("تعذر تحويل رسالة الزبون للإدارة")
                    await message.reply_text("❌ لم نتمكن من إرسال رسالتك للإدارة. حاول لاحقًا.")
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
    
    # الصور والملفات المرسلة ضمن محادثة الدعم
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

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

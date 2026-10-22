import re
import os
import html
import sqlite3
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
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
STORE_BENEFITS_TEXT = '✨ مزايا متجرنا ✨\n\n🎮 شحن ألعابك بسهولة\nشحن بالـID، بالحساب ، مع خيارات متعددة للألعاب والعروض.\n\n⚡ سرعة وسهولة\nخطوات بسيطة لطلب الشحن ومتابعة طلباتك من داخل المتجر.\n\n🔐 خدمة آمنة ومنظمة\nطلباتك، محفظتك ونقاطك مرتبطة بحسابك داخل المتجر.\n\n⭐ نظام النقاط\nمع عملياتك داخل المتجر تقدر تجمع نقاط، وبعد بلوغ الحد المطلوب تقدر تحولها وتستفيد منها.\n🔥 كلما تستعمل المتجر أكثر، عندك فرصة تجمع نقاط أكثر!\n\n👥 نظام الإحالة\nشارك رابطك مع أصدقائك، وكلما استخدموا المتجر وحققوا شروط الإحالة، تحصل على نقاط ومكافآت.\n💡 يعني تقدر تجمع نقاط حتى وأنت مرتاح، وأصدقاؤك هم اللي يستعملوا المتجر!\n\n👑 نظام VIP — مع ازدياد نشاطك وشحناتك، تقترب من مزايا VIP وخصوماته. 🚀\n\n💰 المحفظة\nاشحن محفظتك واستعمل رصيدك في طلباتك بسهولة، مع إمكانية الاستفادة من عروض وبونص الإيداع عند توفرها.\n\n🎁 مكافآت وعروض\nتابع المتجر باستمرار لأن العروض والمكافآت الجديدة تكون متاحة من وقت لآخر.\n\n🚀 الخلاصة: تشحن لعبتك، تجمع نقاط، تستفيد من VIP، وتشارك رابطك مع أصحابك لتزيد فرصك في المكافآت.\n\n❤️ استعمل المتجر… وكل عملية ممكن تكون بداية لمكافأة جديدة!'
TERMS_PRIVACY_TEXT = '📜 الشروط والأحكام وسياسة الخصوصية — SERADJ STORE \n\n1. الاستخدام\nباستخدامك للبوت، فإنك توافق على الالتزام بالشروط والأحكام وسياسة الخصوصية الخاصة بالمتجر.\n\n2. معلومات المستخدم\nقد يتم حفظ معرف Telegram، اسم المستخدم، الاسم الظاهر، معلومات الطلبات، معلومات الشحن التي ترسلها، ومعلومات المحفظة والنقاط والمعاملات المرتبطة بها.\n\n3. استخدام المعلومات\nتُستخدم هذه المعلومات لتقديم خدمات المتجر، معالجة الطلبات والدفع والشحن، تقديم الدعم الفني وتحسين الخدمة.\n\n4. عمليات الدفع\nأنت مسؤول عن التأكد من صحة بيانات الدفع والبيانات التي تقدمها قبل إرسال الطلب. لا ترسل كلمات المرور أو المعلومات الحساسة إلا عند الضرورة الفعلية للخدمة.\n\n5. الطلبات\nتأكد من صحة بيانات اللعبة والحساب قبل تأكيد الطلب، وقد تبدأ المعالجة بعد إرسال الطلب.\n\n6. المحفظة والنقاط\nأرصدة المحفظة والنقاط مرتبطة بحساب Telegram، ويمنع استغلال النظام أو إجراء عمليات وهمية أو متكررة للحصول على رصيد أو نقاط بشكل غير مشروع.\n\n7. الإحالات والمكافآت\nيمنع استخدام الحسابات الوهمية أو أي وسيلة للتحايل على نظام الإحالات والمكافآت. رابط الإحالة يُحتسب للمستخدم الجديد عند أول تشغيل فقط، ولا يمكن تغيير المحيل بعد ذلك.\n\n8. الدعم الفني\nيُستخدم الدعم للاستفسارات والمشاكل المتعلقة بالخدمة، ويمنع استخدامه للإزعاج أو إرسال طلبات متكررة أو غير متعلقة بالخدمة.\n\n9. إيقاف الخدمة\nيحتفظ المتجر بحق رفض أو إيقاف أي طلب يخالف الشروط أو يشتبه في وجود تلاعب أو إساءة استخدام.\n\n10. الخصوصية\nنحترم خصوصيتك ولا نستخدم المعلومات التي يتم جمعها إلا للأغراض المرتبطة بتقديم خدمات المتجر وإدارة الطلبات والدعم.\n\n11. الموافقة\nباستخدامك للبوت وإتمام أي عملية، فإنك تؤكد أنك قرأت هذه الشروط وسياسة الخصوصية ووافقت عليها.'
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

STORE_TZ = ZoneInfo("Africa/Algiers")
DEFAULT_OPEN_MESSAGE = "🟢 تم فتح متجر SERADJ STORE!\nتقدروا الآن تطلبوا خدماتكم بكل سهولة 🛍️"
DEFAULT_CLOSE_MESSAGE = "🔴 تم غلق متجر SERADJ STORE مؤقتًا.\nتقدروا تتصفحوا المتجر، والطلبات الجديدة ترجع عند الافتتاح القادم."

def store_is_open(now=None):
    """Store order availability based on Algeria local time; browsing remains enabled."""
    if get_setting("store_hours_enabled", "0") != "1":
        return True
    now = now or datetime.now(STORE_TZ)
    try:
        opening = datetime.strptime(get_setting("store_open_time", "09:00"), "%H:%M").time()
        closing = datetime.strptime(get_setting("store_close_time", "23:00"), "%H:%M").time()
    except ValueError:
        return True
    current = now.time().replace(tzinfo=None)
    if opening == closing:
        return True  # equal times means open 24 hours
    if opening < closing:
        return opening <= current < closing
    return current >= opening or current < closing  # overnight schedule

def store_closed_notice():
    return (get_setting("store_closed_notice", "🔴 المتجر مغلق حاليًا. يمكنك تصفح الخدمات، لكن الطلبات الجديدة غير متاحة حتى موعد الافتتاح.") or "🔴 المتجر مغلق حاليًا. يمكنك تصفح الخدمات، لكن الطلبات الجديدة غير متاحة حتى موعد الافتتاح.")

async def broadcast_store_transition(application, is_open):
    text = get_setting("store_open_message" if is_open else "store_close_message", DEFAULT_OPEN_MESSAGE if is_open else DEFAULT_CLOSE_MESSAGE)
    with db() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE COALESCE(is_banned,0)=0").fetchall()
    sent = 0
    for row in rows:
        try:
            await application.bot.send_message(chat_id=int(row["user_id"]), text=text)
            sent += 1
        except Exception as exc:
            logger.debug("Store status broadcast failed for %s: %s", row["user_id"], exc)
        if sent and sent % 25 == 0:
            await asyncio.sleep(1)
    logger.info("Store %s broadcast finished; delivered to %s users", "opened" if is_open else "closed", sent)

async def store_schedule_loop(application):
    """Check schedule every 20 seconds and broadcast once per transition."""
    while True:
        try:
            if get_setting("store_hours_enabled", "0") == "1":
                now = datetime.now(STORE_TZ)
                state = "open" if store_is_open(now) else "closed"
                previous = get_setting("store_last_state", "")
                if previous and previous != state:
                    await broadcast_store_transition(application, state == "open")
                set_setting("store_last_state", state)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Store schedule check failed")
        await asyncio.sleep(20)

async def post_init(application):
    application.create_task(store_schedule_loop(application), name="store-schedule-loop")

CANCEL_WORDS = {
    "إلغاء", "الغاء", "❌ إلغاء", "/cancel"
}

MAIN_MENU = [
    ["📦 طلباتي"],
    ["✨ مزايا متجرنا"],
    ["👤 حسابي", "💰 تعبئة الرصيد"],
    ["🛍️ المتجر"],
    ["🎁 إشتري بنقاطي", "🎯 الإحالة والنقاط"],
    ["📞 اتصل بالإدارة", "🔐 السياسات والخصوصية"],
    ["➕ طلب لعبة غير موجودة"],
]

ADMIN_MAIN_MENU = [
    ["🛠️ لوحة التحكم"],
    ["📦 طلباتي"],
    ["✨ مزايا متجرنا"],
    ["👤 حسابي", "💰 تعبئة الرصيد"],
    ["🛍️ المتجر"],
    ["🎁 إشتري بنقاطي", "🎯 الإحالة والنقاط"],
    ["📞 اتصل بالإدارة", "🔐 السياسات والخصوصية"],
]

ADMIN_PANEL_MENU = [
["➕ إضافة", "🎮 إدارة الألعاب"],
["✨ إدارة إيموجيات Premium", "💰 تعديل الأسعار"],
["📂 إدارة البوت", "📨 إرسال إشعار"],
["🎁 إدارة متجر النقاط", "💬 مراسلة زبون"],
["💰 حدود تعبئة الرصيد"],
["👥 التحكم في الأفراد", "👥 إدارة التجار"],
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


async def dispatch_order_to_group(context, order_id, user, draft, player_id, payment_method, price, points_used=0, photo=None):
    """Send an order to the group configured for its game, falling back to admin DM."""
    game_id = int(draft.get("game_id") or 0)
    group_id = get_setting(f"order_group_{game_id}", "").strip()
    if not group_id:
        group_id = str(ADMIN_ID) if ADMIN_ID else ""
    if not group_id:
        logger.warning("No order group/admin configured for order %s", order_id)
        return
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 استلام الطلب", callback_data=f"order_claim:{order_id}")]])
    caption = (f"🆕 طلب جديد #{order_id}\n\n👤 الزبون: {user.full_name}\n🆔 Telegram ID: {user.id}\n"
               f"🎮 الخدمة: {draft.get('game_name','غير محددة')}\n📦 العرض: {draft.get('offer_name','غير محدد')}\n"
               f"📋 معلومات الشحن: {player_id or 'لا تتطلب'}\n📱 الجهاز: {draft.get('platform') or 'غير محدد'}\n"
               f"💰 السعر: {price} DA\n🎁 النقاط المستخدمة: {points_used}\n💳 الدفع: {payment_method}\n📌 الحالة: قيد الانتظار")
    try:
        if photo:
            await context.bot.send_photo(chat_id=int(group_id), photo=photo.file_id, caption=caption, reply_markup=keyboard)
        else:
            await context.bot.send_message(chat_id=int(group_id), text=caption, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed dispatching order %s to group %s", order_id, group_id)

async def set_order_group_command(update, context):
    """In a group, admin runs /setordergroup GAME_ID to route that game's orders here."""
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔ الأمر خاص بمالك المتجر.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await update.effective_message.reply_text("استعمل هذا الأمر داخل القروب الذي تريد استقبال الطلبات فيه: /setordergroup GAME_ID")
        return
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("استعمال الأمر: /setordergroup GAME_ID\nمثال: /setordergroup 1")
        return
    game_id = int(context.args[0])
    with db() as conn:
        game = conn.execute("SELECT name FROM games WHERE id=?", (game_id,)).fetchone()
        if not game:
            await update.effective_message.reply_text("❌ ما لقيتش لعبة بهذا الرقم. شوف أرقام الألعاب بالأمر /ordergames في الخاص.")
            return
        conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (f"order_group_{game_id}", str(chat.id)))
    await update.effective_message.reply_text(f"✅ تم ربط {game['name']} بهذا القروب. الطلبات الجديدة لهذه اللعبة ستصل هنا.")

async def order_games_command(update, context):
    if not is_admin(update.effective_user.id):
        return
    with db() as conn:
        rows = conn.execute("SELECT id,name FROM games WHERE active=1 ORDER BY id").fetchall()
    text = "🎮 أرقام الألعاب لربط القروبات:\n" + ("\n".join(f"{r['id']} — {r['name']}" for r in rows) if rows else "لا توجد ألعاب مفعلة.")
    await update.effective_message.reply_text(text + "\n\nداخل القروب اكتب: /setordergroup رقم_اللعبة")


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


def tiktok_quantity_limits():
    """Return configured TikTok custom quantity limits, with safe defaults."""
    try:
        minimum = int(get_setting("tiktok_min_quantity", "200"))
        maximum = int(get_setting("tiktok_max_quantity", "99999"))
        if minimum < 1 or maximum < minimum:
            raise ValueError
        return minimum, maximum
    except (TypeError, ValueError):
        return 200, 99999


def tiktok_coin_price(method, user_id):
    """Return TikTok coin unit price for payment method and customer type."""
    trader = is_trader(user_id)
    method_key = "flexy" if method == "flexy" else "baridi"
    tier = "trader" if trader else "retail"
    key = f"tiktok_coin_price_{tier}_{method_key}"
    value = get_setting(key, "")
    # Backward compatibility: the old single price becomes retail Baridi price.
    if not value and tier == "retail" and method_key == "baridi":
        value = get_setting("tiktok_coin_price", "0")
    try:
        price = Decimal(value or "0")
        return price if price.is_finite() and price > 0 else Decimal("0")
    except (InvalidOperation, ValueError):
        return Decimal("0")


def is_admin(user_id):
    return user_id == ADMIN_ID and ADMIN_ID != 0


def main_keyboard(user_id):
    if is_admin(user_id):
        keyboard = ADMIN_MAIN_MENU
    else:
        keyboard = [row[:] for row in MAIN_MENU]
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
            phone_number TEXT DEFAULT '',
            is_banned INTEGER DEFAULT 0,
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
            platform_mode TEXT DEFAULT 'none',
            category TEXT DEFAULT 'game'
        );
        CREATE TABLE IF NOT EXISTS recharge_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            method_type TEXT NOT NULL DEFAULT 'id',
            prompt TEXT DEFAULT '',
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            recharge_method_id INTEGER,
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
        CREATE TABLE IF NOT EXISTS point_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            points_cost INTEGER NOT NULL DEFAULT 1,
            stock INTEGER DEFAULT -1,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS point_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            offer_id INTEGER NOT NULL,
            points_cost INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS game_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            request_text TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS referrals (
            referred_user_id INTEGER PRIMARY KEY,
            referrer_user_id INTEGER NOT NULL,
            points_awarded INTEGER DEFAULT 0,
            created_at TEXT DEFAULT ''
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
        CREATE TABLE IF NOT EXISTS trader_loan_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
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
        # Safe migrations for group order claiming; preserves existing orders.
        for column, definition in (("claimed_by", "INTEGER DEFAULT 0"), ("claimed_name", "TEXT DEFAULT ''")):
            try:
                conn.execute(f"ALTER TABLE orders ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError:
                pass

        # Safe migrations for older databases.
        migrations = {
            "users": {
                "account_type": "TEXT DEFAULT 'customer'",
                "trader_requested": "INTEGER DEFAULT 0",
                "phone_number": "TEXT DEFAULT ''",
                "is_banned": "INTEGER DEFAULT 0",
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
                "category": "TEXT DEFAULT 'game'",
            },
            "offers": {
                "recharge_method_id": "INTEGER",
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
        # Repair older databases where applications were saved with the default category='game'.
        # Include common apps/services, using normalized lowercase names and preserving game titles.
        conn.execute("""
            UPDATE games SET category='app'
            WHERE lower(trim(name)) IN (
                'tiktok','tik tok','snapchat+','snapchat plus','netflix','azar',
                'app store','apple store','telegram premium','telegram','spotify',
                'youtube premium','youtube','instagram','facebook','discord',
                'capcut','chatgpt','canva','shahid','osn+','crunchyroll',
                'imo','tinder','truecaller','google play','google play gift card'
            )
            AND (category IS NULL OR trim(category)='' OR category='game')
        """)
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('facebook_url', '')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('telegram_url', '')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("privacy_policy", TERMS_PRIVACY_TEXT))
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("terms_policy", TERMS_PRIVACY_TEXT))
        # Replace only the earlier built-in placeholder texts, preserving any admin-customized values.
        conn.execute("UPDATE settings SET value=? WHERE key='privacy_policy' AND value=?", (TERMS_PRIVACY_TEXT, 'نحترم خصوصيتك. تُستخدم بياناتك فقط لمعالجة الطلبات والتواصل بشأنها. لا تشارك كلمات مرورك إلا عند الضرورة للخدمة المطلوبة، وتجنب إرسال معلومات لا تخص الطلب. يمكنك التواصل مع الإدارة للاستفسار أو طلب حذف بياناتك.'))
        conn.execute("UPDATE settings SET value=? WHERE key='terms_policy' AND value=?", (TERMS_PRIVACY_TEXT, 'باستخدامك SERADJ STORE فأنت توافق على مراجعة تفاصيل العرض والسعر قبل الطلب. قد تتطلب الطلبات إثبات الدفع، وتخضع المعالجة لتوفر الخدمة وتأكيد الإدارة. لا يمكن ضمان إلغاء الطلب بعد بدء تنفيذه.'))
        # Create one legacy recharge method per existing game and attach old offers to it.
        for g in conn.execute("SELECT id, name, recharge_method, player_prompt FROM games").fetchall():
            exists = conn.execute("SELECT id FROM recharge_methods WHERE game_id=? LIMIT 1", (g["id"],)).fetchone()
            if not exists:
                old_type = g["recharge_method"] if g["recharge_method"] in ("id", "login", "none") else "id"
                title = {"id": "الشحن بالـ ID", "login": "الشحن بتسجيل الدخول", "none": "اشتراك بدون معلومات"}.get(old_type, "الشحن بالـ ID")
                cur = conn.execute("INSERT INTO recharge_methods (game_id,title,method_type,prompt,active) VALUES (?,?,?,?,1)", (g["id"], title, old_type, g["player_prompt"] or ""))
                conn.execute("UPDATE offers SET recharge_method_id=? WHERE game_id=? AND recharge_method_id IS NULL", (cur.lastrowid, g["id"]))
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('whatsapp_number', ?)", (WHATSAPP_NUMBER,))


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


def deposit_limits(account_type, method):
    prefix = "trader" if account_type == "trader" else "customer"
    method = "flexy" if method == "flexy" else "baridi"
    try:
        minimum = int(get_setting(f"deposit_{prefix}_{method}_min", "100"))
        maximum = int(get_setting(f"deposit_{prefix}_{method}_max", "1000000"))
    except (TypeError, ValueError):
        minimum, maximum = 100, 1000000
    return minimum, maximum


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


def get_user_row(user_id):
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def contact_request_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 مشاركة رقمي", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def offer_contact_message(message):
    """Offer phone sharing as an optional convenience; never block bot usage."""
    await message.reply_text(
        "📱 تقدر تشارك رقم هاتفك إذا حبيت لتسهيل التواصل، وهذا اختياري.",
        reply_markup=contact_request_keyboard(),
    )


async def admin_show_people(message, banned=False):
    with db() as conn:
        rows = conn.execute(
            "SELECT user_id, username, full_name, phone_number, is_banned, account_type, balance "
            "FROM users WHERE COALESCE(is_banned,0)=? ORDER BY user_id DESC LIMIT 30",
            (1 if banned else 0,),
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM users WHERE COALESCE(is_banned,0)=?", (1 if banned else 0,)).fetchone()[0]
    buttons = []
    for row in rows:
        label = row["full_name"] or (("@"+row["username"]) if row["username"] else str(row["user_id"]))
        kind = "تاجر" if row["account_type"] == "trader" else "زبون"
        balance = int(row["balance"] or 0)
        buttons.append([InlineKeyboardButton(
            f"{kind} | {label} | {balance} DA | ID:{row['user_id']}"[:60],
            callback_data=f"person_view:{row['user_id']}",
        )])
    buttons.append([InlineKeyboardButton("🔎 البحث بالاسم أو ID", callback_data="person_search")])
    buttons.append([InlineKeyboardButton("🚫 المحظورون" if not banned else "👥 المشتركين النشطون",
                                          callback_data="people_banned" if not banned else "people_active")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
    title = "🚫 قائمة المحظورين" if banned else "👥 المشتركين النشطون"
    await message.reply_text(f"{title} — العدد: {total}\n\nكل زر يعرض نوع الحساب والاسم والرصيد وID. اضغط على الشخص لإدارة رصيده ودينه وحظره أو حذف حسابه.\nيعرض هنا آخر 30 حسابًا؛ استعمل البحث للوصول إلى غيرهم.",
                             reply_markup=InlineKeyboardMarkup(buttons))


async def admin_person_card(query, target_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (target_id,)).fetchone()
        orders = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (target_id,)).fetchone()[0]
    if not row:
        await query.edit_message_text("❌ المشترك غير موجود.")
        return
    username = "@" + row["username"] if row["username"] else "غير متوفر"
    phone = row["phone_number"] if "phone_number" in row.keys() and row["phone_number"] else "غير مشارك"
    banned = int(row["is_banned"] or 0) if "is_banned" in row.keys() else 0
    buttons = [
        [InlineKeyboardButton("💰 إضافة رصيد", callback_data=f"person_balance:{target_id}")],
        [InlineKeyboardButton("✏️ تعديل الرصيد", callback_data=f"person_balance_edit:{target_id}")],
    ]
    if row["account_type"] == "trader":
        buttons.append([InlineKeyboardButton("💵 منح سلفية للتاجر", callback_data=f"person_loan_grant:{target_id}")])
        buttons.append([InlineKeyboardButton("✏️ تعديل الدين", callback_data=f"person_debtedit:{target_id}")])
        buttons.append([InlineKeyboardButton("🧹 تصفير الدين", callback_data=f"person_debtzero:{target_id}")])
    buttons += [
        [InlineKeyboardButton("🔓 إلغاء الحظر" if banned else "🚫 حظر المشترك",
                              callback_data=f"person_unban:{target_id}" if banned else f"person_ban:{target_id}")],
        [InlineKeyboardButton("🗑️ حذف الحساب", callback_data=f"person_delete_confirm:{target_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="people_active" if not banned else "people_banned")],
    ]
    await query.edit_message_text(
        f"👤 معلومات المشترك\n\nالاسم: {row['full_name'] or 'غير متوفر'}\n"
        f"Username: {username}\nTelegram ID: {target_id}\nالهاتف: {phone}\n"
        f"نوع الحساب: {'تاجر' if row['account_type']=='trader' else 'زبون'}\n"
        f"الحالة: {'🚫 محظور' if banned else '🟢 نشط'}\n"
        f"الرصيد: {int(row['balance'] or 0)} DA\n"
        + (f"💳 الدين الحالي: {int(row['credit_debt'] or 0)} DA\n" if row['account_type'] == 'trader' else "")
        + f"🎁 نقاط المكافآت: {int(row['points'] or 0)} نقطة\n"
        f"عدد الطلبات: {orders}\n"
        f"تاريخ التسجيل: {row['created_at'] or 'غير معروف'}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


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

    # While the store is closed, customers cannot enter or browse the bot.
    if not is_admin(user.id) and not store_is_open():
        await update.message.reply_text(store_closed_notice())
        return

    # Referral payload is processed once per newly referred account.
    payload = (context.args[0] if context.args else "")
    if payload.startswith("ref_"):
        try:
            referrer_id = int(payload[4:])
        except ValueError:
            referrer_id = 0
        if referrer_id and referrer_id != user.id:
            with db() as conn:
                existing_ref = conn.execute("SELECT referred_user_id FROM referrals WHERE referred_user_id=?", (user.id,)).fetchone()
                referrer_exists = conn.execute("SELECT user_id FROM users WHERE user_id=?", (referrer_id,)).fetchone()
                if not existing_ref and referrer_exists:
                    conn.execute("INSERT INTO referrals (referred_user_id, referrer_user_id, points_awarded, created_at) VALUES (?, ?, 50, ?)", (user.id, referrer_id, now_text()))
                    conn.execute("UPDATE users SET points=COALESCE(points,0)+50 WHERE user_id=?", (referrer_id,))
                    try:
                        await context.bot.send_message(referrer_id, "🎉 انضم مشترك جديد عبر رابط إحالتك! تمت إضافة 50 نقطة إلى حسابك.")
                    except Exception:
                        logger.info("Could not notify referrer %s", referrer_id)

    context.user_data.clear()
    saved = get_user_row(user.id)
    if not is_admin(user.id) and saved and "is_banned" in saved.keys() and int(saved["is_banned"] or 0):
        await update.message.reply_text("🚫 حسابك محظور من استعمال البوت. تواصل مع الإدارة.")
        return

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


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    contact = message.contact if message else None
    if not user or not contact:
        return
    if not is_admin(user.id) and not store_is_open():
        await message.reply_text(store_closed_notice())
        return
    if contact.user_id != user.id:
        await message.reply_text("❌ يجب مشاركة رقمك باستخدام زر Telegram الرسمي، وليس رقم شخص آخر.",
                                 reply_markup=contact_request_keyboard())
        return
    with db() as conn:
        conn.execute("UPDATE users SET phone_number=?, username=?, full_name=? WHERE user_id=?",
                     (contact.phone_number, user.username or "", user.full_name or "", user.id))
    await message.reply_text("✅ تم حفظ رقم هاتفك بنجاح. يمكنك الآن استعمال البوت.",
                             reply_markup=main_keyboard(user.id))


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


def premium_emoji_id(game_id):
    """Return the configured custom emoji ID when enabled for a game."""
    if get_setting(f"premium_emoji_enabled_{game_id}", "1") != "1":
        return ""
    return get_setting(f"premium_emoji_id_{game_id}", "").strip()


def premium_button_kwargs(game_id):
    emoji_id = premium_emoji_id(game_id)
    return {"icon_custom_emoji_id": emoji_id} if emoji_id else {}


def game_button_label(game):
    """Use the Premium button icon instead of the original creation emoji."""
    custom_id = premium_emoji_id(game["id"])
    return game["name"] if custom_id else f"{game['emoji']} {game['name']}"


# ====== عرض المتجر ======

async def show_store(message, user_id, category=None):
    if category not in ("game", "app"):
        await message.reply_text("اختر زر 🎮 الألعاب أو 📱 التطبيقات من القائمة الرئيسية.", reply_markup=main_keyboard(user_id))
        return
    with db() as conn:
        if category == "app":
            games = conn.execute("""
                SELECT * FROM games
                WHERE active=1 AND (
                    lower(trim(COALESCE(category,'')))='app'
                    OR lower(trim(name)) IN (
                        'tiktok','tik tok','snapchat+','snapchat plus','netflix','azar',
                        'app store','apple store','telegram premium','telegram','spotify',
                        'youtube premium','youtube','instagram','facebook','discord',
                        'capcut','chatgpt','canva','shahid','osn+','crunchyroll',
                        'imo','tinder','truecaller','google play','google play gift card'
                    )
                ) ORDER BY id
            """).fetchall()
        else:
            games = conn.execute("SELECT * FROM games WHERE active=1 AND COALESCE(NULLIF(trim(category),''),'game')='game' ORDER BY id").fetchall()
    if not games:
        await message.reply_text("😕 لا توجد خدمات في هذا القسم حالياً.", reply_markup=main_keyboard(user_id))
        return
    buttons = []
    for g in games:
        custom_id = premium_emoji_id(g["id"])
        # When a Premium custom emoji is configured, use it as the button icon
        # and remove the default emoji from the button text to avoid showing both.
        button_text = g["name"] if custom_id else f"{g['emoji']} {g['name']}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"game:{g['id']}", **premium_button_kwargs(g['id']))])
    buttons.append([InlineKeyboardButton("🔙 الأقسام", callback_data="back_main")])
    title = "🎮 قائمة الألعاب:" if category == "game" else "📱 قائمة التطبيقات:"
    lines = [title, ""]
    for g in games:
        # Send the store list as plain text: names and custom-emoji HTML tags can
        # otherwise trigger Telegram's Entity_text_invalid error.
        icon = g['emoji'] or "🎮"
        safe_name = str(g["name"] or "")
        lines.append(f"{icon} {safe_name}")
    await message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


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
        f"💰 رصيد المحفظة: {int(user['balance'] or 0)} DA\n"
        f"🎁 نقاط المكافآت: {int(user['points'] or 0)} نقطة\n"
        f"📅 التسجيل: {user['created_at']}",
        reply_markup=main_keyboard(user_id),
        )

# ====== عرض عروض اللعبة ======

async def open_game(query, game_id, platform=None, recharge_method_id=None):
    user_id = query.from_user.id
    game = get_game(game_id)

    if not game or not game["active"]:
        await query.edit_message_text(
            "❌ هذه الخدمة غير متاحة حالياً."
        )
        return

    game_category = (game["category"] if "category" in game.keys() else "game") or "game"
    category_back = "back_apps" if game_category == "app" else "back_games"
    mode = game["platform_mode"] if "platform_mode" in game.keys() else "none"
    if mode == "both" and platform is None:
        await query.edit_message_text(
            f"📱 اختر نوع الهاتف لخدمة {game['name']}: ",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Android", callback_data=f"platform:{game_id}:android")],
                [InlineKeyboardButton("🍎 iPhone (iOS)", callback_data=f"platform:{game_id}:ios")],
                [InlineKeyboardButton("🔙 رجوع", callback_data=category_back)],
            ]),
        )
        return
    if mode in ("android", "ios"):
        platform = mode
    if mode == "none":
        platform = None

    with db() as conn:
        methods = conn.execute("SELECT * FROM recharge_methods WHERE game_id=? AND active=1 ORDER BY id", (game_id,)).fetchall()
    if recharge_method_id is None and methods:
        buttons = [[InlineKeyboardButton(f"🔀 {m['title']}", callback_data=f"recharge_select:{game_id}:{m['id']}:{platform or 'none'}")] for m in methods]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=category_back)])
        await query.edit_message_text(f"{game['emoji']} {game['name']}\n\nاختر طريقة الشحن:", reply_markup=InlineKeyboardMarkup(buttons))
        return
    selected_method = next((m for m in methods if int(m["id"]) == int(recharge_method_id)), None) if recharge_method_id is not None else (methods[0] if methods else None)
    if not selected_method:
        await query.edit_message_text("لا توجد طريقة شحن مفعلة لهذه الخدمة."); return
    context_method_id = int(selected_method["id"])
    offers = [o for o in get_offers(game_id) if o["recharge_method_id"] is not None and int(o["recharge_method_id"]) == context_method_id]
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
                f"{offer['name']} | 💳 {offer_price(offer, 'baridi', user_id)} DA | 📱 {offer_price(offer, 'flexy', user_id)} DA",
                callback_data=(
                    f"offer:{game_id}:{offer['id']}:{platform or 'none'}"
                ),
            )
        ])

    # TikTok: let the customer request a custom coin quantity in addition to preset offers.
    if (game["name"] or "").strip().lower() == "tiktok":
        tiktok_min, tiktok_max = tiktok_quantity_limits()
        buttons.append([
            InlineKeyboardButton(
                f"✏️ اختيار كمية أخرى ({tiktok_min:,}–{tiktok_max:,})",
                callback_data=f"tiktok_custom:{game_id}:{context_method_id}:{platform or 'none'}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 رجوع",
            callback_data=f"game_back:{game_id}:{platform or 'none'}",
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            "🎮 اختيار لعبة أخرى",
            callback_data=category_back,
        )
    ])

    await query.edit_message_text(
        f"{game['emoji']} {game['name']}\n\n"
        f"{description + chr(10) + chr(10) if description else ''}"
        f"📱 الجهاز: {'Android' if platform == 'android' else 'iPhone (iOS)' if platform == 'ios' else 'غير مطلوب'}\n"
        "اختر العرض المناسب:\n"
        f"💳 BaridiMob / CCP و 📱 Flexy — الأسعار حسب فئتك ({'تاجر' if is_trader(user_id) else 'زبون عادي'}).",
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

    buttons = []
    if get_setting("payment_baridi_enabled", "1") == "1":
        buttons.append([InlineKeyboardButton(
            f"💳 BaridiMob / CCP — {offer_price(offer, 'baridi', user_id)} DA",
            callback_data=f"pay:{game_id}:{offer_id}:baridi",
        )])
    if get_setting("payment_flexy_enabled", "1") == "1":
        buttons.append([InlineKeyboardButton(
            f"📱 Flexy — {offer_price(offer, 'flexy', user_id)} DA",
            callback_data=f"pay:{game_id}:{offer_id}:flexy",
        )])
    buttons += [
        [InlineKeyboardButton(
            f"🎁 استخدام النقاط: {'مفعّل' if context and context.user_data.get('use_points_for_order') else 'غير مفعّل'}",
            callback_data=f"points_toggle:{game_id}:{offer_id}:{platform or 'none'}",
        )],
        [InlineKeyboardButton("💰 الدفع من رصيد المحفظة", callback_data=f"pay:{game_id}:{offer_id}:balance")],
        [
            InlineKeyboardButton(
                "🔙 رجوع للعروض",
                callback_data=f"recharge_select:{game_id}:{int(offer['recharge_method_id'])}:{platform or 'none'}",
            )
        ],
    ]

    await query.edit_message_text(
        "🛍️ تفاصيل العرض\n\n"
        f"🎮 اللعبة: {game['name']}\n"
        f"📦 العرض: {offer['name']}\n"
        f"📱 الجهاز: {'Android' if platform == 'android' else 'iPhone (iOS)' if platform == 'ios' else 'غير مطلوب'}\n\n"
        + (f"💳 BaridiMob / CCP: {offer_price(offer, 'baridi', user_id)} DA\n" if get_setting("payment_baridi_enabled", "1") == "1" else "")
        + (f"📱 Flexy: {offer_price(offer, 'flexy', user_id)} DA\n" if get_setting("payment_flexy_enabled", "1") == "1" else "")
        + f"🏷️ فئة السعر: {'تاجر' if is_trader(user_id) else 'زبون عادي'}\n\nاختر طريقة الدفع:",
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
    if not store_is_open() and not is_admin(query.from_user.id):
        await query.answer(store_closed_notice(), show_alert=True)
        return
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

    if method in ("baridi", "flexy") and get_setting(f"payment_{method}_enabled", "1") != "1":
        await query.edit_message_text("❌ طريقة الدفع هذه غير متاحة حالياً. اختر طريقة أخرى.")
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
            await query.edit_message_text(f"❌ سقف القرض لا يكفي لهذا الطلب.\nسقف القرض: {limit_amount} DA\nالدين الحالي: {debt} DA\nالسعر: {price} DA\nالمتاح: {max(0, limit_amount-debt)} DA")
            return
        method_name = "قرض التاجر"
        details = f"الدين الحالي: {debt} DA\nالمتاح من سقف القرض: {limit_amount-debt} DA\nأجل التسديد: {term_days} يومًا"
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
                f"❌ رصيدك غير كافٍ.\nالسعر: {price} DA\nرصيد المحفظة: {balance} DA\nالنقاط: {available_points}\n\nاضغط تعبئة الرصيد من القائمة الرئيسية ثم أعد الطلب."
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
            details += f"\n🎁 خصم النقاط: {points_used} DA"

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

    with db() as conn:
        selected_method = conn.execute("SELECT * FROM recharge_methods WHERE id=?", (offer["recharge_method_id"],)).fetchone() if "recharge_method_id" in offer.keys() and offer["recharge_method_id"] else None
    custom_prompt = ((selected_method["prompt"] if selected_method else game["player_prompt"]) or "").strip()
    recharge_method = selected_method["method_type"] if selected_method else (game["recharge_method"] if "recharge_method" in game.keys() else "id")
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
        f"🔀 طريقة الشحن: {selected_method['title'] if selected_method else 'الطريقة الافتراضية'}\n"
        f"💳 الدفع: {method_name}\n"
        f"💰 السعر: {price} DA\n\n"
        f"💳 معلومات الدفع:\n{details}\n\n"
        f"{prompt}\n\nللإلغاء أرسل /cancel"
    )


# ====== إنشاء طلب مدفوع من المحفظة ======
async def create_wallet_order(message, context, player_id, user=None):
    user = user or message.from_user
    if not store_is_open() and not is_admin(user.id):
        context.user_data.pop("order_draft", None)
        await message.reply_text(store_closed_notice(), reply_markup=main_keyboard(user.id))
        return
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
    await dispatch_order_to_group(context, order_id, user, draft, player_id, "رصيد المحفظة", price, points_used)
    context.user_data.pop("order_draft", None)
    context.user_data.pop("pending_player_id", None)
    context.user_data.pop("awaiting_player_id", None)
    await message.reply_text(f"✅ تم تسجيل طلبك #{order_id}.\n💰 المبلغ المخصوم: {price} DA\n🎁 النقاط المستخدمة: {points_used}\nسيتم إعلامك عند تحديث الحالة.", reply_markup=main_keyboard(user.id))


async def create_credit_order(message, context, player_id, user=None):
    context.user_data.pop("order_draft", None)
    context.user_data.pop("pending_player_id", None)
    context.user_data.pop("awaiting_player_id", None)
    context.user_data.pop("awaiting_payment_receipt", None)
    await message.reply_text("⛔ نظام القروض غير متاح. اختر طريقة دفع أخرى.", reply_markup=main_keyboard((user or message.from_user).id))


# ====== إنشاء الطلب ======

async def create_order(update, context):
    user = update.effective_user
    player_id = update.message.text.strip()
    draft = context.user_data.get("order_draft")

    if not draft:
        context.user_data.pop("awaiting_player_id", None)
        context.user_data.pop("awaiting_tiktok_custom_amount", None)
        context.user_data.pop("awaiting_tiktok_custom_id", None)
        context.user_data.pop("tiktok_custom_request", None)
        context.user_data.pop("awaiting_credit_repay_amount", None)
        context.user_data.pop("awaiting_trader_loan_amount", None)
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
        f"💰 المبلغ: {draft['price']} DA\n\n"
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
    if user and not is_admin(user.id):
        row = get_user_row(user.id)
        if row and int(row["is_banned"] or 0):
            await message.reply_text("🚫 حسابك محظور من استعمال البوت.")
            return

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
    if user and not is_admin(user.id) and not store_is_open():
        await message.reply_text(store_closed_notice())
        return
    if user and not is_admin(user.id):
        row = get_user_row(user.id)
        if row and int(row["is_banned"] or 0):
            await message.reply_text("🚫 حسابك محظور من استعمال البوت.")
            return

    if context.user_data.get("awaiting_credit_receipt"):
        context.user_data.pop("awaiting_credit_receipt", None)
        context.user_data.pop("awaiting_credit_repay_amount", None)
        context.user_data.pop("credit_repay_amount", None)
        context.user_data.pop("credit_repay_method", None)
        await message.reply_text("⛔ نظام القروض وتسديدها غير متاح.", reply_markup=main_keyboard(user.id))
        return

    if False:  # مسار قديم معطّل
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
            await context.bot.send_photo(ADMIN_ID, photo.file_id, caption=f"💳 طلب تسديد قرض #{payment_id}\nالتاجر: {user.full_name}\nTelegram ID: {user.id}\nالمبلغ: {amount} DA\nطريقة الدفع: {method}\nالدين الحالي: {debt} DA", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ قبول التسديد", callback_data=f"creditpay_approve:{payment_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"creditpay_reject:{payment_id}")]]))
        context.user_data.pop("awaiting_credit_receipt", None)
        context.user_data.pop("credit_repay_amount", None)
        context.user_data.pop("credit_repay_method", None)
        await message.reply_text(f"✅ استلمنا وصل تسديد الدين #{payment_id}. سيتم تحديث الدين بعد موافقة الإدارة.", reply_markup=main_keyboard(user.id))
        return

    if context.user_data.get("awaiting_deposit_receipt"):
        amount = int(context.user_data.get("deposit_amount", 0))
        method = context.user_data.get("deposit_method", "")
        if not method:
            context.user_data.pop("awaiting_deposit_receipt", None)
            await message.reply_text("❌ انتهت جلسة التعبئة. ابدأ من جديد.")
            return
        method_key = "flexy" if "flexy" in method.lower() else "baridi"
        account_type = "trader" if is_trader(user.id) else "customer"
        minimum, maximum = deposit_limits(account_type, method_key)
        if amount < minimum or amount > maximum:
            context.user_data.pop("awaiting_deposit_receipt", None)
            context.user_data.pop("deposit_amount", None)
            context.user_data.pop("deposit_method", None)
            await message.reply_text(f"❌ مبلغ التعبئة خارج الحدود المسموحة ({minimum} إلى {maximum} DA). ابدأ من جديد.")
            return
        photo = message.photo[-1]
        with db() as conn:
            cur = conn.execute("INSERT INTO wallet_deposits (user_id, amount, payment_method, receipt_file_id, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", (user.id, amount, method, photo.file_id, now_text()))
            deposit_id = cur.lastrowid
        if ADMIN_ID:
            try:
                await context.bot.send_photo(ADMIN_ID, photo.file_id,
                    caption=f"💰 طلب تعبئة رصيد #{deposit_id}\nالزبون: {user.full_name}\nTelegram ID: {user.id}\nالمبلغ: {amount} DA\nطريقة الدفع: {method}\nالحالة: قيد المراجعة",
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
    if not store_is_open() and not is_admin(user.id):
        context.user_data.pop("awaiting_payment_receipt", None)
        context.user_data.pop("order_draft", None)
        context.user_data.pop("pending_player_id", None)
        await message.reply_text(store_closed_notice(), reply_markup=main_keyboard(user.id))
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

    # Send the order to its configured product group (or admin fallback).
    await dispatch_order_to_group(context, order_id, user, draft, player_id, draft["method"], draft["price"], int(draft.get("points_used", 0)), photo=photo)

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
        f"💰 المبلغ: {draft['price']} DA\n"
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
            f"💰 السعر: {order['price']} DA\n"
            f"📌 الحالة: {status_label(order['status'])}\n"
            f"🕒 التاريخ: {order['created_at']}\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=main_keyboard(user_id),
    )


async def show_points_shop(message, user_id):
    with db() as conn:
        user_row = conn.execute("SELECT points FROM users WHERE user_id=?", (user_id,)).fetchone()
        offers = conn.execute("SELECT * FROM point_offers WHERE active=1 ORDER BY id").fetchall()
    points = int(user_row["points"] or 0) if user_row else 0
    buttons = [[InlineKeyboardButton(f"🎁 {o['title']} — {o['points_cost']} نقطة" + (f" (المتبقي {o['stock']})" if int(o['stock'] or -1) >= 0 else ""), callback_data=f"points_buy:{o['id']}")] for o in offers if int(o['stock'] if o['stock'] is not None else -1) != 0]
    buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")])
    text = f"🎁 متجر النقاط\nرصيدك: {points} نقطة\n\n" + ("\n".join(f"• {o['title']}: {o['description']}" for o in offers) if offers else "لا توجد عروض بالنقاط حالياً.")
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


def contact_admin_keyboard():
    rows = []
    wa = get_setting("whatsapp_number", WHATSAPP_NUMBER).strip().replace("+", "").replace(" ", "")
    tg = get_setting("telegram_url", os.getenv("TELEGRAM_URL", "")).strip()
    fb = get_setting("facebook_url", os.getenv("FACEBOOK_URL", "")).strip()
    if wa:
        rows.append([InlineKeyboardButton("💬 WhatsApp", url=f"https://wa.me/{wa}")])
    if tg.startswith(("https://t.me/", "https://telegram.me/")):
        rows.append([InlineKeyboardButton("✈️ Telegram", url=tg)])
    if fb.startswith("https://"):
        rows.append([InlineKeyboardButton("📘 Facebook", url=fb)])
    if not rows:
        rows.append([InlineKeyboardButton("⚠️ حسابات التواصل غير مضبوطة", callback_data="contact_unset")])
    return InlineKeyboardMarkup(rows)


# =========================
# زر التواصل عبر واتساب
# =========================

def wa_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 التواصل عبر WhatsApp",
                url=f"https://wa.me/{get_setting('whatsapp_number', WHATSAPP_NUMBER).replace('+', '').replace(' ', '')}",
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
                game_button_label(game),
                callback_data=f"add_offer_game:{game['id']}",
                **premium_button_kwargs(game['id']),
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
    """قائمة مختصرة: اضغط على التطبيق لفتح لوحة التحكم الخاصة به."""
    with db() as conn:
        games = conn.execute("SELECT * FROM games ORDER BY CASE WHEN lower(COALESCE(category,''))='app' THEN 0 ELSE 1 END, name COLLATE NOCASE").fetchall()

    buttons = []
    for game in games:
        state = "🟢" if game["active"] else "🔴"
        buttons.append([InlineKeyboardButton(
            f"{state} [ID: {game['id']}] {game_button_label(game)}",
            callback_data=f"game_manage:{game['id']}",
            **premium_button_kwargs(game['id']),
        )])
    buttons.append([InlineKeyboardButton("🔄 تحديث", callback_data="adm_games")])
    buttons.append([InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")])
    await query.edit_message_text(
        "🎮 <b>إدارة الألعاب والتطبيقات</b>\n\n"
        "اضغط على اسم أي لعبة أو تطبيق لفتح خيارات التحكم: التفعيل، الاسم، الأجهزة، طرق الشحن والأسعار، الوصف، ورسالة طلب المعلومات.",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons),
    )


async def admin_game_manage(query, game_id):
    with db() as conn:
        game = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
    if not game:
        await query.answer("اللعبة أو التطبيق غير موجود.", show_alert=True)
        return
    state = "🟢 مفعّل" if game["active"] else "🔴 متوقف"
    method = game["recharge_method"] if "recharge_method" in game.keys() else "id"
    method_label = {"id": "ID اللاعب", "login": "إيميل وكلمة سر", "none": "بدون معلومات شحن"}.get(method, "ID اللاعب")
    platform = game["platform_mode"] if "platform_mode" in game.keys() else "none"
    buttons = [
        [InlineKeyboardButton(("⏸️ إيقاف" if game["active"] else "🟢 تفعيل"), callback_data=f"game_toggle:{game_id}")],
        [InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"game_rename:{game_id}")],
        [InlineKeyboardButton(f"📱 الأجهزة: {platform} (تغيير)", callback_data=f"game_platform:{game_id}")],
        [InlineKeyboardButton(f"🔀 طرق الشحن والأسعار ({method_label})", callback_data=f"game_methods:{game_id}")],
        [InlineKeyboardButton("📝 تعديل الوصف", callback_data=f"game_desc:{game_id}"), InlineKeyboardButton("✏️ رسالة طلب المعلومات", callback_data=f"game_prompt:{game_id}")],
        [InlineKeyboardButton("🗑️ حذف التطبيق/اللعبة", callback_data=f"game_delete:{game_id}")],
        [InlineKeyboardButton("🔙 قائمة الألعاب والتطبيقات", callback_data="adm_games")],
    ]
    await query.edit_message_text(f"⚙️ <b>إدارة {game_button_label(game)}</b>\n🆔 GAME_ID: <code>{game_id}</code>\nالحالة: {state}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


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
            SELECT offers.id, offers.name, offers.price_baridi, offers.price_flexy, offers.active, offers.android_active, offers.ios_active, offers.reward_points, recharge_methods.title AS method_title
            FROM offers LEFT JOIN recharge_methods ON recharge_methods.id=offers.recharge_method_id
            WHERE offers.game_id = ?
            ORDER BY offers.id
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
                f"{state} [ID: {offer['id']}] {offer['name']} — {offer['method_title'] or 'طريقة قديمة'}",
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
                game_button_label(game),
                callback_data=f"offers_game:{game['id']}",
                **premium_button_kwargs(game['id']),
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
        f"💰 السعر: {order['price']} DA\n"
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
    lines = [f"👤 <b>{user['full_name'] or user['username'] or target_id}</b>", f"🆔 ID: <code>{target_id}</code>", f"🏷️ نوع الحساب: {'تاجر' if user['account_type']=='trader' else 'زبون عادي'}", f"🧾 عدد الطلبات: {totals['n']}", f"💰 مجموع الطلبات غير المرفوضة: {totals['all_total']} DA", f"✅ مجموع المكتمل: {totals['completed_total']} DA", f"⏳ مجموع المعلّق/قيد التنفيذ: {totals['active_total']} DA"]
    lines.append("\n<b>آخر الطلبات:</b>")
    for order in orders:
        lines.append(f"\n🧾 #{order['id']} — {order['game_name'] or 'خدمة محذوفة'} / {order['offer_name'] or 'عرض محذوف'}\n💰 {order['price']} DA | {status_label(order['status'])}\n💳 {order['payment_method'] or 'غير محدد'} | {order['created_at'] or ''}")
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
            f"💰 قيمة الطلبات المكتملة: {r['completed_revenue']} DA"
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
        f"💰 قيمة الطلبات المكتملة: {completed_revenue} DA"
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
        f"\n\nحالة الطرق:\n🏦 BaridiMob / CCP: {'مفعّل ✅' if get_setting('payment_baridi_enabled', '1') == '1' else 'مخفي ❌'}\n📱 Flexy: {'مفعّل ✅' if get_setting('payment_flexy_enabled', '1') == '1' else 'مخفي ❌'}\n\nاختار طريقة الدفع لتعديل معلوماتها أو تغيير ظهورها للزبائن."
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
        [InlineKeyboardButton(
            f"{'🙈 إخفاء' if get_setting('payment_baridi_enabled', '1') == '1' else '👁️ إظهار'} BaridiMob / CCP",
            callback_data="pay_toggle:baridi",
        )],
        [InlineKeyboardButton(
            f"{'🙈 إخفاء' if get_setting('payment_flexy_enabled', '1') == '1' else '👁️ إظهار'} Flexy",
            callback_data="pay_toggle:flexy",
        )],
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
    data = query.data or ""
    user_id = query.from_user.id

    # Block all customer navigation while the store is closed.
    # Check before acknowledging the callback so the alert is shown reliably.
    if not is_admin(user_id) and not store_is_open():
        await query.answer(store_closed_notice(), show_alert=True)
        return
    await query.answer()

    if data == "price_menu_offers":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ هذه الخاصية للإدارة فقط.")
            return
        await query.edit_message_text(
            "💰 اختار اللعبة التي تريد تعديل عروضها:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("اختيار اللعبة", callback_data="adm_offers")], [InlineKeyboardButton("🔙 تعديل الأسعار", callback_data="price_menu_back")]])
        )
        return
    if data == "price_menu_tiktok":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ هذه الخاصية للإدارة فقط.")
            return
        values = {
            "retail_baridi": get_setting("tiktok_coin_price_retail_baridi", get_setting("tiktok_coin_price", "غير محدد")) or "غير محدد",
            "retail_flexy": get_setting("tiktok_coin_price_retail_flexy", "غير محدد") or "غير محدد",
            "trader_baridi": get_setting("tiktok_coin_price_trader_baridi", "غير محدد") or "غير محدد",
            "trader_flexy": get_setting("tiktok_coin_price_trader_flexy", "غير محدد") or "غير محدد",
        }
        await query.edit_message_text(
            "🎵 إعداد أسعار عملة TikTok\n\n"
            f"👤 زبون عادي — BaridiMob / CCP: {values['retail_baridi']} DA/كوين\n"
            f"👤 زبون عادي — Flexy: {values['retail_flexy']} DA/كوين\n"
            f"🏪 تاجر — BaridiMob / CCP: {values['trader_baridi']} DA/كوين\n"
            f"🏪 تاجر — Flexy: {values['trader_flexy']} DA/كوين\n\nاختر السعر الذي تريد تعديله:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 الزبون — BaridiMob / CCP", callback_data="tiktok_price_set:retail:baridi")],
                [InlineKeyboardButton("👤 الزبون — Flexy", callback_data="tiktok_price_set:retail:flexy")],
                [InlineKeyboardButton("🏪 التاجر — BaridiMob / CCP", callback_data="tiktok_price_set:trader:baridi")],
                [InlineKeyboardButton("🏪 التاجر — Flexy", callback_data="tiktok_price_set:trader:flexy")],
                [InlineKeyboardButton("🔙 تعديل الأسعار", callback_data="price_menu_back")],
            ])
        )
        return
    if data == "price_menu_tiktok_limits":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ هذه الخاصية للإدارة فقط.")
            return
        current_min, current_max = tiktok_quantity_limits()
        context.user_data["admin_step"] = "tiktok_min_quantity"
        context.user_data.pop("pending_tiktok_min_quantity", None)
        await query.edit_message_text(
            f"📏 حدود كمية TikTok الحالية:\nالحد الأدنى: {current_min:,} كوينز\nالحد الأقصى: {current_max:,} كوينز\n\nأرسل الحد الأدنى الجديد كعدد صحيح. بعدها سيطلب منك البوت الحد الأقصى.\nللإلغاء أرسل /cancel."
        )
        return
    if data == "price_menu_back":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ هذه الخاصية للإدارة فقط.")
            return
        await query.edit_message_text(
            "💰 تعديل الأسعار\n\nاختار نوع الأسعار التي تريد تعديلها:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 أسعار الألعاب والتطبيقات / العروض", callback_data="price_menu_offers")],
                [InlineKeyboardButton("🎵 أسعار عملة TikTok", callback_data="price_menu_tiktok")],
                [InlineKeyboardButton("📏 حدود كمية TikTok", callback_data="price_menu_tiktok_limits")],
            ])
        )
        return

    if data.startswith("tiktok_price_set:"):
        if not is_admin(user_id):
            await query.edit_message_text("⛔ هذه الخاصية للإدارة فقط.")
            return
        parts = data.split(":")
        if len(parts) != 3 or parts[1] not in ("retail", "trader") or parts[2] not in ("baridi", "flexy"):
            return
        tier, method = parts[1], parts[2]
        step = f"tiktok_coin_price_{tier}_{method}"
        key = f"tiktok_coin_price_{tier}_{method}"
        current = get_setting(key, "")
        if not current and tier == "retail" and method == "baridi":
            current = get_setting("tiktok_coin_price", "")
        context.user_data["admin_step"] = step
        tier_label = "التجزئة (الزبائن)" if tier == "retail" else "الجملة (التجار)"
        method_label = "BaridiMob / CCP" if method == "baridi" else "Flexy"
        await query.edit_message_text(
            f"🎵 سعر كوين TikTok — {tier_label} / {method_label}\n"
            f"السعر الحالي: {current or 'غير محدد'} DA للكوين الواحد.\n\n"
            "أرسل السعر الجديد للكوين الواحد بالدينار، مثال: 0.15 أو 0,15.\n"
            "للإلغاء أرسل /cancel."
        )
        return

    # تعطيل واجهات القروض وطلبات السلفية من التجار؛ منح السلفية متاح للإدارة فقط.
    if data.startswith(("loan_", "loanreq_", "creditpay_", "credit_repay_method:")) or (data.startswith("pay:") and data.endswith(":credit")):
        await query.answer("⛔ نظام القروض والسلفية غير متاح.", show_alert=True)
        return

    if not is_admin(user_id) and not store_is_open():
        await message.reply_text(store_closed_notice())
        return

    if not is_admin(user_id):
        row = get_user_row(user_id)
        if row and "is_banned" in row.keys() and int(row["is_banned"] or 0):
            await query.answer("🚫 حسابك محظور.", show_alert=True)
            return
    if data.startswith("store_category:"):
        category = data.split(":", 1)[1]
        if category not in ("game", "app"):
            await query.answer("القسم غير معروف.", show_alert=True)
            return
        # Remove the category chooser instead of leaving a permanent loading message.
        try:
            await query.message.delete()
        except Exception:
            pass
        await show_store(query.message, user_id, category)
        await query.answer()
        return

    if data == "contact_unset":
        await query.answer("اطلب من الإدارة ضبط روابط التواصل.", show_alert=True)
        return

    if data == "points_shop":
        await show_points_shop(query.message, user_id)
        return
    if data.startswith("points_buy:"):
        try:
            offer_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        with db() as conn:
            offer = conn.execute("SELECT * FROM point_offers WHERE id=? AND active=1", (offer_id,)).fetchone()
            user_row = conn.execute("SELECT points FROM users WHERE user_id=?", (user_id,)).fetchone()
            if not offer or not user_row:
                await query.answer("العرض غير متاح.", show_alert=True); return
            cost = int(offer["points_cost"] or 0)
            points = int(user_row["points"] or 0)
            stock = int(offer["stock"] if offer["stock"] is not None else -1)
            if points < cost:
                await query.answer(f"نقاطك غير كافية. تحتاج {cost} نقطة.", show_alert=True); return
            if stock == 0:
                await query.answer("نفد المخزون.", show_alert=True); return
            conn.execute("UPDATE users SET points=points-? WHERE user_id=?", (cost, user_id))
            conn.execute("INSERT INTO point_redemptions (user_id,offer_id,points_cost,status,created_at) VALUES (?,?,?,'pending',?)", (user_id, offer_id, cost, now_text()))
            if stock > 0:
                conn.execute("UPDATE point_offers SET stock=stock-1 WHERE id=?", (offer_id,))
            redemption_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if ADMIN_ID:
            try:
                await context.bot.send_message(ADMIN_ID, f"🎁 طلب شراء بالنقاط #{redemption_id}\nالمشترك: {query.from_user.full_name}\nID: {user_id}\nالعرض: {offer['title']}\nالتكلفة: {cost} نقطة", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأكيد التسليم", callback_data=f"point_redeem_done:{redemption_id}"), InlineKeyboardButton("❌ رفض وإرجاع النقاط", callback_data=f"point_redeem_reject:{redemption_id}")]]))
            except Exception: logger.exception("Could not notify admin of point redemption")
        await query.edit_message_text(f"✅ تم تسجيل طلبك #{redemption_id} للعرض «{offer['title']}» مقابل {cost} نقطة. الطلب قيد المراجعة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 متجر النقاط", callback_data="points_shop")]]))
        return
    if data.startswith("point_redeem_done:") or data.startswith("point_redeem_reject:"):
        if not is_admin(user_id):
            await query.answer("⛔ غير مسموح لك.", show_alert=True); return
        redemption_id = int(data.split(":", 1)[1]); approve = data.startswith("point_redeem_done:")
        with db() as conn:
            red = conn.execute("SELECT * FROM point_redemptions WHERE id=? AND status='pending'", (redemption_id,)).fetchone()
            if not red:
                await query.answer("تمت معالجة الطلب مسبقًا.", show_alert=True); return
            status = "completed" if approve else "rejected"
            conn.execute("UPDATE point_redemptions SET status=? WHERE id=?", (status, redemption_id))
            if not approve:
                conn.execute("UPDATE users SET points=points+? WHERE user_id=?", (int(red['points_cost']), int(red['user_id'])))
        try:
            await context.bot.send_message(int(red['user_id']), f"{'✅ تم تأكيد تسليم' if approve else '❌ تم رفض'} طلب متجر النقاط #{redemption_id}." + ("" if approve else f" تمت إعادة {red['points_cost']} نقطة إلى حسابك."))
        except Exception: pass
        await query.edit_message_text(f"تمت معالجة طلب متجر النقاط #{redemption_id}.")
        return
    if data.startswith("game_request_status:"):
        if not is_admin(user_id):
            await query.answer("⛔ غير مسموح لك.", show_alert=True); return
        _, req_id, status = data.split(":", 2); req_id=int(req_id)
        if status not in ("reviewed", "added", "rejected"): return
        with db() as conn:
            req=conn.execute("SELECT * FROM game_requests WHERE id=?",(req_id,)).fetchone()
            if not req: await query.answer("الطلب غير موجود.", show_alert=True); return
            conn.execute("UPDATE game_requests SET status=? WHERE id=?",(status,req_id))
        await query.edit_message_text(f"تم تحديث حالة طلب اللعبة #{req_id} إلى {status}.")
        try: await context.bot.send_message(req['user_id'], f"📬 تحديث طلب اللعبة #{req_id}: {status}")
        except Exception: pass
        return

    # Group members can claim a pending order; only the first claim succeeds.
    if data.startswith("order_claim:"):
        try: order_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("طلب غير صالح.", show_alert=True); return
        if query.message.chat.type not in ("group", "supergroup"):
            await query.answer("استلام الطلب متاح من قروب العمل فقط.", show_alert=True); return
        with db() as conn:
            row = conn.execute("SELECT claimed_by, status FROM orders WHERE id=?", (order_id,)).fetchone()
            if not row:
                await query.answer("الطلب غير موجود.", show_alert=True); return
            if row["status"] in ("completed", "rejected"):
                await query.answer("الطلب مغلق بالفعل.", show_alert=True); return
            if int(row["claimed_by"] or 0):
                await query.answer("هذا الطلب استلمه عضو آخر بالفعل.", show_alert=True); return
            conn.execute("UPDATE orders SET claimed_by=?, claimed_name=?, status='processing' WHERE id=? AND COALESCE(claimed_by,0)=0", (user_id, query.from_user.full_name, order_id))
            check = conn.execute("SELECT claimed_by FROM orders WHERE id=?", (order_id,)).fetchone()
            if not check or int(check["claimed_by"] or 0) != user_id:
                await query.answer("سبقك عضو آخر واستلم الطلب.", show_alert=True); return
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ إتمام الطلب", callback_data=f"order_finish:{order_id}")]])
        try: await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception: pass
        await query.answer("تم استلام الطلب باسمك!")
        await query.message.reply_text(f"📥 الطلب #{order_id} استلمه: {query.from_user.full_name}")
        return
    if data.startswith("order_finish:"):
        try: order_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("طلب غير صالح.", show_alert=True); return
        with db() as conn:
            row = conn.execute("SELECT claimed_by, status FROM orders WHERE id=?", (order_id,)).fetchone()
            if not row or int(row["claimed_by"] or 0) != user_id:
                await query.answer("فقط العضو الذي استلم الطلب يمكنه إتمامه.", show_alert=True); return
        # Reuse the existing order-status processing path to notify the customer and apply rewards.
        query.data = f"status:{order_id}:completed"
        data = query.data

    # التحقق من صلاحيات الإدارة
    admin_actions = (
        "adm_",
        "game_manage:",
        "game_toggle:",
        "game_delete:",
        "game_desc:",
        "game_prompt:",
        "game_method:",
        "offers_game:",
        "offer_toggle:",
        "offer_delete:",
        "add_offer_game:",
        "add_offer_method:",
        "game_methods:",
        "recharge_method_add:",
        "recharge_method_toggle:",
        "edit_offer:",
        "order_view:",
        "status:",
        "pay_settings:",
        "pay_toggle:",
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
        "loan_", "loanreq_", "customer_orders:", "creditpay_", "account_type_set:", "reset_data", "reset_confirm", "adm_archived_stats", "people_", "person_", "offer_price_one:", "offer_price_all:", "orders_delete_",
    )

    if data.startswith(admin_actions) and not is_admin(user_id):
        # Allow only the member who claimed this group order to finish it.
        group_finish_allowed = False
        if data.startswith("status:") and data.endswith(":completed") and query.message.chat.type in ("group", "supergroup"):
            try:
                finish_order_id = int(data.split(":")[1])
                with db() as conn:
                    claimed = conn.execute("SELECT claimed_by FROM orders WHERE id=?", (finish_order_id,)).fetchone()
                group_finish_allowed = bool(claimed and int(claimed["claimed_by"] or 0) == user_id)
            except Exception:
                group_finish_allowed = False
        if not group_finish_allowed:
            await query.answer("⛔ غير مسموح لك.", show_alert=True)
            return

    if data.startswith("offer_price_one:"):
        parts = data.split(":")
        if len(parts) != 3 or parts[2] not in ("price_baridi", "price_flexy", "price_baridi_trader", "price_flexy_trader"):
            await query.answer("اختيار غير صالح.", show_alert=True)
            return
        offer_id, column = int(parts[1]), parts[2]
        with db() as conn:
            offer = conn.execute(f"SELECT name, {column} AS current_price FROM offers WHERE id=?", (offer_id,)).fetchone()
        if not offer:
            await query.answer("العرض غير موجود.", show_alert=True)
            return
        context.user_data["admin_step"] = "edit_single_offer_price"
        context.user_data["pending_offer_id"] = offer_id
        context.user_data["pending_offer_price_column"] = column
        labels = {"price_baridi":"سعر الزبون عبر BaridiMob/CCP", "price_flexy":"سعر الزبون عبر Flexy", "price_baridi_trader":"سعر التاجر عبر BaridiMob/CCP", "price_flexy_trader":"سعر التاجر عبر Flexy"}
        await query.message.reply_text(f"✏️ {offer['name']}\n{labels[column]} الحالي: {offer['current_price']} DA\nأرسل السعر الجديد فقط. بقية الأسعار لن تتغير.\nللإلغاء أرسل /cancel.")
        return
    if data.startswith("offer_price_all:"):
        offer_id = int(data.split(":", 1)[1])
        context.user_data["admin_step"] = "edit_price_data"
        context.user_data["pending_offer_id"] = offer_id
        await query.message.reply_text("أرسل الأسعار الأربعة بهذا الترتيب:\nسعر الزبون Baridi | سعر الزبون Flexy | سعر التاجر Baridi | سعر التاجر Flexy\nمثال: 750 | 900 | 650 | 800\nللإلغاء أرسل /cancel.")
        return

    if data == "orders_delete_all":
        await query.edit_message_text("⚠️ هل أنت متأكد من حذف جميع الطلبات؟ سيتم حذف سجلات الطلبات فقط، ولن تتغير حسابات المستخدمين أو الأرصدة أو الألعاب والعروض. لا يمكن التراجع عن العملية.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ نعم، احذف جميع الطلبات", callback_data="orders_delete_confirm")], [InlineKeyboardButton("❌ إلغاء", callback_data="adm_home")]]))
        return
    if data == "orders_delete_confirm":
        with db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            conn.execute("DELETE FROM orders")
            # Reset SQLite sequence if the table uses AUTOINCREMENT.
            try:
                conn.execute("DELETE FROM sqlite_sequence WHERE name='orders'")
            except sqlite3.OperationalError:
                pass
        await query.edit_message_text(f"✅ تم حذف جميع الطلبات ({count} طلب). الحسابات والأرصدة والألعاب والعروض لم تتغير.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")]]))
        return

    if data == "people_active":
        await admin_show_people(query.message, banned=False)
        return
    if data == "people_banned":
        await admin_show_people(query.message, banned=True)
        return
    if data == "person_search":
        context.user_data["person_search_wait"] = True
        await query.message.reply_text("🔎 أرسل اسم المشترك أو @username أو Telegram ID للبحث.")
        return
    if data.startswith("person_view:"):
        await admin_person_card(query, int(data.split(":")[1]))
        return
    if data.startswith("person_ban:") or data.startswith("person_unban:"):
        ban = data.startswith("person_ban:")
        target = int(data.split(":")[1])
        with db() as conn:
            conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if ban else 0, target))
        try:
            await context.bot.send_message(target, "🚫 تم حظر حسابك من استعمال البوت." if ban else "✅ تم إلغاء الحظر عن حسابك. أرسل /start للمتابعة.")
        except Exception:
            pass
        await admin_person_card(query, target)
        return
    if data.startswith("person_balance_edit:"):
        target = int(data.split(":", 1)[1])
        with db() as conn:
            person = conn.execute("SELECT user_id, full_name, balance FROM users WHERE user_id=?", (target,)).fetchone()
        if not person:
            await query.answer("المشترك غير موجود.", show_alert=True)
            return
        context.user_data["person_balance_edit_target"] = target
        await query.message.reply_text(
            f"✏️ تعديل رصيد {person['full_name'] or target} (ID: {target})\n"
            f"الرصيد الحالي: {int(person['balance'] or 0)} DA\n\n"
            "أرسل الرصيد الجديد كاملًا بالدينار. مثال: 2500\n"
            "لجعل الرصيد صفرًا أرسل 0. للإلغاء أرسل /cancel."
        )
        return

    if data.startswith("person_balance:"):
        target = int(data.split(":")[1])
        context.user_data["person_balance_target"] = target
        await query.message.reply_text(f"💰 أرسل المبلغ الذي تريد إضافته إلى رصيد المشترك {target} بالدينار.")
        return
    if data.startswith("person_loan_grant:"):
        if not is_admin(user_id):
            await query.answer("⛔ هذه الخاصية للإدارة فقط.", show_alert=True)
            return
        target = int(data.split(":", 1)[1])
        with db() as conn:
            trader = conn.execute("SELECT user_id, full_name, account_type, credit_debt, credit_term_days FROM users WHERE user_id=?", (target,)).fetchone()
        if not trader or trader["account_type"] != "trader":
            await query.answer("هذا الحساب ليس تاجرًا معتمدًا.", show_alert=True)
            return
        context.user_data["person_loan_grant_target"] = target
        await query.message.reply_text(
            f"💵 منح سلفية للتاجر {trader['full_name'] or target} (ID: {target})\n"
            f"الدين الحالي: {int(trader['credit_debt'] or 0)} DA\n\n"
            "أرسل مبلغ السلفية بالدينار. ستُضاف إلى رصيد التاجر ودينه.\nللإلغاء أرسل /cancel."
        )
        return
    if data.startswith("person_debtedit:"):
        if not is_admin(user_id):
            await query.answer("⛔ هذه الخاصية للإدارة فقط.", show_alert=True)
            return
        target = int(data.split(":", 1)[1])
        context.user_data["person_debt_edit_target"] = target
        await query.message.reply_text(
            f"✏️ أرسل قيمة الدين الجديدة للتاجر {target} بالدينار.\n"
            "مثال: 2500\nلجعل الدين صفرًا أرسل 0. للإلغاء أرسل /cancel."
        )
        return
    if data.startswith("person_debtzero:"):
        if not is_admin(user_id):
            await query.answer("⛔ هذه الخاصية للإدارة فقط.", show_alert=True)
            return
        target = int(data.split(":", 1)[1])
        with db() as conn:
            trader = conn.execute("SELECT account_type FROM users WHERE user_id=?", (target,)).fetchone()
            if not trader or trader["account_type"] != "trader":
                await query.answer("هذا الحساب ليس تاجرًا.", show_alert=True)
                return
            conn.execute("UPDATE users SET credit_debt=0, credit_due_at='' WHERE user_id=?", (target,))
        await query.answer("تم تصفير الدين.", show_alert=True)
        await admin_person_card(query, target)
        return
    if data.startswith("person_delete_confirm:"):
        target = int(data.split(":")[1])
        await query.edit_message_text(f"⚠️ هل أنت متأكد من حذف حساب {target}؟ هذا لا يحذف الطلبات أو سجلات الدفع.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ تأكيد حذف الحساب", callback_data=f"person_delete:{target}")],
                                               [InlineKeyboardButton("إلغاء", callback_data=f"person_view:{target}")]]))
        return
    if data.startswith("person_delete:"):
        target = int(data.split(":")[1])
        with db() as conn:
            conn.execute("DELETE FROM users WHERE user_id=?", (target,))
        await query.edit_message_text(f"تم حذف سجل الحساب {target}. سجلات الطلبات والمدفوعات لم تُحذف.")
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
        await query.edit_message_text(f"✅ تم تغيير نوع الحساب إلى {label}.\nID: {target_id}\n" + ("يمكن للإدارة منح سلفية لهذا التاجر من بطاقة حسابه." if new_type == "trader" else "تم إيقاف صلاحيات التاجر. أي دين قائم يجب تسويته قبل التحويل."))
        return

    if data.startswith("loanreq_approve:") or data.startswith("loanreq_reject:"):
        try:
            request_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("طلب غير صالح", show_alert=True)
            return
        approve = data.startswith("loanreq_approve:")
        with db() as conn:
            req = conn.execute("SELECT * FROM trader_loan_requests WHERE id=?", (request_id,)).fetchone()
            if not req or req["status"] != "pending":
                await query.answer("تمت معالجة هذا الطلب مسبقًا أو أنه غير موجود", show_alert=True)
                return
            trader = conn.execute("SELECT account_type, credit_debt, credit_term_days FROM users WHERE user_id=?", (req["user_id"],)).fetchone()
            if not trader or trader["account_type"] != "trader":
                conn.execute("UPDATE trader_loan_requests SET status='rejected', processed_at=? WHERE id=?", (now_text(), request_id))
                approve = False
            elif approve:
                from datetime import datetime, timedelta
                debt = int(trader["credit_debt"] or 0)
                term = max(1, int(trader["credit_term_days"] or 30))
                due = (datetime.now() + timedelta(days=term)).strftime("%Y-%m-%d %H:%M:%S") if debt == 0 else None
                if due:
                    conn.execute("UPDATE users SET credit_debt=credit_debt+?, balance=balance+?, credit_due_at=? WHERE user_id=?", (int(req["amount"]), int(req["amount"]), due, req["user_id"]))
                else:
                    conn.execute("UPDATE users SET credit_debt=credit_debt+?, balance=balance+? WHERE user_id=?", (int(req["amount"]), int(req["amount"]), req["user_id"]))
                conn.execute("UPDATE trader_loan_requests SET status='approved', processed_at=? WHERE id=? AND status='pending'", (now_text(), request_id))
            else:
                conn.execute("UPDATE trader_loan_requests SET status='rejected', processed_at=? WHERE id=? AND status='pending'", (now_text(), request_id))
            amount = int(req["amount"])
            target_id = int(req["user_id"])
        try:
            await context.bot.send_message(target_id, f"{'✅ تمت الموافقة على' if approve else '❌ تم رفض'} طلب السلفية #{request_id}.\nالمبلغ: {amount} DA" + ("\nتمت إضافة المبلغ إلى دينك." if approve else ""), reply_markup=main_keyboard(target_id))
        except Exception:
            logger.exception("تعذر إشعار التاجر بنتيجة طلب السلفية")
        await query.edit_message_text(f"{'✅ تمت الموافقة على' if approve else '❌ تم رفض'} طلب السلفية #{request_id}\nالتاجر: {target_id}\nالمبلغ: {amount} DA")
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
        await query.message.reply_text(f"💳 إعداد قرض التاجر {trader['full_name'] or trader['username'] or target_id} (ID: {target_id})\nالسقف الحالي: {trader['credit_limit']} DA\nالدين الحالي: {trader['credit_debt']} DA\nالأجل: {trader['credit_term_days']} يوم\nالاستحقاق: {trader['credit_due_at'] or 'لا يوجد'}\n\nأرسل: السقف | عدد الأيام\nمثال: 10000 | 30\nلإيقاف القرض أرسل: 0 | 0")
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
            await context.bot.send_message(pay["user_id"], f"{'✅ تم قبول' if approve else '❌ تم رفض'} تسديد القرض #{payment_id}.\nالمبلغ: {amount} DA\nالدين الحالي: {max(0, debt_before-amount) if approve else debt_before} DA")
        except Exception:
            logger.exception("تعذر إشعار التاجر بتسديد القرض")
        await query.edit_message_caption(caption=f"{'✅ تم قبول' if approve else '❌ تم رفض'} تسديد القرض #{payment_id}\nالتاجر: {pay['user_id']}\nالمبلغ: {amount} DA", reply_markup=None)
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
        amount = int(context.user_data.get("deposit_amount", 0) or 0)
        account_type = "trader" if is_trader(user_id) else "customer"
        minimum, maximum = deposit_limits(account_type, method)
        if amount < minimum or amount > maximum:
            context.user_data.pop("deposit_amount", None)
            await query.edit_message_text(
                f"❌ مبلغ التعبئة خارج الحدود المسموحة لحسابك عبر {'Flexy' if method == 'flexy' else 'BaridiMob / CCP'}.\n"
                f"الحد الأدنى: {minimum} DA\nالحد الأقصى: {maximum} DA\nابدأ التعبئة من جديد بالمبلغ المناسب."
            )
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
            credited_amount = int(dep["amount"])
            is_flexy = "flexy" in str(dep["payment_method"] or "").lower() or "فليكسي" in str(dep["payment_method"] or "").lower()
            if approve:
                # Flexy deposits receive an 15% deduction; other methods are credited in full.
                credited_amount = int(int(dep["amount"]) * 0.85) if is_flexy else int(dep["amount"])
                conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (credited_amount, dep["user_id"]))
        try:
            if approve:
                deduction_note = f"\nاقتطاع فليكسي (15%): {int(dep['amount']) - credited_amount} DA" if is_flexy else ""
                await context.bot.send_message(dep["user_id"], f"✅ تمت الموافقة على تعبئة #{deposit_id}.\nالمبلغ المدفوع: {dep['amount']} DA{deduction_note}\nالمبلغ المضاف إلى محفظتك: {credited_amount} DA.")
            else:
                await context.bot.send_message(dep["user_id"], f"❌ تم رفض تعبئة الرصيد #{deposit_id}. إذا كان هناك خطأ، تواصل مع الإدارة.")
        except Exception:
            logger.exception("تعذر إشعار الزبون بنتيجة التعبئة")
        deduction_caption = f"\nالمضاف للمحفظة: {credited_amount} DA (بعد خصم 15%)" if approve and is_flexy else (f"\nالمضاف للمحفظة: {credited_amount} DA" if approve else "")
        await query.edit_message_caption(caption=f"{'✅ تمت الموافقة' if approve else '❌ تم الرفض'} على تعبئة الرصيد #{deposit_id}\nالمبلغ المدفوع: {dep['amount']} DA{deduction_caption}\nالطريقة: {dep['payment_method']}\nالزبون: {dep['user_id']}", reply_markup=None)
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
        await query.message.reply_text(
            "⚙️ لوحة الإدارة",
            reply_markup=ReplyKeyboardMarkup(ADMIN_PANEL_MENU, resize_keyboard=True),
        )

    # عرض الطلبات
    elif data == "adm_orders":
        await admin_all_orders(query)

    elif data == "adm_customers":
        with db() as conn:
            rows = conn.execute("SELECT u.user_id, u.username, u.full_name, COUNT(o.id) AS order_count, COALESCE(SUM(CASE WHEN o.status != 'rejected' THEN o.price ELSE 0 END), 0) AS total FROM users u JOIN orders o ON o.user_id = u.user_id GROUP BY u.user_id ORDER BY MAX(o.id) DESC LIMIT 50").fetchall()
        buttons = [[InlineKeyboardButton(f"{(r['full_name'] or r['username'] or r['user_id'])} | {r['order_count']} طلب | {r['total']} DA"[:60], callback_data=f"customer_orders:{r['user_id']}")] for r in rows]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
        await query.edit_message_text("👤 اختر زبونًا:", reply_markup=InlineKeyboardMarkup(buttons))

    # الإحصائيات
    elif data == "adm_stats":
        await show_stats(query)

    # إدارة إيموجيات Premium لكل لعبة
    elif data.startswith("premium_game:"):
        game_id = int(data.split(":", 1)[1])
        with db() as conn:
            game = conn.execute("SELECT id, name, emoji FROM games WHERE id=?", (game_id,)).fetchone()
        if not game:
            await query.answer("اللعبة غير موجودة", show_alert=True)
            return
        custom_id = get_setting(f"premium_emoji_id_{game_id}", "").strip()
        enabled = get_setting(f"premium_emoji_enabled_{game_id}", "1") == "1"
        state = "مفعّل 🟢" if enabled else "متوقف ⏸️"
        status = f"\nالإيموجي ID: {custom_id}\nالحالة: {state}" if custom_id else "\nمازال ما ضفت حتى إيموجي لهذه اللعبة."
        buttons = [
            [InlineKeyboardButton("➕ إضافة / تغيير الإيموجي", callback_data=f"premium_set:{game_id}")],
        ]
        if custom_id:
            buttons.append([InlineKeyboardButton("⏯️ تفعيل / إيقاف", callback_data=f"premium_toggle:{game_id}")])
            buttons.append([InlineKeyboardButton("🗑️ حذف الإيموجي", callback_data=f"premium_delete:{game_id}")])
        buttons.append([InlineKeyboardButton("🔙 قائمة الإيموجيات", callback_data="premium_manage")])
        await query.edit_message_text(f"✨ إيموجي Premium — {game['name']}{status}\n\nتقدر تتحكم في الإيموجي من هنا.", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "premium_manage":
        with db() as conn:
            emoji_games = conn.execute("SELECT id, name, emoji FROM games ORDER BY id").fetchall()
        buttons = []
        for game in emoji_games:
            custom_id = get_setting(f"premium_emoji_id_{game['id']}", "").strip()
            enabled = get_setting(f"premium_emoji_enabled_{game['id']}", "1") == "1"
            status = "🟢" if custom_id and enabled else ("⏸️" if custom_id else "⚪")
            buttons.append([InlineKeyboardButton(f"{status} {game_button_label(game)}", callback_data=f"premium_game:{game['id']}", **premium_button_kwargs(game['id']))])
        buttons.append([InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")])
        await query.edit_message_text("✨ إدارة إيموجيات Premium\n🟢 مفعّل | ⏸️ متوقف | ⚪ غير مضاف", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("premium_set:"):
        game_id = int(data.split(":", 1)[1])
        context.user_data["admin_step"] = "premium_emoji_set"
        context.user_data["pending_premium_game_id"] = game_id
        await query.message.reply_text("أرسل الآن ID الإيموجي Premium لهذه اللعبة (الأرقام/المعرف فقط).\nتقدر تجيبه من أداة استخراج Custom Emoji ID.\nأرسل /cancel للإلغاء.")

    elif data.startswith("premium_toggle:"):
        game_id = int(data.split(":", 1)[1])
        current = get_setting(f"premium_emoji_enabled_{game_id}", "1")
        set_setting(f"premium_emoji_enabled_{game_id}", "0" if current == "1" else "1")
        await query.answer("تم تحديث حالة الإيموجي")
        with db() as conn:
            game = conn.execute("SELECT id, name FROM games WHERE id=?", (game_id,)).fetchone()
        custom_id = get_setting(f"premium_emoji_id_{game_id}", "").strip()
        enabled = get_setting(f"premium_emoji_enabled_{game_id}", "1") == "1"
        state = "مفعّل 🟢" if enabled else "متوقف ⏸️"
        buttons = [[InlineKeyboardButton("➕ تغيير الإيموجي", callback_data=f"premium_set:{game_id}")], [InlineKeyboardButton("⏯️ تفعيل / إيقاف", callback_data=f"premium_toggle:{game_id}")], [InlineKeyboardButton("🗑️ حذف الإيموجي", callback_data=f"premium_delete:{game_id}")], [InlineKeyboardButton("🔙 قائمة الإيموجيات", callback_data="premium_manage")]]
        await query.edit_message_text(f"✨ إيموجي Premium — {game['name']}\nالإيموجي ID: {custom_id}\nالحالة: {state}", reply_markup=InlineKeyboardMarkup(buttons))
        return

    elif data.startswith("premium_delete:"):
        game_id = int(data.split(":", 1)[1])
        set_setting(f"premium_emoji_id_{game_id}", "")
        set_setting(f"premium_emoji_enabled_{game_id}", "1")
        await query.answer("تم حذف الإيموجي")
        with db() as conn:
            game = conn.execute("SELECT id, name FROM games WHERE id=?", (game_id,)).fetchone()
        buttons = [[InlineKeyboardButton("➕ إضافة إيموجي", callback_data=f"premium_set:{game_id}")], [InlineKeyboardButton("🔙 قائمة الإيموجيات", callback_data="premium_manage")]]
        await query.edit_message_text(f"✨ إيموجي Premium — {game['name']}\nمازال ما ضفت حتى إيموجي لهذه اللعبة.", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # إدارة طرق الشحن لكل لعبة أو تطبيق
    elif data.startswith("game_methods:"):
        game_id = int(data.split(":", 1)[1])
        with db() as conn:
            game = conn.execute("SELECT name FROM games WHERE id=?", (game_id,)).fetchone()
            methods = conn.execute("SELECT * FROM recharge_methods WHERE game_id=? ORDER BY id", (game_id,)).fetchall()
        if not game:
            await query.edit_message_text("الخدمة غير موجودة."); return
        buttons = []
        for m in methods:
            method_label = ("🟢 " if m["active"] else "🔴 ") + m["title"] + f" ({ {'id':'ID','login':'تسجيل دخول','none':'بدون معلومات'}.get(m['method_type'],'ID') })"
            buttons.append([
                InlineKeyboardButton(method_label, callback_data=f"recharge_method_toggle:{m['id']}"),
                InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"recharge_method_rename:{m['id']}")
            ])
        buttons.append([InlineKeyboardButton("➕ إضافة طريقة شحن", callback_data=f"recharge_method_add:{game_id}")])
        buttons.append([InlineKeyboardButton("🔙 إدارة الألعاب", callback_data="adm_games")])
        await query.edit_message_text(f"🔀 طرق الشحن لـ {game['name']}\nاختر طريقة لتفعيلها/إيقافها أو أضف طريقة جديدة. كل طريقة لها عروض وأسعار مستقلة.", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("recharge_method_add:"):
        game_id = int(data.split(":", 1)[1])
        context.user_data["admin_step"] = "recharge_method_add"
        context.user_data["pending_method_game_id"] = game_id
        await query.message.reply_text("أرسل الطريقة بهذا الشكل:\nاسم الطريقة | id أو login أو none | رسالة طلب المعلومات (اختياري)\n\nمثال: Player ID | id | أرسل ID اللاعب\nمثال: تسجيل دخول | login |\nمثال: بدون معلومات | none |\n\nأرسل /cancel للإلغاء.")

    elif data.startswith("recharge_method_rename:"):
        method_id = int(data.split(":", 1)[1])
        with db() as conn:
            method = conn.execute("SELECT title, game_id FROM recharge_methods WHERE id=?", (method_id,)).fetchone()
        if not method:
            await query.answer("طريقة الشحن غير موجودة", show_alert=True)
            return
        context.user_data["admin_step"] = "recharge_method_rename"
        context.user_data["pending_rename_method_id"] = method_id
        await query.message.reply_text(f"✏️ أرسل الاسم الجديد لطريقة الشحن الحالية: {method['title']}\nأرسل /cancel للإلغاء.")

    elif data.startswith("recharge_method_toggle:"):
        method_id = int(data.split(":", 1)[1])
        with db() as conn:
            row = conn.execute("SELECT game_id FROM recharge_methods WHERE id=?", (method_id,)).fetchone()
            if not row: return
            conn.execute("UPDATE recharge_methods SET active=CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?", (method_id,))
            game_id = row["game_id"]
        await query.answer("تم تحديث حالة طريقة الشحن")
        await admin_games(query)

    elif data.startswith("add_offer_method:"):
        _, game_id, method_id = data.split(":", 2)
        context.user_data["admin_step"] = "add_offer_data"
        context.user_data["pending_game_id"] = int(game_id)
        context.user_data["pending_recharge_method_id"] = int(method_id)
        await query.message.reply_text("➕ أرسل بيانات العرض والأسعار لهذه الطريقة فقط:\nاسم العرض | سعر BaridiMob/CCP للزبون | سعر Flexy للزبون | سعر BaridiMob/CCP للتاجر | سعر Flexy للتاجر | نقاط المكافأة (اختياري)\n\nمثال: 100 Coins | 250 | 300 | 220 | 270 | 5\nيمكنك إرسال 3 خانات فقط أيضاً. أرسل /cancel للإلغاء.")

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

    # تغيير اسم اللعبة أو التطبيق
    elif data.startswith("game_rename:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text("❌ معرّف اللعبة غير صالح.")
            return
        with db() as conn:
            game = conn.execute("SELECT id, name FROM games WHERE id = ?", (game_id,)).fetchone()
        if not game:
            await query.message.reply_text("❌ اللعبة أو التطبيق غير موجود.")
            return
        context.user_data["editing_game_name"] = game_id
        await query.message.reply_text(
            f"✏️ أرسل الاسم الجديد لـ {game['name']}\n\n"
            "سيتم تغيير الاسم في المتجر والقوائم والعروض المرتبطة به، دون تغيير الأسعار أو الطلبات.\n"
            "أرسل /cancel للإلغاء."
        )

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

    # فتح لوحة التحكم الخاصة بلعبة أو تطبيق
    elif data.startswith("game_manage:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("معرّف غير صالح.", show_alert=True)
            return
        await admin_game_manage(query, game_id)

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

        await admin_game_manage(query, game_id)

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

        with db() as conn:
            methods = conn.execute("SELECT id,title FROM recharge_methods WHERE game_id=? AND active=1 ORDER BY id", (game_id,)).fetchall()
        if not methods:
            await query.message.reply_text("لا توجد طريقة شحن. أضف طريقة من إدارة الألعاب ← طرق الشحن والأسعار أولاً.")
            return
        buttons = [[InlineKeyboardButton(m["title"], callback_data=f"add_offer_method:{game_id}:{m['id']}")] for m in methods]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_add_offer")])
        await query.edit_message_text("اختر طريقة الشحن التي سيخصّص لها هذا العرض وأسعاره:", reply_markup=InlineKeyboardMarkup(buttons))

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

        context.user_data["pending_offer_id"] = offer_id
        with db() as conn:
            price_row = conn.execute("SELECT price_baridi, price_flexy, price_baridi_trader, price_flexy_trader FROM offers WHERE id=?", (offer_id,)).fetchone()
        await query.message.reply_text(
            f"💰 تعديل سعر العرض: {offer['name']}\n\n"
            f"الأسعار الحالية: زبون Baridi {price_row['price_baridi']} DA | زبون Flexy {price_row['price_flexy']} DA\n"
            f"تاجر Baridi {price_row['price_baridi_trader']} DA | تاجر Flexy {price_row['price_flexy_trader']} DA\n\n"
            "اختار السعر اللي تحب تبدله فقط؛ باقي الأسعار تبقى كما هي:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 الزبون — BaridiMob/CCP", callback_data=f"offer_price_one:{offer_id}:price_baridi"), InlineKeyboardButton("👤 الزبون — Flexy", callback_data=f"offer_price_one:{offer_id}:price_flexy")],
                [InlineKeyboardButton("🏪 التاجر — BaridiMob/CCP", callback_data=f"offer_price_one:{offer_id}:price_baridi_trader"), InlineKeyboardButton("🏪 التاجر — Flexy", callback_data=f"offer_price_one:{offer_id}:price_flexy_trader")],
                [InlineKeyboardButton("✏️ تعديل الأسعار الأربعة معًا", callback_data=f"offer_price_all:{offer_id}")],
            ])
        )

    # تشغيل/إخفاء طرق الدفع للزبائن
    elif data.startswith("pay_toggle:"):
        method = data.split(":", 1)[1]
        if method not in ("baridi", "flexy"):
            return
        key = f"payment_{method}_enabled"
        current = get_setting(key, "1") == "1"
        set_setting(key, "0" if current else "1")
        await admin_payment_settings(query)

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

        reward_points_granted = 0
        with db() as conn:
            order = conn.execute(
                """SELECT o.user_id, o.game_id, o.offer_id, o.player_id, o.payment_method,
                          o.status, o.points_awarded, o.points_used, o.wallet_charged,
                          o.wallet_refunded, o.credit_charged, o.credit_refunded, o.price,
                          g.name AS game_name, f.name AS offer_name
                   FROM orders o
                   LEFT JOIN games g ON g.id = o.game_id
                   LEFT JOIN offers f ON f.id = o.offer_id
                   WHERE o.id = ?""",
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
                    reward_points_granted = reward_points
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
        order_ref = f"REQ{order_id:06d}"
        game_name = order["game_name"] or "غير محددة"
        offer_name = order["offer_name"] or "غير محدد"
        payment_method = order["payment_method"] or "غير محددة"
        raw_player_id = str(order["player_id"] or "").strip()
        # Never include login credentials in customer notifications.
        player_text = (
            "شحن بالحساب"
            if raw_player_id.startswith("LOGIN EMAIL:") or "[تم حذف بيانات الدخول" in raw_player_id
            else (raw_player_id or "لا يتطلب")
        )

        if new_status == "completed":
            customer_notice = (
                f"🎉 تم إكمال طلبك بنجاح!\n\n"
                f"🔢 رقم الطلب: {order_ref}\n"
                f"🎮 اللعبة: {game_name}\n"
                f"📦 العرض: {offer_name}\n"
                f"👤 بيانات اللاعب: {player_text}\n"
                f"💰 المبلغ: {int(order['price'] or 0):,} DA\n"
                f"💳 طريقة الدفع: {payment_method}\n\n"
                "✅ تم إتمام طلبك بنجاح.\n"
                + (f"🎁 تمت إضافة {reward_points_granted} نقطة مكافأة إلى حسابك.\n" if reward_points_granted else "")
                + "❤️ شكراً لثقتك بـ SERADJ STORE!"
            )
        elif new_status == "rejected":
            customer_notice = (
                f"❌ تم إلغاء/رفض طلبك\n\n"
                f"🔢 رقم الطلب: {order_ref}\n"
                f"🎮 اللعبة: {game_name}\n"
                f"📦 العرض: {offer_name}\n"
                f"💰 المبلغ: {int(order['price'] or 0):,} DA\n"
                f"💳 طريقة الدفع: {payment_method}\n\n"
                "📌 تمت معالجة الطلب على أنه مرفوض. "
                "إذا كان لديك استفسار، يرجى التواصل مع الإدارة.\n"
                + ("💰 تمت إعادة الرصيد/النقاط المستحقة إلى حسابك إذا كان الدفع من المحفظة.\n" if int(order["wallet_charged"] or 0) or int(order["points_used"] or 0) else "")
                + "❤️ شكراً لتفهمك — SERADJ STORE"
            )
        else:
            customer_notice = (
                f"🔄 طلبك قيد التنفيذ\n\n"
                f"🔢 رقم الطلب: {order_ref}\n"
                f"🎮 اللعبة: {game_name}\n"
                f"📦 العرض: {offer_name}\n"
                f"📌 الحالة: {status_text}\n\n"
                "سنرسل لك إشعاراً عند إتمام الطلب. ❤️"
            )

        try:
            # Show the CTA as one button directly under the completion notice,
            # instead of sending a duplicate plain-text message plus another button.
            if new_status == "completed":
                bot_username = get_setting("bot_username", "").strip().lstrip("@")
                if not bot_username:
                    me = await context.bot.get_me()
                    bot_username = (me.username or "").strip().lstrip("@")
                    if bot_username:
                        set_setting("bot_username", bot_username)
                cta_markup = None
                if bot_username:
                    cta_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 اشحن وانطلق!", url=f"https://t.me/{bot_username}")]
                    ])
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=customer_notice,
                    reply_markup=cta_markup or main_keyboard(customer_id),
                )
            else:
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=customer_notice,
                    reply_markup=main_keyboard(customer_id),
                )
        except Exception:
            logger.exception("تعذر إرسال تحديث الطلب أو زر الشحن إلى الزبون (ID=%s)", customer_id)

        # Also notify the store owner/admin about every status change.
        if ADMIN_ID and int(ADMIN_ID) != int(customer_id):
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        f"📣 تحديث حالة طلب\n\n"
                        f"🔢 رقم الطلب: {order_ref}\n"
                        f"👤 Telegram ID للزبون: {customer_id}\n"
                        f"🎮 اللعبة: {game_name}\n"
                        f"📦 العرض: {offer_name}\n"
                        f"💰 المبلغ: {int(order['price'] or 0):,} DA\n"
                        f"💳 الدفع: {payment_method}\n"
                        f"📌 الحالة الجديدة: {status_text}"
                    ),
                )
            except Exception:
                logger.exception("تعذر إرسال إشعار تحديث الطلب إلى الإدارة")

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

    elif data.startswith("recharge_select:"):
        parts = data.split(":")
        if len(parts) != 4: return
        game_id, method_id = int(parts[1]), int(parts[2])
        platform = parts[3] if parts[3] in ("android", "ios") else None
        await open_game(query, game_id, platform, method_id)

    # فتح لعبة للزبون
    elif data.startswith("game:"):
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            return
        context.user_data.pop("selected_platform", None)
        await open_game(query, game_id)

    # TikTok custom coin quantity: calculate price and let the customer choose payment.
    elif data.startswith("tiktok_custom:"):
        parts = data.split(":")
        if len(parts) != 4:
            return
        try:
            game_id, method_id = int(parts[1]), int(parts[2])
        except ValueError:
            return
        game = get_game(game_id)
        if not game or (game["name"] or "").strip().lower() != "tiktok":
            await query.edit_message_text("❌ هذا الخيار متاح لشحن TikTok فقط.")
            return
        context.user_data["tiktok_custom_request"] = {
            "game_id": game_id,
            "method_id": method_id,
            "platform": parts[3] if parts[3] in ("android", "ios") else "",
        }
        context.user_data["awaiting_tiktok_custom_amount"] = True
        tiktok_min, tiktok_max = tiktok_quantity_limits()
        await query.edit_message_text(
            "✏️ اختيار كمية TikTok مخصصة\n\n"
            f"أرسل عدد الكوينز اللي حاب تشحنهم، من {tiktok_min:,} حتى {tiktok_max:,}.\n"
            "بعد إدخال الكمية، يظهر السعر وطرق الدفع تلقائيًا.\n\n"
            "للإلغاء أرسل /cancel"
        )

    elif data.startswith("tiktok_custom_pay:"):
        method = data.split(":", 1)[1]
        if method not in ("baridi", "flexy", "balance"):
            return
        request = context.user_data.get("tiktok_custom_request") or {}
        game = get_game(request.get("game_id")) if request.get("game_id") else None
        amount = int(request.get("amount", 0) or 0)
        minimum, maximum = tiktok_quantity_limits()
        if not game or (game["name"] or "").strip().lower() != "tiktok" or not minimum <= amount <= maximum:
            context.user_data.pop("tiktok_custom_request", None)
            await query.edit_message_text("❌ انتهت جلسة الطلب. ارجع للمتجر وابدأ من جديد.")
            return
        rate_method = "flexy" if method == "flexy" else "baridi"
        price_per_coin = tiktok_coin_price(rate_method, query.from_user.id)
        total = (price_per_coin * Decimal(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if price_per_coin <= 0 or total <= 0:
            await query.edit_message_text("❌ سعر TikTok لهذه الفئة وطريقة الدفع غير مضبوط. تواصل مع الإدارة.")
            return
        price = int(total)
        if method == "baridi":
            method_name = "BaridiMob / CCP"
            details = get_setting("baridi_details", "تواصل مع الإدارة لمعرفة معلومات الدفع.")
        elif method == "flexy":
            method_name = "Flexy"
            details = get_setting("flexy_details", "تواصل مع الإدارة لمعرفة معلومات الدفع.")
        else:
            with db() as conn:
                balance_row = conn.execute("SELECT balance FROM users WHERE user_id=?", (query.from_user.id,)).fetchone()
            balance = int(balance_row["balance"] or 0) if balance_row else 0
            if balance < price:
                await query.edit_message_text(f"❌ رصيد محفظتك غير كافٍ.\nالسعر: {price} DA\nرصيدك: {balance} DA\n\nاختر BaridiMob / CCP أو Flexy، أو عبّئ محفظتك.")
                return
            method_name = "رصيد المحفظة"
            details = "سيُخصم المبلغ من محفظتك عند تأكيد الطلب. (يُطبّق سعر BaridiMob / CCP لفئتك.)"
        context.user_data["order_draft"] = {
            "game_id": game["id"],
            "offer_id": None,
            "game_name": game["name"],
            "offer_name": f"{amount:,} TikTok Coins (كمية مخصصة)",
            "method": method_name,
            "price": price,
            "base_price": price,
            "points_used": 0,
            "payment_type": method,
            "platform": request.get("platform", ""),
            "login_mode": True,
            "tiktok_amount": amount,
        }
        context.user_data.pop("awaiting_tiktok_custom_amount", None)
        context.user_data["awaiting_login_email"] = True
        await query.edit_message_text(
            "✅ تم حساب طلب TikTok\n\n"
            f"🎵 الكمية: {amount:,} كوينز\n"
            f"💵 سعر الكوين الواحد: {format(price_per_coin.normalize(), 'f')} DA\n"
            f"💰 السعر الإجمالي: {price} DA\n"
            f"💳 طريقة الدفع: {method_name}\n\n"
            f"📥 معلومات الدفع:\n{details}\n\n"
            "🔐 الآن أرسل إيميل حساب TikTok المراد شحنه، وبعدها سيطلب منك البوت كلمة السر.\n"
            "⚠️ أرسل بيانات الحساب المراد شحنه فقط.\n"
            "للإلغاء أرسل /cancel"
        )

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
        await query.edit_message_text(f"💳 معلومات الدفع لتسديد القرض:\n{details}\n\nالمبلغ: {context.user_data.get('credit_repay_amount', 0)} DA\n📸 أرسل صورة وصل الدفع. لن ينقص الدين حتى توافق الإدارة.")

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
    elif data == "notify_broadcast_confirm":
        broadcast_text = context.user_data.get("pending_broadcast_text", "")
        if not broadcast_text:
            await query.answer("ما كاين حتى نص للإرسال", show_alert=True)
            return
        with db() as conn:
            recipients = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
        sent = failed = 0
        raw_entities = context.user_data.get("pending_broadcast_entities", [])
        from telegram import MessageEntity
        prefix = "📢 إشعار من SERADJ STORE:\n\n"
        # Telegram entity offsets use UTF-16 code units, not Python character count.
        prefix_utf16_len = len(prefix.encode("utf-16-le")) // 2
        buttons = context.user_data.get("pending_broadcast_buttons", [])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(b["text"], **({"url": b["url"]} if "url" in b else {"callback_data": b["callback_data"]}))]
            for b in buttons
        ]) if buttons else None
        for recipient in recipients:
            try:
                kwargs = {}
                if raw_entities:
                    kwargs["entities"] = [
                        MessageEntity.de_json({**item, "offset": int(item.get("offset", 0)) + prefix_utf16_len}, context.bot)
                        for item in raw_entities
                    ]
                await context.bot.send_message(
                    chat_id=recipient, text=prefix + broadcast_text,
                    reply_markup=keyboard, **kwargs
                )
                sent += 1
            except Exception:
                failed += 1
        for key in ("pending_broadcast_text", "pending_broadcast_entities", "pending_broadcast_buttons"):
            context.user_data.pop(key, None)
        context.user_data.pop("admin_step", None)
        await query.edit_message_text(
            f"✅ انتهى إرسال الإشعار.\\nوصل إلى: {sent}\\nتعذّر الإرسال إلى: {failed}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")]])
        )
        return

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

    # التنقل داخل المتجر: الرجوع إلى قائمة الألعاب/التطبيقات أو المستوى السابق.
    elif data in ("back_games", "back_apps"):
        category = "app" if data == "back_apps" else "game"
        with db() as conn:
            if category == "app":
                rows = conn.execute("""
                    SELECT * FROM games WHERE active=1 AND (
                        lower(trim(COALESCE(category,'')))='app'
                        OR lower(trim(name)) IN (
                            'tiktok','tik tok','snapchat+','snapchat plus','netflix','azar',
                            'app store','apple store','telegram premium','telegram','spotify',
                            'youtube premium','youtube','instagram','facebook','discord',
                            'capcut','chatgpt','canva','shahid','osn+','crunchyroll',
                            'imo','tinder','truecaller','google play','google play gift card'
                        )
                    ) ORDER BY id
                """).fetchall()
            else:
                rows = conn.execute("SELECT * FROM games WHERE active=1 AND COALESCE(NULLIF(trim(category),''),'game')='game' ORDER BY id").fetchall()
        if not rows:
            await query.edit_message_text("😕 لا توجد خدمات في هذا القسم حالياً.")
            return
        buttons = [[InlineKeyboardButton(game_button_label(g), callback_data=f"game:{g['id']}", **premium_button_kwargs(g['id']))] for g in rows]
        buttons.append([InlineKeyboardButton("🔙 الأقسام", callback_data="back_main")])
        await query.edit_message_text("🎮 قائمة الألعاب:" if category == "game" else "📱 قائمة التطبيقات:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("game_back:"):
        parts = data.split(":")
        if len(parts) != 3:
            return
        try:
            game_id = int(parts[1])
        except ValueError:
            return
        platform = parts[2] if parts[2] in ("android", "ios") else None
        await open_game(query, game_id, platform)
    # المتجر للزبائن
    elif data == "store":
        await query.edit_message_text("اختر من القائمة الرئيسية: الألعاب أو التطبيقات.")
    elif data == "back_main":
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=main_keyboard(user_id))

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

    if not is_admin(user_id) and not store_is_open():
        await message.reply_text(store_closed_notice())
        return

    if not is_admin(user_id):
        row = get_user_row(user_id)
        if row and "is_banned" in row.keys() and int(row["is_banned"] or 0):
            await message.reply_text("🚫 حسابك محظور من استعمال البوت. تواصل مع الإدارة.")
            return

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
        context.user_data.pop("editing_game_name", None)
        context.user_data.pop("awaiting_game_request", None)
        context.user_data.pop("person_loan_grant_target", None)
        context.user_data.pop("person_balance_target", None)
        context.user_data.pop("person_debt_edit_target", None)
        context.user_data.pop("awaiting_trader_loan_amount", None)
        context.user_data.pop("pending_tiktok_min_quantity", None)
        context.user_data.pop("pending_premium_game_id", None)

        await message.reply_text(
            "❌ تم إلغاء العملية.",
            reply_markup=main_keyboard(user_id),
        )
        return

    if is_admin(user_id) and context.user_data.get("admin_step") in ("store_open_time", "store_close_time", "store_open_message", "store_close_message"):
        key = context.user_data.get("admin_step")
        if key in ("store_open_time", "store_close_time"):
            try:
                parsed = datetime.strptime(text, "%H:%M")
                value = parsed.strftime("%H:%M")
            except ValueError:
                await message.reply_text("❌ صيغة غير صحيحة. أرسل الوقت هكذا 09:00 أو 18:30.")
                return
        else:
            value = text
            if not value:
                await message.reply_text("❌ الرسالة لا يمكن أن تكون فارغة. أرسل النص أو /cancel.")
                return
        set_setting(key, value)
        context.user_data.pop("admin_step", None)
        if key in ("store_open_time", "store_close_time"):
            set_setting("store_last_state", "open" if store_is_open() else "closed")
            await message.reply_text(f"✅ تم حفظ الإعداد: {value}", reply_markup=ReplyKeyboardMarkup([["🟢 تفعيل أوقات المتجر", "⚪ تعطيل أوقات المتجر"], ["⏰ تعديل وقت الافتتاح", "⏰ تعديل وقت الغلق"], ["📣 تعديل رسالة الافتتاح", "📣 تعديل رسالة الغلق"], ["🔙 إدارة البوت"]], resize_keyboard=True))
        else:
            await message.reply_text("✅ تم حفظ الرسالة الجديدة.", reply_markup=ReplyKeyboardMarkup([["🟢 تفعيل أوقات المتجر", "⚪ تعطيل أوقات المتجر"], ["⏰ تعديل وقت الافتتاح", "⏰ تعديل وقت الغلق"], ["📣 تعديل رسالة الافتتاح", "📣 تعديل رسالة الغلق"], ["🔙 إدارة البوت"]], resize_keyboard=True))
        return

    if not is_admin(user_id) and not store_is_open() and any(context.user_data.get(key) for key in (
        "awaiting_tiktok_custom_amount", "awaiting_login_email", "awaiting_login_password",
        "awaiting_player_id", "awaiting_payment_receipt",
    )):
        for key in ("order_draft", "pending_player_id", "awaiting_player_id",
                    "awaiting_payment_receipt", "awaiting_tiktok_custom_amount",
                    "awaiting_login_email", "awaiting_login_password", "pending_login_email",
                    "tiktok_custom_request"):
            context.user_data.pop(key, None)
        await message.reply_text(store_closed_notice(), reply_markup=main_keyboard(user_id))
        return

    if context.user_data.get("awaiting_tiktok_custom_amount"):
        tiktok_min, tiktok_max = tiktok_quantity_limits()
        try:
            amount_text = text.replace(" ", "").replace(",", "").replace("٬", "")
            amount = int(amount_text)
            if amount < tiktok_min or amount > tiktok_max:
                raise ValueError
        except ValueError:
            await message.reply_text(f"❌ أدخل كمية صحيحة بين {tiktok_min:,} و{tiktok_max:,} كوينز.")
            return
        request = context.user_data.get("tiktok_custom_request") or {}
        game = get_game(request.get("game_id")) if request.get("game_id") else None
        if not game or (game["name"] or "").strip().lower() != "tiktok":
            context.user_data.pop("awaiting_tiktok_custom_amount", None)
            context.user_data.pop("tiktok_custom_request", None)
            await message.reply_text("❌ انتهت جلسة الطلب. ارجع للمتجر وابدأ من جديد.")
            return
        request["amount"] = amount
        context.user_data["tiktok_custom_request"] = request
        context.user_data.pop("awaiting_tiktok_custom_amount", None)
        baridi_rate = tiktok_coin_price("baridi", message.from_user.id)
        flexy_rate = tiktok_coin_price("flexy", message.from_user.id)
        baridi_total = (baridi_rate * Decimal(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP) if baridi_rate > 0 else Decimal("0")
        flexy_total = (flexy_rate * Decimal(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP) if flexy_rate > 0 else Decimal("0")
        if baridi_total <= 0 and flexy_total <= 0:
            context.user_data.pop("tiktok_custom_request", None)
            await message.reply_text("❌ أسعار TikTok غير محددة لهذه الفئة حاليًا. تواصل مع الإدارة.")
            return
        tier_label = "التاجر" if is_trader(message.from_user.id) else "الزبون العادي"
        baridi_label = f"💳 BaridiMob / CCP — {int(baridi_total)} DA" if baridi_total > 0 else "💳 BaridiMob / CCP — غير متاح"
        flexy_label = f"📱 Flexy — {int(flexy_total)} DA" if flexy_total > 0 else "📱 Flexy — غير متاح"
        payment_rows = []
        if baridi_total > 0:
            payment_rows.append([InlineKeyboardButton(baridi_label, callback_data="tiktok_custom_pay:baridi")])
            payment_rows.append([InlineKeyboardButton("💰 الدفع من رصيد المحفظة (بسعر BaridiMob / CCP)", callback_data="tiktok_custom_pay:balance")])
        if flexy_total > 0:
            payment_rows.append([InlineKeyboardButton(flexy_label, callback_data="tiktok_custom_pay:flexy")])
        await message.reply_text(
            f"✅ الكمية المطلوبة: {amount:,} كوينز\n"
            f"🏷️ فئة السعر: {tier_label}\n"
            f"💳 سعر BaridiMob / CCP: {format(baridi_rate.normalize(), 'f') if baridi_rate > 0 else 'غير مضبوط'} DA/كوين — {int(baridi_total) if baridi_total > 0 else '—'} DA\n"
            f"📱 سعر Flexy: {format(flexy_rate.normalize(), 'f') if flexy_rate > 0 else 'غير مضبوط'} DA/كوين — {int(flexy_total) if flexy_total > 0 else '—'} DA\n\n"
            "اختر طريقة الدفع:",
            reply_markup=InlineKeyboardMarkup(payment_rows),
        )
        return

    if context.user_data.get("awaiting_credit_repay_amount"):
        try:
            amount = int(text.replace(" ", "").replace("DA", ""))
            with db() as conn:
                debt_row = conn.execute("SELECT credit_debt FROM users WHERE user_id=?", (user_id,)).fetchone()
            debt = int(debt_row["credit_debt"] or 0) if debt_row else 0
            if amount < 1 or amount > debt:
                raise ValueError
        except ValueError:
            with db() as conn:
                debt_row = conn.execute("SELECT credit_debt FROM users WHERE user_id=?", (user_id,)).fetchone()
            debt = int(debt_row["credit_debt"] or 0) if debt_row else 0
            await message.reply_text(f"❌ أدخل مبلغًا صحيحًا لا يتجاوز الدين الحالي ({debt} DA).")
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
            await message.reply_text("❌ أدخل مبلغًا صحيحًا لا يقل عن 100 DA.")
            return
        context.user_data["deposit_amount"] = amount
        context.user_data.pop("awaiting_deposit_amount", None)
        await message.reply_text(
            f"💰 مبلغ التعبئة: {amount} DA\nإذا اخترت Flexy، يُخصم 15% ويُضاف 85% فقط إلى محفظتك ({int(amount * 0.85)} DA).\nاختر طريقة الدفع:",
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
            f"💳 طريقة الدفع: {draft['method']}\n💰 المبلغ: {draft['price']} DA\n\n"
            "📸 الآن أرسل صورة وصل الدفع لإتمام الطلب.\nلإلغاء العملية أرسل /cancel"
        )
        return

    if is_admin(user_id) and context.user_data.get("person_search_wait"):
        context.user_data.pop("person_search_wait", None)
        term = text.strip().lstrip("@")
        with db() as conn:
            if term.isdigit():
                rows = conn.execute("SELECT user_id, username, full_name, is_banned FROM users WHERE user_id=? LIMIT 20", (int(term),)).fetchall()
            else:
                rows = conn.execute("SELECT user_id, username, full_name, is_banned FROM users WHERE full_name LIKE ? OR username LIKE ? ORDER BY user_id DESC LIMIT 20", (f"%{term}%", f"%{term}%")).fetchall()
        buttons = [[InlineKeyboardButton(f"{r['full_name'] or r['username'] or r['user_id']} | {r['user_id']}"[:60], callback_data=f"person_view:{r['user_id']}")] for r in rows]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="people_active")])
        await message.reply_text("نتائج البحث:" if rows else "لم يتم العثور على مشترك.", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if is_admin(user_id) and context.user_data.get("person_debt_edit_target"):
        target = int(context.user_data.pop("person_debt_edit_target"))
        try:
            new_debt = int(text.replace(" ", "").replace("DA", "").replace(",", ""))
            if new_debt < 0:
                raise ValueError
        except ValueError:
            context.user_data["person_debt_edit_target"] = target
            await message.reply_text("❌ أرسل مبلغًا صحيحًا يساوي صفرًا أو أكثر، أو /cancel للإلغاء.")
            return
        with db() as conn:
            trader = conn.execute("SELECT account_type, full_name FROM users WHERE user_id=?", (target,)).fetchone()
            if not trader or trader["account_type"] != "trader":
                await message.reply_text("❌ الحساب ليس تاجرًا؛ لم يتم تعديل الدين.")
                return
            conn.execute(
                "UPDATE users SET credit_debt=?, credit_due_at=CASE WHEN ?=0 THEN '' ELSE credit_due_at END WHERE user_id=?",
                (new_debt, new_debt, target),
            )
        await message.reply_text(f"✅ تم تحديث دين التاجر {trader['full_name'] or target} إلى {new_debt} DA. لم يتغير رصيد المحفظة.")
        return

    if is_admin(user_id) and context.user_data.get("person_loan_grant_target"):
        target = int(context.user_data.pop("person_loan_grant_target"))
        try:
            amount = int(text.replace(" ", "").replace("DA", "").replace(",", ""))
            if amount < 1:
                raise ValueError
        except ValueError:
            context.user_data["person_loan_grant_target"] = target
            await message.reply_text("❌ أرسل مبلغ سلفية صحيحًا أكبر من صفر، أو أرسل /cancel للإلغاء.")
            return
        with db() as conn:
            trader = conn.execute("SELECT user_id, full_name, account_type, credit_debt, credit_term_days FROM users WHERE user_id=?", (target,)).fetchone()
            if not trader or trader["account_type"] != "trader":
                await message.reply_text("❌ الحساب لم يعد حساب تاجر؛ لم تُمنح السلفية.")
                return
            new_debt = int(trader["credit_debt"] or 0) + amount
            term_days = max(1, int(trader["credit_term_days"] or 30))
            due_at = (datetime.now() + timedelta(days=term_days)).strftime("%Y-%m-%d")
            conn.execute("UPDATE users SET balance=balance+?, credit_debt=credit_debt+?, credit_due_at=? WHERE user_id=?", (amount, amount, due_at, target))
        await message.reply_text(f"✅ تم منح سلفية بقيمة {amount} DA للتاجر {trader['full_name'] or target}.\nالدين الإجمالي الآن: {new_debt} DA.")
        try:
            await context.bot.send_message(target, f"💵 منحتك الإدارة سلفية بقيمة {amount} DA.\nتمت إضافتها إلى رصيدك.\nإجمالي الدين: {new_debt} DA\nتاريخ التسديد المحدد: {due_at}")
        except Exception:
            logger.exception("تعذر إشعار التاجر بمنح السلفية")
        return

    if is_admin(user_id) and context.user_data.get("person_balance_edit_target"):
        target = int(context.user_data.pop("person_balance_edit_target"))
        try:
            new_balance = int(text.replace(" ", "").replace("DA", "").replace(",", ""))
            if new_balance < 0:
                raise ValueError
        except ValueError:
            context.user_data["person_balance_edit_target"] = target
            await message.reply_text("❌ أرسل رصيدًا صحيحًا يساوي صفرًا أو أكثر، أو أرسل /cancel للإلغاء.")
            return
        with db() as conn:
            person = conn.execute("SELECT full_name FROM users WHERE user_id=?", (target,)).fetchone()
            if not person:
                await message.reply_text("❌ المشترك غير موجود؛ لم يتم تعديل الرصيد.")
                return
            conn.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, target))
        await message.reply_text(f"✅ تم تعديل رصيد {person['full_name'] or target} إلى {new_balance} DA.")
        try:
            await context.bot.send_message(target, f"ℹ️ تم تحديث رصيد محفظتك من طرف الإدارة.\nالرصيد الجديد: {new_balance} DA.")
        except Exception:
            logger.exception("تعذر إشعار المشترك بتعديل رصيده")
        return

    if is_admin(user_id) and context.user_data.get("person_balance_target"):
        target = int(context.user_data.pop("person_balance_target"))
        try:
            amount = int(text.replace(" ", "").replace("DA", ""))
            if amount < 1:
                raise ValueError
        except ValueError:
            context.user_data["person_balance_target"] = target
            await message.reply_text("أرسل مبلغًا صحيحًا أكبر من صفر.")
            return
        with db() as conn:
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, target))
        await message.reply_text(f"✅ تمت إضافة {amount} DA إلى رصيد المشترك {target}.")
        return

    # حفظ اسم اللعبة أو التطبيق الجديد
    if is_admin(user_id):
        game_id = context.user_data.get("editing_game_name")
        if game_id is not None:
            new_name = text.strip()
            if not new_name or len(new_name) > 80:
                await message.reply_text("❌ الاسم غير صالح. أرسل اسمًا من 1 إلى 80 حرفًا، أو /cancel للإلغاء.")
                return
            try:
                with db() as conn:
                    duplicate = conn.execute("SELECT id FROM games WHERE lower(name)=lower(?) AND id<>?", (new_name, int(game_id))).fetchone()
                    if duplicate:
                        await message.reply_text("❌ يوجد لعبة أو تطبيق بهذا الاسم بالفعل. أرسل اسمًا مختلفًا.")
                        return
                    conn.execute("UPDATE games SET name = ? WHERE id = ?", (new_name, int(game_id)))
                context.user_data.pop("editing_game_name", None)
                await message.reply_text("✅ تم تغيير اسم اللعبة / التطبيق بنجاح.")
            except Exception:
                logger.exception("فشل تغيير اسم اللعبة أو التطبيق")
                await message.reply_text("❌ حدث خطأ أثناء تغيير الاسم.")
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

        if step == "deposit_limits_set":
            parts = [x.strip() for x in text.split("|")]
            try:
                if len(parts) != 4:
                    raise ValueError
                parsed = []
                for part in parts:
                    pair = part.split("-")
                    if len(pair) != 2:
                        raise ValueError
                    low, high = int(pair[0].strip()), int(pair[1].strip())
                    if low < 1 or high < low:
                        raise ValueError
                    parsed.append((low, high))
            except ValueError:
                await message.reply_text("❌ صيغة غير صحيحة. مثال: 100-5000 | 200-3000 | 500-20000 | 500-10000")
                return
            keys = [("customer","baridi"),("customer","flexy"),("trader","baridi"),("trader","flexy")]
            for (account, method), (low, high) in zip(keys, parsed):
                set_setting(f"deposit_{account}_{method}_min", str(low))
                set_setting(f"deposit_{account}_{method}_max", str(high))
            context.user_data.pop("admin_step", None)
            labels = ["الزبون BaridiMob/CCP", "الزبون Flexy", "التاجر BaridiMob/CCP", "التاجر Flexy"]
            summary = "\n".join(f"{label}: {low} إلى {high} DA" for label, (low, high) in zip(labels, parsed))
            await message.reply_text("✅ تم حفظ حدود التعبئة:\n" + summary, reply_markup=admin_keyboard())
            return

        if step == "tiktok_min_quantity":
            try:
                minimum = int(text.strip().replace(",", "").replace("٬", ""))
                if minimum < 1 or minimum > 10000000:
                    raise ValueError
            except ValueError:
                await message.reply_text("❌ الحد الأدنى لازم يكون عددًا صحيحًا أكبر من صفر. أعد الإرسال أو أرسل /cancel.")
                return
            context.user_data["pending_tiktok_min_quantity"] = minimum
            context.user_data["admin_step"] = "tiktok_max_quantity"
            current_max = tiktok_quantity_limits()[1]
            await message.reply_text(
                f"✅ الحد الأدنى المؤقت: {minimum:,} كوينز.\n\n"
                f"أرسل الآن الحد الأقصى للكمية (الحد الأقصى الحالي {current_max:,}).\n"
                "لازم يكون أكبر من أو يساوي الحد الأدنى.\nللإلغاء أرسل /cancel."
            )
            return

        if step == "tiktok_max_quantity":
            minimum = context.user_data.get("pending_tiktok_min_quantity")
            try:
                maximum = int(text.strip().replace(",", "").replace("٬", ""))
                if minimum is None or maximum < int(minimum) or maximum > 10000000:
                    raise ValueError
            except ValueError:
                minimum_shown = context.user_data.get("pending_tiktok_min_quantity", "غير معروف")
                await message.reply_text(f"❌ الحد الأقصى لازم يكون عددًا صحيحًا لا يقل عن {minimum_shown}. أعد الإرسال أو أرسل /cancel.")
                return
            set_setting("tiktok_min_quantity", str(int(minimum)))
            set_setting("tiktok_max_quantity", str(maximum))
            context.user_data.pop("pending_tiktok_min_quantity", None)
            context.user_data.pop("admin_step", None)
            await message.reply_text(
                f"✅ تم حفظ حدود كمية TikTok.\n\nالحد الأدنى: {int(minimum):,} كوينز\n"
                f"الحد الأقصى: {maximum:,} كوينز\n\nستظهر هذه الحدود للزبون ويتحقق منها البوت تلقائيًا.",
                reply_markup=admin_keyboard(),
            )
            return

        if step and step.startswith("tiktok_coin_price_"):
            try:
                raw_price = text.strip().replace("DA", "").replace("DA", "").replace("da", "").replace(",", ".").replace(" ", "")
                price = Decimal(raw_price)
                if not price.is_finite() or price <= 0 or price > Decimal("1000000"):
                    raise InvalidOperation
                price = price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP).normalize()
            except (InvalidOperation, ValueError):
                await message.reply_text("❌ السعر غير صحيح. أرسل رقمًا أكبر من صفر، مثال: 0.15 أو 0,15. أو /cancel للإلغاء.")
                return
            price_text = format(price, "f")
            set_setting(step, price_text)
            # Keep old setting in sync for legacy retail Baridi users.
            if step == "tiktok_coin_price_retail_baridi":
                set_setting("tiktok_coin_price", price_text)
            context.user_data.pop("admin_step", None)
            tier, method = step.removeprefix("tiktok_coin_price_").split("_", 1)
            tier_label = "التجزئة (الزبائن)" if tier == "retail" else "الجملة (التجار)"
            method_label = "BaridiMob / CCP" if method == "baridi" else "Flexy"
            await message.reply_text(
                f"✅ تم حفظ سعر TikTok.\nالفئة: {tier_label}\nطريقة الدفع: {method_label}\n"
                f"سعر الكوين الواحد: {price_text} DA.\nسيُستخدم هذا السعر لحساب الكمية المخصصة تلقائيًا.",
                reply_markup=admin_keyboard(),
            )
            return

        if step == "account_convert_user_id":
            try:
                target_id = int(text.strip())
                if target_id <= 0:
                    raise ValueError
            except ValueError:
                await message.reply_text("❌ أرسل Telegram ID صحيحًا.")
                return
            with db() as conn:
                target = conn.execute("SELECT user_id, username, full_name, account_type FROM users WHERE user_id=?", (target_id,)).fetchone()
            if not target:
                await message.reply_text("❌ الحساب غير موجود في قاعدة البيانات.")
                return
            context.user_data.pop("admin_step", None)
            context.user_data["account_convert_target_id"] = target_id
            current = "تاجر" if target["account_type"] == "trader" else "زبون عادي"
            buttons = [[InlineKeyboardButton("👤 تحويل إلى زبون عادي", callback_data=f"account_type_set:customer:{target_id}")], [InlineKeyboardButton("🏪 تحويل إلى تاجر", callback_data=f"account_type_set:trader:{target_id}")], [InlineKeyboardButton("❌ إلغاء", callback_data="adm_home")]]
            await message.reply_text(f"👤 الحساب: {target['full_name'] or target['username'] or target_id}\nID: {target_id}\nالنوع الحالي: {current}\n\nاختر نوع الحساب الجديد.", reply_markup=InlineKeyboardMarkup(buttons))
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
                    await message.reply_text(f"❌ لا يمكن جعل سقف القرض أقل من الدين الحالي ({row['credit_debt']} DA).")
                    return
                conn.execute("UPDATE users SET credit_limit = ?, credit_term_days = ?, credit_due_at = CASE WHEN credit_debt = 0 THEN '' ELSE credit_due_at END WHERE user_id = ?", (limit_amount, term_days, target_id))
            context.user_data.pop("admin_step", None)
            context.user_data.pop("loan_target_id", None)
            try:
                await context.bot.send_message(target_id, f"💳 تم تحديث إعدادات القرض الخاصة بك.\nسقف القرض: {limit_amount} DA\nأجل التسديد: {term_days} يومًا" if limit_amount else "⛔ تم إيقاف إمكانية استخدام قرض جديد في حسابك. الدين الحالي يبقى واجب التسديد.")
            except Exception:
                logger.exception("تعذر إشعار التاجر بإعداد القرض")
            await message.reply_text("✅ تم حفظ إعدادات القرض.", reply_markup=admin_keyboard())
            return

        if step == "contact_settings":
            parts = [x.strip() for x in text.split("|")]
            if len(parts) != 3:
                await message.reply_text("الصيغة: رقم واتساب | رابط تيليغرام | رابط فيسبوك")
                return
            wa, tg, fb = parts
            if wa:
                wa = wa.replace("+", "").replace(" ", "").replace("-", "")
                if not wa.isdigit():
                    await message.reply_text("رقم واتساب غير صحيح. أرسله بالأرقام الدولية دون +.")
                    return
                set_setting("whatsapp_number", wa)
            if tg:
                if not tg.startswith(("https://t.me/", "https://telegram.me/")):
                    await message.reply_text("رابط تيليغرام يجب أن يبدأ بـ https://t.me/")
                    return
                set_setting("telegram_url", tg)
            if fb:
                if not fb.startswith("https://"):
                    await message.reply_text("رابط فيسبوك يجب أن يبدأ بـ https://")
                    return
                set_setting("facebook_url", fb)
            context.user_data.pop("admin_step", None)
            await message.reply_text("✅ تم حفظ حسابات التواصل.", reply_markup=admin_keyboard())
            return

        if step == "recharge_method_rename":
            new_title = text.strip()
            if not new_title or len(new_title) > 80:
                await message.reply_text("❌ الاسم غير صالح. أرسل اسمًا من 1 إلى 80 حرفًا.")
                return
            method_id = int(context.user_data.get("pending_rename_method_id", 0))
            with db() as conn:
                row = conn.execute("SELECT game_id FROM recharge_methods WHERE id=?", (method_id,)).fetchone()
                if not row:
                    await message.reply_text("❌ طريقة الشحن غير موجودة.", reply_markup=admin_keyboard())
                    context.user_data.pop("admin_step", None)
                    context.user_data.pop("pending_rename_method_id", None)
                    return
                conn.execute("UPDATE recharge_methods SET title=? WHERE id=?", (new_title, method_id))
                game_id = row["game_id"]
            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_rename_method_id", None)
            await message.reply_text(f"✅ تم تغيير اسم طريقة الشحن إلى: {new_title}", reply_markup=admin_keyboard())
            # إظهار إدارة طرق الشحن لتأكيد الاسم الجديد
            with db() as conn:
                game = conn.execute("SELECT name FROM games WHERE id=?", (game_id,)).fetchone()
                methods = conn.execute("SELECT * FROM recharge_methods WHERE game_id=? ORDER BY id", (game_id,)).fetchall()
            if game:
                buttons = []
                for m in methods:
                    method_label = ("🟢 " if m["active"] else "🔴 ") + m["title"] + f" ({ {'id':'ID','login':'تسجيل دخول','none':'بدون معلومات'}.get(m['method_type'],'ID') })"
                    buttons.append([
                        InlineKeyboardButton(method_label, callback_data=f"recharge_method_toggle:{m['id']}"),
                        InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"recharge_method_rename:{m['id']}")
                    ])
                buttons.append([InlineKeyboardButton("➕ إضافة طريقة شحن", callback_data=f"recharge_method_add:{game_id}")])
                buttons.append([InlineKeyboardButton("🔙 إدارة الألعاب", callback_data="adm_games")])
                await message.reply_text(f"🔀 طرق الشحن لـ {game['name']}", reply_markup=InlineKeyboardMarkup(buttons))
            return

        if step == "recharge_method_add":
            parts = [x.strip() for x in text.split("|", 2)]
            if len(parts) < 2 or not parts[0] or parts[1] not in ("id", "login", "none"):
                await message.reply_text("الصيغة: اسم الطريقة | id أو login أو none | رسالة طلب المعلومات (اختياري)")
                return
            game_id = int(context.user_data.get("pending_method_game_id", 0))
            with db() as conn:
                conn.execute("INSERT INTO recharge_methods (game_id,title,method_type,prompt,active) VALUES (?,?,?,?,1)", (game_id, parts[0], parts[1], parts[2] if len(parts)>2 else ""))
            context.user_data.pop("admin_step", None); context.user_data.pop("pending_method_game_id", None)
            await message.reply_text("✅ تمت إضافة طريقة الشحن. أضف عروضها من لوحة الإدارة ← إضافة عرض.", reply_markup=admin_keyboard())
            return

        if step == "point_offer_add":
            parts=[x.strip() for x in text.split("|")]
            if len(parts) != 4:
                await message.reply_text("الصيغة: الاسم | الوصف | تكلفة النقاط | المخزون (-1 غير محدود)"); return
            try:
                cost=int(parts[2]); stock=int(parts[3])
                if cost < 1 or stock < -1: raise ValueError
            except ValueError:
                await message.reply_text("التكلفة يجب أن تكون موجبة والمخزون -1 أو صفر أو أكثر."); return
            with db() as conn:
                conn.execute("INSERT INTO point_offers (title,description,points_cost,stock,active,created_at) VALUES (?,?,?,?,1,?)",(parts[0],parts[1],cost,stock,now_text()))
            context.user_data.pop("admin_step",None)
            await message.reply_text("✅ تمت إضافة العرض إلى متجر النقاط.",reply_markup=admin_keyboard()); return

        # إضافة لعبة
        if step == "add_game":
            parts = [part.strip() for part in text.split("|")]

            if not parts[0]:
                await message.reply_text(
                    "❌ اكتب اسم اللعبة."
                )
                return

            game_name = parts[0]
            emoji = parts[1] if len(parts) > 1 and parts[1] else "🎮"
            category = parts[2].lower() if len(parts) > 2 and parts[2] else context.user_data.get("pending_add_category", "game")
            if category not in ("game", "app"):
                await message.reply_text("❌ النوع يجب أن يكون game أو app."); return

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
                    INSERT INTO games (name, emoji, active, category)
                    VALUES (?, ?, 1, ?)
                    """,
                    (game_name, emoji, category),
                )

            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_add_category", None)

            await message.reply_text(
                f"✅ تمت إضافة {'التطبيق' if category == 'app' else 'اللعبة'}: {emoji} {game_name}",
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
                price_baridi_trader = int(parts[3]) if len(parts) >= 5 else price_baridi
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
                    (game_id, recharge_method_id, name, price_baridi, price_flexy, price_baridi_trader, price_flexy_trader, reward_points, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        game_id,
                        context.user_data.get("pending_recharge_method_id"),
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
            context.user_data.pop("pending_recharge_method_id", None)

            await message.reply_text(
                f"✅ تمت إضافة العرض: {offer_name}\n\n"
                f"🏦 BaridiMob/CCP: {price_baridi} DA\n"
                f"📱 Flexy: {price_flexy} DA\n"
                f"🏪 أسعار التاجر — BaridiMob/CCP: {price_baridi_trader} DA | Flexy: {price_flexy_trader} DA\n🎁 نقاط المكافأة: {reward_points}",
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

        # تعديل سعر واحد فقط لعرض مع الحفاظ على بقية الأسعار
        if step == "edit_single_offer_price":
            try:
                new_price = int(text)
                if new_price < 0:
                    raise ValueError
            except ValueError:
                await message.reply_text("❌ أرسل سعرًا صحيحًا (0 أو أكثر)، أو /cancel للإلغاء.")
                return
            offer_id = context.user_data.get("pending_offer_id")
            column = context.user_data.get("pending_offer_price_column")
            if column not in ("price_baridi", "price_flexy", "price_baridi_trader", "price_flexy_trader") or not offer_id:
                context.user_data.pop("admin_step", None)
                await message.reply_text("❌ انتهت جلسة تعديل السعر. افتح تعديل سعر العرض من جديد.")
                return
            with db() as conn:
                result = conn.execute(f"UPDATE offers SET {column}=? WHERE id=?", (new_price, offer_id))
                offer_name_row = conn.execute("SELECT name FROM offers WHERE id=?", (offer_id,)).fetchone()
            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_offer_id", None)
            context.user_data.pop("pending_offer_price_column", None)
            if not result.rowcount or not offer_name_row:
                await message.reply_text("❌ العرض غير موجود.", reply_markup=admin_keyboard())
            else:
                await message.reply_text(f"✅ تم تعديل السعر فقط إلى {new_price} DA للعرض {offer_name_row['name']}. بقية الأسعار بقيت كما هي.", reply_markup=admin_keyboard())
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
                f"🏦 BaridiMob/CCP: {price_baridi} DA\n"
                f"📱 Flexy: {price_flexy} DA\n"
                f"🏪 للتاجر — BaridiMob/CCP: {price_baridi_trader} DA | Flexy: {price_flexy_trader} DA",
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

        if step == "premium_emoji_set":
            game_id = context.user_data.get("pending_premium_game_id")
            # Easiest path: admin sends/pastes one custom emoji; fallback accepts its numeric ID.
            custom_id = ""
            for entity in (message.entities or []):
                if getattr(entity, "type", "") == "custom_emoji" and getattr(entity, "custom_emoji_id", None):
                    custom_id = entity.custom_emoji_id
                    break
            if not custom_id and text.isdigit() and len(text) >= 5:
                custom_id = text
            if not game_id or not custom_id:
                await message.reply_text("❌ ما قدرتش نقرأ الإيموجي. ابعث إيموجي Premium وحده من تيليغرام، أو ابعث الـ ID تاعه كأرقام فقط. /cancel للإلغاء.")
                return
            set_setting(f"premium_emoji_id_{game_id}", custom_id)
            set_setting(f"premium_emoji_enabled_{game_id}", "1")
            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_premium_game_id", None)
            await message.reply_text("✅ تم حفظ إيموجي Premium وتفعيله. سيظهر في زر اللعبة وفي قائمة الألعاب إذا كان البوت/مالك البوت مؤهلاً لاستخدام الإيموجيات المخصصة.", reply_markup=ReplyKeyboardMarkup(ADMIN_PANEL_MENU, resize_keyboard=True))
            return

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

        if step == "notify_broadcast_message":
            context.user_data["pending_broadcast_text"] = text
            context.user_data["pending_broadcast_entities"] = [
                entity.to_dict() for entity in (message.entities or [])
            ]
            context.user_data["admin_step"] = "notify_broadcast_buttons"
            await message.reply_text(
                "✅ حفظت نص الإشعار.\n\n"
                "تقدر تبعث إيموجيات Premium داخل النص مباشرة إذا كانت ظاهرة عندك في تيليغرام.\n\n"
                "إذا حبيت تزيد أزرار، ابعث كل زر في سطر بهذا الشكل:\n"
                "رابط | اسم الزر | https://example.com\n"
                "قسم | اسم الزر | store_category:game (قسم الألعاب)\n"
                "قسم | اسم الزر | store_category:app (قسم التطبيقات)\n"
                "قسم | اسم الزر | game:ID (لعبة محددة)\n"
                "قسم | اسم الزر | offer:GAME_ID:OFFER_ID (عرض محدد)\n"
                "قسم | اسم الزر | recharge_select:GAME_ID:METHOD_ID:none (طريقة شحن/سيرفر محدد)\n"
                "قسم | اسم الزر | freefire أو store أو back_main\n\n"
                "تقدر تستعمل callback_data لأي زر تنقل موجود في البوت. الحد الأقصى 8 أزرار.\n"
                "إذا ما تحتاجش أزرار ابعث: بدون\n"
                "للإلغاء ابعث /cancel."
            )
            return

        if step == "notify_broadcast_buttons":
            buttons = []
            if text.strip().lower() not in ("بدون", "لا", "no", "none"):
                for line in text.splitlines():
                    parts = [part.strip() for part in line.split("|", 2)]
                    if len(parts) != 3 or parts[0] not in ("رابط", "قسم") or not parts[1] or not parts[2]:
                        await message.reply_text("❌ صيغة غير صحيحة. استعمل: رابط | اسم الزر | https://example.com أو قسم | اسم الزر | freefire (يفتح فري فاير مباشرة) أو store")
                        return
                    kind, label, target = parts
                    if kind == "رابط":
                        if not target.startswith(("https://", "http://")):
                            await message.reply_text("❌ الرابط لازم يبدأ بـ https:// أو http://")
                            return
                        buttons.append({"text": label, "url": target})
                    else:
                        if target == "freefire":
                            with db() as conn:
                                game_row = conn.execute(
                                    "SELECT id FROM games WHERE active=1 AND lower(name) LIKE '%free fire%' ORDER BY id LIMIT 1"
                                ).fetchone()
                            if not game_row:
                                await message.reply_text("❌ ما لقيتش خدمة Free Fire مفعّلة في قاعدة البيانات. تأكد من اسم اللعبة في لوحة الإدارة.")
                                return
                            callback_target = f"game:{game_row['id']}"
                        elif target in ("store", "back_main", "store_category:game", "store_category:app"):
                            callback_target = target
                        elif re.fullmatch(r"game:[0-9]+", target):
                            game_id = int(target.split(":", 1)[1])
                            game_row = get_game(game_id)
                            if not game_row or not game_row["active"]:
                                await message.reply_text("❌ رقم اللعبة غير صحيح أو اللعبة غير مفعّلة.")
                                return
                            callback_target = target
                        elif re.fullmatch(r"offer:[0-9]+:[0-9]+(?::(?:android|ios|none))?", target):
                            callback_target = target
                        elif re.fullmatch(r"recharge_select:[0-9]+:[0-9]+(?::(?:android|ios|none))?", target):
                            # Directly open a specific recharge method/server inside a game.
                            parts_target = target.split(":")
                            game_id, method_id = int(parts_target[1]), int(parts_target[2])
                            with db() as conn:
                                valid_method = conn.execute(
                                    "SELECT 1 FROM games g JOIN recharge_methods rm ON rm.game_id=g.id "
                                    "WHERE g.id=? AND g.active=1 AND rm.id=? AND rm.active=1",
                                    (game_id, method_id),
                                ).fetchone()
                            if not valid_method:
                                await message.reply_text("❌ معرّف اللعبة أو طريقة الشحن/السيرفر غير صحيح أو غير مفعّل.")
                                return
                            callback_target = target
                        else:
                            allowed_prefixes = (
                                "store_category:", "game_method:", "game:", "offer:", "recharge_select:",
                                "platform:", "method:", "server:", "app:", "back_",
                            )
                            if len(target.encode("utf-8")) > 64 or not target.startswith(allowed_prefixes):
                                await message.reply_text(
                                    "❌ وجهة القسم غير مدعومة أو طويلة جدًا. استعمل store_category:game أو "
                                    "store_category:app أو game:ID أو offer:GAME_ID:OFFER_ID أو "
                                    "recharge_select:GAME_ID:METHOD_ID:none، "
                                    "أو callback_data لزر تنقّل موجود في البوت."
                                )
                                return
                            callback_target = target
                        if len(callback_target.encode("utf-8")) > 64:
                            await message.reply_text("❌ وجهة الزر طويلة جدًا.")
                            return
                        buttons.append({"text": label, "callback_data": callback_target})
                    if len(buttons) > 8:
                        await message.reply_text("❌ الحد الأقصى 8 أزرار.")
                        return
            context.user_data["pending_broadcast_buttons"] = buttons
            context.user_data["admin_step"] = "notify_broadcast_confirm"
            with db() as conn:
                total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            preview_rows = [
                [InlineKeyboardButton(b["text"], **({"url": b["url"]} if "url" in b else {"callback_data": b["callback_data"]}))]
                for b in buttons
            ]
            preview_rows.append([
                InlineKeyboardButton("✅ إرسال للجميع", callback_data="notify_broadcast_confirm"),
                InlineKeyboardButton("❌ إلغاء", callback_data="notify_cancel")
            ])
            await message.reply_text(
                f"📨 معاينة إشعار لجميع المشتركين ({total} حساب):\n\n{text}\n\nتأكيد الإرسال؟",
                reply_markup=InlineKeyboardMarkup(preview_rows)
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
        if not is_admin(user_id) and not store_is_open():
            context.user_data.pop("order_draft", None)
            context.user_data.pop("awaiting_player_id", None)
            context.user_data.pop("pending_player_id", None)
            await message.reply_text(store_closed_notice(), reply_markup=main_keyboard(user_id))
            return
        await create_order(update, context)
        return

    # =========================
    # أزرار القائمة الرئيسية
    # =========================

    if text == "🛍️ المتجر":
        await message.reply_text(
            "🛍️ اختار القسم لي حاب تتصفح:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 الألعاب", callback_data="store_category:game")],
                [InlineKeyboardButton("📱 التطبيقات", callback_data="store_category:app")],
            ])
        )
        return
    # توافق مع الأزرار القديمة إذا كانت ما زالت ظاهرة في جلسة المستخدم
    if text == "🎮 الألعاب":
        await show_store(message, user_id, "game"); return
    if text == "📱 التطبيقات":
        await show_store(message, user_id, "app"); return
    if text == "🎁 إشتري بنقاطي":
        await show_points_shop(message, user_id); return
    if text == "🎯 الإحالة والنقاط":
        bot_username = get_setting("bot_username", "").strip()
        if not bot_username:
            try:
                me = await context.bot.get_me(); bot_username = me.username or ""
                if bot_username: set_setting("bot_username", bot_username)
            except Exception: bot_username = ""
        user_row = get_user_row(user_id)
        points = int(user_row["points"] or 0) if user_row else 0
        link = f"https://t.me/{bot_username}?start=ref_{user_id}" if bot_username else "تعذر إنشاء الرابط الآن؛ حاول لاحقاً."
        await message.reply_text(f"🎯 نظام الإحالة والمكافآت\n\nرابط الإحالة الخاص بك:\n{link}\n\n🎁 تحصل على 50 نقطة عن كل مشترك جديد يسجل عبر رابطك.\nرصيد نقاطك الحالي: {points} نقطة.")
        return
    if text == "✨ مزايا متجرنا":
        await message.reply_text(STORE_BENEFITS_TEXT, reply_markup=main_keyboard(user_id)); return
    if text == "🔐 السياسات والخصوصية":
        policy_text = get_setting("terms_policy", TERMS_PRIVACY_TEXT)
        await message.reply_text(policy_text, reply_markup=main_keyboard(user_id)); return
    if text == "➕ طلب لعبة غير موجودة":
        context.user_data["awaiting_game_request"] = True
        await message.reply_text("🎮 اكتب اسم اللعبة أو التطبيق الذي تريد إضافته، ويمكنك ذكر تفاصيل النسخة أو طريقة الشحن. أرسل /cancel للإلغاء.", reply_markup=cancel_keyboard()); return
    if context.user_data.get("awaiting_game_request"):
        if len(text) < 2:
            await message.reply_text("اكتب اسم اللعبة أو التطبيق بشكل أوضح."); return
        with db() as conn:
            cur=conn.execute("INSERT INTO game_requests (user_id,request_text,status,created_at) VALUES (?,?, 'pending', ?)",(user_id,text,now_text())); request_id=cur.lastrowid
        context.user_data.pop("awaiting_game_request",None)
        if ADMIN_ID:
            try: await context.bot.send_message(ADMIN_ID,f"➕ طلب لعبة/تطبيق جديد #{request_id}\nمن: {message.from_user.full_name}\nID: {user_id}\nالطلب: {text}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👀 قيد المراجعة",callback_data=f"game_request_status:{request_id}:reviewed"),InlineKeyboardButton("✅ تمت الإضافة",callback_data=f"game_request_status:{request_id}:added"),InlineKeyboardButton("❌ مرفوض",callback_data=f"game_request_status:{request_id}:rejected")]]))
            except Exception: logger.exception("Could not send game request")
        await message.reply_text(f"✅ تم إرسال اقتراحك للإدارة برقم #{request_id}.",reply_markup=main_keyboard(user_id)); return

    if text == "📦 طلباتي":
        await show_my_orders(update, context)
        return

    if text == "👤 حسابي":
        await show_account(update.effective_message, update.effective_user.id)
        return

    if text == "💰 حدود تعبئة الرصيد" and is_admin(user_id):
        context.user_data["admin_step"] = "deposit_limits_set"
        await message.reply_text(
            "أرسل الحدود الأربعة بهذا الترتيب، كل حد أدنى-أقصى، وافصل بينها بعلامة |\n"
            "1) الزبون BaridiMob/CCP | 2) الزبون Flexy | 3) التاجر BaridiMob/CCP | 4) التاجر Flexy\n"
            "مثال: 100-5000 | 200-3000 | 500-20000 | 500-10000\n"
            "الأرقام بالدينار الجزائري. أرسل /cancel للإلغاء."
        )
        return

    if text == "💰 تعبئة الرصيد":
        context.user_data["awaiting_deposit_amount"] = True
        await message.reply_text("💰 أرسل مبلغ التعبئة بالدينار الجزائري (مثال: 1000 DA).\nالحد الأدنى 100 DA.\nللإلغاء أرسل /cancel")
        return

    if text in ("💳 تسديد القرض", "💳 قروض التجار"):
        context.user_data.pop("awaiting_credit_repay_amount", None)
        context.user_data.pop("awaiting_credit_receipt", None)
        context.user_data.pop("person_loan_grant_target", None)
        await message.reply_text("⛔ تم إلغاء نظام القروض والسلفية من المتجر.", reply_markup=main_keyboard(user_id))
        return

    if False:  # مسار تسديد القرض القديم معطّل
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
        await message.reply_text(f"💳 تسديد القرض\nالدين الحالي: {debt} DA\nتاريخ الاستحقاق: {due_at or 'غير محدد'}\n\nأرسل مبلغ التسديد بالدينار (كلي أو جزئي)، ثم أرسل صورة وصل الدفع. ينقص الدين بعد موافقة الإدارة فقط.\nللإلغاء أرسل /cancel")
        return

    if text == "📞 اتصل بالإدارة":
        await message.reply_text("📞 اختر وسيلة التواصل مع إدارة SERADJ STORE:", reply_markup=contact_admin_keyboard())
        return

    if is_admin(user_id) and text == "📇 إعدادات التواصل":
        context.user_data["admin_step"] = "contact_settings"
        await message.reply_text("📇 أرسل حسابات التواصل بهذا الشكل في رسالة واحدة:\nرقم واتساب الدولي بدون + | رابط تيليغرام | رابط فيسبوك\n\nمثال: 213XXXXXXXXX | https://t.me/username | https://facebook.com/username\n\nيمكنك ترك أي خانة فارغة للإبقاء على قيمتها الحالية. أرسل /cancel للإلغاء.", reply_markup=cancel_keyboard())
        return

    # =========================
    # أزرار لوحة الإدارة
    # =========================

    if is_admin(user_id):
        if text == "🛠️ لوحة التحكم":
            await show_admin_panel(update, context)
            return

        if text == "➕ إضافة":
            await message.reply_text("➕ اختار واش تحب تزيد:", reply_markup=ReplyKeyboardMarkup([["➕ إضافة لعبة", "➕ إضافة عرض"], ["🔙 لوحة الإدارة"]], resize_keyboard=True))
            return
        if text == "🛍️ المتجر":
            await message.reply_text("🛍️ إدارة الألعاب والتطبيقات:", reply_markup=ReplyKeyboardMarkup([["🎮 الألعاب", "📱 التطبيقات"], ["🔙 لوحة الإدارة"]], resize_keyboard=True))
            return
        if text == "📂 إدارة البوت":
            await message.reply_text("📂 إدارة البوت:", reply_markup=ReplyKeyboardMarkup([["📋 كل الطلبات", "🗑️ حذف جميع الطلبات"], ["💳 إعدادات الدفع", "📊 الإحصائيات"], ["📝 إدارة النصوص", "📇 إعدادات التواصل"], ["🕒 أوقات المتجر", "🧹 تصفير الحسابات والطلبات"], ["🔄 تحويل زبون / تاجر"], ["🔙 لوحة الإدارة"]], resize_keyboard=True))
            return
        if text == "🕒 أوقات المتجر":
            enabled = get_setting("store_hours_enabled", "0") == "1"
            opening = get_setting("store_open_time", "09:00")
            closing = get_setting("store_close_time", "23:00")
            await message.reply_text(
                f"🕒 إعداد أوقات المتجر (توقيت الجزائر)\n\nالحالة: {'مفعّل' if enabled else 'معطّل'}\nالافتتاح: {opening}\nالغلق: {closing}\n\nاختر إجراءً. عند التعطيل تبقى الطلبات متاحة دائمًا. عند التفعيل يمكن تصفح المتجر خارج الوقت لكن لا يمكن إرسال طلب جديد.",
                reply_markup=ReplyKeyboardMarkup([["🟢 تفعيل أوقات المتجر", "⚪ تعطيل أوقات المتجر"], ["⏰ تعديل وقت الافتتاح", "⏰ تعديل وقت الغلق"], ["📣 تعديل رسالة الافتتاح", "📣 تعديل رسالة الغلق"], ["🔙 إدارة البوت"]], resize_keyboard=True))
            return
        if text == "🟢 تفعيل أوقات المتجر":
            set_setting("store_hours_enabled", "1")
            set_setting("store_last_state", "open" if store_is_open() else "closed")
            await message.reply_text("✅ تم تفعيل أوقات المتجر.", reply_markup=main_keyboard(user_id))
            return
        if text == "⚪ تعطيل أوقات المتجر":
            set_setting("store_hours_enabled", "0")
            await message.reply_text("✅ تم تعطيل أوقات المتجر؛ الطلبات متاحة في كل الأوقات.", reply_markup=main_keyboard(user_id))
            return
        if text == "⏰ تعديل وقت الافتتاح":
            context.user_data["admin_step"] = "store_open_time"
            await message.reply_text("أرسل وقت الافتتاح بصيغة 24 ساعة مثل 09:00 أو 18:30. للإلغاء أرسل /cancel")
            return
        if text == "⏰ تعديل وقت الغلق":
            context.user_data["admin_step"] = "store_close_time"
            await message.reply_text("أرسل وقت الغلق بصيغة 24 ساعة مثل 23:00 أو 02:30. للإلغاء أرسل /cancel")
            return
        if text == "📣 تعديل رسالة الافتتاح":
            context.user_data["admin_step"] = "store_open_message"
            await message.reply_text("أرسل رسالة الافتتاح الجديدة. سيتم إرسالها للمشتركين عند فتح المتجر. للإلغاء أرسل /cancel")
            return
        if text == "📣 تعديل رسالة الغلق":
            context.user_data["admin_step"] = "store_close_message"
            await message.reply_text("أرسل رسالة الغلق الجديدة. سيتم إرسالها للمشتركين عند غلق المتجر. للإلغاء أرسل /cancel")
            return

        if text == "📱 التطبيقات":
            await show_store(message, user_id, "app")
            return
        if text == "🎮 الألعاب":
            await show_store(message, user_id, "game")
            return

        if text == "✨ إدارة إيموجيات Premium":
            with db() as conn:
                emoji_games = conn.execute("SELECT id, name, emoji FROM games ORDER BY id").fetchall()
            buttons = []
            for game in emoji_games:
                custom_id = get_setting(f"premium_emoji_id_{game['id']}", "").strip()
                enabled = get_setting(f"premium_emoji_enabled_{game['id']}", "1") == "1"
                status = "🟢" if custom_id and enabled else ("⏸️" if custom_id else "⚪")
                buttons.append([InlineKeyboardButton(f"{status} {game_button_label(game)}", callback_data=f"premium_game:{game['id']}", **premium_button_kwargs(game['id']))])
            buttons.append([InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")])
            await message.reply_text("✨ إدارة إيموجيات Premium\nاختار لعبة لإضافة إيموجي مخصص أو تغييره أو إيقافه.", reply_markup=InlineKeyboardMarkup(buttons))
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
            forced_category = "game"
            context.user_data["pending_add_category"] = forced_category
            example = "Free Fire | 🔥 | game"
            await message.reply_text(
                f"➕ ابعث الاسم | الإيموجي\nمثال: {example}\n\n"
                "تقدر كذلك تبعث الاسم | الإيموجي | النوع (game أو app). لإضافة تطبيق اكتب app في خانة النوع.\n"
                "ابعث /cancel للإلغاء."
            )
            return

        if text == "🎁 إدارة متجر النقاط":
            context.user_data["admin_step"] = "point_offer_add"
            await message.reply_text("أرسل العرض بهذا الشكل:\nالاسم | الوصف | تكلفة النقاط | المخزون (-1 لمخزون غير محدود)\nمثال: اشتراك تجريبي | اشتراك رقمي | 200 | 10\nللإلغاء /cancel")
            return
        if text == "📬 طلبات الألعاب":
            with db() as conn: rows=conn.execute("SELECT * FROM game_requests ORDER BY id DESC LIMIT 30").fetchall()
            if not rows: await message.reply_text("لا توجد طلبات ألعاب."); return
            buttons=[]
            for r in rows:
                buttons.append([InlineKeyboardButton(f"#{r['id']} {r['request_text'][:35]} ({r['status']})",callback_data=f"game_request_status:{r['id']}:reviewed")])
            await message.reply_text("📬 طلبات الألعاب والتطبيقات الأخيرة:",reply_markup=InlineKeyboardMarkup(buttons)); return

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

        if text in ("💰 تعديل الأسعار", "💰 تعديل سعر عرض"):
            await message.reply_text(
                "💰 تعديل الأسعار\n\nاختار نوع الأسعار التي تريد تعديلها:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 أسعار الألعاب والتطبيقات / العروض", callback_data="price_menu_offers")],
                    [InlineKeyboardButton("🎵 أسعار عملة TikTok", callback_data="price_menu_tiktok")],
                    [InlineKeyboardButton("📏 حدود كمية TikTok", callback_data="price_menu_tiktok_limits")],
                ]),
            )
            return

        if text == "📋 كل الطلبات":
            await message.reply_text("📋 إدارة الطلبات:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("عرض جميع الطلبات", callback_data="adm_orders")], [InlineKeyboardButton("🗑️ حذف جميع الطلبات", callback_data="orders_delete_all")]]))
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
        if text in ("📏 حدود كمية TikTok", "🎵 سعر عملة TikTok"):
            await message.reply_text(
                "افتح 💰 تعديل الأسعار ثم اختار إعداد TikTok الذي تريد تغييره.",
                reply_markup=admin_keyboard(),
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

        if text in ("🔄 تحويل نوع الحساب", "🔄 تحويل زبون / تاجر"):
            context.user_data["admin_step"] = "account_convert_user_id"
            await message.reply_text("🔄 تحويل نوع الحساب\n\nأرسل Telegram ID للحساب الذي تريد تحويله إلى تاجر أو زبون.\nبعدها اختر النوع الجديد من الأزرار التي ستظهر لك.\n\nللإلغاء أرسل /cancel")
            return

        if text == "👥 التحكم في الأفراد":
            await admin_show_people(message, banned=False)
            return

        if text == "🗑️ حذف جميع الطلبات":
            with db() as conn:
                count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            await message.reply_text(f"🗑️ حذف جميع الطلبات\nعدد الطلبات الحالية: {count}\n\nسيتم حذف سجلات الطلبات فقط، ولن تتغير حسابات المستخدمين أو الأرصدة أو الألعاب والعروض. العملية لا يمكن التراجع عنها.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("متابعة إلى التأكيد", callback_data="orders_delete_all")], [InlineKeyboardButton("إلغاء", callback_data="adm_home")]]))
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
                label = f"{row['full_name'] or row['username'] or row['user_id']} | {row['order_count']} طلب | {row['total']} DA"
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
            context.user_data["admin_step"] = "notify_broadcast_message"
            await message.reply_text("📨 ابعث نص الإشعار الذي تريد إرساله لجميع المشتركين.\n\nابعث /cancel للإلغاء.")
            return

        if text == "🔙 القائمة الرئيسية":
            await message.reply_text(
                "🏠 القائمة الرئيسية.",
                reply_markup=main_keyboard(user_id),
            )
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
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("ordergames", order_games_command))
    app.add_handler(CommandHandler("setordergroup", set_order_group_command))

    # أزرار Inline
    app.add_handler(CallbackQueryHandler(callback_handler))

    # مشاركة رقم الهاتف اختيارية؛ إذا أرسل المستخدم رقمه نحفظه
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

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

import re
import os
import html
import json
import io
import sqlite3
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio
import base64
from types import SimpleNamespace

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    ForceReply,
    InputMediaPhoto,
)

from telegram.request import HTTPXRequest

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = (os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "seradj_store.db")
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "213671629818")
# Required channel subscription (configure these on the hosting panel).
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()
REQUIRED_CHANNEL_LINK = os.getenv("REQUIRED_CHANNEL_LINK", "").strip()
STORE_NAME = "SERADJ STORE"
STORE_BENEFITS_TEXT = '✨ مزايا متجرنا ✨\n\n🎮 شحن ألعابك بسهولة\nشحن بالـID، بالحساب ، مع خيارات متعددة للألعاب والعروض.\n\n⚡ سرعة وسهولة\nخطوات بسيطة لطلب الشحن ومتابعة طلباتك من داخل المتجر.\n\n🔐 خدمة آمنة ومنظمة\nطلباتك، محفظتك ونقاطك مرتبطة بحسابك داخل المتجر.\n\n⭐ نظام النقاط\nكل 1 DA تنفقه في طلب مكتمل = نقطة DA، وكل 1 USD = نقطة USD. تقدر تحول كل 100 نقطة إلى 1 من العملة نفسها في محفظتك.\n🔥 كلما تستعمل المتجر أكثر، عندك فرصة تجمع نقاط أكثر!\n\n👥 نظام الإحالة\nشارك رابطك مع أصدقائك، وكلما استخدموا المتجر وحققوا شروط الإحالة، تحصل على مكافآت في المحفظة ونقاط إضافية.\n💡 يعني تقدر تجمع نقاط حتى وأنت مرتاح، وأصدقاؤك هم اللي يستعملوا المتجر!\n\n👑 نظام VIP — مع ازدياد نشاطك وشحناتك، تقترب من مزايا VIP وخصوماته. 🚀\n\n💰 المحفظة\nاشحن محفظتك واستعمل رصيدك في طلباتك بسهولة، مع إمكانية الاستفادة من عروض وبونص الإيداع عند توفرها.\n\n🎁 مكافآت وعروض\nتابع المتجر باستمرار لأن العروض والمكافآت الجديدة تكون متاحة من وقت لآخر.\n\n🚀 الخلاصة: تشحن لعبتك، تجمع نقاط، تستفيد من VIP، وتشارك رابطك مع أصحابك لتزيد فرصك في المكافآت.\n\n❤️ استعمل المتجر… وكل عملية ممكن تكون بداية لمكافأة جديدة!'
TERMS_PRIVACY_TEXT = '📜 الشروط والأحكام وسياسة الخصوصية — SERADJ STORE \n\n1. الاستخدام\nباستخدامك للبوت، فإنك توافق على الالتزام بالشروط والأحكام وسياسة الخصوصية الخاصة بالمتجر.\n\n2. معلومات المستخدم\nقد يتم حفظ معرف Telegram، اسم المستخدم، الاسم الظاهر، معلومات الطلبات، معلومات الشحن التي ترسلها، ومعلومات المحفظة والنقاط والمعاملات المرتبطة بها.\n\n3. استخدام المعلومات\nتُستخدم هذه المعلومات لتقديم خدمات المتجر، معالجة الطلبات والدفع والشحن، تقديم الدعم الفني وتحسين الخدمة.\n\n4. عمليات الدفع\nأنت مسؤول عن التأكد من صحة بيانات الدفع والبيانات التي تقدمها قبل إرسال الطلب. لا ترسل كلمات المرور أو المعلومات الحساسة إلا عند الضرورة الفعلية للخدمة.\n\n5. الطلبات\nتأكد من صحة بيانات اللعبة والحساب قبل تأكيد الطلب، وقد تبدأ المعالجة بعد إرسال الطلب.\n\n6. المحفظة والنقاط\nأرصدة المحفظة والنقاط مرتبطة بحساب Telegram، ويمنع استغلال النظام أو إجراء عمليات وهمية أو متكررة للحصول على رصيد أو نقاط بشكل غير مشروع.\n\n7. الإحالات والمكافآت\nيمنع استخدام الحسابات الوهمية أو أي وسيلة للتحايل على نظام الإحالات والمكافآت. رابط الإحالة يُحتسب للمستخدم الجديد عند أول تشغيل فقط، ولا يمكن تغيير المحيل بعد ذلك.\n\n8. الدعم الفني\nيُستخدم الدعم للاستفسارات والمشاكل المتعلقة بالخدمة، ويمنع استخدامه للإزعاج أو إرسال طلبات متكررة أو غير متعلقة بالخدمة.\n\n9. إيقاف الخدمة\nيحتفظ المتجر بحق رفض أو إيقاف أي طلب يخالف الشروط أو يشتبه في وجود تلاعب أو إساءة استخدام.\n\n10. الخصوصية\nنحترم خصوصيتك ولا نستخدم المعلومات التي يتم جمعها إلا للأغراض المرتبطة بتقديم خدمات المتجر وإدارة الطلبات والدعم.\n\n11. الموافقة\nباستخدامك للبوت وإتمام أي عملية، فإنك تؤكد أنك قرأت هذه الشروط وسياسة الخصوصية ووافقت عليها.'
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

async def send_system_log(bot, message, level="INFO"):
    """Send a concise operational log to the admin-configured private log channel."""
    channel_id = get_setting("system_log_channel_id", "").strip()
    if not channel_id:
        return False
    try:
        await bot.send_message(chat_id=int(channel_id), text=f"{level} | SERADJ STORE\n{message}")
        return True
    except Exception:
        logger.exception("Could not send message to system log channel")
        return False

async def global_error_handler(update, context):
    err = context.error
    logger.error("Unhandled exception while processing update", exc_info=(type(err), err, err.__traceback__))
    summary = f"🔴 خطأ غير معالج\nالنوع: {type(err).__name__}\nالتفاصيل: {str(err)[:1200]}"
    await send_system_log(context.bot, summary, "ERROR")

# Runtime timers for 15-minute checkout sessions.
CART_TIMEOUT_TASKS = {}

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

async def marketing_reminder_loop(application):
    """Deliver persistent reminders; any existing order cancels pending reminders."""
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with db() as conn:
                conn.execute("""UPDATE marketing_reminders SET cancelled=1
                    WHERE cancelled=0 AND sent_at='' AND user_id IN
                    (SELECT DISTINCT user_id FROM orders)""")
                if get_setting("marketing_reminders_enabled", "1") == "1":
                    rows = conn.execute("""SELECT r.id,r.user_id,r.sequence_no
                        FROM marketing_reminders r JOIN users u ON u.user_id=r.user_id
                        WHERE r.cancelled=0 AND r.sent_at='' AND r.due_at<=?
                        AND COALESCE(u.is_banned,0)=0
                        AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.user_id=r.user_id)
                        ORDER BY r.due_at LIMIT 50""", (now,)).fetchall()
                else:
                    rows = []
            for row in rows:
                uid = int(row["user_id"])
                body = get_setting("marketing_reminder_text", "👋 ما زلت ما طلبتش؟ 🛍️ تصفح العروض الآن!")
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🛍️ تصفّح العروض", callback_data="browse_offers")]])
                try:
                    await application.bot.send_message(chat_id=uid, text=body, reply_markup=keyboard)
                    with db() as conn:
                        conn.execute("UPDATE marketing_reminders SET sent_at=? WHERE id=? AND sent_at=''", (now_text(), row["id"]))
                        count = max(0, min(10, int(get_setting("marketing_reminder_count", "2"))))
                        interval = max(1, int(get_setting("marketing_reminder_interval_minutes", "1440")))
                        if int(row["sequence_no"]) < count:
                            due = (datetime.now() + timedelta(minutes=interval)).strftime("%Y-%m-%d %H:%M:%S")
                            conn.execute("INSERT OR IGNORE INTO marketing_reminders(user_id,sequence_no,due_at) VALUES(?,?,?)",
                                         (uid, int(row["sequence_no"])+1, due))
                except Exception as exc:
                    logger.info("Marketing reminder failed for %s: %s", uid, exc)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Marketing reminder loop failed")
        await asyncio.sleep(30)


async def scheduled_broadcast_loop(application):
    """Send one-time admin-scheduled broadcasts, persisted in SQLite."""
    while True:
        try:
            now = datetime.now(STORE_TZ).strftime("%Y-%m-%d %H:%M:%S")
            with db() as conn:
                rows = conn.execute("SELECT id, message, entities_json FROM scheduled_broadcasts WHERE cancelled=0 AND sent_at='' AND due_at<=? ORDER BY due_at LIMIT 20", (now,)).fetchall()
                recipients = [int(r[0]) for r in conn.execute("SELECT user_id FROM users WHERE COALESCE(is_banned,0)=0").fetchall()]
            for row in rows:
                # Mark first to avoid duplicate sends if the process restarts during delivery.
                with db() as conn:
                    cur = conn.execute("UPDATE scheduled_broadcasts SET sent_at=? WHERE id=? AND sent_at='' AND cancelled=0", (now_text(), row['id']))
                    if cur.rowcount == 0:
                        continue
                # Send the exact original text so Telegram entity offsets (especially
                # custom_emoji entities) remain unchanged. Prefixing text can corrupt
                # entity offsets and make Premium emoji disappear or reject the message.
                try:
                    raw_entities = json.loads(row["entities_json"] or "[]")
                except (TypeError, ValueError, KeyError):
                    raw_entities = []
                from telegram import MessageEntity
                entities = [
                    MessageEntity.de_json(item, application.bot)
                    for item in raw_entities
                    if isinstance(item, dict) and item.get("type") and item.get("offset") is not None and item.get("length") is not None
                ]
                for uid in recipients:
                    try:
                        kwargs = {"entities": entities} if entities else {}
                        await application.bot.send_message(chat_id=uid, text=row['message'], **kwargs)
                    except Exception as exc:
                        logger.warning("Scheduled broadcast %s failed for user %s: %s", row['id'], uid, exc)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled broadcast loop failed")
        await asyncio.sleep(15)

async def post_init(application):
    application.create_task(scheduled_broadcast_loop(application), name="scheduled-broadcast-loop")
    application.create_task(store_schedule_loop(application), name="store-schedule-loop")
    application.create_task(marketing_reminder_loop(application), name="marketing-reminder-loop")
    await send_system_log(application.bot, "🟢 تم تشغيل البوت بنجاح.", "START")

CANCEL_WORDS = {
    "إلغاء", "الغاء", "❌ إلغاء", "/cancel"
}

MAIN_MENU = [
    ["✨ مزايا متجرنا"],
    ["👤 حسابي", "🛍️ المتجر"],
    ["➕ طلب لعبة غير موجودة"],
    ["🏪 ترقية الحساب إلى تاجر", "🎯 الإحالة"],
    ["🔐 السياسات والخصوصية", "📞 اتصل بالإدارة"],
]

ADMIN_MAIN_MENU = [
    ["🛠️ لوحة التحكم"],
    ["💰 طلبات التعبئة"],
    ["✨ مزايا متجرنا"],
    ["👤 حسابي", "🛍️ المتجر"],
    ["➕ طلب لعبة غير موجودة"],
    ["🏪 ترقية الحساب إلى تاجر", "🎯 الإحالة"],
    ["🔐 السياسات والخصوصية", "📞 اتصل بالإدارة"],
]

# لوحة الإدارة الرئيسية: أزرار قليلة وواضحة، وباقي الوظائف داخل أقسامها.
ADMIN_PANEL_MENU = [
    ["💰 طلبات التعبئة", "📦 الطلبات والعملاء"],
    ["👥 المشتركين والتجار", "🛍️ إدارة المتجر"],
    ["💎 الأسعار والرصيد", "📣 التسويق والتواصل"],
    ["⚙️ إعدادات البوت", "📊 التقارير والصيانة"],
    ["💳 إدارة الفليكسي"],
    ["🔙 القائمة الرئيسية"],
]

# Legacy layout retained for compatibility with saved references.
ADMIN_PANEL_MENU_OLD = [
    ["📦 الطلبات والعملاء", "👥 المشتركين والتجار"],
    ["🛍️ إدارة المتجر", "💎 الأسعار والرصيد"],
    ["📣 التسويق والتواصل", "⚙️ إعدادات البوت"],
    ["📊 التقارير والصيانة"],
    ["🔙 القائمة الرئيسية"],
]

ADMIN_SUBMENUS = {
    "📦 الطلبات والعملاء": [
        ["📋 كل الطلبات", "💰 طلبات تعبئة الرصيد"],
        ["🧪 الطلب التجريبي", "📬 طلبات الألعاب"],
        ["💬 مراجعة الآراء"],
        ["💬 مراسلة زبون"],
        ["🔙 لوحة الإدارة"],
    ],
    "👥 المشتركين والتجار": [
        ["👥 التحكم في الأفراد", "👥 إدارة التجار"],
        ["💰 ترتيب محافظ المشتركين"],
        ["🔄 تحويل زبون / تاجر"],
        ["🔙 لوحة الإدارة"],
    ],
    "🛍️ إدارة المتجر": [
        ["➕ إضافة", "🎮 إدارة الألعاب"],
        ["✨ إدارة إيموجيات Premium"],
        ["🔙 لوحة الإدارة"],
    ],
    "💎 الأسعار والرصيد": [
        ["💰 تعديل الأسعار", "💰 حدود تعبئة الرصيد"],
        ["💳 إعدادات الدفع"],
        ["🔙 لوحة الإدارة"],
    ],
    "📣 التسويق والتواصل": [
        ["📨 إرسال إشعار", "⏰ إشعار مجدول"],
        ["🛍️ التذكير التسويقي", "📢 إعدادات النشر للقناة"],
        ["📇 إعدادات التواصل"],
        ["🔙 لوحة الإدارة"],
    ],
    "⚙️ إعدادات البوت": [
        ["⚙️ إعدادات البوت", "📝 إدارة النصوص"],
        ["🕒 أوقات المتجر", "📂 إدارة البوت"],
        ["🔙 لوحة الإدارة"],
    ],
    "📊 التقارير والصيانة": [
        ["📊 الإحصائيات", "🧹 تصفير الحسابات والطلبات"],
        ["🗑️ حذف جميع الطلبات"],
        ["🔙 لوحة الإدارة"],
    ],
}

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_order_amount(value, currency="DA"):
    """Format stored order amounts without truncating fractional USD prices."""
    currency = (currency or "DA").upper()
    try:
        amount = Decimal(str(value if value is not None else 0))
        if currency == "USD":
            return f"{amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f} USD"
        return f"{amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP):,.0f} {currency}"
    except (InvalidOperation, ValueError):
        return f"{value} {currency}"


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


async def dispatch_order_to_group(context, order_id, user, draft, player_id, payment_method, price, points_used=0, photo=None, photo_ids=None):
    """Send an order to the group configured for its game, falling back to admin DM."""
    game_id = int(draft.get("game_id") or 0)
    group_id = get_setting("order_group_all", "").strip() or get_setting(f"order_group_{game_id}", "").strip()
    is_work_group = bool(group_id)
    if not group_id:
        group_id = str(ADMIN_ID) if ADMIN_ID else ""
    if not group_id:
        logger.warning("No order group/admin configured for order %s", order_id)
        return
    # In a configured work group, staff can claim the order as before.
    # When detached, send the owner a private review/complete/cancel keyboard.
    if is_work_group:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 استلام الطلب", callback_data=f"order_claim:{order_id}")]])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 مراجعة الطلب", callback_data=f"order_review:{order_id}")],
            [InlineKeyboardButton("✅ إتمام الطلب", callback_data=f"order_finish:{order_id}"),
             InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"order_cancel:{order_id}")],
        ])
    caption = (f"🆕 طلب جديد #{order_id}\n\n👤 الزبون: {user.full_name}\n🆔 Telegram ID: {user.id}\n"
               f"🎮 الخدمة: {draft.get('game_name','غير محددة')}\n📦 العرض: {draft.get('offer_name','غير محدد')}\n"
               f"📋 معلومات الشحن: {player_id or 'لا تتطلب'}\n📱 الجهاز: {draft.get('platform') or 'غير محدد'}\n"
               f"💰 السعر: {price} {draft.get('currency', 'DA')}\n" + f"🎁 النقاط المستخدمة: {points_used}\n💳 الدفع: {payment_method}\n📌 الحالة: قيد الانتظار")
    try:
        photo_ids = list(photo_ids or ([photo.file_id] if photo else []))
        if len(photo_ids) > 1:
            media = [InputMediaPhoto(media=fid, caption=caption if i == 0 else None) for i, fid in enumerate(photo_ids[:10])]
            await context.bot.send_media_group(chat_id=int(group_id), media=media)
            await context.bot.send_message(chat_id=int(group_id), text=f"🧾 التحكم في الطلب #{order_id}", reply_markup=keyboard)
        elif photo_ids:
            await context.bot.send_photo(chat_id=int(group_id), photo=photo_ids[0], caption=caption, reply_markup=keyboard)
        else:
            await context.bot.send_message(chat_id=int(group_id), text=caption, reply_markup=keyboard)
        # The group keyboard is visible to everyone, so send the detach control privately to the owner only.
        if is_work_group and ADMIN_ID and str(group_id) != str(ADMIN_ID):
            try:
                await context.bot.send_message(
                    chat_id=int(ADMIN_ID),
                    text=f"🔌 التحكم في استقبال الطلبات\n🎮 اللعبة: {draft.get('game_name', 'غير محددة')}\n🧾 الطلب: #{order_id}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔌 عزل الطلبات عن المجموعة", callback_data=("order_detach:all" if get_setting("order_group_all", "").strip() == str(group_id) else f"order_detach:{game_id}"))]])
                )
            except Exception:
                logger.exception("Could not send owner-only detach button for game %s", game_id)
    except Exception:
        logger.exception("Failed dispatching order %s to group %s", order_id, group_id)

def trader_group_for_chat(chat_id):
    with db() as conn:
        return conn.execute(
            "SELECT tg.*, u.account_type, u.trader_wallet_currency, u.balance, u.balance_usd, u.full_name "
            "FROM trader_work_groups tg LEFT JOIN users u ON u.user_id=tg.trader_id WHERE tg.group_id=?",
            (int(chat_id),),
        ).fetchone()


def trader_group_offer_page(group_id, page=0, per_page=8):
    offset = max(0, int(page)) * per_page
    with db() as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM offers o JOIN games g ON g.id=o.game_id WHERE o.active=1 AND g.active=1").fetchone()[0])
        rows = conn.execute(
            "SELECT o.id,o.name,o.game_id,g.name AS game_name,COALESCE(tgo.active,0) AS selected "
            "FROM offers o JOIN games g ON g.id=o.game_id "
            "LEFT JOIN trader_group_offers tgo ON tgo.offer_id=o.id AND tgo.group_id=? "
            "WHERE o.active=1 AND g.active=1 ORDER BY g.id,o.sort_order,o.id LIMIT ? OFFSET ?",
            (int(group_id), per_page, offset),
        ).fetchall()
    return rows, total


async def show_trader_group_offer_config(message, group_id, page=0, edit=False):
    per_page = 8
    rows, total = trader_group_offer_page(group_id, page, per_page)
    if not rows:
        text_out = "لا توجد عروض مفعّلة في المتجر لإضافتها إلى هذه المجموعة."
        if edit:
            await message.edit_text(text_out)
        else:
            await message.reply_text(text_out)
        return
    buttons = []
    for row in rows:
        icon = "✅" if int(row["selected"] or 0) else "➕"
        label = f"{icon} {row['game_name']} — {row['name']}"
        buttons.append([InlineKeyboardButton(label[:60], callback_data=f"tgcfg:{row['id']}:{page}")])
    pages = max(1, (total + per_page - 1) // per_page)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"tgcfgpage:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="tgcfgnop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"tgcfgpage:{page+1}"))
    buttons.append(nav)
    text_out = (
        "⚙️ العروض المتاحة في هذه المجموعة\n\n"
        "اضغط على العرض لإضافته أو إزالته من قائمة العروض التي يستطيع التاجر نشرها.\n"
        "✅ = متاح للتاجر | ➕ = غير مضاف"
    )
    if edit:
        await message.edit_text(text_out, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text(text_out, reply_markup=InlineKeyboardMarkup(buttons))


async def set_trader_group_command(update, context):
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    if not user or not is_admin(user.id):
        await message.reply_text("⛔ هذا الأمر خاص بمالك المتجر.")
        return
    if not chat or chat.type not in ("group", "supergroup"):
        await message.reply_text("استعمل الأمر داخل مجموعة التاجر: /settradergroup TELEGRAM_ID")
        return
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await message.reply_text("الاستعمال داخل مجموعة التاجر:\n/settradergroup TELEGRAM_ID\n\nيمكنك معرفة ID التاجر من بطاقة حسابه أو من أمر /myid.")
        return
    trader_id = int(context.args[0])
    with db() as conn:
        trader = conn.execute("SELECT user_id,full_name,account_type,trader_wallet_currency,balance,balance_usd FROM users WHERE user_id=?", (trader_id,)).fetchone()
        if not trader or trader["account_type"] != "trader":
            await message.reply_text("❌ هذا الحساب غير موجود أو ليس تاجراً معتمداً.")
            return
        existing = conn.execute("SELECT group_id FROM trader_work_groups WHERE trader_id=?", (trader_id,)).fetchone()
        if existing and int(existing["group_id"]) != int(chat.id):
            await message.reply_text(f"❌ هذا التاجر مربوط بمجموعة أخرى ({existing['group_id']}). افصل الربط القديم أولاً بالأمر /unsettradergroup داخل المجموعة القديمة.")
            return
        conn.execute(
            "INSERT INTO trader_work_groups(group_id,trader_id,created_at) VALUES(?,?,?) "
            "ON CONFLICT(group_id) DO UPDATE SET trader_id=excluded.trader_id",
            (int(chat.id), trader_id, now_text()),
        )
    currency = "USD" if str(trader["trader_wallet_currency"] or "DA").upper() == "USD" else "DA"
    balance = float(trader["balance_usd"] or 0) if currency == "USD" else float(trader["balance"] or 0)
    await message.reply_text(
        f"✅ تم ربط المجموعة بالتاجر {trader['full_name'] or trader_id}.\n"
        f"🆔 Telegram ID: {trader_id}\n💰 المحفظة المرتبطة: {currency}\n"
        f"💳 الرصيد الحالي: {balance:g} {currency}\n\n"
        "التاجر يستطيع نشر العروض المحددة فقط عبر /publish."
    )


async def unset_trader_group_command(update, context):
    user = update.effective_user
    chat = update.effective_chat
    if not user or not is_admin(user.id):
        await update.effective_message.reply_text("⛔ هذا الأمر خاص بمالك المتجر.")
        return
    if not chat or chat.type not in ("group", "supergroup"):
        await update.effective_message.reply_text("استعمل الأمر داخل المجموعة المراد فصلها.")
        return
    with db() as conn:
        conn.execute("DELETE FROM trader_work_groups WHERE group_id=?", (int(chat.id),))
        conn.execute("DELETE FROM trader_group_offers WHERE group_id=?", (int(chat.id),))
    await update.effective_message.reply_text("🔌 تم فصل المجموعة عن محفظة التاجر وحذف إعدادات عروضها. سجلات الطلبات السابقة تبقى محفوظة.")


async def trader_group_offers_command(update, context):
    user = update.effective_user
    chat = update.effective_chat
    if not user or not is_admin(user.id):
        await update.effective_message.reply_text("⛔ هذا الأمر خاص بمالك المتجر.")
        return
    if not chat or chat.type not in ("group", "supergroup"):
        await update.effective_message.reply_text("استعمل الأمر داخل مجموعة التاجر.")
        return
    if not trader_group_for_chat(chat.id):
        await update.effective_message.reply_text("❌ هذه المجموعة غير مربوطة بتاجر. اربطها أولاً بالأمر /settradergroup TELEGRAM_ID.")
        return
    await show_trader_group_offer_config(update.effective_message, chat.id, 0)


async def trader_publish_command(update, context):
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    if not user or not chat or chat.type not in ("group", "supergroup"):
        await message.reply_text("استعمل /publish داخل مجموعة التاجر.")
        return
    group = trader_group_for_chat(chat.id)
    if not group:
        await message.reply_text("❌ هذه المجموعة غير مربوطة بتاجر.")
        return
    if int(group["trader_id"]) != int(user.id):
        await message.reply_text("⛔ نشر العروض متاح للتاجر المرتبط بهذه المجموعة فقط.")
        return
    with db() as conn:
        rows = conn.execute(
            "SELECT o.id,o.name,o.game_id,g.name AS game_name FROM trader_group_offers tgo "
            "JOIN offers o ON o.id=tgo.offer_id JOIN games g ON g.id=o.game_id "
            "WHERE tgo.group_id=? AND tgo.active=1 AND o.active=1 AND g.active=1 ORDER BY g.id,o.sort_order,o.id",
            (int(chat.id),),
        ).fetchall()
    if not rows:
        await message.reply_text("لا توجد عروض متاحة للنشر في هذه المجموعة. اطلب من الإدارة ضبطها عبر /groupoffers.")
        return
    buttons = [[InlineKeyboardButton(f"{r['game_name']} — {r['name']}"[:60], callback_data=f"tgp:{r['id']}")] for r in rows]
    await message.reply_text("📣 اختر العرض الذي تريد نشره في المجموعة:", reply_markup=InlineKeyboardMarkup(buttons))


async def handle_trader_group_callback(query, context, data):
    """Handle trader-group offer publication, acceptance, cancellation and completion."""
    user_id = int(query.from_user.id)
    chat = query.message.chat if query.message else None
    chat_id = int(chat.id) if chat else 0

    if data == "tgcfgnop":
        await query.answer()
        return True
    if data.startswith("tgcfgpage:"):
        if not is_admin(user_id) or not chat or chat.type not in ("group", "supergroup"):
            await query.answer("هذا الإجراء خاص بالإدارة وداخل مجموعة التاجر.", show_alert=True)
            return True
        try:
            page = max(0, int(data.split(":", 1)[1]))
        except ValueError:
            await query.answer("صفحة غير صالحة.", show_alert=True); return True
        await query.answer()
        await show_trader_group_offer_config(query.message, chat_id, page, edit=True)
        return True
    if data.startswith("tgcfg:"):
        if not is_admin(user_id) or not chat or chat.type not in ("group", "supergroup"):
            await query.answer("هذا الإجراء خاص بالإدارة وداخل مجموعة التاجر.", show_alert=True)
            return True
        try:
            _, offer_text, page_text = data.split(":", 2)
            offer_id, page = int(offer_text), int(page_text)
        except ValueError:
            await query.answer("بيانات العرض غير صالحة.", show_alert=True); return True
        with db() as conn:
            selected = conn.execute("SELECT active FROM trader_group_offers WHERE group_id=? AND offer_id=?", (chat_id, offer_id)).fetchone()
            if selected and int(selected["active"] or 0):
                conn.execute("UPDATE trader_group_offers SET active=0 WHERE group_id=? AND offer_id=?", (chat_id, offer_id))
            else:
                conn.execute("INSERT INTO trader_group_offers(group_id,offer_id,active) VALUES(?,?,1) ON CONFLICT(group_id,offer_id) DO UPDATE SET active=1", (chat_id, offer_id))
        await query.answer("تم تحديث العروض المتاحة.")
        await show_trader_group_offer_config(query.message, chat_id, page, edit=True)
        return True

    if data.startswith("tgp:"):
        if not chat or chat.type not in ("group", "supergroup"):
            await query.answer("انشر العروض من داخل المجموعة.", show_alert=True); return True
        group = trader_group_for_chat(chat_id)
        if not group or int(group["trader_id"]) != user_id:
            await query.answer("النشر متاح للتاجر المرتبط بهذه المجموعة فقط.", show_alert=True); return True
        try:
            offer_id = int(data.split(":", 1)[1])
        except ValueError:
            await query.answer("العرض غير صالح.", show_alert=True); return True
        currency = "USD" if str(group["trader_wallet_currency"] or "DA").upper() == "USD" else "DA"
        with db() as conn:
            offer = conn.execute("SELECT o.*,g.name AS game_name FROM offers o JOIN games g ON g.id=o.game_id "
                                 "JOIN trader_group_offers tgo ON tgo.offer_id=o.id AND tgo.group_id=? AND tgo.active=1 "
                                 "WHERE o.id=? AND o.active=1 AND g.active=1", (chat_id, offer_id)).fetchone()
        if not offer:
            await query.answer("هذا العرض غير متاح في هذه المجموعة.", show_alert=True); return True
        try:
            price = Decimal(str(trader_offer_price(offer, int(group["trader_id"]))))
        except Exception:
            await query.answer("تعذر تحديد سعر التاجر لهذا العرض.", show_alert=True); return True
        if not price.is_finite() or price <= 0:
            await query.answer("سعر التاجر لهذا العرض غير مضبوط.", show_alert=True); return True
        price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if currency == "USD" else price.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO trader_group_deals(group_id,trader_id,offer_id,game_name,offer_name,price,currency,status,published_by,created_at) "
                "VALUES(?,?,?,?,?,?,?,'open',?,?)",
                (chat_id, int(group["trader_id"]), offer_id, offer["game_name"], offer["name"], float(price), currency, user_id, now_text()),
            )
            deal_id = int(cur.lastrowid)
        label = f"{price:g} {currency}"
        deal_text = (f"📣 عرض شحن جديد #{deal_id}\n\n🎮 اللعبة: {offer['game_name']}\n"
                     f"📦 العرض: {offer['name']}\n💰 السعر: {label}\n\n"
                     "اضغط على قبول العرض إذا كنت مستعدًا لتنفيذه. سيتم الخصم مباشرة من محفظة التاجر.")
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🟢 قبول العرض", callback_data=f"tga:{deal_id}")]])
        try:
            posted = await context.bot.send_message(chat_id=chat_id, text=deal_text, reply_markup=keyboard)
            with db() as conn:
                conn.execute("UPDATE trader_group_deals SET posted_message_id=? WHERE id=?", (posted.message_id, deal_id))
            await query.answer("تم نشر العرض في المجموعة.", show_alert=True)
            try:
                await query.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        except Exception:
            with db() as conn:
                conn.execute("UPDATE trader_group_deals SET status='cancelled',cancelled_by=?,cancelled_at=? WHERE id=? AND status='open'", (user_id, now_text(), deal_id))
            await query.answer("تعذر نشر العرض. تأكد أن البوت يستطيع إرسال الرسائل في المجموعة.", show_alert=True)
        return True

    if data.startswith("tga:"):
        if not chat or chat.type not in ("group", "supergroup"):
            await query.answer("هذا الزر يعمل داخل مجموعة التاجر فقط.", show_alert=True); return True
        try:
            deal_id = int(data.split(":", 1)[1])
        except ValueError:
            await query.answer("رقم الطلب غير صالح.", show_alert=True); return True
        try:
            with db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                deal = conn.execute("SELECT * FROM trader_group_deals WHERE id=? AND group_id=?", (deal_id, chat_id)).fetchone()
                if not deal or deal["status"] != "open":
                    await query.answer("هذا العرض تم قبوله أو إغلاقه مسبقًا.", show_alert=True); return True
                if int(deal["trader_id"]) == user_id:
                    await query.answer("التاجر لا يمكنه قبول عرضه بنفسه.", show_alert=True); return True
                col = "balance_usd" if deal["currency"] == "USD" else "balance"
                wallet = conn.execute(f"SELECT COALESCE({col},0) AS bal FROM users WHERE user_id=? AND account_type='trader'", (deal["trader_id"],)).fetchone()
                if not wallet:
                    await query.answer("محفظة التاجر غير موجودة.", show_alert=True); return True
                before = Decimal(str(wallet["bal"] or 0))
                amount = Decimal(str(deal["price"] or 0))
                if before < amount:
                    await query.answer(f"رصيد التاجر غير كافٍ. المتوفر: {before:g} {deal['currency']}", show_alert=True); return True
                after = before - amount
                changed = conn.execute(f"UPDATE users SET {col}=? WHERE user_id=? AND COALESCE({col},0)>=?", (float(after), deal["trader_id"], float(amount)))
                if changed.rowcount != 1:
                    await query.answer("تعذر الخصم بسبب تغير الرصيد. أعد المحاولة.", show_alert=True); return True
                claimed = conn.execute("UPDATE trader_group_deals SET status='accepted',accepted_by=?,accepted_at=? WHERE id=? AND status='open'", (user_id, now_text(), deal_id))
                if claimed.rowcount != 1:
                    raise RuntimeError("Deal was claimed concurrently")
                conn.execute("INSERT INTO wallet_transactions(user_id,currency,kind,amount,balance_before,balance_after,note,admin_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                             (deal["trader_id"], deal["currency"], "خصم طلب مجموعة", float(amount), float(before), float(after),
                              f"طلب مجموعة #{deal_id} | المنفذ Telegram ID: {user_id} | {deal['game_name']} - {deal['offer_name']}", user_id, now_text()))
        except Exception as exc:
            logger.exception("Trader group deal acceptance failed")
            await query.answer("حدث خطأ ولم يتم تأكيد قبول العرض أو خصمه. حاول مجددًا.", show_alert=True)
            return True
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📦 استلام الطلب", callback_data=f"tgr:{deal_id}"), InlineKeyboardButton("🔴 إلغاء الطلب", callback_data=f"tgc:{deal_id}")]])
        try:
            await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
        await query.answer("تم قبول العرض وخصمه من محفظة التاجر.", show_alert=True)
        await query.message.reply_text(
            f"🟢 تم قبول العرض #{deal_id}\n👤 المنفذ: {query.from_user.full_name}\n"
            f"💸 المخصوم: {amount:g} {deal['currency']}\n💳 رصيد التاجر المتبقي: {after:g} {deal['currency']}"
        )
        return True

    if data.startswith("tgc:"):
        if not chat or chat.type not in ("group", "supergroup"):
            await query.answer("هذا الزر يعمل داخل مجموعة التاجر فقط.", show_alert=True); return True
        try:
            deal_id = int(data.split(":", 1)[1])
        except ValueError:
            await query.answer("رقم الطلب غير صالح.", show_alert=True); return True
        try:
            with db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                deal = conn.execute("SELECT * FROM trader_group_deals WHERE id=? AND group_id=?", (deal_id, chat_id)).fetchone()
                if not deal or deal["status"] != "accepted":
                    await query.answer("لا يمكن إلغاء هذا الطلب؛ ربما تمت معالجته مسبقًا.", show_alert=True); return True
                if user_id != int(deal["accepted_by"] or 0) and not is_admin(user_id):
                    await query.answer("إلغاء الطلب متاح لمن قبله أو لمالك المتجر فقط.", show_alert=True); return True
                col = "balance_usd" if deal["currency"] == "USD" else "balance"
                wallet = conn.execute(f"SELECT COALESCE({col},0) AS bal FROM users WHERE user_id=?", (deal["trader_id"],)).fetchone()
                if not wallet:
                    await query.answer("محفظة التاجر غير موجودة.", show_alert=True); return True
                before = Decimal(str(wallet["bal"] or 0)); amount = Decimal(str(deal["price"] or 0)); after = before + amount
                changed = conn.execute(f"UPDATE trader_group_deals SET status='cancelled',cancelled_by=?,cancelled_at=? WHERE id=? AND status='accepted'", (user_id, now_text(), deal_id))
                if changed.rowcount != 1:
                    raise RuntimeError("Deal cancellation race")
                conn.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (float(after), deal["trader_id"]))
                conn.execute("INSERT INTO wallet_transactions(user_id,currency,kind,amount,balance_before,balance_after,note,admin_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                             (deal["trader_id"], deal["currency"], "استرجاع طلب مجموعة", float(amount), float(before), float(after),
                              f"إلغاء الطلب #{deal_id} | ألغاه Telegram ID: {user_id}", user_id, now_text()))
        except Exception:
            logger.exception("Trader group deal cancellation failed")
            await query.answer("حدث خطأ أثناء الإلغاء؛ لم يتم تأكيد العملية.", show_alert=True); return True
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.answer("تم إلغاء الطلب وإرجاع المبلغ إلى محفظة التاجر.", show_alert=True)
        await query.message.reply_text(f"🔴 تم إلغاء الطلب #{deal_id}.\n↩️ المسترجع: {amount:g} {deal['currency']}\n💳 رصيد التاجر الجديد: {after:g} {deal['currency']}")
        return True

    if data.startswith("tgr:"):
        if not chat or chat.type not in ("group", "supergroup"):
            await query.answer("هذا الزر يعمل داخل مجموعة التاجر فقط.", show_alert=True); return True
        try:
            deal_id = int(data.split(":", 1)[1])
        except ValueError:
            await query.answer("رقم الطلب غير صالح.", show_alert=True); return True
        with db() as conn:
            deal = conn.execute("SELECT * FROM trader_group_deals WHERE id=? AND group_id=?", (deal_id, chat_id)).fetchone()
            if not deal or deal["status"] != "accepted":
                await query.answer("الطلب غير متاح للاستلام أو تمت معالجته.", show_alert=True); return True
            if user_id != int(deal["accepted_by"] or 0) and not is_admin(user_id):
                await query.answer("استلام الطلب متاح لمن قبله أو لمالك المتجر فقط.", show_alert=True); return True
            changed = conn.execute("UPDATE trader_group_deals SET status='completed',completed_by=?,completed_at=? WHERE id=? AND status='accepted'", (user_id, now_text(), deal_id))
            if changed.rowcount != 1:
                await query.answer("تمت معالجة الطلب مسبقًا.", show_alert=True); return True
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.answer("تم تأكيد استلام الطلب وإغلاقه.", show_alert=True)
        await query.message.reply_text(f"✅ تم استلام وإكمال الطلب #{deal_id}.\n👤 المنفذ: {query.from_user.full_name}\n📌 الحالة: مكتمل. لا يوجد استرجاع للمبلغ.")
        return True
    return False


async def _send_trader_history_page(target, target_id, section="deals", page=0, edit=False):
    page = max(0, int(page))
    per_page = 8
    with db() as conn:
        trader = conn.execute(
            "SELECT user_id,full_name,account_type,trader_wallet_currency,balance,balance_usd FROM users WHERE user_id=?",
            (target_id,),
        ).fetchone()
        if not trader or trader["account_type"] != "trader":
            text = "❌ لم يتم العثور على تاجر معتمد بهذا Telegram ID."
            if edit:
                await target.edit_message_text(text)
            else:
                await target.reply_text(text)
            return
        group = conn.execute("SELECT group_id FROM trader_work_groups WHERE trader_id=?", (target_id,)).fetchone()
        if section == "wallet":
            total = int(conn.execute("SELECT COUNT(*) FROM wallet_transactions WHERE user_id=?", (target_id,)).fetchone()[0])
            rows = conn.execute(
                "SELECT currency,kind,amount,balance_before,balance_after,note,admin_id,created_at "
                "FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (target_id, per_page, page * per_page),
            ).fetchall()
        else:
            section = "deals"
            total = int(conn.execute("SELECT COUNT(*) FROM trader_group_deals WHERE trader_id=?", (target_id,)).fetchone()[0])
            rows = conn.execute(
                "SELECT id,game_name,offer_name,price,currency,status,published_by,accepted_by,accepted_at,"
                "completed_by,completed_at,cancelled_by,cancelled_at,created_at "
                "FROM trader_group_deals WHERE trader_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (target_id, per_page, page * per_page),
            ).fetchall()

    currency = "USD" if str(trader["trader_wallet_currency"] or "DA").upper() == "USD" else "DA"
    balance = float(trader["balance_usd"] or 0) if currency == "USD" else float(trader["balance"] or 0)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages - 1)
    header = (
        f"📊 سجل التاجر: {trader['full_name'] or target_id}\n"
        f"🆔 Telegram ID: {target_id} | 👥 المجموعة: {group['group_id'] if group else 'غير مربوط'}\n"
        f"💳 المحفظة: {currency} | الرصيد الحالي: {balance:g} {currency}\n\n"
    )
    lines = []
    if section == "deals":
        lines.append(f"📦 سجل العروض والطلبات — الصفحة {page+1}/{pages} (الإجمالي: {total})")
        names = {"open": "🟡 منشور ولم يُقبل", "accepted": "🔵 مقبول وقيد التنفيذ", "completed": "✅ مكتمل", "cancelled": "🔴 ملغى"}
        if not rows:
            lines.append("لا توجد عمليات في المجموعة بعد.")
        for d in rows:
            line = (f"\n#{d['id']} | {d['game_name']} — {d['offer_name']}\n"
                    f"💰 {float(d['price']):g} {d['currency']} | {names.get(d['status'], d['status'])}\n"
                    f"🕒 النشر: {d['created_at'] or '-'}")
            if d["accepted_by"]:
                line += f"\n👤 قبله: {d['accepted_by']} ({d['accepted_at'] or '-'})"
            if d["completed_by"]:
                line += f"\n📦 الاستلام: {d['completed_by']} ({d['completed_at'] or '-'})"
            if d["cancelled_by"]:
                line += f"\n❌ الإلغاء: {d['cancelled_by']} ({d['cancelled_at'] or '-'})"
            lines.append(line)
    else:
        lines.append(f"💳 سجل معاملات المحفظة — الصفحة {page+1}/{pages} (الإجمالي: {total})")
        if not rows:
            lines.append("لا توجد معاملات مسجلة في المحفظة.")
        for r in rows:
            unit = "USD" if r["currency"] == "USD" else "DA"
            lines.append(
                f"\n🕒 {r['created_at'] or '-'}\n{r['kind']} | {float(r['amount']):g} {unit}\n"
                f"الرصيد: {float(r['balance_before']):g} ← {float(r['balance_after']):g} {unit}\n"
                f"السبب: {r['note'] or '-'}"
            )
    buttons = [[
        InlineKeyboardButton("📦 سجل العروض", callback_data=f"history:{target_id}:deals:0"),
        InlineKeyboardButton("💳 سجل المحفظة", callback_data=f"history:{target_id}:wallet:0"),
    ]]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"history:{target_id}:{section}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="history:noop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"history:{target_id}:{section}:{page+1}"))
    if nav:
        buttons.append(nav)
    markup = InlineKeyboardMarkup(buttons)
    text = header + "\n".join(lines)
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.reply_text(text, reply_markup=markup)


async def trader_history_command(update, context):
    """Show paginated trader group-deal and wallet history."""
    message, user = update.effective_message, update.effective_user
    if not message or not user:
        return
    target_id = None
    if context.args:
        if not is_admin(user.id):
            await message.reply_text("⛔ عرض سجل تاجر آخر متاح لمالك المتجر فقط.")
            return
        if not context.args[0].lstrip("-").isdigit():
            await message.reply_text("الاستعمال: /history TELEGRAM_ID")
            return
        target_id = int(context.args[0])
    elif is_admin(user.id):
        chat = update.effective_chat
        linked = trader_group_for_chat(chat.id) if chat and chat.type in ("group", "supergroup") else None
        if not linked:
            await message.reply_text("استعمل /history TELEGRAM_ID أو نفّذ الأمر داخل مجموعة تاجر مرتبطة.")
            return
        target_id = int(linked["trader_id"])
    else:
        with db() as conn:
            own = conn.execute("SELECT account_type FROM users WHERE user_id=?", (user.id,)).fetchone()
        if not own or own["account_type"] != "trader":
            await message.reply_text("⛔ هذا الأمر متاح للتجار ومالك المتجر فقط.")
            return
        target_id = int(user.id)
    await _send_trader_history_page(message, target_id, "deals", 0, edit=False)


async def set_order_group_command(update, context):
    """In a group, admin runs /setordergroup GAME_ID to route that game's orders here."""
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔ الأمر خاص بمالك المتجر.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await update.effective_message.reply_text("استعمل هذا الأمر داخل القروب الذي تريد استقبال الطلبات فيه: /setordergroup GAME_ID")
        return
    if not context.args:
        await update.effective_message.reply_text("الاستعمال: /setordergroup all أو /setordergroup GAME_ID")
        return
    if context.args[0].lower() == "all":
        with db() as conn:
            conn.execute("INSERT INTO settings(key,value) VALUES('order_group_all',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(chat.id),))
        await update.effective_message.reply_text(
            "✅ تم ربط هذا القروب بجميع طلبات المتجر الجديدة.\nهذا القروب مخصص لاستلام الطلبات والوصول فقط.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    if not context.args[0].isdigit():
        await update.effective_message.reply_text("الاستعمال: /setordergroup all أو /setordergroup GAME_ID")
        return
    game_id = int(context.args[0])
    with db() as conn:
        game = conn.execute("SELECT name FROM games WHERE id=?", (game_id,)).fetchone()
        if not game:
            await update.effective_message.reply_text("❌ ما لقيتش لعبة بهذا الرقم. شوف /ordergames.")
            return
        conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (f"order_group_{game_id}", str(chat.id)))
    await update.effective_message.reply_text(
        f"✅ تم ربط {game['name']} بهذا القروب.\nهذا القروب مخصص لاستلام الطلبات والوصول فقط.",
        reply_markup=ReplyKeyboardRemove(),
    )

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


LANGUAGE_TEXTS = {
    "ar": {
        "language": "🌐 اللغة", "choose_language": "اختر لغة واجهة المتجر:",
        "language_saved": "✅ تم تغيير لغة المتجر إلى العربية.",
        "dashboard": "🎛️ لوحة التحكم", "account": "👤 حسابي", "store": "🛍️ المتجر", "benefits": "✨ مزايا متجرنا",
        "orders": "📦 طلباتي", "deposit": "💰 تعبئة الرصيد", "referral": "🎯 الإحالة والنقاط",
        "request": "➕ طلب لعبة غير موجودة", "upgrade": "🏪 ترقية الحساب إلى تاجر",
        "admin": "🛡️ لوحة الإدارة", "welcome": "🎮 مرحباً بك في {store}!\n\n🛍️ شحن الألعاب والخدمات الرقمية\n💳 الدفع عبر BaridiMob / CCP أو Flexy\n\nاختر الخدمة من القائمة بالأسفل 👇",
        "store_choose": "🛍️ اختار القسم لي حاب تتصفح:", "games": "🎮 الألعاب", "apps": "📱 التطبيقات",
        "back": "🔙 القائمة الرئيسية", "account_title": "👤 حسابك في SERADJ STORE",
        "id": "🆔 ID", "name": "👤 الاسم", "type": "🏷️ نوع الحساب", "trader": "تاجر معتمد", "customer": "زبون عادي",
        "order_count": "📦 عدد الطلبات", "wallet_da": "💰 محفظة الدينار", "wallet_usd": "💵 محفظة الدولار",
        "points": "🎁 النقاط", "account_orders": "📦 طلباتي", "account_deposit": "💰 تعبئة المحفظة", "wallet_history": "📜 سجل المحفظة",
        "contact": "📞 اتصل بالإدارة", "privacy": "🔐 الخصوصية والسياسات", "username": "🔗 اسم المستخدم",
        "not_available": "غير متوفر", "not_registered": "أرسل /start لتسجيل حسابك.",
        "account_points": "⭐ نقاطي", "benefits_text": "✨ مزايا متجرنا ✨\n\n🎮 شحن ألعابك بسهولة\nشحن بالـID أو بالحساب، مع خيارات متعددة للألعاب والعروض.\n\n⚡ سرعة وسهولة\nخطوات بسيطة لطلب الشحن ومتابعة طلباتك.\n\n🔐 خدمة آمنة ومنظمة\nطلباتك ومحفظتك ونقاطك مرتبطة بحسابك.\n\n⭐ نظام النقاط والإحالة\nاجمع النقاط وشارك رابطك مع أصدقائك للاستفادة من المكافآت.\n\n💰 المحفظة\nاشحن محفظتك واستعمل رصيدك في الطلبات.",
        "referral_title": "🎯 نظام الإحالة والمكافآت", "referral_link": "رابطك", "points_da": "نقاط DA", "points_usd": "نقاط USD",
        "request_prompt": "🎮 اكتب اسم اللعبة أو التطبيق الذي تريد إضافته، ويمكنك ذكر تفاصيل النسخة أو طريقة الشحن. أرسل /cancel للإلغاء.",
        "deposit_choose": "💰 اختر المحفظة التي تريد تعبئتها:", "deposit_da": "🇩🇿 محفظة الدينار DA", "deposit_usd": "💵 محفظة الدولار USD",
        "orders_prompt": "📦 لعرض طلباتك اضغط الزر أدناه:", "view_orders": "عرض طلباتي", "upgrade_prompt": "🏪 لطلب ترقية حسابك إلى تاجر، اتصل بالإدارة من الزر الموجود أسفل المحادثة.",
        "referral_unavailable": "🎯 نظام الإحالة غير متاح حالياً.", "referral_link_unavailable": "تعذر إنشاء الرابط الآن.",
    },
    "en": {
        "language": "🌐 Language", "choose_language": "Choose your store interface language:",
        "language_saved": "✅ Store language changed to English.",
        "dashboard": "🎛️ Control Panel", "account": "👤 My Account", "store": "🛍️ Store", "benefits": "✨ Store Benefits",
        "orders": "📦 My Orders", "deposit": "💰 Top Up Wallet", "referral": "🎯 Referrals & Points",
        "request": "➕ Request a Missing Game", "upgrade": "🏪 Become a Trader",
        "admin": "🛡️ Admin Panel", "welcome": "🎮 Welcome to {store}!\n\n🛍️ Game top-ups and digital services\n💳 Pay via BaridiMob / CCP or Flexy\n\nChoose a service below 👇",
        "store_choose": "🛍️ Choose a category to browse:", "games": "🎮 Games", "apps": "📱 Apps",
        "back": "🔙 Main Menu", "account_title": "👤 Your SERADJ STORE Account",
        "id": "🆔 ID", "name": "👤 Name", "type": "🏷️ Account type", "trader": "Verified trader", "customer": "Customer",
        "order_count": "📦 Orders", "wallet_da": "💰 DZD Wallet", "wallet_usd": "💵 USD Wallet",
        "points": "🎁 Points", "account_orders": "📦 My Orders", "account_deposit": "💰 Top Up Wallet", "wallet_history": "📜 Wallet History",
        "contact": "📞 Contact Admin", "privacy": "🔐 Privacy & Policies", "username": "🔗 Username",
        "not_available": "Not available", "not_registered": "Send /start to register your account.",
        "account_points": "⭐ My Points", "benefits_text": "✨ Store Benefits ✨\n\n🎮 Easy game top-ups\nTop up by ID or account, with multiple games and offers.\n\n⚡ Fast and simple\nA few steps to place and track your orders.\n\n🔐 Safe and organized service\nYour orders, wallet and points are linked to your account.\n\n⭐ Points and referrals\nEarn points and share your referral link to receive rewards.\n\n💰 Wallet\nTop up your wallet and use your balance for orders.",
        "referral_title": "🎯 Referral & Rewards", "referral_link": "Your link", "points_da": "DA Points", "points_usd": "USD Points",
        "request_prompt": "🎮 Enter the name of the game or app you want us to add. You can include version or top-up details. Send /cancel to cancel.",
        "deposit_choose": "💰 Choose the wallet you want to top up:", "deposit_da": "🇩🇿 DZD Wallet", "deposit_usd": "💵 USD Wallet",
        "orders_prompt": "📦 Press the button below to view your orders:", "view_orders": "View My Orders", "upgrade_prompt": "🏪 To upgrade your account to trader, contact the administration using the button below the chat.",
        "referral_unavailable": "🎯 The referral system is currently unavailable.", "referral_link_unavailable": "Unable to create the link right now.",
    },

}

def user_language(user_id):
    row = get_user_row(user_id)
    lang = (row["language"] if row and "language" in row.keys() else "ar") or "ar"
    return lang if lang in LANGUAGE_TEXTS else "ar"

def tr(user_id, key, **kwargs):
    lang = user_language(user_id)
    value = LANGUAGE_TEXTS.get(lang, LANGUAGE_TEXTS["ar"]).get(key, LANGUAGE_TEXTS["ar"].get(key, key))
    return value.format(**kwargs) if kwargs else value

def contact_admin_keyboard():
    """Build contact options from the admin-configured store settings."""
    rows = []
    wa = re.sub(r"[^0-9]", "", get_setting("whatsapp_number", WHATSAPP_NUMBER))
    telegram_url = (get_setting("telegram_url", "") or "").strip()
    facebook_url = (get_setting("facebook_url", "") or "").strip()
    if wa:
        rows.append([InlineKeyboardButton("💬 WhatsApp", url=f"https://wa.me/{wa}")])
    if telegram_url.startswith(("https://t.me/", "http://t.me/", "https://telegram.me/")):
        rows.append([InlineKeyboardButton("✈️ Telegram", url=telegram_url)])
    if facebook_url.startswith(("https://", "http://")):
        rows.append([InlineKeyboardButton("📘 Facebook", url=facebook_url)])
    rows.append([InlineKeyboardButton("💬 مراسلة الإدارة هنا", callback_data="contact:start")])
    return InlineKeyboardMarkup(rows)


def main_keyboard(user_id):
    # Keep only the three permanent customer controls in the reply keyboard.
    # All shop navigation is presented as inline buttons in the current message.
    lang = user_language(user_id)
    labels = {
        "ar": ("📞 اتصل بالإدارة", "🔐 الخصوصية والسياسات"),
        "en": ("📞 Contact Admin", "🔐 Privacy & Policies"),
    }
    contact_label, policy_label = labels.get(lang, labels["ar"])
    keyboard = [["/start"], [contact_label], [policy_label]]
    # Keep the administrator entry visible at the very bottom of the persistent keyboard.
    if is_admin(user_id):
        keyboard.append(["🛠️ لوحة التحكم"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def customer_inline_menu(user_id):
    rows = [
        [InlineKeyboardButton(tr(user_id, "account"), callback_data="home:account"), InlineKeyboardButton(tr(user_id, "store"), callback_data="home:store")],
        [InlineKeyboardButton(tr(user_id, "benefits"), callback_data="home:benefits"), InlineKeyboardButton(tr(user_id, "orders"), callback_data="home:orders")],
        [InlineKeyboardButton(tr(user_id, "deposit"), callback_data="home:deposit"), InlineKeyboardButton(tr(user_id, "referral"), callback_data="home:referral")],
        [InlineKeyboardButton(tr(user_id, "request"), callback_data="home:request")],
        [InlineKeyboardButton(tr(user_id, "language"), callback_data="language_menu")],
    ]
    if not is_trader(user_id):
        rows.append([InlineKeyboardButton(tr(user_id, "upgrade"), callback_data="home:upgrade")])
    # Admin-only panels are deliberately kept as the final menu entries.
    if is_admin(user_id):
        rows.append([InlineKeyboardButton(tr(user_id, "dashboard"), callback_data="home:admin")])
        rows.append([InlineKeyboardButton(tr(user_id, "admin"), callback_data="home:admin")])
    return InlineKeyboardMarkup(rows)

async def ids_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show game, recharge-method/server, and offer IDs to the admin."""
    user_id = update.effective_user.id if update.effective_user else 0
    if not is_admin(user_id):
        await update.effective_message.reply_text("⛔ هذا الأمر خاص بالإدارة.")
        return

    chunks = []
    with db() as conn:
        chunks.append("🎮 معرّفات الألعاب (GAME_ID)\n")
        games = conn.execute("SELECT id, name, active FROM games ORDER BY id").fetchall()
        if games:
            chunks.extend(f"{r['id']} | {r['name']} | {'مفعّلة' if r['active'] else 'معطّلة'}\n" for r in games)
        else:
            chunks.append("لا توجد ألعاب مسجلة.\n")

        chunks.append("\n🔀 معرّفات طرق الشحن والسيرفرات (METHOD_ID)\n")
        methods = conn.execute(
            "SELECT rm.id, rm.game_id, g.name AS game_name, rm.title, rm.active "
            "FROM recharge_methods rm LEFT JOIN games g ON g.id=rm.game_id "
            "ORDER BY rm.game_id, rm.id"
        ).fetchall()
        if methods:
            chunks.extend(
                f"GAME_ID={r['game_id']} | METHOD_ID={r['id']} | {r['game_name'] or 'لعبة غير معروفة'} → {r['title']} | {'مفعّلة' if r['active'] else 'معطّلة'}\n"
                for r in methods
            )
        else:
            chunks.append("لا توجد طرق شحن مسجلة.\n")

        chunks.append("\n💎 معرّفات العروض (OFFER_ID)\n")
        offers = conn.execute(
            "SELECT o.id, o.game_id, g.name AS game_name, o.recharge_method_id, o.name, o.active "
            "FROM offers o LEFT JOIN games g ON g.id=o.game_id ORDER BY o.game_id, o.id"
        ).fetchall()
        if offers:
            chunks.extend(
                f"OFFER_ID={r['id']} | GAME_ID={r['game_id']} | METHOD_ID={r['recharge_method_id']} | {r['game_name'] or 'لعبة غير معروفة'} → {r['name']} | {'مفعّل' if r['active'] else 'معطّل'}\n"
                for r in offers
            )
        else:
            chunks.append("لا توجد عروض مسجلة.\n")

    text = ''.join(chunks)
    # Telegram message text is limited; send the report in safe-sized chunks.
    for start in range(0, len(text), 3500):
        await update.effective_message.reply_text(text[start:start + 3500])


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
        resize_keyboard=True,
        is_persistent=True,
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
            balance_usd REAL DEFAULT 0,
            trader_wallet_currency TEXT DEFAULT 'DA',
            points INTEGER DEFAULT 0,
            points_da INTEGER DEFAULT 0,
            points_usd REAL DEFAULT 0,
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
            price_usd_trader REAL DEFAULT 0,
            reward_points INTEGER DEFAULT 0,
            android_active INTEGER DEFAULT 1,
            ios_active INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_id INTEGER,
            offer_id INTEGER,
            player_id TEXT DEFAULT '',
            payment_method TEXT DEFAULT '',
            price INTEGER DEFAULT 0,
            currency TEXT DEFAULT 'DA',
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            points_awarded INTEGER DEFAULT 0,
            points_used INTEGER DEFAULT 0,
            platform TEXT DEFAULT '',
            credit_charged INTEGER DEFAULT 0,
            credit_refunded INTEGER DEFAULT 0,
            payment_receipt_file_ids TEXT DEFAULT '[]',
            shipping_receipt_file_ids TEXT DEFAULT '[]',
            shipping_receipt_file_id TEXT DEFAULT '',
            shipping_receipt_by INTEGER DEFAULT NULL,
            shipping_receipt_at TEXT DEFAULT '',
            completion_message TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            offer_id INTEGER NOT NULL,
            offer_name TEXT NOT NULL DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS trader_work_groups (
            group_id INTEGER PRIMARY KEY,
            trader_id INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS trader_group_offers (
            group_id INTEGER NOT NULL,
            offer_id INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (group_id, offer_id)
        );
        CREATE TABLE IF NOT EXISTS trader_group_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            trader_id INTEGER NOT NULL,
            offer_id INTEGER NOT NULL,
            game_name TEXT NOT NULL DEFAULT '',
            offer_name TEXT NOT NULL DEFAULT '',
            price REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'DA',
            status TEXT NOT NULL DEFAULT 'open',
            posted_message_id INTEGER DEFAULT NULL,
            published_by INTEGER DEFAULT NULL,
            accepted_by INTEGER DEFAULT NULL,
            accepted_at TEXT DEFAULT '',
            completed_by INTEGER DEFAULT NULL,
            completed_at TEXT DEFAULT '',
            cancelled_by INTEGER DEFAULT NULL,
            cancelled_at TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS custom_payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '💳',
            currency TEXT NOT NULL DEFAULT 'USD',
            instructions TEXT DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS offer_payment_methods (
            offer_id INTEGER NOT NULL,
            method_id INTEGER NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (offer_id, method_id)
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
        CREATE TABLE IF NOT EXISTS referral_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referred_user_id INTEGER NOT NULL,
            referrer_user_id INTEGER NOT NULL,
            milestone_amount INTEGER NOT NULL,
            points_awarded INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(referred_user_id, milestone_amount)
        );
        CREATE TABLE IF NOT EXISTS wallet_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL DEFAULT 0,
            amount_usd REAL DEFAULT 0,
            currency TEXT DEFAULT 'DA',
            payment_method TEXT DEFAULT '',
            receipt_file_id TEXT DEFAULT '',
            receipt_file_ids TEXT DEFAULT '[]',
            receipt_type TEXT DEFAULT 'photo',
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'DA',
            kind TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            balance_before REAL NOT NULL DEFAULT 0,
            balance_after REAL NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            admin_id INTEGER DEFAULT NULL,
            created_at TEXT NOT NULL
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
            receipt_file_ids TEXT DEFAULT '[]',
            receipt_type TEXT DEFAULT 'photo',
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
        # Isolated Flexy monitoring subsystem; does not touch shop wallets/orders.
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS flexy_subscribers (
            slot INTEGER PRIMARY KEY CHECK(slot BETWEEN 1 AND 10),
            user_id INTEGER UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            balance REAL NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            display_name TEXT DEFAULT '',
            display_emoji TEXT DEFAULT '👤'
        );
        CREATE TABLE IF NOT EXISTS flexy_sms_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_chat_id INTEGER NOT NULL,
            source_message_id INTEGER NOT NULL,
            sender TEXT DEFAULT '',
            gross_amount REAL NOT NULL,
            message_text TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            credited_slot INTEGER DEFAULT NULL,
            net_amount REAL DEFAULT 0,
            UNIQUE(source_chat_id, source_message_id)
        );
        CREATE TABLE IF NOT EXISTS flexy_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_before REAL NOT NULL,
            balance_after REAL NOT NULL,
            note TEXT DEFAULT '',
            admin_id INTEGER DEFAULT NULL,
            sms_event_id INTEGER DEFAULT NULL,
            created_at TEXT NOT NULL
        );
        """)
        # Add optional display labels without changing existing subscriber IDs or balances.
        flexy_sub_columns = {row[1] for row in conn.execute("PRAGMA table_info(flexy_subscribers)").fetchall()}
        if "display_name" not in flexy_sub_columns:
            conn.execute("ALTER TABLE flexy_subscribers ADD COLUMN display_name TEXT DEFAULT ''")
        if "display_emoji" not in flexy_sub_columns:
            conn.execute("ALTER TABLE flexy_subscribers ADD COLUMN display_emoji TEXT DEFAULT '👤'")

        # Migrate Flexy SMS event tables created by earlier bot versions.
        # CREATE TABLE IF NOT EXISTS does not add columns to an existing SQLite table.
        flexy_event_columns = {row[1] for row in conn.execute("PRAGMA table_info(flexy_sms_events)").fetchall()}
        flexy_event_migrations = {
            "source_chat_id": "INTEGER NOT NULL DEFAULT 0",
            "source_message_id": "INTEGER NOT NULL DEFAULT 0",
            "sender": "TEXT DEFAULT ''",
            "gross_amount": "REAL NOT NULL DEFAULT 0",
            "message_text": "TEXT DEFAULT ''",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "status": "TEXT NOT NULL DEFAULT 'pending'",
            "credited_slot": "INTEGER DEFAULT NULL",
            "net_amount": "REAL DEFAULT 0",
        }
        for column, definition in flexy_event_migrations.items():
            if column not in flexy_event_columns:
                conn.execute(f"ALTER TABLE flexy_sms_events ADD COLUMN {column} {definition}")

        # Repair legacy schemas that accidentally made message_id unique on its own.
        # Telegram message IDs are only unique within a chat, so the correct key is
        # (source_chat_id, source_message_id). Preserve all existing event data.
        unique_indexes = conn.execute("PRAGMA index_list('flexy_sms_events')").fetchall()
        bad_unique_constraint = False
        for idx in unique_indexes:
            # PRAGMA index_list: seq, name, unique, origin, partial
            if not idx[2] or (len(idx) > 3 and idx[3] == 'pk'):
                continue
            index_name = idx[1]
            index_columns = [r[2] for r in conn.execute(f"PRAGMA index_info('{index_name}')").fetchall()]
            if index_columns != ['source_chat_id', 'source_message_id']:
                bad_unique_constraint = True
                break
        if bad_unique_constraint:
            conn.execute("""CREATE TABLE flexy_sms_events_repaired (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_chat_id INTEGER NOT NULL DEFAULT 0,
                source_message_id INTEGER NOT NULL DEFAULT 0,
                sender TEXT DEFAULT '',
                gross_amount REAL NOT NULL DEFAULT 0,
                message_text TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                credited_slot INTEGER DEFAULT NULL,
                net_amount REAL DEFAULT 0
            )""")
            conn.execute("""INSERT OR IGNORE INTO flexy_sms_events_repaired
                (id,source_chat_id,source_message_id,sender,gross_amount,message_text,created_at,status,credited_slot,net_amount)
                SELECT id,COALESCE(source_chat_id,0),COALESCE(source_message_id,0),COALESCE(sender,''),
                       COALESCE(gross_amount,0),COALESCE(message_text,''),COALESCE(created_at,''),
                       COALESCE(status,'pending'),credited_slot,COALESCE(net_amount,0)
                FROM flexy_sms_events ORDER BY id""")
            conn.execute("DROP TABLE flexy_sms_events")
            conn.execute("ALTER TABLE flexy_sms_events_repaired RENAME TO flexy_sms_events")

        # Partial unique index avoids collisions between legacy rows whose newly-added
        # source IDs default to zero, while deduplicating only the same post in the same chat.
        conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_flexy_sms_source_message
            ON flexy_sms_events(source_chat_id, source_message_id)
            WHERE source_chat_id != 0 AND source_message_id != 0""")

        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('flexy_deduction_percent','0')")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('flexy_channel_id','')")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('flexy_sms_source_chat_id','')")

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
                "points_da": "INTEGER DEFAULT 0",
                "points_usd": "REAL DEFAULT 0",
                "credit_limit": "INTEGER DEFAULT 0",
                "credit_debt": "INTEGER DEFAULT 0",
                "credit_term_days": "INTEGER DEFAULT 0",
                "credit_due_at": "TEXT DEFAULT ''",
                "trader_wallet_currency": "TEXT DEFAULT 'DA'",
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
                "price_usd_trader": "REAL DEFAULT 0",
                "price_usd": "REAL DEFAULT 0",
                "reward_points": "INTEGER DEFAULT 0",
                "android_active": "INTEGER DEFAULT 1",
                "ios_active": "INTEGER DEFAULT 1",
                "sort_order": "INTEGER DEFAULT 0",
            },
            "orders": {
                "game_id": "INTEGER", "offer_id": "INTEGER",
                "player_id": "TEXT DEFAULT ''", "payment_method": "TEXT DEFAULT ''",
                "price": "INTEGER DEFAULT 0", "currency": "TEXT DEFAULT 'DA'", "status": "TEXT DEFAULT 'pending'",
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

        # Preserve the existing order of old offers, while allowing admin reordering.
        conn.execute("UPDATE offers SET sort_order=id WHERE COALESCE(sort_order,0)=0")

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
        order_cols = {r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()}
        # Trader accounts do not participate in the points system.
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
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_exchange_rate', '254')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_sell_rate', (SELECT value FROM settings WHERE key='usd_exchange_rate'))")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_buy_rate', (SELECT value FROM settings WHERE key='usd_exchange_rate'))")
        # Requested USD payment options are pre-created but disabled until configured by admin.
        for method_name, method_emoji in (("Binance", "🟡"), ("USDT", "💵"), ("Bybit", "🔶"), ("RedotPay", "🔴")):
            conn.execute(
                "INSERT INTO custom_payment_methods (name, emoji, currency, instructions, enabled, created_at) "
                "SELECT ?, ?, 'USD', '⚠️ الإدارة لم تضبط تعليمات الدفع بعد. لا تفعّل هذه الطريقة قبل إدخال بيانات الدفع.', 0, ? "
                "WHERE NOT EXISTS (SELECT 1 FROM custom_payment_methods WHERE lower(name)=lower(?))",
                (method_name, method_emoji, now_text(), method_name),
            )
        conn.execute("""CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            entities_json TEXT NOT NULL DEFAULT '[]',
            due_at TEXT NOT NULL,
            sent_at TEXT DEFAULT '',
            cancelled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT ''
        )""")
        # Upgrade older databases without losing already scheduled notifications.
        scheduled_columns = {row[1] for row in conn.execute("PRAGMA table_info(scheduled_broadcasts)").fetchall()}
        if "entities_json" not in scheduled_columns:
            conn.execute("ALTER TABLE scheduled_broadcasts ADD COLUMN entities_json TEXT NOT NULL DEFAULT '[]'")
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            created_at TEXT DEFAULT '',
            approved INTEGER NOT NULL DEFAULT 0,
            published INTEGER NOT NULL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS marketing_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sequence_no INTEGER NOT NULL,
            due_at TEXT NOT NULL,
            sent_at TEXT DEFAULT '',
            cancelled INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, sequence_no)
        )""")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('marketing_reminders_enabled','1')")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('marketing_reminder_delay_minutes','60')")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('marketing_reminder_count','2')")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('marketing_reminder_interval_minutes','1440')")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('marketing_reminder_text',?)", ("👋 ما زلت ما طلبتش من SERADJ STORE؟ 🛍️\\nتصفح العروض واختار الخدمة اللي تحتاجها!",))

        # Safe additive migrations for an existing production database.
        order_cols = {r["name"] for r in conn.execute("PRAGMA table_info(orders)").fetchall()}
        for column, definition in {
            "payment_receipt_file_ids": "TEXT DEFAULT '[]'",
            "shipping_receipt_file_ids": "TEXT DEFAULT '[]'",
            "shipping_receipt_file_id": "TEXT DEFAULT ''",
            "shipping_receipt_by": "INTEGER DEFAULT NULL",
            "shipping_receipt_at": "TEXT DEFAULT ''",
        }.items():
            if column not in order_cols:
                conn.execute(f"ALTER TABLE orders ADD COLUMN {column} {definition}")

        user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "balance_usd" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN balance_usd REAL DEFAULT 0")
        if "language" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ar'")
        deposit_cols = {r["name"] for r in conn.execute("PRAGMA table_info(wallet_deposits)").fetchall()}
        if "amount_usd" not in deposit_cols:
            conn.execute("ALTER TABLE wallet_deposits ADD COLUMN amount_usd REAL DEFAULT 0")
        if "currency" not in deposit_cols:
            conn.execute("ALTER TABLE wallet_deposits ADD COLUMN currency TEXT DEFAULT 'DA'")
        if "paid_amount" not in deposit_cols:
            conn.execute("ALTER TABLE wallet_deposits ADD COLUMN paid_amount REAL DEFAULT 0")
        if "receipt_file_ids" not in deposit_cols:
            conn.execute("ALTER TABLE wallet_deposits ADD COLUMN receipt_file_ids TEXT DEFAULT '[]'")
        if "receipt_type" not in deposit_cols:
            conn.execute("ALTER TABLE wallet_deposits ADD COLUMN receipt_type TEXT DEFAULT 'photo'")
        order_cols = {r["name"] for r in conn.execute("PRAGMA table_info(orders)").fetchall()}
        if "completion_message" not in order_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN completion_message TEXT DEFAULT ''")
        # Migrate older wallet ledgers in-place. CREATE TABLE IF NOT EXISTS does not
        # add columns to an existing production table, so add every field used by
        # current deposit/admin history queries without deleting existing records.
        wallet_tx_cols = {r["name"] for r in conn.execute("PRAGMA table_info(wallet_transactions)").fetchall()}
        wallet_tx_migrations = {
            "currency": "TEXT NOT NULL DEFAULT 'DA'",
            "kind": "TEXT NOT NULL DEFAULT 'عملية قديمة'",
            "amount": "REAL NOT NULL DEFAULT 0",
            "balance_before": "REAL NOT NULL DEFAULT 0",
            "balance_after": "REAL NOT NULL DEFAULT 0",
            "note": "TEXT DEFAULT ''",
            "admin_id": "INTEGER DEFAULT NULL",
            "created_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in wallet_tx_migrations.items():
            if column not in wallet_tx_cols:
                conn.execute(f"ALTER TABLE wallet_transactions ADD COLUMN {column} {definition}")


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
                ORDER BY CASE WHEN COALESCE(sort_order,0)>0 THEN sort_order ELSE 1000000+id END, id
                """,
                (game_id,),
            ).fetchall()

        return conn.execute(
            """
            SELECT * FROM offers
            WHERE game_id = ?
            ORDER BY CASE WHEN COALESCE(sort_order,0)>0 THEN sort_order ELSE 1000000+id END, id
            """,
            (game_id,),
        ).fetchall()


def is_trader(user_id):
    if is_admin(user_id):
        return True
    with db() as conn:
        row = conn.execute("SELECT account_type FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return bool(row and row["account_type"] == "trader")


def points_enabled(user_id):
    """Loyalty points are available to all buyers, including approved traders."""
    return True


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
    """Return the subscriber's payable DA price; USD-priced offers use the sell rate."""
    usd_source = _offer_usd_source_price(offer, user_id) if "_offer_usd_source_price" in globals() else None
    trader = is_trader(user_id)
    da_base = (usd_source * usd_sell_rate()) if usd_source is not None else Decimal(str(offer["price_baridi_trader"] if trader else offer["price_baridi"]))
    if method == "baridi":
        return int(da_base.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return int((da_base * Decimal("1.18")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def trader_wallet_currency(user_id):
    row = get_user_row(user_id)
    value = (row["trader_wallet_currency"] if row and "trader_wallet_currency" in row.keys() else "DA")
    return "USD" if str(value or "DA").upper() == "USD" else "DA"


def usd_sell_rate():
    """DA received for 1 USD when pricing a USD-denominated offer in DA."""
    try:
        value = Decimal(get_setting("usd_sell_rate", get_setting("usd_exchange_rate", "254")))
        return value if value.is_finite() and value > 0 else Decimal("254")
    except (InvalidOperation, ValueError):
        return Decimal("254")


def usd_buy_rate():
    """DA divisor used to convert a DA-denominated offer into USD."""
    try:
        value = Decimal(get_setting("usd_buy_rate", get_setting("usd_exchange_rate", "254")))
        return value if value.is_finite() and value > 0 else Decimal("254")
    except (InvalidOperation, ValueError):
        return Decimal("254")


def _offer_usd_source_price(offer, user_id):
    """Return USD source price only when the matching DZD source price is unset.

    DZD prices take precedence whenever configured. This prevents an old USD
    override from silently replacing a newly entered customer/trader DZD price.
    To make a USD-denominated offer, its matching DZD base price is set to zero
    by the USD-price editor below.
    """
    try:
        trader = is_trader(user_id)
        key = "price_usd_trader" if trader else "price_usd"
        da_key = "price_baridi_trader" if trader else "price_baridi"
        da_value = Decimal(str(offer[da_key] or 0)) if da_key in offer.keys() else Decimal("0")
        value = Decimal(str(offer[key] or 0)) if key in offer.keys() else Decimal("0")
        if da_value > 0:
            return None
        return value if value.is_finite() and value > 0 else None
    except Exception:
        return None


def trader_offer_price(offer, user_id):
    """Trader's configured wallet price; USD source prices are converted to DA at sell rate."""
    usd_source = _offer_usd_source_price(offer, user_id)
    if trader_wallet_currency(user_id) == "USD":
        if usd_source is not None:
            return float(usd_source.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        da_price = Decimal(str(offer["price_baridi_trader"] or 0))
        return float((da_price / usd_buy_rate()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if usd_source is not None:
        return int((usd_source * usd_sell_rate()).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return int(Decimal(str(offer["price_baridi_trader"] or 0)))


def wallet_offer_price(offer, user_id, currency="DA"):
    """Convert each subscriber's configured offer currency using the matching buy/sell rate."""
    usd_source = _offer_usd_source_price(offer, user_id)
    da_price = Decimal(str(offer["price_baridi_trader"] if is_trader(user_id) else offer["price_baridi"]))
    if usd_source is not None:
        return float(usd_source.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if str(currency).upper() == "USD" else int((usd_source * usd_sell_rate()).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if str(currency).upper() == "USD":
        return float((da_price / usd_buy_rate()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return int(da_price)


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


async def admin_show_people(message, banned=False, page=0):
    page=max(0,int(page or 0)); per_page=12
    with db() as conn:
        rows = conn.execute(
            "SELECT user_id, username, full_name, phone_number, is_banned, account_type, balance "
            "FROM users WHERE COALESCE(is_banned,0)=? ORDER BY user_id DESC LIMIT ? OFFSET ?",
            (1 if banned else 0, per_page, page*per_page),
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
    pages=(int(total)+per_page-1)//per_page
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ السابق",callback_data=f"people_page:{1 if banned else 0}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{max(1,pages)}",callback_data="people_page:noop"))
    if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️",callback_data=f"people_page:{1 if banned else 0}:{page+1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔎 البحث بالاسم أو ID", callback_data="person_search")])
    buttons.append([InlineKeyboardButton("🚫 المحظورون" if not banned else "👥 المشتركين النشطون",
                                          callback_data="people_banned" if not banned else "people_active")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
    title = "🚫 قائمة المحظورين" if banned else "👥 المشتركين النشطون"
    await message.reply_text(f"{title} — العدد: {total}\nالصفحة {page+1} من {max(1,(int(total)+per_page-1)//per_page)}\nاضغط على الشخص لإدارة حسابه.",
                             reply_markup=InlineKeyboardMarkup(buttons))


async def admin_wallet_ranking(query, currency="DA", page=0):
    """Show every registered account ranked by one wallet currency."""
    currency = "USD" if str(currency).upper() == "USD" else "DA"
    page = max(0, int(page or 0))
    per_page = 15
    balance_col = "balance_usd" if currency == "USD" else "balance"
    with db() as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        rows = conn.execute(
            f"SELECT user_id, username, full_name, account_type, is_banned, balance, balance_usd "
            f"FROM users ORDER BY COALESCE({balance_col},0) DESC, user_id ASC LIMIT ? OFFSET ?",
            (per_page, page * per_page),
        ).fetchall()
    pages = max(1, (total + per_page - 1) // per_page)
    title = "💵 ترتيب محافظ الدولار USD" if currency == "USD" else "💰 ترتيب محافظ الدينار DA"
    lines = [f"{title}", f"عدد الحسابات: {total}", "━━━━━━━━━━━━━━━━━━"]
    if not rows:
        lines.append("لا توجد حسابات مسجلة.")
    for index, row in enumerate(rows, start=page * per_page + 1):
        name = row["full_name"] or ("@" + row["username"] if row["username"] else str(row["user_id"]))
        kind = "تاجر" if row["account_type"] == "trader" else "زبون"
        status = " | محظور" if int(row["is_banned"] or 0) else ""
        amount = float(row["balance_usd"] or 0) if currency == "USD" else int(row["balance"] or 0)
        unit = "USD" if currency == "USD" else "DA"
        lines.append(f"{index}. {name} — {amount:,.2f} {unit}\n   {kind}{status} | ID: {row['user_id']}")
    buttons = [[
        InlineKeyboardButton("💰 ترتيب DA", callback_data="wallet_rank:DA:0"),
        InlineKeyboardButton("💵 ترتيب USD", callback_data="wallet_rank:USD:0"),
    ]]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"wallet_rank:{currency}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="wallet_rank:noop:0"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"wallet_rank:{currency}:{page+1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
    await edit_query_message(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


async def admin_person_card(query, target_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (target_id,)).fetchone()
        orders = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (target_id,)).fetchone()[0]
    if not row:
        await edit_query_message(query, "❌ المشترك غير موجود.")
        return
    username = "@" + row["username"] if row["username"] else "غير متوفر"
    phone = row["phone_number"] if "phone_number" in row.keys() and row["phone_number"] else "غير مشارك"
    banned = int(row["is_banned"] or 0) if "is_banned" in row.keys() else 0
    buttons = [
        [InlineKeyboardButton("📜 سجل عمليات المحفظة", callback_data=f"admin_wallet_history:{target_id}")],
        [InlineKeyboardButton("💰 إضافة رصيد DA", callback_data=f"person_balance:{target_id}")],
        [InlineKeyboardButton("✏️ تعديل رصيد DA", callback_data=f"person_balance_edit:{target_id}")],
        [InlineKeyboardButton("💵 إضافة رصيد USD", callback_data=f"person_balance_usd:{target_id}")],
        [InlineKeyboardButton("✏️ تعديل رصيد USD", callback_data=f"person_balance_usd_edit:{target_id}")],
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
    await edit_query_message(query, 
        f"👤 معلومات المشترك\n\nالاسم: {row['full_name'] or 'غير متوفر'}\n"
        f"Username: {username}\nTelegram ID: {target_id}\nالهاتف: {phone}\n"
        f"نوع الحساب: {'تاجر' if row['account_type']=='trader' else 'زبون'}\n"
        f"الحالة: {'🚫 محظور' if banned else '🟢 نشط'}\n"
        f"الرصيد: {int(row['balance'] or 0)} DA\n"
        f"💵 رصيد الدولار: {float(row['balance_usd'] or 0):.2f} USD\n"
        + (f"💳 الدين الحالي: {int(row['credit_debt'] or 0)} DA\n" if row['account_type'] == 'trader' else "")
        + f"🎁 نقاط DA: {float(row['points_da'] or 0):g} | نقاط USD: {float(row['points_usd'] or 0):.3f}\n"
        f"عدد الطلبات: {orders}\n"
        f"تاريخ التسجيل: {row['created_at'] or 'غير معروف'}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ====== التحقق من الاشتراك في القناة ======

def current_required_channel():
    return get_setting("required_channel", REQUIRED_CHANNEL).strip()

def current_required_channel_link():
    return get_setting("required_channel_link", REQUIRED_CHANNEL_LINK).strip()

def subscription_keyboard():
    buttons = []
    channel_link = current_required_channel_link()
    if channel_link:
        buttons.append([InlineKeyboardButton("📢 اشترك في القناة", url=channel_link)])
    buttons.append([InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check_subscription")])
    return InlineKeyboardMarkup(buttons)

async def is_subscribed(bot, user_id):
    """Check required channel membership using admin-configured DB settings or env defaults."""
    channel = current_required_channel()
    if not channel or get_setting("required_subscription_enabled", "1") != "1":
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        logger.exception("تعذر التحقق من اشتراك المستخدم %s في القناة %s", user_id, channel)
        return False

# ====== أوامر البداية ======

class _PrivateStartCallbackQuery:
    """Adapt a channel-button deep link into a private callback navigation."""
    def __init__(self, message, user, data):
        self.message = message
        self.from_user = user
        self.data = data
    async def answer(self, *args, **kwargs):
        return None
    async def edit_message_text(self, text, **kwargs):
        # Never edit the original channel post; send the destination privately.
        return await self.message.reply_text(text, **kwargs)
    async def edit_message_reply_markup(self, **kwargs):
        return await self.message.reply_text("تم فتح القسم المطلوب.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # The bot is an order receiver in work groups, not a customer-facing shop UI.
    # Never publish the persistent customer keyboard in a group.
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        return
    user = update.effective_user

    with db() as conn:
        cursor = conn.execute(
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
        is_new_user = cursor.rowcount == 1

    # Notify the admin only on the user's first registration, not on every /start.
    if is_new_user and ADMIN_ID and user.id != ADMIN_ID:
        username_text = f"@{user.username}" if user.username else "غير موجود"
        language_text = getattr(user, "language_code", None) or "غير متوفر"
        user_link = f"tg://user?id={user.id}"
        notification = (
            "🆕 دخل مشترك جديد إلى البوت\n\n"
            f"👤 الاسم: {user.full_name or 'غير متوفر'}\n"
            f"🔗 username: {username_text}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"🌐 اللغة: {language_text}\n"
            f"🤖 حساب آلي: {'نعم' if user.is_bot else 'لا'}\n"
            f"🔎 فتح الحساب: {user_link}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=notification)
        except Exception:
            logger.exception("تعذر إرسال إشعار المشترك الجديد للإدارة")

    # Persist a one-time reminder schedule for accounts that have never ordered.
    if not is_admin(user.id):
        try:
            delay = max(1, min(525600, int(get_setting("marketing_reminder_delay_minutes", "60"))))
            count = max(0, min(10, int(get_setting("marketing_reminder_count", "2"))))
            with db() as conn:
                has_order = conn.execute("SELECT 1 FROM orders WHERE user_id=? LIMIT 1", (user.id,)).fetchone()
                has_schedule = conn.execute("SELECT 1 FROM marketing_reminders WHERE user_id=? LIMIT 1", (user.id,)).fetchone()
                if not has_order and not has_schedule and count > 0:
                    due = (datetime.now() + timedelta(minutes=delay)).strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute("INSERT OR IGNORE INTO marketing_reminders(user_id,sequence_no,due_at) VALUES(?,?,?)", (user.id, 1, due))
        except Exception:
            logger.exception("Could not schedule marketing reminders for user %s", user.id)

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
        if is_new_user and referrer_id and referrer_id != user.id:
            with db() as conn:
                existing_ref = conn.execute("SELECT referred_user_id FROM referrals WHERE referred_user_id=?", (user.id,)).fetchone()
                referrer_exists = conn.execute("SELECT user_id FROM users WHERE user_id=?", (referrer_id,)).fetchone()
                referrer_type = conn.execute("SELECT account_type FROM users WHERE user_id=?", (referrer_id,)).fetchone() if referrer_exists else None
                if not existing_ref and referrer_exists:
                    award = bool(referrer_type)
                    conn.execute("INSERT INTO referrals (referred_user_id, referrer_user_id, points_awarded, created_at) VALUES (?, ?, ?, ?)", (user.id, referrer_id, 1 if award else 0, now_text()))
                    if award:
                        ref_wallet = conn.execute("SELECT balance, balance_usd FROM users WHERE user_id=?", (referrer_id,)).fetchone()
                        reward_ratio = 0.5 if referrer_type["account_type"] == "trader" else 1.0
                        referral_da = 5 * reward_ratio
                        referral_usd = 0.019 * reward_ratio
                        before_da = float(ref_wallet["balance"] or 0)
                        before_usd = float(ref_wallet["balance_usd"] or 0)
                        conn.execute("UPDATE users SET balance=COALESCE(balance,0)+?, balance_usd=COALESCE(balance_usd,0)+? WHERE user_id=?", (referral_da, referral_usd, referrer_id))
                        conn.execute("INSERT INTO wallet_transactions(user_id,currency,kind,amount,balance_before,balance_after,note,created_at) VALUES(?,?,?,?,?,?,?,?)", (referrer_id,"DA","مكافأة تسجيل إحالة",referral_da,before_da,before_da+referral_da,"تسجيل مشترك جديد عبر رابط الإحالة",now_text()))
                        conn.execute("INSERT INTO wallet_transactions(user_id,currency,kind,amount,balance_before,balance_after,note,created_at) VALUES(?,?,?,?,?,?,?,?)", (referrer_id,"USD","مكافأة تسجيل إحالة",referral_usd,before_usd,before_usd+referral_usd,"تسجيل مشترك جديد عبر رابط الإحالة",now_text()))
                    try:
                        await context.bot.send_message(referrer_id, (f"🎉 انضم مشترك جديد عبر رابط إحالتك! تمت إضافة {referral_da:g} DA إلى محفظة الدينار و{referral_usd:g} USD إلى محفظة الدولار.") if award else "تم تسجيل الإحالة بنجاح.")
                    except Exception:
                        logger.info("Could not notify referrer %s", referrer_id)

    # Replace the previous inline navigation card on /start, but keep the
    # persistent reply-keyboard message. Re-sending it on every /start caused
    # repeated standalone "القائمة الرئيسية" messages in the chat.
    _existing_reply_keyboard_id = context.user_data.get("reply_keyboard_message_id")
    _old_navigation_id = context.user_data.get("navigation_message_id")
    if _old_navigation_id:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=int(_old_navigation_id))
        except Exception:
            pass
    context.user_data.clear()
    if _existing_reply_keyboard_id:
        context.user_data["reply_keyboard_message_id"] = _existing_reply_keyboard_id
    saved = get_user_row(user.id)
    if not is_admin(user.id) and saved and "is_banned" in saved.keys() and int(saved["is_banned"] or 0):
        await update.message.reply_text("🚫 حسابك محظور من استعمال البوت. تواصل مع الإدارة.")
        return

    # Mandatory channel membership check before allowing customers into the bot.
    if not is_admin(user.id) and not await is_subscribed(context.bot, user.id):
        await update.message.reply_text(
            "🔒 لاستخدام بوت SERADJ STORE، لازم تشترك أولًا في قناتنا ثم تضغط على «تحققت من الاشتراك».",
            reply_markup=subscription_keyboard(),
        )
        return

    # Buttons published in channels use t.me/<bot>?start=nav_<payload>.
    # Re-run their callback privately so a click never edits the shared channel post.
    if payload.startswith("nav_"):
        try:
            encoded = payload[4:]
            padded = encoded + ("=" * (-len(encoded) % 4))
            nav_data = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            if not nav_data or len(nav_data.encode("utf-8")) > 64:
                raise ValueError("invalid navigation payload")
        except Exception:
            await update.message.reply_text("❌ رابط الزر غير صالح. افتح المتجر من القائمة الرئيسية.", reply_markup=main_keyboard(user.id))
            return
        fake_query = _PrivateStartCallbackQuery(update.message, user, nav_data)
        fake_update = SimpleNamespace(callback_query=fake_query, effective_user=user, effective_message=update.message)
        await callback_handler(fake_update, context)
        return

    welcome_text = tr(user.id, "welcome", store=STORE_NAME)
    if user_language(user.id) == "ar":
        welcome_text = get_setting("welcome_message", welcome_text)

    # Show the customer's personalized account animation immediately on entering the bot.
    nav_msg = None
    try:
        account_row = get_user_row(user.id)
        if account_row:
            with db() as conn:
                order_count = conn.execute(
                    "SELECT COUNT(*) FROM orders WHERE user_id = ?", (user.id,)
                ).fetchone()[0]
            account_animation = generate_account_gif(
                account_row["full_name"],
                account_row["balance"],
                account_row["balance_usd"],
                order_count,
                user_language(user.id),
                username=account_row["username"],
            )
            if account_animation:
                nav_msg = await update.message.reply_animation(
                    animation=account_animation,
                    caption=welcome_text,
                    reply_markup=customer_inline_menu(user.id),
                )
    except Exception:
        logging.exception("Could not show personalized account GIF on /start")

    if nav_msg is None:
        nav_msg = await update.message.reply_text(
            welcome_text,
            reply_markup=customer_inline_menu(user.id),
        )
    context.user_data["navigation_message_id"] = nav_msg.message_id
    # Telegram cannot attach inline and reply keyboards to the same message.
    # Persist this per-user flag in SQLite so /start never emits a repeated menu bubble.
    keyboard_flag = f"reply_keyboard_sent_{user.id}"
    if get_setting(keyboard_flag, "0") != "1":
        await update.message.reply_text("استخدم الأزرار أسفل المحادثة.", reply_markup=main_keyboard(user.id))
        set_setting(keyboard_flag, "1")


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
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        return
    uid = update.effective_user.id if update.effective_user else 0
    task = CART_TIMEOUT_TASKS.pop(uid, None)
    if task and not task.done(): task.cancel()
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

async def show_store(message, user_id, category=None, context=None, query=None):
    if category not in ("game", "app"):
        text = "اختر زر 🎮 الألعاب أو 📱 التطبيقات من القائمة الرئيسية."
        if query:
            await edit_query_message(query, text, reply_markup=main_keyboard(user_id))
        else:
            await message.reply_text(text, reply_markup=main_keyboard(user_id))
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
        text = "😕 لا توجد خدمات في هذا القسم حالياً."
        if query:
            await edit_query_message(query, text, reply_markup=main_keyboard(user_id))
        else:
            await message.reply_text(text, reply_markup=main_keyboard(user_id))
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
    # Keep store browsing inside the same Telegram message. Callback navigation
    # must edit the current message instead of creating another window.
    markup = InlineKeyboardMarkup(buttons)
    if query is not None:
        try:
            await edit_query_message(query, "\n".join(lines), reply_markup=markup)
        except Exception as exc:
            # Telegram raises MessageNotModified when the content is identical.
            if "Message is not modified" not in str(exc):
                raise
    else:
        await message.reply_text("\n".join(lines), reply_markup=markup)


# ====== حساب الزبون ======

def generate_account_gif(full_name, balance_da, balance_usd, total_orders, language="ar", username=None):
    """Create a personalized, lightweight animated card using the user's exact latest reference design."""
    if not PIL_AVAILABLE:
        logging.error("Account GIF unavailable: Pillow is not installed.")
        return None

    import base64
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    if not hasattr(generate_account_gif, "_template_base"):
        template_data = base64.b64decode(
        "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"
        )
        generate_account_gif._template_base = Image.open(io.BytesIO(template_data)).convert("RGB")
    base = generate_account_gif._template_base.copy()
    W, H = base.size  # 960 x 640, preserving the supplied 3:2 reference layout

    font_ar = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
    font_ar_bold = "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"
    font_latin = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_latin_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    def load_font(path, size, fallback=font_latin):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            try:
                return ImageFont.truetype(fallback, size)
            except Exception:
                return ImageFont.load_default()

    def fit_font(text, path, max_size, min_size, max_width, fallback=font_latin):
        for size in range(max_size, min_size - 1, -1):
            font = load_font(path, size, fallback)
            box = ImageDraw.Draw(base).textbbox((0, 0), text, font=font)
            if box[2] - box[0] <= max_width:
                return font
        return load_font(path, min_size, fallback)

    name = (str(full_name or "صديقنا").strip() or "صديقنا")
    if len(name) > 28:
        name = name[:27] + "…"
    clean_username = str(username or "").strip().lstrip("@")
    username_text = f"{clean_username}" if clean_username else ("غير متوفر" if language == "ar" else "Not available")

    # Personalized identity is written exactly where the reference says Telegram / @SERADJ_STORE.
    identity = base.copy()
    d = ImageDraw.Draw(identity, "RGBA")
    name_font = fit_font(name, font_ar_bold, 58, 30, 500, font_latin_bold)
    username_font = fit_font(username_text, font_latin_bold, 34, 20, 590, font_latin_bold)
    try:
        d.text((525, 105), name, font=name_font, fill=(255, 255, 255, 255),
               anchor="mm", direction="rtl", stroke_width=1, stroke_fill=(2, 18, 48, 230))
    except (TypeError, ValueError, KeyError):
        d.text((525, 105), name, font=name_font, fill=(255, 255, 255, 255),
               anchor="mm", stroke_width=1, stroke_fill=(2, 18, 48, 230))
    d.text((555, 198), username_text, font=username_font, fill=(248, 252, 255, 255),
           anchor="mm", stroke_width=1, stroke_fill=(0, 20, 55, 210))

    # Compact value panels cover only the template's zero placeholders; all labels and artwork stay untouched.
    def value_panel(draw, box, value, suffix, font_size=47):
        x1, y1, x2, y2 = box
        draw.rounded_rectangle(box, radius=18, fill=(2, 16, 39, 255),
                               outline=(0, 150, 255, 165), width=2)
        text = str(value)
        vf = load_font(font_latin_bold, font_size)
        sf = load_font(font_latin_bold, 27)
        if suffix:
            combined = f"{text} {suffix}"
        else:
            combined = text
        draw.text(((x1+x2)//2, (y1+y2)//2), combined, font=vf,
                  fill=(255,255,255,255), anchor="mm", stroke_width=1,
                  stroke_fill=(0, 20, 50, 255))

    value_layer = identity.copy()
    vd = ImageDraw.Draw(value_layer, "RGBA")
    da_value = f"{float(balance_da or 0):,.0f} DA"
    usd_value = f"{float(balance_usd or 0):,.2f} $"
    orders_value = f"{int(total_orders or 0):,}"
    value_panel(vd, (270, 337, 560, 420), da_value, "", 43)
    value_panel(vd, (270, 480, 560, 565), usd_value, "", 43)
    value_panel(vd, (700, 435, 930, 555), orders_value, "", 58)

    # A shared 192-colour palette preserves the blue neon gradients without frame-to-frame colour flicker.
    palette = base.resize((800, 533), Image.Resampling.LANCZOS).quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    frames = []
    for idx in range(4):
        frame = value_layer.copy().convert("RGBA")
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow, "RGBA")

        # Very soft moving glint around the SERADJ crown/logo ring.
        start = idx * 90 + 8
        gd.arc((62, 8, 300, 246), start=start, end=start + 34,
               fill=(80, 195, 255, 105), width=5)
        gd.arc((66, 12, 296, 242), start=start, end=start + 34,
               fill=(210, 245, 255, 155), width=2)

        # Subtle moving highlights on the three original blue card frames.
        shift = idx * 115
        gd.line((25 + shift % 520, 280, min(110 + shift % 520, 595), 280),
                fill=(170, 230, 255, 145), width=4)
        gd.line((635 + shift % 260, 280, min(710 + shift % 260, 935), 280),
                fill=(170, 230, 255, 135), width=4)
        gd.line((25 + shift % 520, 575, min(90 + shift % 520, 595), 575),
                fill=(75, 180, 255, 110), width=3)

        # Keep the shimmer restrained: a small blurred halo, not a flashing effect.
        soft = glow.filter(ImageFilter.GaussianBlur(3))
        frame = Image.alpha_composite(frame, soft)
        frame = Image.alpha_composite(frame, glow)
        frames.append(frame.convert("RGB").resize((800, 533), Image.Resampling.LANCZOS).quantize(palette=palette, dither=Image.Dither.NONE))

    out = io.BytesIO()
    frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:],
                   duration=180, loop=0, optimize=True, disposal=2)
    out.seek(0)
    out.name = "seradj_account.gif"
    logging.info("Account GIF generated: %s bytes", len(out.getvalue()))
    return out

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

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(user_id, "account_points"), callback_data="account_points"), InlineKeyboardButton(tr(user_id, "account_orders"), callback_data="account_orders")],
        [InlineKeyboardButton(tr(user_id, "account_deposit"), callback_data="account_deposit")],
        [InlineKeyboardButton(tr(user_id, "wallet_history"), callback_data="wallet_history")],
    ])

    animation = None
    try:
        animation = generate_account_gif(
            user["full_name"], user["balance"], user["balance_usd"], total,
            user_language(user_id), username=user["username"]
        )
        if animation:
            await message.reply_animation(
                animation=animation,
                caption=tr(user_id, "account_title"),
                reply_markup=markup,
            )
            return
    except Exception:
        logging.exception("Failed to generate or send customer account GIF")
        # If Telegram rejects the animation after it was generated, allow the
        # normal text account view to be sent as a fallback.
        animation = None

    if animation is None:
        username = f"@{user['username']}" if user["username"] else "غير متوفر"
        lang = user_language(user_id)
        type_label = tr(user_id, "trader") if user["account_type"] == "trader" else tr(user_id, "customer")
        await message.reply_text(
            f"{tr(user_id, 'account_title')}\n\n"
            f"{tr(user_id, 'id')}: {user_id}\n{tr(user_id, 'name')}: {user['full_name']}\n{tr(user_id, 'username')}: {username or tr(user_id, 'not_available')}\n"
            f"{tr(user_id, 'order_count')}: {total}\n"
            f"{tr(user_id, 'wallet_da')}: {int(user['balance'] or 0)} DA\n"
            f"{tr(user_id, 'wallet_usd')}: {float(user['balance_usd'] or 0):.2f} USD\n"
            f"{tr(user_id, 'type')}: {type_label}",
            reply_markup=markup,
        )

# ====== عرض عروض اللعبة ======

async def open_game(query, game_id, platform=None, recharge_method_id=None, price_mode="choose"):
    user_id = query.from_user.id
    game = get_game(game_id)

    if not game or not game["active"]:
        await edit_query_message(query, 
            "❌ هذه الخدمة غير متاحة حالياً."
        )
        return

    game_category = (game["category"] if "category" in game.keys() else "game") or "game"
    category_back = "back_apps" if game_category == "app" else "back_games"
    mode = game["platform_mode"] if "platform_mode" in game.keys() else "none"
    if mode == "both" and platform is None:
        await edit_query_message(query, 
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
        await edit_query_message(query, f"{game['emoji']} {game['name']}\n\nاختر طريقة الشحن:", reply_markup=InlineKeyboardMarkup(buttons))
        return
    selected_method = next((m for m in methods if int(m["id"]) == int(recharge_method_id)), None) if recharge_method_id is not None else (methods[0] if methods else None)
    if not selected_method:
        await edit_query_message(query, "لا توجد طريقة شحن مفعلة لهذه الخدمة."); return
    context_method_id = int(selected_method["id"])
    offers = [o for o in get_offers(game_id) if o["recharge_method_id"] is not None and int(o["recharge_method_id"]) == context_method_id]
    if platform == "android":
        offers = [o for o in offers if int(o["android_active"] or 0)]
    elif platform == "ios":
        offers = [o for o in offers if int(o["ios_active"] or 0)]
    description = (game["description"] or "").strip()

    if not offers:
        await edit_query_message(query, 
            f"{game['emoji']} {game['name']}\n\n"
            f"{description + chr(10) + chr(10) if description else ''}"
            "لا توجد عروض حالياً.\n"
            "تواصل مع الإدارة للمزيد من المعلومات."
        )
        return

    buttons = []

    for offer in offers:
        da_price = wallet_offer_price(offer, user_id, "DA")
        usd_price = wallet_offer_price(offer, user_id, "USD")
        buttons.append([InlineKeyboardButton(
            f"{offer['name']} | 💰 {da_price} DA / 💵 {usd_price:.2f} USD",
            callback_data=f"offer:{game_id}:{offer['id']}:{platform or 'none'}:wallet_da",
        )])

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

    await edit_query_message(query, 
        f"{game['emoji']} {game['name']}\n\n"
        f"{description + chr(10) + chr(10) if description else ''}"
        f"📱 الجهاز: {'Android' if platform == 'android' else 'iPhone (iOS)' if platform == 'ios' else 'غير مطلوب'}\n"
        + ("اختر طريقة عرض الأسعار من الأزرار أعلاه؛ ستظهر أسعار الطريقة المختارة فقط.\n" if price_mode == "choose" else "اختر العرض المناسب من الأسعار المعروضة فقط.\n")
        + f"الأسعار حسب فئتك ({'تاجر' if is_trader(user_id) else 'زبون عادي'}).",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ====== تفاصيل العرض ======

async def open_offer(query, game_id, offer_id, platform=None, context=None, price_mode="choose"):
    user_id = query.from_user.id
    game = get_game(game_id)
    offers = get_offers(game_id)

    offer = next(
        (item for item in offers if item["id"] == offer_id),
        None,
    )

    if not game or not offer:
        await edit_query_message(query, 
            "❌ هذا العرض غير متاح."
        )
        return
    if platform == "android" and not int(offer["android_active"] or 0):
        await edit_query_message(query, "❌ هذا العرض غير متوفر على Android.")
        return
    if platform == "ios" and not int(offer["ios_active"] or 0):
        await edit_query_message(query, "❌ هذا العرض غير متوفر على iPhone.")
        return

    buttons = []
    da_price = wallet_offer_price(offer, user_id, "DA")
    usd_price = wallet_offer_price(offer, user_id, "USD")
    buttons.extend([
        [InlineKeyboardButton(f"💰 الدفع من محفظة الدينار — {da_price} DA", callback_data=f"pay:{game_id}:{offer_id}:balance")],
        [InlineKeyboardButton(f"💵 الدفع من محفظة الدولار — {usd_price:.2f} USD", callback_data=f"pay:{game_id}:{offer_id}:balance_usd")],
        [InlineKeyboardButton("🛒 إضافة إلى السلة", callback_data=f"cart_add:{game_id}:{offer_id}:{platform or 'none'}:wallet_da")],
        [InlineKeyboardButton("🛒 عرض السلة", callback_data="cart_view")],
        [InlineKeyboardButton("🔙 رجوع للعروض", callback_data=f"recharge_select:{game_id}:{int(offer['recharge_method_id'])}:{platform or 'none'}")],
    ])
    wallet_price = int(offer_price(offer, "baridi", user_id))
    buttons[0] = [InlineKeyboardButton(f"💰 الدفع من محفظة الدينار — {wallet_price} DA", callback_data=f"pay:{game_id}:{offer_id}:balance")]
    buttons[1] = [InlineKeyboardButton(f"💵 الدفع من محفظة الدولار — {usd_price:.2f} USD", callback_data=f"pay:{game_id}:{offer_id}:balance_usd")]
    buttons.append([InlineKeyboardButton("🔙 رجوع للعروض", callback_data=f"recharge_select:{game_id}:{int(offer['recharge_method_id'])}:{platform or 'none'}")])
    if context is not None:
        context.user_data["use_points_for_order"] = False
    await edit_query_message(query, 
        "🛍️ تفاصيل العرض\n\n"
        f"🎮 اللعبة: {game['name']}\n"
        f"📦 العرض: {offer['name']}\n"
        f"📱 الجهاز: {'Android' if platform == 'android' else 'iPhone (iOS)' if platform == 'ios' else 'غير مطلوب'}\n\n"
        f"💰 السعر: {wallet_price} DA / {usd_price:.2f} USD\n"
        + "💳 اختر المحفظة المناسبة عند الدفع.",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ====== سلة المشتريات والمهلة الزمنية ======
def _cart_method_info(game_id, offer_id):
    game = get_game(game_id)
    offer = next((x for x in get_offers(game_id) if int(x["id"]) == int(offer_id)), None)
    if not game or not offer:
        return None, None, None
    with db() as conn:
        method = conn.execute("SELECT * FROM recharge_methods WHERE id=?", (offer["recharge_method_id"],)).fetchone() if offer["recharge_method_id"] else None
    kind = (method["method_type"] if method else game["recharge_method"]) or "id"
    return game, offer, kind


def _cart_total(cart, payment_type, user_id):
    total = 0
    for item in cart["items"]:
        _, offer, _ = _cart_method_info(cart["game_id"], item["offer_id"])
        if not offer:
            continue
        ccy = "USD" if payment_type in ("balance_usd", "trader_wallet_usd") else "DA"
        total += wallet_offer_price(offer, user_id, ccy) * int(item["quantity"])
    return total


def _cart_text(cart, user_id, payment_type=None):
    game = get_game(cart["game_id"])
    lines = ["🛒 سلة مشترياتك", f"🎮 اللعبة: {game['name'] if game else '—'}", ""]
    total = 0
    for item in cart["items"]:
        _, offer, _ = _cart_method_info(cart["game_id"], item["offer_id"])
        if not offer:
            continue
        ccy_for_price = "USD" if payment_type in ("balance_usd", "trader_wallet_usd") else "DA"
        unit = wallet_offer_price(offer, user_id, ccy_for_price) if payment_type else 0
        subtotal = unit * int(item["quantity"])
        total += subtotal
        item_ccy = "USD" if payment_type in ("balance_usd", "trader_wallet_usd") else "DA"
        item_label = f"{subtotal:.2f} USD" if item_ccy == "USD" else f"{int(subtotal)} DA"
        lines.append(f"• {offer['name']} × {item['quantity']}" + (f" — {item_label}" if payment_type else ""))
    if payment_type:
        ccy = "USD" if payment_type in ("balance_usd", "trader_wallet_usd") else "DA"
        lines += ["", f"💰 المجموع: {total:.2f} {ccy}" if ccy == "USD" else f"💰 المجموع: {int(total)} DA"]
    lines += ["", "تقدر تزيد أو تنقص الكمية أو تحذف أي عرض."]
    return "\n".join(lines)


async def _expire_cart_checkout(context, user_id, token):
    try:
        await asyncio.sleep(15 * 60)
        user_data = context.application.user_data.get(user_id, {})
        if user_data.get("cart_checkout_token") != token:
            return
        user_data.pop("cart_checkout_token", None)
        user_data["expired_order_checkout"] = True
        for key in ("order_draft", "pending_player_id", "awaiting_player_id", "awaiting_login_email", "awaiting_login_password", "pending_login_email", "awaiting_payment_receipt", "cart_checkout_active"):
            user_data.pop(key, None)
        try:
            await context.bot.send_message(chat_id=user_id, text="⏰ انتهت مهلة الدفع (15 دقيقة)، وتم إلغاء العملية تلقائيًا. ابدأ طلبًا جديدًا إذا ما زلت ترغب في الشراء.", reply_markup=main_keyboard(user_id))
        except Exception:
            logger.exception("تعذر إرسال إشعار انتهاء مهلة السلة للمستخدم %s", user_id)
    finally:
        CART_TIMEOUT_TASKS.pop(user_id, None)


async def _begin_cart_timer(context, user_id):
    context.user_data.pop("expired_order_checkout", None)
    old = CART_TIMEOUT_TASKS.pop(user_id, None)
    if old and not old.done():
        old.cancel()
    token = f"{user_id}:{datetime.now().timestamp()}"
    context.user_data["cart_checkout_token"] = token
    context.user_data["cart_checkout_active"] = True
    CART_TIMEOUT_TASKS[user_id] = asyncio.create_task(_expire_cart_checkout(context, user_id, token))


async def _cart_add(query, context, game_id, offer_id, platform, price_mode="choose"):
    game, offer, kind = _cart_method_info(game_id, offer_id)
    if not game or not offer:
        await query.answer("العرض غير متوفر.", show_alert=True); return
    if platform == "android" and not int(offer["android_active"] or 0):
        await query.answer("العرض غير متوفر على Android.", show_alert=True); return
    if platform == "ios" and not int(offer["ios_active"] or 0):
        await query.answer("العرض غير متوفر على iPhone.", show_alert=True); return
    cart = context.user_data.get("cart")
    method_id = int(offer["recharge_method_id"] or 0)
    if cart and (int(cart["game_id"]) != int(game_id) or int(cart.get("recharge_method_id", 0)) != method_id or cart.get("platform", "") != (platform if platform != "none" else "")):
        await query.answer("السلة تقبل عروض نفس اللعبة ونفس طريقة الشحن والجهاز فقط. أفرغ السلة أو أكمل الطلب الحالي أولًا.", show_alert=True); return
    selected_mode = price_mode if price_mode in ("baridi", "flexy", "usd", "trader_da", "trader_usd", "wallet_da") else "choose"
    if cart and cart.get("price_mode", "choose") != selected_mode:
        await query.answer("السلة الحالية من فئة أسعار مختلفة. أكمل الطلب أو أفرغ السلة أولًا.", show_alert=True); return
    if not cart:
        cart = {"game_id": int(game_id), "recharge_method_id": method_id, "method_type": kind, "platform": platform if platform != "none" else "", "price_mode": selected_mode, "items": []}
        context.user_data["cart"] = cart
    existing = next((x for x in cart["items"] if int(x["offer_id"]) == int(offer_id)), None)
    if existing:
        existing["quantity"] = min(99, int(existing["quantity"]) + 1)
    else:
        cart["items"].append({"offer_id": int(offer_id), "quantity": 1})
    await query.answer("تمت إضافة العرض إلى السلة ✅")
    await edit_query_message(query, _cart_text(cart, query.from_user.id), reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 عرض السلة", callback_data="cart_view")],
        [InlineKeyboardButton("🔙 مواصلة التسوق", callback_data=f"recharge_select:{game_id}:{method_id}:{platform}")]
    ]))


async def _cart_view(query, context):
    cart = context.user_data.get("cart")
    if not cart or not cart.get("items"):
        await edit_query_message(query, "🛒 السلة فارغة.")
        return
    rows = []
    for item in cart["items"]:
        _, offer, _ = _cart_method_info(cart["game_id"], item["offer_id"])
        if offer:
            oid = int(item["offer_id"])
            rows.append([InlineKeyboardButton(f"➖ {offer['name']}", callback_data=f"cart_dec:{oid}"), InlineKeyboardButton(f"{item['quantity']} ×", callback_data="cart_view"), InlineKeyboardButton("➕", callback_data=f"cart_inc:{oid}"), InlineKeyboardButton("🗑️", callback_data=f"cart_del:{oid}")])
    rows += [[InlineKeyboardButton("💳 متابعة للدفع", callback_data="cart_checkout")], [InlineKeyboardButton("🧹 إفراغ السلة", callback_data="cart_clear")]]
    await edit_query_message(query, _cart_text(cart, query.from_user.id), reply_markup=InlineKeyboardMarkup(rows))


async def _cart_checkout(query, context):
    cart = context.user_data.get("cart")
    if not cart or not cart.get("items"):
        await edit_query_message(query, "🛒 السلة فارغة."); return
    buttons = [
        [InlineKeyboardButton(f"💰 الدفع من محفظة الدينار — {_cart_total(cart, 'balance', query.from_user.id)} DA", callback_data="cart_pay:balance")],
        [InlineKeyboardButton(f"💵 الدفع من محفظة الدولار — {_cart_total(cart, 'balance_usd', query.from_user.id):.2f} USD", callback_data="cart_pay:balance_usd")],
        [InlineKeyboardButton("🔙 رجوع للسلة", callback_data="cart_view")],
    ]
    await edit_query_message(query, "💳 اختر المحفظة التي تريد الدفع منها.\n⏳ عند اختيار الدفع تبدأ مهلة 15 دقيقة.", reply_markup=InlineKeyboardMarkup(buttons))

async def _cart_start_payment(query, context, payment_type):
    cart = context.user_data.get("cart")
    if not cart or not cart.get("items"):
        await edit_query_message(query, "🛒 السلة فارغة."); return
    if payment_type not in ("baridi", "flexy", "balance", "balance_usd", "trader_wallet", "trader_wallet_usd"):
        await query.answer("طريقة الدفع غير مدعومة للسلة حاليًا.", show_alert=True); return
    game = get_game(cart["game_id"])
    if payment_type in ("trader_wallet", "trader_wallet_usd") and not is_trader(query.from_user.id):
        await query.answer("طريقة الدفع غير متاحة.", show_alert=True); return
    wallet_ccy = "USD" if payment_type in ("balance_usd", "trader_wallet_usd") else "DA"
    base_total = _cart_total(cart, payment_type, query.from_user.id)
    total = base_total
    if payment_type in ("balance", "balance_usd", "trader_wallet", "trader_wallet_usd"):
        column = "balance_usd" if wallet_ccy == "USD" else "balance"
        with db() as conn:
            row = conn.execute(f"SELECT {column} AS wallet_balance FROM users WHERE user_id=?", (query.from_user.id,)).fetchone()
        if not row or float(row["wallet_balance"] or 0) < float(total):
            await edit_query_message(query, f"❌ رصيد محفظة {wallet_ccy} غير كافٍ. المجموع {total} {wallet_ccy}."); return
        method_name = f"محفظة {wallet_ccy}"
    else:
        method_name = "BaridiMob / CCP" if payment_type == "baridi" else "Flexy"
    names = []
    for item in cart["items"]:
        _, offer, _ = _cart_method_info(cart["game_id"], item["offer_id"])
        if offer:
            names.append(f"{offer['name']} × {item['quantity']}")
    context.user_data["order_draft"] = {"cart_mode": True, "cart_items": [dict(x) for x in cart["items"]], "game_id": cart["game_id"], "offer_id": cart["items"][0]["offer_id"], "game_name": game["name"] if game else "", "offer_name": " + ".join(names), "method": method_name, "price": total, "base_price": base_total, "points_used": 0, "payment_type": payment_type, "currency": wallet_ccy, "wallet_currency": wallet_ccy, "platform": cart.get("platform", ""), "login_mode": cart.get("method_type") == "login"}
    await _begin_cart_timer(context, query.from_user.id)
    if cart.get("method_type") == "login":
        context.user_data["awaiting_login_email"] = True
        prompt = "🔐 أرسل إيميل الحساب الذي تملكه أو لديك إذن بشحنه. سيطلب البوت كلمة السر بعدها."
    elif cart.get("method_type") == "none":
        context.user_data["pending_player_id"] = ""
        if payment_type in ("balance", "balance_usd", "trader_wallet", "trader_wallet_usd"):
            await create_wallet_order(query.message, context, "", user=query.from_user); return
        context.user_data["awaiting_payment_receipt"] = True
        prompt = "📸 أرسل صورة وصل الدفع لإتمام الطلب. تقدر ترسل عدة صور مع بعض كألبوم."
    else:
        context.user_data["awaiting_player_id"] = True
        prompt = "🆔 أرسل Player ID الخاص بنفس اللاعب."
    await edit_query_message(query, _cart_text(cart, query.from_user.id, payment_type) + f"\n\n💳 طريقة الدفع: {method_name}\n⏳ لديك 15 دقيقة لإتمام الطلب.\n\n{prompt}\nللإلغاء أرسل /cancel")


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
        await edit_query_message(query, 
            "❌ العرض لم يعد متاحاً."
        )
        return

    currency = "DA"
    if method in ("balance", "balance_usd"):
        currency = "USD" if method == "balance_usd" else "DA"
        price = wallet_offer_price(offer, query.from_user.id, currency)
        method_name = f"محفظة {currency}"
        details = "سيتم الخصم من المحفظة التي اخترتها."
    elif method in ("baridi", "flexy") and (
        get_setting(f"payment_{method}_enabled", "1") != "1"
        or get_setting(f"offer_payment_{method}_{offer_id}", "1") != "1"
    ):
        await edit_query_message(query, "❌ طريقة الدفع هذه غير متاحة حالياً لهذا العرض. اختر طريقة أخرى.")
        return

    if method == "trader_wallet":
        currency = "DA"
        price = wallet_offer_price(offer, query.from_user.id, currency)
        method_name = "محفظة DA"
        details = "سيتم الخصم من محفظة الدينار."
    elif method == "balance_usd":
        # USD wallet price and currency were calculated in the first branch above.
        method_name = "محفظة USD"
        details = "سيتم الخصم من محفظة الدولار."
    elif method == "baridi":
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
            await edit_query_message(query, "❌ القرض غير مفعّل لحسابك. تواصل مع الإدارة.")
            return
        price = offer_price(offer, "baridi", query.from_user.id)
        if debt + price > limit_amount:
            await edit_query_message(query, f"❌ سقف القرض لا يكفي لهذا الطلب.\nسقف القرض: {limit_amount} DA\nالدين الحالي: {debt} DA\nالسعر: {price} DA\nالمتاح: {max(0, limit_amount-debt)} DA")
            return
        method_name = "قرض التاجر"
        details = f"الدين الحالي: {debt} DA\nالمتاح من سقف القرض: {limit_amount-debt} DA\nأجل التسديد: {term_days} يومًا"
    elif method.startswith("custom_"):
        try:
            custom_id = int(method.split("_", 1)[1])
        except (ValueError, IndexError):
            await edit_query_message(query, "❌ طريقة الدفع غير صحيحة.")
            return
        with db() as conn:
            custom_method = conn.execute("SELECT * FROM custom_payment_methods WHERE id=? AND enabled=1", (custom_id,)).fetchone()
            offer_method = conn.execute("SELECT enabled FROM offer_payment_methods WHERE offer_id=? AND method_id=?", (offer_id, custom_id)).fetchone()
        if not custom_method:
            await edit_query_message(query, "❌ طريقة الدفع هذه غير متاحة حالياً.")
            return
        currency = (custom_method["currency"] or "USD").upper()
        if currency == "USD" and get_setting("usd_payments_enabled", "0") != "1":
            await edit_query_message(query, "❌ طرق الدفع بالدولار متوقفة مؤقتًا.")
            return
        if offer_method and not int(offer_method["enabled"] or 0):
            await edit_query_message(query, "❌ طريقة الدفع هذه متوقفة لهذا العرض.")
            return
        base_dzd = Decimal(offer_price(offer, "baridi", query.from_user.id))
        if currency == "USD":
            explicit_usd = _offer_usd_source_price(offer, query.from_user.id)
            if explicit_usd is not None:
                price = float(explicit_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            else:
                price = float((base_dzd / usd_buy_rate()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        else:
            price = int(base_dzd)
        method_name = f"{custom_method['emoji']} {custom_method['name']}"
        details = custom_method["instructions"] or "تواصل مع الإدارة لمعرفة تعليمات الدفع."
    elif method == "balance":
        with db() as conn:
            row = conn.execute("SELECT balance FROM users WHERE user_id = ?", (query.from_user.id,)).fetchone()
        balance = int(row["balance"] or 0) if row else 0
        price = offer_price(offer, "baridi", query.from_user.id)
        # لا تُعامل نقاط الولاء كأنها دنانير ولا تُضاف إلى رصيد المحفظة.
        context.user_data["use_points_for_order"] = False
        method_name = "رصيد المحفظة"
        details = "سيُخصم المبلغ من محفظتك عند تأكيد الطلب."
    else:
        await edit_query_message(query, 
            "❌ طريقة الدفع غير صحيحة."
        )
        return

    if method in ("balance", "balance_usd", "trader_wallet"):
        wallet_col = "balance_usd" if currency == "USD" else "balance"
        with db() as conn:
            row = conn.execute(f"SELECT {wallet_col} AS wallet_balance FROM users WHERE user_id=?", (query.from_user.id,)).fetchone()
        balance = float(row["wallet_balance"] or 0) if row else 0
        if balance < float(price):
            await edit_query_message(query, f"❌ رصيد محفظة {currency} غير كافٍ.\nالسعر: {price} {currency}\nرصيدك: {balance} {currency}\nعبّئ محفظتك أو اختر طريقة أخرى.")
            return

    # Loyalty points are not cash and must never be auto-deducted from a normal order.
    base_price = price
    points_used = 0
    context.user_data["use_points_for_order"] = False

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
        "currency": currency if method.startswith("custom_") or method in ("balance", "balance_usd", "trader_wallet") else "DA",
        "wallet_currency": currency if method in ("balance", "balance_usd", "trader_wallet") else "DA",
        "platform": context.user_data.get("selected_platform", ""),
    }
    await _begin_cart_timer(context, query.from_user.id)

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
        if method in ("balance", "balance_usd", "trader_wallet"):
            await create_wallet_order(query.message, context, "", user=query.from_user)
            return
        if method == "credit":
            await create_credit_order(query.message, context, "", user=query.from_user)
            return
        context.user_data["awaiting_payment_receipt"] = True
        prompt = "🧾 هذا العرض لا يحتاج ID أو بيانات دخول. أرسل صورة وصل الدفع مباشرة لإتمام الطلب، وتقدر ترسل عدة صور مع بعض كألبوم."
    else:
        context.user_data["awaiting_player_id"] = True
        prompt = custom_prompt or "🆔 أرسل الآن معرف اللاعب (Player ID).\nإذا ما تحتاجش الخدمة معرف، أرسل: بدون"

    await edit_query_message(query, 
        "✅ اخترت العرض بنجاح!\n\n"
        f"🎮 اللعبة: {game['name']}\n"
        f"📦 العرض: {offer['name']}\n"
        f"🔀 طريقة الشحن: {selected_method['title'] if selected_method else 'الطريقة الافتراضية'}\n"
        f"💳 الدفع: {method_name}\n"
        f"💰 السعر: {price} {currency if method.startswith('custom_') or method in ('balance', 'balance_usd', 'trader_wallet') else 'DA'}\n"
        + f"\n💳 معلومات الدفع:\n{details}\n\n"
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
    wallet_ccy = str(draft.get("wallet_currency", "DA")).upper()
    price = float(draft["price"]) if wallet_ccy == "USD" else int(draft["price"])
    points_used = int(draft.get("points_used", 0))
    if wallet_ccy not in ("DA", "USD"):
        wallet_ccy = "DA"
    wallet_col = "balance_usd" if wallet_ccy == "USD" else "balance"
    with db() as conn:
        row = conn.execute(f"SELECT {wallet_col} AS wallet_balance, points FROM users WHERE user_id = ?", (user.id,)).fetchone()
        if not row or float(row["wallet_balance"] or 0) < float(price) or int(row["points"] or 0) < points_used:
            await message.reply_text(f"❌ رصيد محفظة {wallet_ccy} أو النقاط غير كافٍ. راجع حسابك وأعد الطلب.")
            return
        conn.execute(f"UPDATE users SET {wallet_col} = {wallet_col} - ?, points = points - ? WHERE user_id = ?", (price, points_used, user.id))
        cursor = conn.execute(
            "INSERT INTO orders (user_id, game_id, offer_id, player_id, payment_method, price, currency, status, created_at, points_used, platform, wallet_charged) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, 1)",
            (user.id, draft["game_id"], draft["offer_id"], player_id, draft.get("method", "رصيد المحفظة"), price, wallet_ccy, now_text(), points_used, draft.get("platform", "")),
        )
        order_id = cursor.lastrowid
        if draft.get("cart_mode"):
            for item in draft.get("cart_items", []):
                _, cart_offer, _ = _cart_method_info(draft["game_id"], item["offer_id"])
                if cart_offer:
                    unit = wallet_offer_price(cart_offer, user.id, wallet_ccy)
                    conn.execute("INSERT INTO order_items (order_id, offer_id, offer_name, quantity, unit_price) VALUES (?, ?, ?, ?, ?)", (order_id, item["offer_id"], cart_offer["name"], item["quantity"], unit))
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 قيد التنفيذ", callback_data=f"status:{order_id}:processing"), InlineKeyboardButton("✅ مكتمل", callback_data=f"status:{order_id}:completed")],
        [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"status:{order_id}:rejected")],
    ])
    await dispatch_order_to_group(context, order_id, user, draft, player_id, draft.get("method", "رصيد المحفظة"), price, points_used)
    context.user_data.pop("order_draft", None)
    context.user_data.pop("pending_player_id", None)
    context.user_data.pop("awaiting_player_id", None)
    context.user_data.pop("awaiting_login_email", None)
    context.user_data.pop("awaiting_login_password", None)
    context.user_data.pop("pending_login_email", None)
    context.user_data.pop("awaiting_payment_receipt", None)
    context.user_data.pop("cart_checkout_active", None)
    context.user_data.pop("cart_checkout_token", None)
    task = CART_TIMEOUT_TASKS.pop(user.id, None)
    if task and not task.done(): task.cancel()
    if draft.get("cart_mode"):
        context.user_data.pop("cart", None)
    await message.reply_text(f"✅ تم تسجيل طلبك #{order_id}.\n💰 المبلغ المخصوم: {price} {wallet_ccy}\n🎁 النقاط المستخدمة: {points_used}\nسيتم إعلامك عند تحديث الحالة.", reply_markup=main_keyboard(user.id))


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

    if draft.get("payment_type") in ("balance", "balance_usd", "trader_wallet", "trader_wallet_usd"):
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
        f"💰 المبلغ: {draft['price']} {draft.get('currency', 'DA')}\n\n"
        "📸 الآن أرسل صورة وصل الدفع لإتمام الطلب. تقدر ترسل عدة صور مع بعض كألبوم.\n\n"
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
    if user and is_admin(user.id) and context.user_data.get("admin_step") == "notify_broadcast_photo" and message.photo:
        context.user_data["pending_broadcast_photo_file_id"] = message.photo[-1].file_id
        context.user_data["admin_step"] = "notify_broadcast_buttons"
        await message.reply_text(
            "✅ تم حفظ صورة الإشعار. الآن أرسل الأزرار (كل زر في سطر) أو اكتب بدون."
        )
        return
    if user and context.user_data.pop("expired_order_checkout", False):
        await message.reply_text("⏰ انتهت مهلة الدفع (15 دقيقة)، ولم يتم تسجيل الطلب. أعد الطلب من المتجر إذا كنت لا تزال ترغب في الشراء.", reply_markup=main_keyboard(user.id))
        return
    # Work-group shipping receipts must remain available even when the customer store is closed.
    if user and context.user_data.get("awaiting_order_receipt") and context.user_data.get("order_receipt_group_id"):
        receipt_order_id = int(context.user_data.get("awaiting_order_receipt"))
        source_group = int(context.user_data.get("order_receipt_group_id"))
        if message.chat_id != source_group:
            await message.reply_text("📷 أرسل الوصل في نفس قروب الطلب الذي بدأت منه العملية.")
            return
        with db() as conn:
            claimed = conn.execute("SELECT claimed_by,status FROM orders WHERE id=?", (receipt_order_id,)).fetchone()
        if not claimed or not int(claimed["claimed_by"] or 0) or claimed["status"] in ("completed", "rejected"):
            context.user_data.pop("awaiting_order_receipt", None)
            context.user_data.pop("order_receipt_group_id", None)
            await message.reply_text("⛔ لم يعد الطلب مفتوحًا لإرفاق وصل الشحن.")
            return
        key = f"shipping_receipts:{receipt_order_id}"
        ids = context.user_data.setdefault(key, [])
        fid = message.photo[-1].file_id
        if fid not in ids:
            ids.append(fid)
        await asyncio.sleep(1.3)  # collect all images from a Telegram album
        current_album = context.user_data.get(key, [])
        if not current_album or current_album[-1] != fid:
            return
        receipt_ids = list(context.user_data.get(key, []))[:10]
        context.user_data[f"order_receipt_photos:{receipt_order_id}"] = receipt_ids
        context.user_data[f"order_receipt_photo:{receipt_order_id}"] = receipt_ids[0]
        with db() as conn:
            conn.execute("UPDATE orders SET shipping_receipt_file_id=?, shipping_receipt_file_ids=?, shipping_receipt_by=?, shipping_receipt_at=? WHERE id=?",
                         (receipt_ids[0], json.dumps(receipt_ids), user.id, now_text(), receipt_order_id))
        context.user_data.pop("awaiting_order_receipt", None)
        context.user_data.pop("order_receipt_group_id", None)
        await message.reply_text(
            f"✅ تم حفظ {len(context.user_data[key])} صورة لوصل الطلب #{receipt_order_id}. اضغط لإتمام الطلب وإرسالها للزبون:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ إتمام وإرسال الوصل", callback_data=f"order_finish_with_receipt:{receipt_order_id}")]])
        )
        return
    if user and not is_admin(user.id) and not store_is_open():
        await message.reply_text(store_closed_notice())
        return
    if user and not is_admin(user.id):
        row = get_user_row(user.id)
        if row and int(row["is_banned"] or 0):
            await message.reply_text("🚫 حسابك محظور من استعمال البوت.")
            return

    if context.user_data.get("awaiting_order_completion_text"):
        completion_order_id = int(context.user_data.get("awaiting_order_completion_text"))
        expected_chat = context.user_data.get("order_completion_chat_id")
        if expected_chat and message.chat_id != int(expected_chat):
            await message.reply_text("أرسل نص الإتمام في نفس محادثة/مجموعة الطلب.")
            return
        if not text or len(text.strip()) < 2:
            await message.reply_text("اكتب رسالة واضحة من حرفين على الأقل.")
            return
        with db() as conn:
            row = conn.execute("SELECT claimed_by,status FROM orders WHERE id=?", (completion_order_id,)).fetchone()
            if not row or row["status"] in ("completed", "rejected"):
                context.user_data.pop("awaiting_order_completion_text", None)
                context.user_data.pop("order_completion_chat_id", None)
                await message.reply_text("الطلب غير متاح أو تمت معالجته.")
                return
            if message.chat.type in ("group", "supergroup") and int(row["claimed_by"] or 0) != user.id:
                await message.reply_text("إتمام الطلب برسالة متاح لمستلم الطلب فقط.")
                return
            conn.execute("UPDATE orders SET completion_message=? WHERE id=?", (text.strip(), completion_order_id))
        context.user_data.pop("awaiting_order_completion_text", None)
        context.user_data.pop("order_completion_chat_id", None)
        await message.reply_text(
            f"✅ تم حفظ رسالة الطلب #{completion_order_id}. اضغط لتأكيد الإتمام وإرسالها للزبون:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأكيد الإتمام وإرسال النص", callback_data=f"status:{completion_order_id}:completed")], [InlineKeyboardButton("❌ إلغاء", callback_data=f"order_finish_back:{completion_order_id}")]])
        )
        return

    if context.user_data.get("awaiting_order_receipt"):
        if not user:
            context.user_data.pop("awaiting_order_receipt", None); return
        receipt_order_id = int(context.user_data.get("awaiting_order_receipt"))
        source_group = context.user_data.get("order_receipt_group_id")
        if source_group and message.chat_id != int(source_group):
            await message.reply_text("📷 أرسل الوصل في نفس قروب الطلب الذي بدأت منه العملية."); return
        if not source_group and not is_admin(user.id):
            context.user_data.pop("awaiting_order_receipt", None); return
        if source_group:
            with db() as conn:
                claimed = conn.execute("SELECT claimed_by,status FROM orders WHERE id=?", (receipt_order_id,)).fetchone()
            valid_receipt_order = bool(claimed and int(claimed["claimed_by"] or 0) and claimed["status"] not in ("completed", "rejected"))
            if not valid_receipt_order:
                context.user_data.pop("awaiting_order_receipt", None)
                context.user_data.pop("order_receipt_group_id", None)
                await message.reply_text("⛔ الطلب غير مستلم أو تمت معالجته؛ لا يمكن إرفاق وصل له."); return
        key = f"shipping_receipts:{receipt_order_id}"
        ids = context.user_data.setdefault(key, [])
        fid = message.photo[-1].file_id
        if fid not in ids:
            ids.append(fid)
        await asyncio.sleep(1.3)
        current_album = context.user_data.get(key, [])
        if not current_album or current_album[-1] != fid:
            return
        receipt_ids = list(context.user_data.get(key, []))[:10]
        context.user_data[f"order_receipt_photos:{receipt_order_id}"] = receipt_ids
        context.user_data[f"order_receipt_photo:{receipt_order_id}"] = receipt_ids[0]
        with db() as conn:
            conn.execute("UPDATE orders SET shipping_receipt_file_id=?, shipping_receipt_file_ids=?, shipping_receipt_by=?, shipping_receipt_at=? WHERE id=?",
                         (receipt_ids[0], json.dumps(receipt_ids), user.id, now_text(), receipt_order_id))
        context.user_data.pop("awaiting_order_receipt", None)
        context.user_data.pop("order_receipt_group_id", None)
        await message.reply_text(
            f"✅ تم حفظ {len(receipt_ids)} صورة لوصل الطلب #{receipt_order_id}. اختر إتمام الطلب بالصورة:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ إتمام وإرسال الوصل", callback_data=f"order_finish_with_receipt:{receipt_order_id}")], [InlineKeyboardButton("❌ إلغاء الخطوة", callback_data=f"order_finish_back:{receipt_order_id}")]])
        )
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
        with db() as conn:
            pending_existing = conn.execute("SELECT id FROM wallet_deposits WHERE user_id=? AND status='pending' LIMIT 1", (user.id,)).fetchone()
        if pending_existing:
            await message.reply_text(f"لديك طلب تعبئة قيد المراجعة #{pending_existing['id']}، انتظر قرار الإدارة.", reply_markup=main_keyboard(user.id))
            for k in ("awaiting_deposit_receipt", "deposit_amount", "deposit_amount_usd", "deposit_method", "deposit_currency", "deposit_paid_amount", "deposit_flexy_mode", "deposit_requested_amount"):
                context.user_data.pop(k, None)
            return
        method = context.user_data.get("deposit_method", "")
        currency = (context.user_data.get("deposit_currency") or "DA").upper()
        if not method:
            context.user_data.pop("awaiting_deposit_receipt", None)
            await message.reply_text("❌ انتهت جلسة التعبئة. ابدأ من جديد.")
            return
        if currency == "USD":
            amount_usd = float(context.user_data.get("deposit_amount_usd", 0) or 0)
            if not (amount_usd > 0):
                context.user_data.pop("awaiting_deposit_receipt", None)
                await message.reply_text("❌ مبلغ الدولار غير صحيح. ابدأ التعبئة من جديد.")
                return
            amount = 0
        else:
            amount = int(context.user_data.get("deposit_amount", 0) or 0)
            requested_amount = int(context.user_data.get("deposit_requested_amount", amount) or amount)
            method_key = "flexy" if "flexy" in method.lower() else "baridi"
            account_type = "trader" if is_trader(user.id) else "customer"
            minimum, maximum = deposit_limits(account_type, method_key)
            if requested_amount < minimum or requested_amount > maximum:
                context.user_data.pop("awaiting_deposit_receipt", None)
                context.user_data.pop("deposit_amount", None)
                context.user_data.pop("deposit_method", None)
                await message.reply_text(f"❌ مبلغ التعبئة خارج الحدود المسموحة ({minimum} إلى {maximum} DA). ابدأ من جديد.")
                return
            amount_usd = 0.0
        receipt_type = "video" if message.video else "photo"
        receipt_file_id = message.video.file_id if message.video else message.photo[-1].file_id
        paid_amount = (float(context.user_data.get("deposit_paid_amount", 0) or 0) or (int(round(amount * 1.18)) if method.lower() == "flexy" else amount)) if currency == "DA" else amount_usd
        with db() as conn:
            cur = conn.execute("INSERT INTO wallet_deposits (user_id, amount, amount_usd, currency, payment_method, receipt_file_id, receipt_file_ids, receipt_type, status, created_at, paid_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)", (user.id, amount, amount_usd, currency, method, receipt_file_id, json.dumps([receipt_file_id]), receipt_type, now_text(), paid_amount))
            deposit_id = cur.lastrowid
        display_amount = f"{amount_usd:.2f} USD" if currency == "USD" else f"{amount} DA"
        if ADMIN_ID:
            try:
                send_receipt = context.bot.send_video if receipt_type == "video" else context.bot.send_photo
                await send_receipt(ADMIN_ID, receipt_file_id,
                    caption=f"💰 طلب تعبئة رصيد #{deposit_id}\nالزبون: {user.full_name}\nTelegram ID: {user.id}\nالمبلغ المضاف للمحفظة: {display_amount}\nالمبلغ المدفوع: {paid_amount:g} {'USD' if currency == 'USD' else 'DA'}\nالمحفظة: {currency}\nطريقة الدفع: {method}\nالحالة: قيد المراجعة",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ قبول التعبئة", callback_data=f"deposit_approve:{deposit_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"deposit_reject:{deposit_id}")]]))
            except Exception:
                logger.exception("تعذر إرسال طلب تعبئة الرصيد للإدارة")
        for k in ("awaiting_deposit_receipt", "deposit_amount", "deposit_amount_usd", "deposit_method", "deposit_currency", "deposit_paid_amount", "deposit_flexy_mode", "deposit_requested_amount"):
            context.user_data.pop(k, None)
        await message.reply_text(f"✅ استلمنا وصل التعبئة #{deposit_id}. سيضاف الرصيد إلى محفظة {currency} بعد تأكيد الإدارة.", reply_markup=main_keyboard(user.id))
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

    if draft and draft.get("cart_mode") and not context.user_data.get("cart_checkout_active"):
        context.user_data.pop("awaiting_payment_receipt", None)
        await message.reply_text("⏰ انتهت مهلة الدفع أو أُلغيت العملية. ابدأ طلبًا جديدًا من السلة.", reply_markup=main_keyboard(user.id))
        return
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

    # Collect all photos sent together as a Telegram album before creating the order.
    receipt_key = "pending_order_receipt_photos"
    receipt_ids = context.user_data.setdefault(receipt_key, [])
    incoming_file_id = message.photo[-1].file_id
    if incoming_file_id not in receipt_ids:
        receipt_ids.append(incoming_file_id)
    await asyncio.sleep(1.3)
    current_receipts = context.user_data.get(receipt_key, [])
    if not current_receipts or current_receipts[-1] != incoming_file_id:
        return
    receipt_ids = list(context.user_data.get(receipt_key, []))[:10]
    photo = message.photo[-1]

    # إنشاء الطلب بعد استلام صورة الوصل
    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO orders (
                user_id, game_id, offer_id, player_id,
                payment_method, price, currency, status, created_at, points_used, platform, payment_receipt_file_ids
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                draft["game_id"],
                draft["offer_id"],
                player_id,
                draft["method"],
                draft["price"],
                draft.get("currency", "DA"),
                "pending",
                now_text(),
                int(draft.get("points_used", 0)),
                draft.get("platform", ""),
                json.dumps(receipt_ids),
            ),
        )
        order_id = cursor.lastrowid
        if draft.get("cart_mode"):
            for item in draft.get("cart_items", []):
                _, cart_offer, _ = _cart_method_info(draft["game_id"], item["offer_id"])
                if cart_offer:
                    unit = int(offer_price(cart_offer, "flexy" if draft.get("payment_type") == "flexy" else "baridi", user.id))
                    conn.execute("INSERT INTO order_items (order_id, offer_id, offer_name, quantity, unit_price) VALUES (?, ?, ?, ?, ?)", (order_id, item["offer_id"], cart_offer["name"], item["quantity"], unit))
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
    await dispatch_order_to_group(context, order_id, user, draft, player_id, draft["method"], draft["price"], int(draft.get("points_used", 0)), photo=photo, photo_ids=receipt_ids)

    # إنهاء حالة الطلب المؤقتة
    context.user_data.pop("order_draft", None)
    context.user_data.pop("pending_player_id", None)
    context.user_data.pop("awaiting_payment_receipt", None)
    context.user_data.pop("pending_order_receipt_photos", None)
    context.user_data.pop("use_points_for_order", None)
    if draft.get("cart_mode"):
        context.user_data.pop("cart", None)
    context.user_data.pop("cart_checkout_active", None)
    context.user_data.pop("cart_checkout_token", None)
    task = CART_TIMEOUT_TASKS.pop(user.id, None)
    if task and not task.done(): task.cancel()

    await message.reply_text(
        f"✅ تم استلام {len(receipt_ids)} صورة لوصل الدفع وتسجيل طلبك!\n\n"
        f"🧾 رقم الطلب: #{order_id}\n"
        f"🎮 الخدمة: {draft['game_name']}\n"
        f"📦 العرض: {draft['offer_name']}\n"
        f"{('🆔 معرف اللاعب: ' + player_id + chr(10)) if player_id else '📋 لا يتطلب هذا العرض ID أو بيانات دخول.' + chr(10)}"
        f"💳 طريقة الدفع: {draft['method']}\n"
        f"💰 المبلغ: {draft['price']} {draft.get('currency', 'DA')}\n"
        "📌 الحالة: قيد الانتظار\n\n"
        "ستتحقق الإدارة من الوصل قبل معالجة طلبك.",
        reply_markup=main_keyboard(user.id),
    )
# =========================
# عرض طلبات الزبون
# =========================

async def show_my_orders(update, context):
    user_id = update.effective_user.id
    callback_query = update.callback_query
    target_message = update.effective_message
    if target_message is None and update.callback_query:
        target_message = update.callback_query.message

    with db() as conn:
        orders = conn.execute(
            """
            SELECT id, game_id, offer_id, player_id,
                   payment_method, price, currency, status, created_at
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
        text = "📦 ما عندك حتى طلب حاليا."
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home:main")]])
        if callback_query:
            await edit_query_message(callback_query, text, reply_markup=markup)
        else:
            await target_message.reply_text(text, reply_markup=main_keyboard(user_id))
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
            f"💰 السعر: {format_order_amount(order['price'], order['currency'])}\n"
            f"📌 الحالة: {status_label(order['status'])}\n"
            f"🕒 التاريخ: {order['created_at']}\n"
        )

    lines.append("\nاستعمل القائمة الرئيسية للرجوع إلى المتجر.")
    if callback_query:
        await edit_query_message(callback_query, 
            "\n".join(lines), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home:main")]])
        )
    else:
        await target_message.reply_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=main_keyboard(user_id)
        )


async def show_points_shop(message, user_id):
    if not points_enabled(user_id):
        await message.reply_text("⭐ نظام النقاط متاح لجميع المشترين.", reply_markup=main_keyboard(user_id)); return
    with db() as conn:
        row = conn.execute("SELECT points_da, points_usd FROM users WHERE user_id=?", (user_id,)).fetchone()
    da = float(row["points_da"] or 0) if row else 0
    usd = float(row["points_usd"] or 0) if row else 0.0
    points_rate = 200 if is_trader(user_id) else 100
    buttons = [
        [InlineKeyboardButton("🔄 تحويل نقاط DA إلى محفظة الدينار", callback_data="points_convert:DA")],
        [InlineKeyboardButton("🔄 تحويل نقاط USD إلى محفظة الدولار", callback_data="points_convert:USD")],
    ]
    await message.reply_text(
        "⭐ نقاطك في SERADJ STORE\n\n"
        f"🇩🇿 نقاط الدينار: {da:,} نقطة DA\n"
        f"💵 نقاط الدولار: {usd:.3f} نقطة USD\n\n"
        f"💱 كل {points_rate} نقطة DA = 1 DA في المحفظة.\n"
        f"💱 كل {points_rate} نقطة USD = 1 USD في المحفظة.\n"
        f"يمكنك تحويل مضاعفات {points_rate} نقطة، والباقي يبقى محفوظًا.",
        reply_markup=InlineKeyboardMarkup(buttons))

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
            is_persistent=True,
        ),
    )


#=========================

#إدارة الألعاب

#=========================


# =========================
# اختيار لعبة لإضافة عرض
# =========================

async def admin_choose_offer_game(query, page=0):
    page=max(0,int(page or 0)); per_page=8
    with db() as conn:
        total=int(conn.execute("SELECT COUNT(*) FROM games").fetchone()[0])
        games = conn.execute("SELECT id, name, emoji FROM games ORDER BY id LIMIT ? OFFSET ?", (per_page,page*per_page)).fetchall()

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

    pages=max(1,(total+per_page-1)//per_page)
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ السابق",callback_data=f"adm_add_offer:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}",callback_data="adm_add_offer:noop"))
    if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️",callback_data=f"adm_add_offer:{page+1}"))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 رجوع",callback_data="adm_home")])

    await edit_query_message(query, 
        "🎮 اختار اللعبة لي حاب تزيدلها عرض:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================
# إدارة الألعاب
# =========================

async def admin_games(query, page=0):
    """Paginated game/app administration list."""
    page=max(0, int(page or 0)); per_page=8
    with db() as conn:
        total=int(conn.execute("SELECT COUNT(*) FROM games").fetchone()[0])
        games = conn.execute("SELECT * FROM games ORDER BY CASE WHEN lower(COALESCE(category,''))='app' THEN 0 ELSE 1 END, name COLLATE NOCASE LIMIT ? OFFSET ?", (per_page,page*per_page)).fetchall()
    pages=max(1,(total+per_page-1)//per_page)
    if page >= pages: page=pages-1
    buttons=[]
    for game in games:
        state="🟢" if game["active"] else "🔴"
        buttons.append([InlineKeyboardButton(f"{state} [ID: {game['id']}] {game_button_label(game)}", callback_data=f"game_manage:{game['id']}", **premium_button_kwargs(game['id']))])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"adm_games_page:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="adm_games_page:noop"))
    if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"adm_games_page:{page+1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔄 تحديث", callback_data=f"adm_games_page:{page}")])
    buttons.append([InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")])
    await edit_query_message(query, "🎮 <b>إدارة الألعاب والتطبيقات</b>\n\nاضغط على اسم أي لعبة أو تطبيق لفتح خيارات التحكم.\n🟢 مفعّل | 🔴 متوقف", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


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
    await edit_query_message(query, f"⚙️ <b>إدارة {game_button_label(game)}</b>\n🆔 GAME_ID: <code>{game_id}</code>\nالحالة: {state}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


# =========================
# عرض عروض لعبة معينة
# =========================

async def admin_offers(query, game_id, page=0):
    page=max(0,int(page or 0)); per_page=8
    with db() as conn:
        game=conn.execute("SELECT name, emoji FROM games WHERE id=?",(game_id,)).fetchone()
        total=int(conn.execute("SELECT COUNT(*) FROM offers WHERE game_id=?",(game_id,)).fetchone()[0])
        offers=conn.execute("SELECT id,name,active FROM offers WHERE game_id=? ORDER BY CASE WHEN COALESCE(sort_order,0)>0 THEN sort_order ELSE 1000000+id END,id LIMIT ? OFFSET ?",(game_id,per_page,page*per_page)).fetchall()
    if not game:
        await edit_query_message(query, "❌ اللعبة غير موجودة."); return
    pages=max(1,(total+per_page-1)//per_page)
    if page>=pages: page=pages-1
    buttons=[]
    for offer in offers:
        state="🟢" if offer["active"] else "🔴"
        buttons.append([InlineKeyboardButton(f"{state} {offer['name']} · إدارة العرض",callback_data=f"offer_manage:{offer['id']}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ السابق",callback_data=f"offers_game_page:{game_id}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}",callback_data="offers_game_page:noop"))
    if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️",callback_data=f"offers_game_page:{game_id}:{page+1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton("📝 إرسال قائمة أسعار اللعبة كاملة", callback_data=f"bulk_price_game:{game_id}")])
    buttons.append([InlineKeyboardButton("🔙 اختيار لعبة أخرى",callback_data="adm_offers")])
    text=f"{game['emoji']} <b>عروض {game['name']}</b>\n\nاختر العرض لفتح إعداداته أو أرسل قائمة أسعار اللعبة كاملة.\n🟢 مفعّل | 🔴 متوقف\nالعدد: {total}"
    if not total: text+="\n\nما كاين حتى عرض لهذه اللعبة حاليا."
    await edit_query_message(query, text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(buttons))


async def admin_offer_manage(query, offer_id):
    with db() as conn:
        offer = conn.execute("""SELECT o.*, g.name AS game_name, g.emoji AS game_emoji,
            r.title AS method_title FROM offers o LEFT JOIN games g ON g.id=o.game_id
            LEFT JOIN recharge_methods r ON r.id=o.recharge_method_id WHERE o.id=?""", (offer_id,)).fetchone()
    if not offer:
        await edit_query_message(query, "❌ العرض غير موجود.")
        return
    state = "🟢 مفعّل" if offer['active'] else "🔴 متوقف"
    buttons = [
        [InlineKeyboardButton("⏸️ إيقاف العرض" if offer['active'] else "🟢 تفعيل العرض", callback_data=f"offer_toggle:{offer_id}")],
        [InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"offer_rename:{offer_id}"), InlineKeyboardButton("💰 تعديل الأسعار", callback_data=f"edit_offer:{offer_id}")],
        [InlineKeyboardButton(f"🤖 Android: {'متاح' if offer['android_active'] else 'موقوف'}", callback_data=f"offer_platform:{offer_id}:android"), InlineKeyboardButton(f"🍎 iPhone: {'متاح' if offer['ios_active'] else 'موقوف'}", callback_data=f"offer_platform:{offer_id}:ios")],
        [InlineKeyboardButton("⬆️ تقديم العرض", callback_data=f"offer_move:{offer_id}:up"), InlineKeyboardButton("⬇️ تأخير العرض", callback_data=f"offer_move:{offer_id}:down")],
        [InlineKeyboardButton("🗑️ حذف العرض", callback_data=f"offer_delete:{offer_id}")],
        [InlineKeyboardButton("🔙 قائمة العروض", callback_data=f"offers_game:{offer['game_id']}")],
    ]
    await edit_query_message(query, 
        f"📦 <b>إدارة العرض</b>\n\n{offer['game_emoji']} {offer['game_name']}\nالعرض: <b>{offer['name']}</b>\nطريقة الشحن: {offer['method_title'] or 'طريقة قديمة'}\nالحالة: {state}\n\nاختر الإجراء المطلوب:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons)
    )


# =========================
# اختيار لعبة لإدارة عروضها
# =========================

async def admin_choose_manage_game(query, page=0):
    page=max(0,int(page or 0)); per_page=8
    with db() as conn:
        total=int(conn.execute("SELECT COUNT(*) FROM games").fetchone()[0])
        games=conn.execute("SELECT id,name,emoji FROM games ORDER BY id LIMIT ? OFFSET ?",(per_page,page*per_page)).fetchall()
    pages=max(1,(total+per_page-1)//per_page)
    if page>=pages: page=pages-1
    buttons=[[InlineKeyboardButton(game_button_label(game),callback_data=f"offers_game:{game['id']}",**premium_button_kwargs(game['id']))] for game in games]
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ السابق",callback_data=f"adm_offers_page:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}",callback_data="adm_offers_page:noop"))
    if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️",callback_data=f"adm_offers_page:{page+1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 رجوع",callback_data="adm_home")])
    await edit_query_message(query, "📦 اختار اللعبة باش تشوف عروضها وتتحكم فيها:",reply_markup=InlineKeyboardMarkup(buttons))


# =========================
# عرض جميع الطلبات للإدارة
# =========================

async def admin_all_orders(query, page=0):
    page=max(0, int(page or 0)); per_page=12
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
            LIMIT ? OFFSET ?
            """,
            (per_page, page * per_page),
        ).fetchall()
        total_orders = int(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0])

    if not orders:
        await edit_query_message(query, 
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

    pages=(total_orders + per_page - 1)//per_page
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"adm_orders:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{max(1,pages)}", callback_data="adm_orders:noop"))
    if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"adm_orders:{page+1}"))
    buttons.append(nav)
    buttons.append([
        InlineKeyboardButton("🔄 تحديث", callback_data=f"adm_orders:{page}"),
        InlineKeyboardButton("🔙 رجوع", callback_data="adm_home"),
    ])

    await edit_query_message(query, 
        f"📋 <b>طلبات المتجر — {total_orders} طلب</b>\n\n"
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
        await edit_query_message(query, "❌ الطلب غير موجود.")
        return

    text = (
        f"🧾 <b>تفاصيل الطلب #{order['id']}</b>\n\n"
        f"👤 المستخدم: <code>{order['user_id']}</code>\n"
        f"🎮 اللعبة: {order['game_name'] or 'غير موجودة'}\n"
        f"📦 العرض: {order['offer_name'] or 'غير موجود'}\n"
        f"🆔 معرّف اللاعب: {order['player_id'] or 'غير محدد'}\n"
        f"💳 طريقة الدفع: {order['payment_method'] or 'غير محددة'}\n"
        f"💰 السعر: {format_order_amount(order['price'], order['currency'])}\n"
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

    await edit_query_message(query, 
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
        await edit_query_message(query, "❌ الزبون غير موجود.")
        return
    lines = [f"👤 <b>{user['full_name'] or user['username'] or target_id}</b>", f"🆔 ID: <code>{target_id}</code>", f"🏷️ نوع الحساب: {'تاجر' if user['account_type']=='trader' else 'زبون عادي'}", f"🧾 عدد الطلبات: {totals['n']}", f"💰 مجموع الطلبات غير المرفوضة: {totals['all_total']} DA", f"✅ مجموع المكتمل: {totals['completed_total']} DA", f"⏳ مجموع المعلّق/قيد التنفيذ: {totals['active_total']} DA"]
    lines.append("\n<b>آخر الطلبات:</b>")
    for order in orders:
        lines.append(f"\n🧾 #{order['id']} — {order['game_name'] or 'خدمة محذوفة'} / {order['offer_name'] or 'عرض محذوف'}\n💰 {format_order_amount(order['price'], order['currency'])} | {status_label(order['status'])}\n💳 {order['payment_method'] or 'غير محدد'} | {order['created_at'] or ''}")
    await edit_query_message(query, "\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 قائمة الزبائن", callback_data="adm_customers")]]))


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
        await edit_query_message(query, 
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
    await edit_query_message(query, "\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_stats")]]))


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

    await edit_query_message(query, 
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
    sell_rate = get_setting("usd_sell_rate", get_setting("usd_exchange_rate", "254"))
    buy_rate = get_setting("usd_buy_rate", get_setting("usd_exchange_rate", "254"))
    usd_on = get_setting("usd_payments_enabled", "0") == "1"
    text = (
        "💳 <b>إعدادات الدفع</b>\n\n"
        f"🏦 <b>BaridiMob / CCP:</b>\n{html.escape(baridi)}\n\n"
        f"📱 <b>Flexy:</b>\n{html.escape(flexy)}\n\n"
        f"💵 سعر بيع الدولار: 1 USD = {html.escape(str(sell_rate))} DA (يضرب في)\n"
        f"💱 سعر شراء الدولار: 1 USD = {html.escape(str(buy_rate))} DA (يقسم على)\n"
        f"حالة الطرق الأساسية:\n🏦 BaridiMob / CCP: {'مفعّل ✅' if get_setting('payment_baridi_enabled', '1') == '1' else 'مخفي ❌'}\n"
        f"📱 Flexy: {'مفعّل ✅' if get_setting('payment_flexy_enabled', '1') == '1' else 'مخفي ❌'}\n\n"
        f"🌐 <b>طرق الدفع بالدولار ككل:</b> {'مفعّلة ✅' if usd_on else 'مخفية ❌'}\n"
        "زر واحد يتحكم في ظهور/إخفاء جميع طرق الدفع بالدولار عند الزبائن.\n\n"
        "طرق الدفع الرقمية (تعديل التعليمات لكل طريقة فقط):"
    )
    buttons = [
        [InlineKeyboardButton("🏦 تعديل BaridiMob / CCP", callback_data="pay_settings:baridi")],
        [InlineKeyboardButton("📱 تعديل Flexy", callback_data="pay_settings:flexy")],
        [InlineKeyboardButton(f"{'🙈 إخفاء' if get_setting('payment_baridi_enabled','1')=='1' else '👁️ إظهار'} BaridiMob / CCP", callback_data="pay_toggle:baridi")],
        [InlineKeyboardButton(f"{'🙈 إخفاء' if get_setting('payment_flexy_enabled','1')=='1' else '👁️ إظهار'} Flexy", callback_data="pay_toggle:flexy")],
        [InlineKeyboardButton("💵 تعديل سعر بيع الدولار (يضرب في)", callback_data="pay_usd_sell_rate")],
        [InlineKeyboardButton("💱 تعديل سعر شراء الدولار (يقسم على)", callback_data="pay_usd_buy_rate")],
        [InlineKeyboardButton(f"{'🙈 إخفاء كل طرق الدولار' if usd_on else '👁️ إظهار كل طرق الدولار'}", callback_data="usd_pay_toggle_all")],
        [InlineKeyboardButton("➕ إضافة طريقة دفع جديدة", callback_data="custom_pay_add")],
    ]
    with db() as conn:
        methods = conn.execute("SELECT * FROM custom_payment_methods ORDER BY id").fetchall()
    for method in methods:
        currency = (method["currency"] or "USD").upper()
        state = "مفعّلة ضمن المجموعة ✅" if currency == "USD" and usd_on else ("مخفية ضمن المجموعة ❌" if currency == "USD" else ("مفعّلة ✅" if int(method["enabled"] or 0) else "مخفية ❌"))
        buttons.append([InlineKeyboardButton(
            f"{method['emoji']} {method['name']} ({currency}) — {state}",
            callback_data=f"custom_pay_info:{method['id']}"
        ), InlineKeyboardButton("✏️ تعليمات", callback_data=f"custom_pay_edit:{method['id']}")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
    await edit_query_message(query, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def show_pending_deposits(target, page=0, edit=False):
    """Admin-only paginated queue of pending wallet deposit requests."""
    if isinstance(page, str):
        try: page = int(page)
        except ValueError: page = 0
    page = max(0, page)
    per_page = 8
    with db() as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM wallet_deposits WHERE status='pending'").fetchone()[0])
        rows = conn.execute("""SELECT d.id,d.user_id,d.amount,d.amount_usd,d.currency,d.payment_method,d.created_at,
                                    u.full_name,u.username
                             FROM wallet_deposits d LEFT JOIN users u ON u.user_id=d.user_id
                             WHERE d.status='pending' ORDER BY d.id DESC LIMIT ? OFFSET ?""",
                            (per_page, page * per_page)).fetchall()
    if total == 0:
        text = "💰 لا توجد طلبات تعبئة رصيد معلّقة حاليًا."
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تحديث", callback_data="deposit_queue:0")], [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")]])
    else:
        pages = (total + per_page - 1) // per_page
        if page >= pages:
            page = pages - 1
            return await show_pending_deposits(target, page, edit=edit)
        buttons = []
        for r in rows:
            curr = (r["currency"] or "DA").upper()
            amount = f"{float(r['amount_usd'] or 0):g} USD" if curr == "USD" else f"{int(r['amount'] or 0)} DA"
            name = r["full_name"] or ("@" + r["username"] if r["username"] else str(r["user_id"]))
            buttons.append([InlineKeyboardButton(f"#{r['id']} | {name[:18]} | {amount}", callback_data=f"deposit_open:{r['id']}:{page}")])
        nav=[]
        if page > 0: nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"deposit_queue:{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="deposit_queue:noop"))
        if page + 1 < pages: nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"deposit_queue:{page+1}"))
        buttons.append(nav)
        buttons.append([InlineKeyboardButton("🔄 تحديث", callback_data=f"deposit_queue:{page}"), InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")])
        text = f"💰 طلبات تعبئة الرصيد المعلّقة\nعدد الطلبات: {total}\nاختر طلبًا لمراجعة الوصل واتخاذ القرار."
        markup = InlineKeyboardMarkup(buttons)
    if edit:
        try: await target.edit_text(text, reply_markup=markup)
        except Exception: await target.message.reply_text(text, reply_markup=markup)
    else:
        await target.reply_text(text, reply_markup=markup)


# =========================
# معالجة أزرار لوحة التحكم
# =========================

async def edit_query_message(query, text, **kwargs):
    """Edit callback source safely whether it is text or a media/GIF message."""
    # Acknowledge callbacks even on branches that only edit/reply and otherwise
    # leave Telegram's loading spinner running.
    try:
        await query.answer()
    except Exception:
        pass
    message = getattr(query, "message", None)
    has_media = bool(message and (
        getattr(message, "animation", None)
        or getattr(message, "photo", None)
        or getattr(message, "video", None)
        or getattr(message, "document", None)
        or getattr(message, "audio", None)
        or getattr(message, "voice", None)
    ))
    if has_media:
        try:
            return await query.edit_message_caption(caption=text, **kwargs)
        except Exception:
            # Captions are limited to 1024 chars; long pages must become text messages.
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            return await query.message.reply_text(text, **kwargs)
    try:
        return await query.edit_message_text(text=text, **kwargs)
    except Exception as exc:
        # If Telegram refuses an edit (e.g. old/deleted message), send a fresh reply.
        if "Message is not modified" in str(exc):
            return None
        return await query.message.reply_text(text, **kwargs)


async def callback_handler(update, context):
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id
    # Default for ordinary section/navigation callbacks; set True only when
    # a group/admin terminal order action is normalized to status:... below.
    group_order_terminal_action = False

    if data == "contact:start":
        await query.answer()
        with db() as conn:
            conn.execute(
                "INSERT INTO customer_chats (user_id, is_open, updated_at) VALUES (?, 1, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET is_open=1, updated_at=excluded.updated_at",
                (user_id, now_text()),
            )
        await edit_query_message(
            query,
            "💬 تواصل مع إدارة SERADJ STORE\n\nاكتب رسالتك هنا وسيتم تحويلها للإدارة. يمكنك إرسال نص أو صورة أو وصل دفع.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة", callback_data="home:main")]]),
        )
        return

    if data == "language_menu":
        await query.answer()
        await edit_query_message(query, tr(user_id, "choose_language"), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇩🇿 العربية", callback_data="language_set:ar")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="language_set:en")],
            [InlineKeyboardButton(tr(user_id, "back"), callback_data="home:main")],
        ]))
        return
    if data.startswith("language_set:"):
        lang = data.split(":", 1)[1]
        if lang not in LANGUAGE_TEXTS:
            await query.answer("Unsupported language", show_alert=True)
            return
        with db() as conn:
            conn.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        await query.answer(LANGUAGE_TEXTS[lang]["language_saved"])
        await edit_query_message(query, LANGUAGE_TEXTS[lang]["welcome"].format(store=STORE_NAME), reply_markup=customer_inline_menu(user_id))
        return

    # Main customer navigation: edit the current menu message instead of
    # sending a fresh navigation window on every tap (for customers/traders/admin).
    if data.startswith("home:"):
        action = data.split(":", 1)[1]
        context.user_data["navigation_message_id"] = query.message.message_id
        await query.answer()
        if action == "admin":
            if not is_admin(user_id):
                await query.answer("هذا القسم خاص بالإدارة.", show_alert=True)
                return
            await edit_query_message(query, "👑 لوحة تحكم SERADJ STORE")
            admin_menu_msg = await query.message.reply_text("اختر من لوحة الإدارة:", reply_markup=admin_keyboard())
            context.user_data["reply_keyboard_message_id"] = admin_menu_msg.message_id
            # The edited heading is a transient navigation window; remove it.
            try:
                await query.message.delete()
            except Exception:
                pass
            return
        if action == "store":
            await edit_query_message(query, tr(user_id, "store_choose"), reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(tr(user_id, "games"), callback_data="store_category:game")],
                [InlineKeyboardButton(tr(user_id, "apps"), callback_data="store_category:app")],
                [InlineKeyboardButton(tr(user_id, "back"), callback_data="home:main")],
            ]))
            return
        if action == "main":
            welcome = tr(user_id, "welcome", store=STORE_NAME)
            if user_language(user_id) == "ar":
                welcome = get_setting("welcome_message", welcome)
            await edit_query_message(query, welcome, reply_markup=customer_inline_menu(user_id))
            return
        if action == "benefits":
            await edit_query_message(query, tr(user_id, "benefits_text"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(user_id, "back"), callback_data="home:main")]]))
            return
        if action == "account":
            # Use the same account renderer as the persistent reply-keyboard
            # button, so the personalized GIF is shown from either entry point.
            await show_account(query.message, user_id)
            return
        if action == "request":
            context.user_data["awaiting_game_request"] = True
            await edit_query_message(query, tr(user_id, "request_prompt"))
            return
        if action == "referral":
            if not points_enabled(user_id):
                await edit_query_message(query, tr(user_id, "referral_unavailable"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(user_id, "back"), callback_data="home:main")]])); return
            bot_username = get_setting("bot_username", "").strip()
            if not bot_username:
                try:
                    me = await context.bot.get_me(); bot_username = me.username or ""
                    if bot_username: set_setting("bot_username", bot_username)
                except Exception: bot_username = ""
            row = get_user_row(user_id)
            da = float(row["points_da"] or 0) if row else 0.0
            usd = float(row["points_usd"] or 0) if row else 0.0
            link = f"https://t.me/{bot_username}?start=ref_{user_id}" if bot_username else tr(user_id, "referral_link_unavailable")
            await edit_query_message(query, f"{tr(user_id, 'referral_title')}\n\n{tr(user_id, 'referral_link')}: {link}\n\n{tr(user_id, 'points_da')}: {da:,} | {tr(user_id, 'points_usd')}: {usd:.3f}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(user_id, "back"), callback_data="home:main")]]))
            return
        if action == "orders":
            await edit_query_message(query, tr(user_id, "orders_prompt"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(user_id, "view_orders"), callback_data="account_orders")], [InlineKeyboardButton(tr(user_id, "back"), callback_data="home:main")]]))
            return
        if action == "deposit":
            await edit_query_message(query, tr(user_id, "deposit_choose"), reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(tr(user_id, "deposit_da"), callback_data="deposit_currency:DA")],
                [InlineKeyboardButton(tr(user_id, "deposit_usd"), callback_data="deposit_currency:USD")],
                [InlineKeyboardButton(tr(user_id, "back"), callback_data="home:main")],
            ]))
            return
        if action == "upgrade":
            await edit_query_message(query, 
                tr(user_id, "upgrade_prompt"),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(user_id, "back"), callback_data="home:main")]])
            )
            return

    # Paginated trader history navigation.
    if data == "history:noop":
        await query.answer()
        return
    if data.startswith("history:"):
        try:
            _, target_text, section, page_text = data.split(":", 3)
            target_id, page = int(target_text), int(page_text)
            if section not in ("deals", "wallet") or page < 0:
                raise ValueError
        except ValueError:
            await query.answer("بيانات السجل غير صالحة.", show_alert=True)
            return
        authorized = is_admin(user_id) or user_id == target_id
        if not authorized:
            await query.answer("عرض هذا السجل غير مسموح لك.", show_alert=True)
            return
        await query.answer()
        await _send_trader_history_page(query.message, target_id, section, page, edit=True)
        return

    # Independent trader-group workflow (uses the trader's existing SERADJ wallet).
    if data.startswith(("tgcfg:", "tgcfgpage:", "tgp:", "tga:", "tgc:", "tgr:")) or data == "tgcfgnop":
        handled = await handle_trader_group_callback(query, context, data)
        if handled:
            return

    # Flexy wallet administration and SMS credit allocation.
    if data == "flexy_noop":
        await query.answer("لا يوجد مشترك نشط.", show_alert=True); return
    if data.startswith("flexy_") and not is_admin(user_id) and not data.startswith("flexy_credit:"):
        await query.answer("هذا القسم خاص بالإدارة.", show_alert=True); return
    if data == "flexy_set_percent":
        context.user_data["flexy_admin_step"] = "percent"
        await query.message.reply_text("أرسل نسبة الاقتطاع من 0 إلى 100. مثال: 15\nللإلغاء أرسل /cancel.")
        return
    if data == "flexy_set_channel_help":
        context.user_data["flexy_admin_step"] = "channel"
        await query.message.reply_text("لتعيين القناة: أرسل هنا رسالة مُعاد توجيهها من القناة الخاصة. لازم يكون البوت مشرفًا فيها مع صلاحية نشر الرسائل.\nللإلغاء أرسل /cancel.")
        return
    if data == "flexy_subscribers":
        with db() as conn:
            rows = conn.execute("SELECT slot,user_id,active,balance FROM flexy_subscribers ORDER BY slot").fetchall()
        lines = [f"{r['slot']} — {'🟢 نشط' if r['active'] else '🔴 متوقف'} — ID: {r['user_id'] or 'غير معيّن'} — الرصيد: {r['balance']:g} DA" for r in rows]
        buttons = [[InlineKeyboardButton(f"تعيين/تغيير {i}", callback_data=f"flexy_assign:{i}"), InlineKeyboardButton("✏️ الاسم", callback_data=f"flexy_label:{i}"), InlineKeyboardButton("✏️ الرصيد", callback_data=f"flexy_setbal:{i}"), InlineKeyboardButton("تفعيل/إيقاف", callback_data=f"flexy_toggle:{i}")] for i in range(1,11)]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="flexy_back")])
        await query.message.reply_text("👥 مشتركو الفليكسي\n\n" + ("\n".join(lines) if lines else "لا يوجد مشتركين بعد."), reply_markup=InlineKeyboardMarkup(buttons)); return
    if data.startswith("flexy_label:"):
        try:
            slot = int(data.split(":", 1)[1])
            if not 1 <= slot <= 10:
                raise ValueError
        except Exception:
            await query.answer("رقم المشترك غير صالح.", show_alert=True); return
        context.user_data["flexy_label_slot"] = slot
        await query.message.reply_text(
            f"أرسل اسم المشترك رقم {slot} فقط، دون إيموجي.\nمثال: أحمد محمد\nللإلغاء أرسل /cancel."
        )
        await query.answer()
        return
    if data.startswith("flexy_assign:"):
        slot=int(data.split(":",1)[1]); context.user_data["flexy_assign_slot"]=slot
        await query.message.reply_text(f"أرسل Telegram ID للمشترك رقم {slot}. يمكنه إيجاد ID عبر /myid. أرسل 0 لإلغاء التعيين."); return
    if data.startswith("flexy_setbal:"):
        try:
            slot = int(data.split(":", 1)[1])
            if not 1 <= slot <= 10:
                raise ValueError
        except Exception:
            await query.answer("رقم المشترك غير صالح.", show_alert=True); return
        context.user_data["flexy_set_balance_slot"] = slot
        await query.message.reply_text(
            f"أرسل الرصيد الجديد للمشترك رقم {slot} بالدينار.\n"
            "مثال: 15000 أو 15000.50\n"
            "سيتم استبدال الرصيد الحالي بهذا المبلغ، مع تسجيل التعديل في السجل.\n"
            "للإلغاء أرسل /cancel."
        )
        await query.answer()
        return
    if data.startswith("flexy_toggle:"):
        slot=int(data.split(":",1)[1])
        with db() as conn:
            row=conn.execute("SELECT active FROM flexy_subscribers WHERE slot=?",(slot,)).fetchone()
            if row: conn.execute("UPDATE flexy_subscribers SET active=?,updated_at=? WHERE slot=?",(0 if row['active'] else 1,now_text(),slot))
            else: conn.execute("INSERT INTO flexy_subscribers(slot,active,updated_at) VALUES(?,0,?)",(slot,now_text()))
        await query.answer("تم تحديث حالة المشترك."); await query.message.reply_text("تم تحديث المشترك. افتح إدارة الفليكسي لعرض الحالة الجديدة."); return
    if data == "flexy_balances":
        with db() as conn:
            rows=conn.execute("SELECT slot,user_id,active,balance FROM flexy_subscribers ORDER BY slot").fetchall()
            tx=conn.execute("SELECT slot,kind,amount,balance_after,note,created_at FROM flexy_transactions ORDER BY id DESC LIMIT 20").fetchall()
        lines=[f"{r['slot']} | ID {r['user_id'] or '-'} | {'نشط' if r['active'] else 'متوقف'} | {r['balance']:g} DA" for r in rows]
        lines += ["", "آخر 20 عملية:"] + [f"{r['created_at']} | مشترك {r['slot']} | {r['kind']} {r['amount']:g} | الرصيد {r['balance_after']:g}" for r in tx]
        await query.message.reply_text("\n".join(lines) if lines else "لا توجد بيانات."); return
    if data == "flexy_back":
        await flexy_admin_panel(query.message); return
    if data.startswith("flexy_credit:"):
        try: _, event_id, slot_text=data.split(":",2); event_id=int(event_id); slot=int(slot_text)
        except Exception: await query.answer("طلب غير صالح.",show_alert=True); return
        with db() as conn:
            event=conn.execute("SELECT * FROM flexy_sms_events WHERE id=?",(event_id,)).fetchone()
            sub=conn.execute("SELECT * FROM flexy_subscribers WHERE slot=? AND active=1 AND user_id IS NOT NULL",(slot,)).fetchone()
            if not event or event['status']!='pending' or not sub:
                await query.answer("تمت معالجة التعبئة أو المشترك غير نشط.",show_alert=True); return
            if not is_admin(user_id) and int(sub["user_id"]) != int(user_id):
                await query.answer("هذا الزر مخصص للمشترك صاحب هذا الرقم.", show_alert=True); return
            pct=Decimal(get_setting("flexy_deduction_percent","0"))
            net=(Decimal(str(event['gross_amount']))*(Decimal('100')-pct)/Decimal('100')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
            before=Decimal(str(sub['balance'])); after=before+net
            conn.execute("UPDATE flexy_subscribers SET balance=?,updated_at=? WHERE slot=?",(float(after),now_text(),slot))
            conn.execute("INSERT INTO flexy_transactions(slot,user_id,kind,amount,balance_before,balance_after,note,sms_event_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(slot,sub['user_id'],'تعبئة SMS',float(net),float(before),float(after),f"المبلغ الأصلي {event['gross_amount']:g} DA | اقتطاع {pct}%",event_id,now_text()))
            conn.execute("UPDATE flexy_sms_events SET status='credited',credited_slot=?,net_amount=? WHERE id=? AND status='pending'",(slot,float(net),event_id))
        await query.answer("تمت إضافة الرصيد.")
        # Do not send a private bot notification to the subscriber.
        # Publish the credited amount and resulting balance in the Flexy output channel post.
        await edit_query_message(query, 
            f"✅ تمت إضافة التعبئة إلى محفظة المشترك {slot}\n\n"
            f"💰 المبلغ الأصلي: {event['gross_amount']:g} DA\n"
            f"📉 نسبة الاقتطاع: {pct}%\n"
            f"➕ المضاف للمحفظة: {net:g} DA\n"
            f"💳 الرصيد الجديد: {after:g} DA"
        )
        return

    if data == "check_subscription":
        if not await is_subscribed(context.bot, user_id):
            await query.answer("❌ مازال ما تأكدش اشتراكك. اشترك في القناة ثم أعد المحاولة.", show_alert=True)
            return
        await query.answer("✅ تم التأكد من اشتراكك!")
        welcome_text = get_setting(
            "welcome_message",
            f"🎮 مرحباً بك في {STORE_NAME}!\n\n"
            "🛍️ شحن الألعاب والخدمات الرقمية\n"
            "💳 الدفع عبر BaridiMob / CCP أو Flexy\n\n"
            "اختر الخدمة من القائمة بالأسفل 👇",
        )
        await query.message.reply_text(welcome_text, reply_markup=main_keyboard(user_id))
        return

    # Block all customer navigation while the store is closed.
    # Check before acknowledging the callback so the alert is shown reliably.
    if not is_admin(user_id) and not store_is_open():
        await query.answer(store_closed_notice(), show_alert=True)
        return
    # Defer acknowledgement for work-group order actions: their handlers answer
    # only after validating/updating the order. A second answer makes Telegram
    # raise "query is already answered" and interrupts the workflow.
    group_order_callbacks = ("order_claim:", "order_release:", "order_cancel:", "order_finish:",
                            "order_receipt:", "order_finish_now:", "order_finish_with_receipt:")
    defer_ack = query.message.chat.type in ("group", "supergroup") and data.startswith(group_order_callbacks)
    if not defer_ack and not data.startswith(("coupon_", "cart_coupon_", "offer_coupon_")):
        await query.answer()

    if data.startswith("cart_add:"):
        try:
            parts = data.split(":", 4)
            _, gid, oid, platform = parts[:4]
            price_mode = parts[4] if len(parts) > 4 else "choose"
            await _cart_add(query, context, int(gid), int(oid), platform, price_mode)
        except Exception:
            logger.exception("Cart add failed")
            await query.answer("تعذرت إضافة العرض للسلة.", show_alert=True)
        return
    if data == "cart_view":
        await _cart_view(query, context); return
    if data == "cart_checkout":
        await _cart_checkout(query, context); return
    if data == "cart_clear":
        context.user_data.pop("cart", None)
        await edit_query_message(query, "🧹 تم إفراغ السلة."); return
    if data.startswith(("cart_inc:", "cart_dec:", "cart_del:")):
        cart = context.user_data.get("cart")
        if not cart:
            await edit_query_message(query, "🛒 السلة فارغة."); return
        action, oid_text = data.split(":", 1); oid = int(oid_text)
        item = next((x for x in cart["items"] if int(x["offer_id"]) == oid), None)
        if item:
            if action == "cart_inc": item["quantity"] = min(99, int(item["quantity"]) + 1)
            elif action == "cart_dec": item["quantity"] = int(item["quantity"]) - 1
            else: item["quantity"] = 0
            if item["quantity"] <= 0: cart["items"].remove(item)
        if not cart["items"]: context.user_data.pop("cart", None); await edit_query_message(query, "🛒 السلة فارغة."); return
        await _cart_view(query, context); return
    if data.startswith("cart_pay:"):
        await _cart_start_payment(query, context, data.split(":", 1)[1]); return

    if data == "browse_offers":
        await query.message.reply_text(
            "🛍️ اختر القسم لتصفح العروض:",
            reply_markup=ReplyKeyboardMarkup([["🎮 الألعاب", "📱 التطبيقات"], ["🛍️ المتجر"]], resize_keyboard=True)
        )
        return

    if data.startswith("order_channel_toggle:"):
        if not is_admin(user_id):
            await query.answer("خاص بالإدارة.", show_alert=True)
            return
        enabled = data.split(":", 1)[1] == "1"
        set_setting("order_channel_enabled", "1" if enabled else "0")
        await edit_query_message(query, "✅ تم تفعيل نشر الطلبات في القناة." if enabled else "⏸️ تم إيقاف النشر في القناة.")
        return
    if data == "order_channel_clear:1":
        if not is_admin(user_id):
            await query.answer("خاص بالإدارة.", show_alert=True)
            return
        set_setting("order_channel_id", "")
        set_setting("order_channel_enabled", "0")
        context.user_data.pop("awaiting_order_channel_id", None)
        await edit_query_message(query, "🗑️ تم حذف القناة وإيقاف النشر.")
        return

    # Safe demo orders: no charge, no real fulfillment, clearly labeled as test.
    if data == "test_order_abort":
        await edit_query_message(query, "تم إلغاء الطلب التجريبي.")
        return
    if data.startswith("test_order_game:"):
        try:
            test_game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await edit_query_message(query, "اختيار لعبة غير صالح.")
            return
        if not is_admin(user_id):
            await query.answer("الطلب التجريبي متاح لمالك المتجر فقط.", show_alert=True)
            return
        with db() as conn:
            game = conn.execute("SELECT id,name FROM games WHERE id=? AND active=1", (test_game_id,)).fetchone()
            if not game:
                await edit_query_message(query, "اللعبة غير موجودة أو غير مفعّلة.")
                return
            cur = conn.execute("INSERT INTO orders (user_id, game_id, offer_id, player_id, payment_method, price, status, created_at, points_awarded, points_used, platform, credit_charged, credit_refunded) VALUES (?, ?, NULL, ?, ?, 0, 'pending', ?, 0, 0, '', 0, 0)", (user_id, test_game_id, '[طلب تجريبي - لا يوجد شحن حقيقي]', 'طلب تجريبي (بدون دفع)', now_text()))
            test_order_id = cur.lastrowid
        demo_user = query.from_user
        draft = {"game_id": test_game_id, "game_name": game["name"], "offer_name": "طلب تجريبي", "platform": "تجريبي"}
        await dispatch_order_to_group(context, test_order_id, demo_user, draft, "طلب تجريبي - لا تشحن", "طلب تجريبي (بدون دفع)", 0, 0)
        await edit_query_message(query, f"🧪 تم إنشاء الطلب التجريبي #{test_order_id} للعبة {game['name']}، بلا خصم رصيد وبلا شحن حقيقي.")
        return

    # Receipt is optional in private admin chat. In work groups, the claimant
    # completes the order directly; normalize it to the shared status processor.
    if data.startswith("order_finish:"):
        try:
            finish_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("رقم الطلب غير صالح.", show_alert=True)
            return
        if query.message.chat.type == "private":
            if not is_admin(user_id):
                await query.answer("هذا الإجراء خاص بمالك المتجر.", show_alert=True)
                return
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📷 إرفاق وصل الشحن", callback_data=f"order_receipt:{finish_id}")],
                [InlineKeyboardButton("📝 إتمام برسالة نصية", callback_data=f"order_finish_text:{finish_id}")],
                [InlineKeyboardButton("⏭️ إتمام بدون صورة", callback_data=f"order_finish_now:{finish_id}")],
                [InlineKeyboardButton("↩️ رجوع", callback_data=f"order_finish_back:{finish_id}")],
            ]))
            return
        if query.message.chat.type not in ("group", "supergroup"):
            await query.answer("هذا الإجراء متاح من قروب العمل فقط.", show_alert=True)
            return
        with db() as conn:
            claimed = conn.execute("SELECT claimed_by, status FROM orders WHERE id=?", (finish_id,)).fetchone()
        if not claimed:
            await query.answer("الطلب غير موجود.", show_alert=True)
            return
        if claimed["status"] in ("completed", "rejected"):
            await query.answer("تمت معالجة الطلب مسبقًا.", show_alert=True)
            return
        is_claimant = int(claimed["claimed_by"] or 0) == user_id
        if not is_claimant:
            # مساعد المجموعة يستطيع فتح خيار إرفاق الوصل فقط؛ لا يستطيع الإتمام دون وصل.
            await query.answer("يمكنك إرسال وصل الشحن كمساعد. الإتمام بدون وصل متاح لمستلم الطلب فقط.")
            await query.message.reply_text(
                f"📷 إذا كنت تساعد في شحن الطلب #{finish_id}، اضغط زر إرسال الوصل الموجود أسفل الطلب الأصلي."
            )
            return
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📷 إرفاق وصل الشحن", callback_data=f"order_receipt:{finish_id}")],
            [InlineKeyboardButton("📝 إتمام برسالة نصية", callback_data=f"order_finish_text:{finish_id}")],
            [InlineKeyboardButton("⏭️ إتمام بدون صورة", callback_data=f"order_finish_now:{finish_id}")],
            [InlineKeyboardButton("🔄 تنازل عن الطلب", callback_data=f"order_release:{finish_id}")],
        ]))
        await query.answer("اختر إرفاق الوصل أو إتمام الطلب بدون صورة.")
        return

    if data.startswith("order_finish_text:"):
        try:
            text_order_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("رقم الطلب غير صالح.", show_alert=True); return
        if query.message.chat.type not in ("group", "supergroup", "private"):
            await query.answer("هذا الإجراء غير متاح هنا.", show_alert=True); return
        if query.message.chat.type == "private" and not is_admin(user_id):
            await query.answer("للإدارة فقط.", show_alert=True); return
        with db() as conn:
            row = conn.execute("SELECT claimed_by,status FROM orders WHERE id=?", (text_order_id,)).fetchone()
        if not row or row["status"] in ("completed", "rejected"):
            await query.answer("الطلب غير متاح أو تمت معالجته.", show_alert=True); return
        if query.message.chat.type in ("group", "supergroup") and int(row["claimed_by"] or 0) != user_id:
            await query.answer("إتمام الطلب برسالة متاح لمستلم الطلب فقط.", show_alert=True); return
        context.user_data["awaiting_order_completion_text"] = text_order_id
        context.user_data["order_completion_chat_id"] = query.message.chat_id
        await query.message.reply_text(f"📝 اكتب الرسالة التي تريد إرسالها للزبون بخصوص الطلب #{text_order_id}. أرسل /cancel لإلغاء الخطوة.", reply_markup=ForceReply(selective=True, input_field_placeholder="اكتب رسالة إتمام الطلب"))
        await query.answer("بانتظار نص الرسالة.")
        return

    if data.startswith("order_receipt:"):
        try:
            receipt_order_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("رقم الطلب غير صالح.", show_alert=True); return
        chat_type = query.message.chat.type
        if chat_type == "private":
            if not is_admin(user_id):
                await query.answer("هذا الإجراء خاص بالإدارة.", show_alert=True); return
        elif chat_type in ("group", "supergroup"):
            with db() as conn:
                claimed = conn.execute("SELECT claimed_by,status FROM orders WHERE id=?", (receipt_order_id,)).fetchone()
            if not claimed or not int(claimed["claimed_by"] or 0) or claimed["status"] in ("completed", "rejected"):
                await query.answer("لازم يكون الطلب مستلمًا من أحد أعضاء المجموعة قبل إرفاق الوصل.", show_alert=True); return
            context.user_data["order_receipt_group_id"] = query.message.chat_id
        else:
            await query.answer("هذا الإجراء غير متاح هنا.", show_alert=True); return
        context.user_data["awaiting_order_receipt"] = receipt_order_id
        await query.message.reply_text(
            f"📷 ابعث صورة وصل الشحن للطلب #{receipt_order_id} كردّ مباشر على هذه الرسالة حتى يستقبلها البوت داخل المجموعة.\nللإلغاء أرسل /cancel_receipt.",
            reply_markup=ForceReply(selective=True, input_field_placeholder="ردّ بصورة وصل الشحن")
        )
        if chat_type in ("group", "supergroup"):
            await query.answer("بانتظار صورة الوصل.")
        return

    if data.startswith("order_finish_back:"):
        try:
            context.user_data.pop(f"order_receipt_photo:{int(data.split(':',1)[1])}", None)
        except (ValueError, IndexError):
            pass
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 مراجعة الطلب", callback_data=f"order_review:{data.split(':',1)[1]}")],
            [InlineKeyboardButton("✅ إتمام الطلب", callback_data=f"order_finish:{data.split(':',1)[1]}")],
            [InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"order_cancel:{data.split(':',1)[1]}")],
        ]))
        return

    if data.startswith("order_finish_now:") or data.startswith("order_finish_with_receipt:"):
        finish_id = int(data.split(":", 1)[1])
        if query.message.chat.type == "private":
            if not is_admin(user_id):
                await query.answer("هذا الإجراء خاص بمالك المتجر.", show_alert=True); return
        elif query.message.chat.type in ("group", "supergroup"):
            with db() as conn:
                claimed = conn.execute("SELECT claimed_by,status,shipping_receipt_file_id,shipping_receipt_file_ids FROM orders WHERE id=?", (finish_id,)).fetchone()
            if not claimed or not int(claimed["claimed_by"] or 0) or claimed["status"] in ("completed", "rejected"):
                await query.answer("الطلب غير مستلم أو تمت معالجته.", show_alert=True); return
            if data.startswith("order_finish_now:") and int(claimed["claimed_by"] or 0) != user_id:
                await query.answer("إتمام الطلب بدون وصل متاح فقط للعضو الذي استلمه.", show_alert=True); return
            if data.startswith("order_finish_with_receipt:") and not (claimed["shipping_receipt_file_id"] or claimed["shipping_receipt_file_ids"] not in (None, "", "[]") or context.user_data.get(f"order_receipt_photo:{finish_id}") or context.user_data.get(f"order_receipt_photos:{finish_id}")):
                await query.answer("أرسل صورة الوصل أولاً من زر إرسال وصل الشحن.", show_alert=True); return
        else:
            await query.answer("هذا الإجراء غير متاح هنا.", show_alert=True); return
        group_order_terminal_action = True
        data = f"status:{finish_id}:completed"
    elif not group_order_terminal_action:
        group_order_terminal_action = False

    # Normalize group-order cancellation before entering the main callback routing chain.
    if data.startswith("order_cancel:"):
        is_cancel = data.startswith("order_cancel:")
        try:
            action_order_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("طلب غير صالح.", show_alert=True)
            return
        is_private = query.message.chat.type == "private"
        if is_private and not is_admin(user_id):
            await query.answer("هذا الإجراء خاص بمالك المتجر.", show_alert=True)
            return
        if not is_private and query.message.chat.type not in ("group", "supergroup"):
            await query.answer("هذا الإجراء متاح من الخاص أو قروب العمل.", show_alert=True)
            return
        with db() as conn:
            claimed_row = conn.execute("SELECT claimed_by, status FROM orders WHERE id=?", (action_order_id,)).fetchone()
            if not claimed_row:
                await query.answer("الطلب غير موجود.", show_alert=True)
                return
            if not is_private and int(claimed_row["claimed_by"] or 0) != user_id:
                await query.answer("فقط العضو الذي استلم الطلب يمكنه تنفيذ هذا الإجراء.", show_alert=True)
                return
            if claimed_row["status"] in ("completed", "rejected"):
                await query.answer("تمت معالجة الطلب مسبقًا.", show_alert=True)
                return
        group_order_terminal_action = True
        # Route through the existing status processor, preserving the callback message
        # and explicit group-action flag for the final group-message update.
        data = f"status:{action_order_id}:{'rejected' if is_cancel else 'completed'}"

    if data.startswith("order_review:"):
        try:
            review_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("رقم الطلب غير صالح.", show_alert=True)
            return
        if query.message.chat.type != "private" or not is_admin(user_id):
            await query.answer("مراجعة الطلب من الخاص متاحة لمالك المتجر فقط.", show_alert=True)
            return
        with db() as conn:
            review = conn.execute(
                """SELECT o.id, o.user_id, o.player_id, o.payment_method, o.price, o.status,
                          o.points_used, o.platform, g.name AS game_name, f.name AS offer_name
                   FROM orders o LEFT JOIN games g ON g.id=o.game_id
                   LEFT JOIN offers f ON f.id=o.offer_id WHERE o.id=?""",
                (review_id,),
            ).fetchone()
            # Opening the review action is the admin's confirmation that the order
            # has entered review. Notify the customer only on the first transition.
            notify_review_customer = bool(review and review["status"] == "pending")
            if notify_review_customer:
                conn.execute("UPDATE orders SET status='processing' WHERE id=? AND status='pending'", (review_id,))
        if not review:
            await query.answer("الطلب غير موجود.", show_alert=True)
            return
        if notify_review_customer:
            try:
                await context.bot.send_message(
                    chat_id=review["user_id"],
                    text=(f"👀 تم استلام طلبك #{review_id} من إدارة SERADJ STORE، "
                          "وهو الآن قيد المراجعة والتحقق.\n\n"
                          "سنرسل لك إشعاراً فور بدء التنفيذ أو عند اكتمال الطلب. ❤️"),
                )
            except Exception:
                logger.exception("تعذر إرسال إشعار مراجعة الطلب للزبون (order=%s, user=%s)", review_id, review["user_id"])
        status_names = {"pending": "قيد الانتظار", "processing": "قيد التنفيذ", "completed": "مكتمل", "rejected": "ملغي"}
        player_info = str(review["player_id"] or "لا يتطلب")
        if player_info.startswith("LOGIN EMAIL:"):
            player_info = "شحن بالحساب (بيانات الدخول مخفية في المراجعة)"
        text_review = (
            f"🔎 مراجعة الطلب #{review_id}\n\n"
            f"👤 الزبون: {review['user_id']}\n"
            f"🎮 اللعبة: {review['game_name'] or 'غير محددة'}\n"
            f"📦 العرض: {review['offer_name'] or 'غير محدد'}\n"
            f"📋 معلومات الشحن: {player_info}\n"
            f"📱 الجهاز: {review['platform'] or 'غير محدد'}\n"
            f"💰 السعر: {int(review['price'] or 0)} DA\n"
            f"💳 الدفع: {review['payment_method'] or 'غير محدد'}\n"
            f"🎁 النقاط المستخدمة: {int(review['points_used'] or 0)}\n"
            f"📌 الحالة: {status_names.get(review['status'], review['status'])}"
        )
        await query.message.reply_text(text_review)
        await query.answer("تم عرض تفاصيل الطلب.")
        return

    if data.startswith("order_release:"):
        try:
            release_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("طلب غير صالح.", show_alert=True); return
        with db() as conn:
            r = conn.execute("SELECT claimed_by,status FROM orders WHERE id=?", (release_id,)).fetchone()
            if not r or int(r["claimed_by"] or 0) != user_id:
                await query.answer("فقط مستلم الطلب يمكنه التنازل عنه.", show_alert=True); return
            if r["status"] in ("completed", "rejected"):
                await query.answer("الطلب مغلق بالفعل.", show_alert=True); return
            conn.execute("UPDATE orders SET claimed_by=NULL, claimed_name=NULL, status='pending' WHERE id=?", (release_id,))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📥 استلام الطلب", callback_data=f"order_claim:{release_id}")]])
        try:
            await query.edit_message_reply_markup(reply_markup=kb)
            await query.message.reply_text(f"🔄 تم التنازل عن الطلب #{release_id} وأصبح متاحًا للاستلام من عضو آخر.")
        except Exception: pass
        await query.answer("تم التنازل عن الطلب.")
        return

    if data.startswith("order_detach:"):
        if not is_admin(user_id):
            await query.answer("هذا الزر خاص بمالك المتجر.", show_alert=True); return
        detach_value = data.split(":", 1)[1]
        if detach_value == "all":
            with db() as conn:
                conn.execute("DELETE FROM settings WHERE key='order_group_all'")
            await query.answer("تم إلغاء ربط القروب بجميع الطلبات.", show_alert=True)
            try: await query.message.reply_text("🔌 تم فصل القروب عن جميع الطلبات الجديدة؛ تعود الإعدادات الخاصة بكل لعبة للعمل.")
            except Exception: pass
            return
        try:
            detach_game_id = int(detach_value)
        except (ValueError, IndexError):
            await query.answer("اللعبة غير صالحة.", show_alert=True); return
        with db() as conn:
            game = conn.execute("SELECT name FROM games WHERE id=?", (detach_game_id,)).fetchone()
            conn.execute("DELETE FROM settings WHERE key=?", (f"order_group_{detach_game_id}",))
        await query.answer("تم عزل المجموعة عن الطلبات الجديدة لهذه اللعبة.", show_alert=True)
        try: await query.message.reply_text(f"🔌 تم فصل استقبال الطلبات الجديدة للعبة {game['name'] if game else detach_game_id} عن هذه المجموعة.")
        except Exception: pass
        return

    if data.startswith("bulk_price_game:"):
        if not is_admin(user_id):
            await query.answer("هذه الخاصية للإدارة فقط.", show_alert=True)
            return
        try:
            game_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("اللعبة غير صالحة.", show_alert=True)
            return
        with db() as conn:
            game = conn.execute("SELECT name FROM games WHERE id=?", (game_id,)).fetchone()
            offers = conn.execute("SELECT name FROM offers WHERE game_id=? ORDER BY CASE WHEN COALESCE(sort_order,0)>0 THEN sort_order ELSE 1000000+id END,id", (game_id,)).fetchall()
        if not game or not offers:
            await edit_query_message(query, "لا توجد عروض لهذه اللعبة حتى الآن.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"offers_game:{game_id}")]]))
            return
        context.user_data["admin_step"] = "bulk_game_prices"
        context.user_data["bulk_price_game_id"] = game_id
        names = "\n".join(f"• {r['name']}" for r in offers)
        await edit_query_message(query, 
            f"📝 تحديث أسعار {game['name']} دفعة واحدة\n\n"
            "أرسل كل عرض في سطر بهذا الترتيب:\n"
            "اسم العرض | زبون DA | تاجر DA | زبون USD | تاجر USD\n\n"
            "مثال: 100 Diamonds | 240 | 220 | 0 | 0\n"
            "إذا كان السعر بالدينار، ضع 0 في الدولار ليُحسب تلقائياً بسعر شراء الدولار.\n"
            "إذا كان السعر بالدولار، ضع 0 في الدينار ليُحسب تلقائياً بسعر بيع الدولار.\n"
            "لكل فئة (زبون/تاجر) أدخل عملة واحدة فقط، والثانية 0.\n"
            "سعر Flexy يُحسب تلقائياً (+18%).\n\n"
            f"العروض المسجلة حالياً:\n{names}\n\nأرسل /cancel للإلغاء."
        )
        return

    if data == "price_menu_offers":
        if not is_admin(user_id):
            await edit_query_message(query, "⛔ هذه الخاصية للإدارة فقط.")
            return
        await edit_query_message(query, 
            "💰 اختار اللعبة التي تريد تعديل عروضها:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("اختيار اللعبة", callback_data="adm_offers")], [InlineKeyboardButton("🔙 تعديل الأسعار", callback_data="price_menu_back")]])
        )
        return
    if data == "price_menu_tiktok":
        if not is_admin(user_id):
            await edit_query_message(query, "⛔ هذه الخاصية للإدارة فقط.")
            return
        values = {
            "retail_baridi": get_setting("tiktok_coin_price_retail_baridi", get_setting("tiktok_coin_price", "غير محدد")) or "غير محدد",
            "retail_flexy": get_setting("tiktok_coin_price_retail_flexy", "غير محدد") or "غير محدد",
            "trader_baridi": get_setting("tiktok_coin_price_trader_baridi", "غير محدد") or "غير محدد",
            "trader_flexy": get_setting("tiktok_coin_price_trader_flexy", "غير محدد") or "غير محدد",
        }
        await edit_query_message(query, 
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
            await edit_query_message(query, "⛔ هذه الخاصية للإدارة فقط.")
            return
        current_min, current_max = tiktok_quantity_limits()
        context.user_data["admin_step"] = "tiktok_min_quantity"
        context.user_data.pop("pending_tiktok_min_quantity", None)
        await edit_query_message(query, 
            f"📏 حدود كمية TikTok الحالية:\nالحد الأدنى: {current_min:,} كوينز\nالحد الأقصى: {current_max:,} كوينز\n\nأرسل الحد الأدنى الجديد كعدد صحيح. بعدها سيطلب منك البوت الحد الأقصى.\nللإلغاء أرسل /cancel."
        )
        return
    if data == "price_menu_back":
        if not is_admin(user_id):
            await edit_query_message(query, "⛔ هذه الخاصية للإدارة فقط.")
            return
        await edit_query_message(query, 
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
            await edit_query_message(query, "⛔ هذه الخاصية للإدارة فقط.")
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
        await edit_query_message(query, 
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
        await show_store(query.message, user_id, category, context=context, query=query)
        await query.answer()
        return

    if data == "contact_unset":
        await query.answer("اطلب من الإدارة ضبط روابط التواصل.", show_alert=True)
        return

    if data.startswith(("coupon_", "cart_coupon_", "offer_coupon_")):
        await query.answer("❌ تم إلغاء نظام قسائم التخفيض.", show_alert=True)
        return

    if data.startswith("points_convert:"):
        if not points_enabled(user_id):
            await query.answer("النقاط متاحة لجميع المشترين.", show_alert=True); return
        ccy = data.split(":", 1)[1].upper()
        if ccy not in ("DA", "USD"):
            await query.answer("نوع نقاط غير صالح.", show_alert=True); return
        column = "points_da" if ccy == "DA" else "points_usd"
        wallet = "balance" if ccy == "DA" else "balance_usd"
        points_rate = 200 if is_trader(user_id) else 100
        with db() as conn:
            row = conn.execute(f"SELECT {column} AS pts FROM users WHERE user_id=?", (user_id,)).fetchone()
            available = float(row["pts"] or 0) if row else 0.0
            whole = int(available // points_rate)
            if whole < 1:
                await query.answer(f"تحتاج إلى {points_rate} نقطة على الأقل للتحويل.", show_alert=True); return
            redeem_points = whole * points_rate
            credit = whole if ccy == "DA" else round(whole, 2)
            conn.execute(f"UPDATE users SET {column}=COALESCE({column},0)-?, {wallet}=COALESCE({wallet},0)+? WHERE user_id=?", (redeem_points, credit, user_id))
        await query.answer("تم تحويل النقاط إلى محفظتك بنجاح.", show_alert=True)
        await query.message.reply_text(f"✅ تم تحويل {redeem_points} نقطة {ccy} إلى {credit:g} {ccy} في محفظتك.")
        await show_points_shop(query.message, user_id)
        return

    if data == "points_shop":
        await show_points_shop(query.message, user_id)
        return
    if data.startswith(("points_buy:", "point_redeem_done:", "point_redeem_reject:")):
        await query.answer("❌ متجر استبدال النقاط القديم متوقف. يمكنك تحويل نقاطك إلى المحفظة من صفحة نقاطي.", show_alert=True)
        return
    if data.startswith("game_request_view:"):
        if not is_admin(user_id):
            await query.answer("⛔ غير مسموح لك.", show_alert=True); return
        try:
            req_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("رقم الطلب غير صالح.", show_alert=True); return
        with db() as conn:
            row = conn.execute("SELECT gr.*, u.username, u.full_name, u.phone_number, u.created_at AS user_created_at FROM game_requests gr LEFT JOIN users u ON u.user_id=gr.user_id WHERE gr.id=?", (req_id,)).fetchone()
        if not row:
            await query.answer("الطلب غير موجود.", show_alert=True); return
        username = ("@" + row["username"].lstrip("@")) if row["username"] else "غير متوفر"
        phone = row["phone_number"] or "غير مسجل"
        name = row["full_name"] or "غير متوفر"
        status_names = {"pending":"قيد الانتظار", "reviewed":"قيد المراجعة", "added":"تمت الإضافة", "rejected":"مرفوض"}
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👀 قيد المراجعة", callback_data=f"game_request_status:{req_id}:reviewed"), InlineKeyboardButton("✅ تمت الإضافة", callback_data=f"game_request_status:{req_id}:added")],
            [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"game_request_status:{req_id}:rejected")],
            [InlineKeyboardButton("🔄 تحديث القائمة", callback_data="game_requests_list")],
        ])
        text_out = (f"📬 تفاصيل طلب اللعبة/التطبيق #{req_id}\n\n"
                    f"🎮 الطلب: {row['request_text']}\n"
                    f"👤 اسم المشترك: {name}\n"
                    f"🔗 اسم المستخدم: {username}\n"
                    f"🆔 Telegram ID: {row['user_id']}\n"
                    f"📱 رقم الهاتف: {phone}\n"
                    f"📅 تاريخ الطلب: {row['created_at'] or 'غير متوفر'}\n"
                    f"📅 تاريخ التسجيل: {row['user_created_at'] or 'غير متوفر'}\n"
                    f"📌 الحالة: {status_names.get(row['status'], row['status'])}")
        await edit_query_message(query, text_out, reply_markup=keyboard)
        return

    if data.startswith("game_requests_list"):
        if not is_admin(user_id):
            await query.answer("⛔ غير مسموح لك.", show_alert=True); return
        if data.endswith(":noop"):
            return
        try: page = int(data.split(":",1)[1]) if ":" in data else 0
        except ValueError: page = 0
        page=max(0,page); per_page=8
        with db() as conn:
            total=int(conn.execute("SELECT COUNT(*) FROM game_requests").fetchone()[0])
            rows = conn.execute("SELECT * FROM game_requests ORDER BY id DESC LIMIT ? OFFSET ?", (per_page,page*per_page)).fetchall()
        if not rows:
            await edit_query_message(query, "📬 لا توجد طلبات ألعاب أو تطبيقات."); return
        pages=(total+per_page-1)//per_page
        buttons = [[InlineKeyboardButton(f"#{r['id']} {r['request_text'][:32]} ({r['status']})", callback_data=f"game_request_view:{r['id']}")] for r in rows]
        nav=[]
        if page>0: nav.append(InlineKeyboardButton("⬅️ السابق",callback_data=f"game_requests_list:{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{pages}",callback_data="game_requests_list:noop"))
        if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️",callback_data=f"game_requests_list:{page+1}"))
        buttons.append(nav); buttons.append([InlineKeyboardButton("🔙 لوحة الإدارة",callback_data="adm_home")])
        await edit_query_message(query, f"📬 اختر طلبًا لعرض التفاصيل — {total} طلب:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("game_request_status:"):
        if not is_admin(user_id):
            await query.answer("⛔ غير مسموح لك.", show_alert=True); return
        try:
            _, req_id, status = data.split(":", 2); req_id = int(req_id)
        except (ValueError, IndexError):
            await query.answer("بيانات الطلب غير صالحة.", show_alert=True); return
        if status not in ("reviewed", "added", "rejected"):
            await query.answer("حالة غير صالحة.", show_alert=True); return
        with db() as conn:
            req = conn.execute("SELECT gr.*, u.username, u.full_name, u.phone_number, u.created_at AS user_created_at FROM game_requests gr LEFT JOIN users u ON u.user_id=gr.user_id WHERE gr.id=?", (req_id,)).fetchone()
            if not req:
                await query.answer("الطلب غير موجود.", show_alert=True); return
            conn.execute("UPDATE game_requests SET status=? WHERE id=?", (status, req_id))
        status_names = {"reviewed":"قيد المراجعة", "added":"تمت الإضافة", "rejected":"مرفوض"}
        username = ("@" + req["username"].lstrip("@")) if req["username"] else "غير متوفر"
        details = (f"📬 تم تحديث طلب اللعبة/التطبيق #{req_id}\n\n"
                   f"🎮 الطلب: {req['request_text']}\n"
                   f"👤 اسم المشترك: {req['full_name'] or 'غير متوفر'}\n"
                   f"🔗 اسم المستخدم: {username}\n"
                   f"🆔 Telegram ID: {req['user_id']}\n"
                   f"📱 رقم الهاتف: {req['phone_number'] or 'غير مسجل'}\n"
                   f"📅 تاريخ الطلب: {req['created_at'] or 'غير متوفر'}\n"
                   f"📌 الحالة الجديدة: {status_names[status]}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👀 قيد المراجعة", callback_data=f"game_request_status:{req_id}:reviewed"), InlineKeyboardButton("✅ تمت الإضافة", callback_data=f"game_request_status:{req_id}:added")],
            [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"game_request_status:{req_id}:rejected")],
            [InlineKeyboardButton("📬 رجوع إلى طلبات الألعاب", callback_data="game_requests_list")],
        ])
        await edit_query_message(query, details, reply_markup=keyboard)
        customer_status = {"reviewed":"طلبك قيد المراجعة 👀", "added":"خبر مفرح! تمت إضافة اللعبة/التطبيق الذي اقترحته ✅🎮", "rejected":"نعتذر، لم نتمكن من قبول اقتراح اللعبة/التطبيق حاليًا ❌"}
        try:
            await context.bot.send_message(int(req["user_id"]), f"📬 تحديث طلبك #{req_id}\n🎮 {req['request_text']}\n{customer_status[status]}")
        except Exception:
            logger.exception("Could not notify customer about game request status")
        return

    # Group members can claim a pending order; only the first claim succeeds.
    if data.startswith("order_claim:"):
        try: order_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("طلب غير صالح.", show_alert=True); return
        if query.message.chat.type not in ("group", "supergroup"):
            await query.answer("استلام الطلب متاح من قروب العمل فقط.", show_alert=True); return
        with db() as conn:
            row = conn.execute("SELECT claimed_by, status, game_id, user_id FROM orders WHERE id=?", (order_id,)).fetchone()
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
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ إتمام الطلب", callback_data=f"order_finish:{order_id}"),
             InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"order_cancel:{order_id}")],
            [InlineKeyboardButton("📝 إتمام برسالة نصية", callback_data=f"order_finish_text:{order_id}")],
            [InlineKeyboardButton("📷 إرسال وصل الشحن (للمساعدين)", callback_data=f"order_receipt:{order_id}")],
            [InlineKeyboardButton("🔄 تنازل عن الطلب", callback_data=f"order_release:{order_id}")],
        ])
        try: await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception: pass
        await query.answer("تم استلام الطلب باسمك!")
        await query.message.reply_text(f"📥 الطلب #{order_id} استلمه: {query.from_user.full_name}")
        # The claim operation moves the order from pending to processing.
        # Send a customer-facing review notice once, at this transition.
        if row["status"] == "pending":
            try:
                await context.bot.send_message(
                    chat_id=row["user_id"],
                    text=(f"👀 تم استلام طلبك #{order_id} من فريق SERADJ STORE، "
                          "وهو الآن قيد المراجعة والتحقق.\n\n"
                          "سنرسل لك إشعاراً فور بدء التنفيذ أو عند اكتمال الطلب. ❤️"),
                )
            except Exception:
                logger.exception("تعذر إرسال إشعار استلام/مراجعة الطلب للزبون (order=%s, user=%s)", order_id, row["user_id"])
        return

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
        "offer_manage:",
        "offer_move:",
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
        "deposit_approve:",
        "deposit_reject:",
        "chat_reply:",
        "loan_", "loanreq_", "customer_orders:", "creditpay_", "account_type_set:", "reset_data", "reset_confirm", "adm_archived_stats", "people_", "person_", "offer_price_one:", "offer_price_all:", "orders_delete_",
    )

    if data.startswith(admin_actions) and not is_admin(user_id):
        # Allow only the member who claimed a group order to complete or cancel it.
        group_finish_allowed = False
        if (data.startswith("status:") and data.endswith((":completed", ":rejected"))
                and query.message.chat.type in ("group", "supergroup")):
            try:
                action_order_id = int(data.split(":")[1])
                with db() as conn:
                    claimed = conn.execute("SELECT claimed_by FROM orders WHERE id=?", (action_order_id,)).fetchone()
                owns_receipt = bool(context.user_data.get(f"order_receipt_photo:{action_order_id}"))
                group_finish_allowed = bool(claimed and (int(claimed["claimed_by"] or 0) == user_id or owns_receipt))
            except Exception:
                group_finish_allowed = False
        if not group_finish_allowed:
            await query.answer("⛔ غير مسموح لك.", show_alert=True)
            return

    if data.startswith("offer_price_usd:"):
        if not is_admin(user_id):
            return
        try:
            _, offer_id_text, column = data.split(":", 2)
            offer_id = int(offer_id_text)
        except (ValueError, TypeError):
            await query.answer("اختيار غير صالح.", show_alert=True)
            return
        if column not in ("price_usd", "price_usd_trader"):
            await query.answer("اختيار غير صالح.", show_alert=True)
            return
        with db() as conn:
            offer = conn.execute(f"SELECT name, {column} AS current_price FROM offers WHERE id=?", (offer_id,)).fetchone()
        if not offer:
            await query.answer("العرض غير موجود.", show_alert=True)
            return
        context.user_data["admin_step"] = "edit_single_offer_usd_price"
        context.user_data["pending_offer_id"] = offer_id
        context.user_data["pending_offer_usd_column"] = column
        who = "الزبون" if column == "price_usd" else "التاجر"
        await edit_query_message(query, f"💵 سعر الدولار للـ{who} في {offer['name']} حاليًا: {offer['current_price']} USD\nأرسل السعر الجديد بالدولار (0 لإلغاء السعر بالدولار).\nعند عرض السعر بالدينار يُضرب في سعر بيع الدولار.")
        return

    if data.startswith("offer_price_one:"):
        parts = data.split(":")
        if len(parts) != 3 or parts[2] not in ("price_baridi", "price_baridi_trader"):
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
        labels = {"price_baridi":"سعر الزبون عبر BaridiMob/CCP", "price_baridi_trader":"سعر التاجر عبر BaridiMob/CCP"}
        await edit_query_message(query, f"✏️ {offer['name']}\n{labels[column]} الحالي: {offer['current_price']} DA\nأرسل السعر الجديد فقط. سيُعاد حساب سعر Flexy المقابل تلقائيًا (+18%).\nللإلغاء أرسل /cancel.")
        return
    if data.startswith("offer_price_all:"):
        offer_id = int(data.split(":", 1)[1])
        context.user_data["admin_step"] = "edit_price_data"
        context.user_data["pending_offer_id"] = offer_id
        await edit_query_message(query, "أرسل السعرين بهذا الترتيب:\nسعر الزبون BaridiMob | سعر التاجر BaridiMob\nمثال: 750 | 650\nسيُحسب سعر Flexy تلقائيًا بإضافة 18%. أرسل /cancel للإلغاء.")
        return

    if data == "orders_delete_all":
        await edit_query_message(query, "⚠️ هل أنت متأكد من حذف جميع الطلبات؟ سيتم حذف سجلات الطلبات فقط، ولن تتغير حسابات المستخدمين أو الأرصدة أو الألعاب والعروض. لا يمكن التراجع عن العملية.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ نعم، احذف جميع الطلبات", callback_data="orders_delete_confirm")], [InlineKeyboardButton("❌ إلغاء", callback_data="adm_home")]]))
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
        await edit_query_message(query, f"✅ تم حذف جميع الطلبات ({count} طلب). الحسابات والأرصدة والألعاب والعروض لم تتغير.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")]]))
        return

    if data.startswith("wallet_rank:"):
        if not is_admin(user_id):
            await query.answer("غير مسموح", show_alert=True)
            return
        parts = data.split(":")
        if len(parts) == 3 and parts[1] != "noop":
            await admin_wallet_ranking(query, parts[1], int(parts[2]))
        return

    if data == "people_active":
        await admin_show_people(query.message, banned=False)
        return
    if data == "people_banned":
        await admin_show_people(query.message, banned=True)
        return
    if data.startswith("people_page:"):
        if not is_admin(user_id):
            await query.answer("غير مسموح", show_alert=True); return
        if data.endswith(":noop"):
            return
        try: _, banned_flag, page = data.split(":",2); banned_flag=int(banned_flag); page=int(page)
        except ValueError:
            await query.answer("صفحة غير صالحة",show_alert=True); return
        await admin_show_people(query.message, banned=bool(banned_flag), page=page)
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
    if data.startswith("person_balance_usd_edit:"):
        target = int(data.split(":", 1)[1])
        with db() as conn:
            person = conn.execute("SELECT user_id, full_name, balance_usd FROM users WHERE user_id=?", (target,)).fetchone()
        if not person:
            await query.answer("المشترك غير موجود.", show_alert=True); return
        context.user_data["person_balance_usd_edit_target"] = target
        await query.message.reply_text(
            f"✏️ تعديل رصيد الدولار للمشترك {person['full_name'] or target} (ID: {target})\n"
            f"الرصيد الحالي: {float(person['balance_usd'] or 0):.2f} USD\n"
            "أرسل الرصيد الجديد بالدولار (مثال: 12.50). للصفر أرسل 0، وللإلغاء /cancel."
        )
        return

    if data.startswith("person_balance_usd:"):
        target = int(data.split(":", 1)[1])
        context.user_data["person_balance_usd_target"] = target
        await query.message.reply_text(f"💵 أرسل مبلغ الدولار الذي تريد إضافته إلى رصيد المشترك {target}. مثال: 10 أو 12.50 USD.")
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
        await edit_query_message(query, f"⚠️ هل أنت متأكد من حذف حساب {target}؟ هذا لا يحذف الطلبات أو سجلات الدفع.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ تأكيد حذف الحساب", callback_data=f"person_delete:{target}")],
                                               [InlineKeyboardButton("إلغاء", callback_data=f"person_view:{target}")]]))
        return
    if data.startswith("person_delete:"):
        target = int(data.split(":")[1])
        with db() as conn:
            conn.execute("DELETE FROM users WHERE user_id=?", (target,))
        await edit_query_message(query, f"تم حذف سجل الحساب {target}. سجلات الطلبات والمدفوعات لم تُحذف.")
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
        await edit_query_message(query, f"✅ تم تغيير نوع الحساب إلى {label}.\nID: {target_id}\n" + ("يمكن للإدارة منح سلفية لهذا التاجر من بطاقة حسابه." if new_type == "trader" else "تم إيقاف صلاحيات التاجر. أي دين قائم يجب تسويته قبل التحويل."))
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
        await edit_query_message(query, f"{'✅ تمت الموافقة على' if approve else '❌ تم رفض'} طلب السلفية #{request_id}\nالتاجر: {target_id}\nالمبلغ: {amount} DA")
        return

    if data.startswith("loan_manage:"):
        target_id = int(data.split(":", 1)[1])
        with db() as conn:
            trader = conn.execute("SELECT user_id, username, full_name, credit_limit, credit_debt, credit_term_days, credit_due_at FROM users WHERE user_id = ? AND account_type = 'trader'", (target_id,)).fetchone()
        if not trader:
            await edit_query_message(query, "❌ التاجر غير موجود أو حسابه غير معتمد.")
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

    if data.startswith("admin_wallet_history:"):
        if not is_admin(user_id):
            await query.answer("للإدارة فقط.", show_alert=True); return
        target = int(data.split(":", 1)[1])
        with db() as conn:
            rows = conn.execute("SELECT currency,kind,amount,balance_before,balance_after,note,admin_id,created_at FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 50", (target,)).fetchall()
        lines = [f"📜 سجل المحفظة للمشترك {target}:"]
        for r in rows:
            unit = "USD" if r["currency"] == "USD" else "DA"
            lines.append(f"\n{r['created_at']} | {r['kind']}\nالمبلغ: {float(r['amount']):g} {unit} | {float(r['balance_before']):g} ← {float(r['balance_after']):g}\nالسبب: {r['note'] or 'غير محدد'} | Admin ID: {r['admin_id'] or '-'}")
        await query.message.reply_text("\n".join(lines) if rows else "لا توجد عمليات مسجلة لهذا المشترك.")
        return

    if data == "account_wallet":
        await query.answer("عرض رصيد المحفظة موجود ضمن معلومات حسابك.", show_alert=True)
        return

    if data == "account_deposit":
        with db() as conn:
            pending_dep = conn.execute("SELECT id FROM wallet_deposits WHERE user_id=? AND status='pending' LIMIT 1", (user_id,)).fetchone()
        if pending_dep:
            await edit_query_message(query, 
                f"⏳ لديك طلب تعبئة قيد المراجعة #{pending_dep['id']}، لا يمكنك إرسال طلب آخر حتى تتم معالجته.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home:main")]])
            )
            await query.answer()
            return
        for k in ("awaiting_deposit_amount", "awaiting_deposit_amount_usd", "deposit_amount", "deposit_amount_usd", "deposit_method", "deposit_currency", "awaiting_deposit_receipt"):
            context.user_data.pop(k, None)
        await edit_query_message(query, "💰 اختر المحفظة التي تريد تعبئتها:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇩🇿 محفظة الدينار DA", callback_data="deposit_currency:DA")],
            [InlineKeyboardButton("💵 محفظة الدولار USD", callback_data="deposit_currency:USD")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home:main")],
        ]))
        await query.answer()
        return

    if data == "account_points":
        await show_points_shop(query.message, user_id)
        return

    if data == "account_orders":
        await show_my_orders(update, context)
        return

    if data == "wallet_history":
        with db() as conn:
            rows = conn.execute("SELECT currency,kind,amount,balance_before,balance_after,note,created_at FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 30", (user_id,)).fetchall()
        if not rows:
            await query.message.reply_text("📜 لا توجد عمليات مسجلة في محفظتك بعد.")
        else:
            lines = ["📜 آخر عمليات محفظتك:"]
            for r in rows:
                unit = "USD" if r["currency"] == "USD" else "DA"
                lines.append(f"\n• {r['created_at']}\n{r['kind']} | {float(r['amount']):g} {unit}\nالرصيد: {float(r['balance_before']):g} ← {float(r['balance_after']):g} {unit}" + (f"\n{r['note']}" if r['note'] else ""))
            await query.message.reply_text("\n".join(lines))
        return

    if data.startswith("deposit_currency:"):
        currency = data.split(":", 1)[1].upper()
        with db() as conn:
            pending = conn.execute("SELECT id FROM wallet_deposits WHERE user_id=? AND status='pending' LIMIT 1", (user_id,)).fetchone()
        if pending:
            await query.answer(f"لديك طلب تعبئة قيد المراجعة #{pending['id']}.", show_alert=True)
            return
        if currency == "DA":
            context.user_data["deposit_currency"] = "DA"
            context.user_data["awaiting_deposit_amount"] = True
            await edit_query_message(query, "🇩🇿 محفظة الدينار\nأرسل مبلغ التعبئة بالدينار الجزائري (مثال: 1000 DA).\nالحد الأدنى 100 DA.\nللإلغاء أرسل /cancel")
        elif currency == "USD":
            context.user_data["deposit_currency"] = "USD"
            context.user_data["awaiting_deposit_amount_usd"] = True
            await edit_query_message(query, "💵 محفظة الدولار USD\nأرسل المبلغ بالدولار، مثال: 10 أو 12.50 USD.\nيُضاف الرصيد إلى محفظة الدولار فقط بعد موافقة الإدارة.\nلا يوجد تحويل تلقائي إلى الدينار؛ للتحويل تواصل مع الإدارة مباشرة.\nللإلغاء أرسل /cancel")
        return

    if data.startswith("deposit_usd_method:"):
        try: method_id = int(data.split(":", 1)[1])
        except ValueError: return
        amount_usd = float(context.user_data.get("deposit_amount_usd", 0) or 0)
        with db() as conn:
            method_row = conn.execute("SELECT * FROM custom_payment_methods WHERE id=? AND enabled=1 AND upper(currency)='USD'", (method_id,)).fetchone()
        if not method_row or get_setting("usd_payments_enabled", "0") != "1":
            await edit_query_message(query, "❌ طريقة الدفع بالدولار غير متاحة حاليًا. تواصل مع الإدارة."); return
        if amount_usd <= 0:
            await edit_query_message(query, "❌ مبلغ الدولار غير صحيح. ابدأ التعبئة من جديد."); return
        context.user_data["deposit_method"] = f"{method_row['emoji']} {method_row['name']}"
        context.user_data["deposit_currency"] = "USD"
        context.user_data["awaiting_deposit_receipt"] = True
        details = method_row["instructions"] or "تواصل مع الإدارة لمعرفة تعليمات الدفع."
        await edit_query_message(query, f"💵 تعبئة محفظة الدولار\nالمبلغ: {amount_usd:.2f} USD\nطريقة الدفع: {method_row['name']}\n\n{details}\n\n📸 بعد الدفع، أرسل صورة أو فيديو وصل الدفع هنا. لا يُضاف الرصيد إلا بعد موافقة الإدارة.")
        return

    if data.startswith("deposit_method:"):
        method = data.split(":", 1)[1]
        if method not in ("baridi", "ccp", "flexy"):
            return
        amount = int(context.user_data.get("deposit_amount", 0) or 0)
        account_type = "trader" if is_trader(user_id) else "customer"
        minimum, maximum = deposit_limits(account_type, "flexy" if method == "flexy" else "baridi")
        if amount < minimum or amount > maximum:
            context.user_data.pop("deposit_amount", None)
            await edit_query_message(query, 
                f"❌ مبلغ التعبئة خارج الحدود المسموحة لحسابك عبر {'Flexy' if method == 'flexy' else 'BaridiMob / CCP'}.\n"
                f"الحد الأدنى: {minimum} DA\nالحد الأقصى: {maximum} DA\nابدأ التعبئة من جديد بالمبلغ المناسب."
            )
            return
        method_names = {"baridi": "BaridiMob", "ccp": "CCP", "flexy": "Flexy"}
        context.user_data["deposit_method"] = method_names[method]
        context.user_data["deposit_currency"] = "DA"
        if method == "flexy":
            await edit_query_message(query, 
                f"🟠 اختر طريقة احتساب Flexy لتعبئة {amount} دج:\n\n"
                f"1️⃣ تدفع {int(round(amount * 1.18))} دج وتُضاف {amount} دج كاملة إلى محفظتك.\n"
                f"2️⃣ تدفع {amount} دج وتُخصم نسبة 15%، فيُضاف {int(round(amount * 0.85))} دج إلى محفظتك.\n\nاختر الطريقة:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"دفع {int(round(amount * 1.18))} دج وإضافة {amount} دج", callback_data="deposit_flexy_mode:full")],
                    [InlineKeyboardButton(f"دفع {amount} دج وإضافة {int(round(amount * 0.85))} دج", callback_data="deposit_flexy_mode:deduct")],
                ])
            )
            return
        context.user_data["awaiting_deposit_receipt"] = True
        context.user_data["deposit_paid_amount"] = amount
        details_key = "ccp_details" if method == "ccp" else "baridi_details"
        details = get_setting(details_key, get_setting("baridi_details", "تواصل مع الإدارة لمعرفة معلومات الدفع."))
        await edit_query_message(query, f"💳 تعبئة محفظة الدينار\nالمبلغ الذي سيضاف للمحفظة: {amount} DA\nالمبلغ المطلوب دفعه عبر {method_names[method]}: {amount} DA\n\n{details}\n\n📸 بعد الدفع، أرسل صورة أو فيديو وصل الدفع هنا. لا يُضاف الرصيد إلا بعد موافقة الإدارة.")
        return

    if data.startswith("deposit_flexy_mode:"):
        mode = data.split(":", 1)[1]
        amount = int(context.user_data.get("deposit_amount", 0) or 0)
        if mode not in ("full", "deduct") or amount <= 0:
            await query.answer("انتهت جلسة التعبئة. ابدأ من جديد.", show_alert=True)
            return
        requested_amount = amount
        credit_amount = amount if mode == "full" else int(round(amount * 0.85))
        paid_amount = int(round(amount * 1.18)) if mode == "full" else amount
        context.user_data["deposit_requested_amount"] = requested_amount
        context.user_data["deposit_amount"] = credit_amount
        context.user_data["deposit_paid_amount"] = paid_amount
        context.user_data["deposit_flexy_mode"] = mode
        context.user_data["awaiting_deposit_receipt"] = True
        details = get_setting("flexy_details", "تواصل مع الإدارة لمعرفة معلومات Flexy.")
        await edit_query_message(query, 
            f"🟠 تعبئة محفظة Flexy\nالمبلغ المدفوع: {paid_amount} DA\n"
            f"المبلغ الذي سيضاف إلى محفظتك بعد الموافقة: {credit_amount} DA\n\n"
            f"{details}\n\n📸 أرسل صورة أو فيديو وصل الدفع هنا. لا يُضاف الرصيد إلا بعد موافقة الإدارة."
        )
        return

    if data.startswith("deposit_queue:"):
        if not is_admin(user_id):
            await query.answer("⛔ هذا القسم خاص بالإدارة.", show_alert=True); return
        raw_page = data.split(":", 1)[1]
        if raw_page == "noop":
            return
        await show_pending_deposits(query, page=raw_page, edit=True)
        return

    if data.startswith("deposit_open:"):
        if not is_admin(user_id):
            await query.answer("⛔ هذا القسم خاص بالإدارة.", show_alert=True); return
        try:
            _, dep_id, page = data.split(":", 2); dep_id=int(dep_id); page=int(page)
        except (ValueError, IndexError):
            await query.answer("طلب غير صالح.", show_alert=True); return
        with db() as conn:
            dep = conn.execute("SELECT d.*,u.full_name FROM wallet_deposits d LEFT JOIN users u ON u.user_id=d.user_id WHERE d.id=?", (dep_id,)).fetchone()
        if not dep:
            await query.answer("طلب التعبئة غير موجود.", show_alert=True); return
        if dep["status"] != "pending":
            await query.answer("تمت معالجة هذا الطلب مسبقًا.", show_alert=True); return
        currency=(dep["currency"] or "DA").upper()
        amount=f"{float(dep['amount_usd'] or 0):g} USD" if currency=="USD" else f"{int(dep['amount'] or 0)} DA"
        caption=(f"💰 طلب تعبئة رصيد #{dep_id}\nالمشترك: {dep['full_name'] or dep['user_id']}\nID: {dep['user_id']}\n"
                 f"المبلغ المطلوب إضافته: {amount}\nطريقة الدفع: {dep['payment_method']}\nالتاريخ: {dep['created_at']}\nالحالة: قيد المراجعة")
        actions=InlineKeyboardMarkup([[InlineKeyboardButton("✅ قبول التعبئة",callback_data=f"deposit_approve:{dep_id}"),InlineKeyboardButton("❌ رفض",callback_data=f"deposit_reject:{dep_id}")], [InlineKeyboardButton("🔙 قائمة طلبات التعبئة",callback_data=f"deposit_queue:{page}")]])
        try:
            if "receipt_type" in dep.keys() and dep["receipt_type"] == "video":
                await context.bot.send_video(chat_id=user_id, video=dep["receipt_file_id"], caption=caption, reply_markup=actions)
            else:
                await context.bot.send_photo(chat_id=user_id, photo=dep["receipt_file_id"], caption=caption, reply_markup=actions)
        except Exception:
            logger.exception("Could not display deposit %s from admin queue", dep_id)
            await query.message.reply_text(caption, reply_markup=actions)
        await query.answer("تم فتح طلب التعبئة.")
        return

    if data.startswith("deposit_approve:") or data.startswith("deposit_reject:"):
        # callback_handler acknowledges ordinary callbacks near its entry point.
        # Do not call query.answer() a second time here: Telegram rejects duplicate
        # callback answers, which previously caused approval to abort before crediting.
        if not is_admin(user_id):
            await query.message.reply_text("⛔ هذا الإجراء خاص بالإدارة.")
            return
        # Approval/rejection must be atomic: never mark approved unless the wallet
        # credit and ledger entry have both succeeded.
        try:
            deposit_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.message.reply_text("❌ رقم طلب التعبئة غير صالح.")
            return

        approve = data.startswith("deposit_approve:")
        try:
            with db() as conn:
                # Older production databases may not yet have the paid_amount column.
                cols = {r["name"] for r in conn.execute("PRAGMA table_info(wallet_deposits)").fetchall()}
                if "paid_amount" not in cols:
                    conn.execute("ALTER TABLE wallet_deposits ADD COLUMN paid_amount REAL DEFAULT 0")
                # Ensure older installations also have the ledger table before approval.
                conn.execute("""CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'DA',
                    kind TEXT NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    balance_before REAL NOT NULL DEFAULT 0,
                    balance_after REAL NOT NULL DEFAULT 0,
                    note TEXT DEFAULT '',
                    admin_id INTEGER DEFAULT NULL,
                    created_at TEXT NOT NULL
                )""")
                ledger_cols = {r["name"] for r in conn.execute("PRAGMA table_info(wallet_transactions)").fetchall()}
                ledger_migrations = {
                    "currency": "TEXT NOT NULL DEFAULT 'DA'",
                    "kind": "TEXT NOT NULL DEFAULT 'عملية قديمة'",
                    "amount": "REAL NOT NULL DEFAULT 0",
                    "balance_before": "REAL NOT NULL DEFAULT 0",
                    "balance_after": "REAL NOT NULL DEFAULT 0",
                    "note": "TEXT DEFAULT ''",
                    "admin_id": "INTEGER DEFAULT NULL",
                    "created_at": "TEXT NOT NULL DEFAULT ''",
                }
                for column, definition in ledger_migrations.items():
                    if column not in ledger_cols:
                        conn.execute(f"ALTER TABLE wallet_transactions ADD COLUMN {column} {definition}")

                dep = conn.execute("SELECT * FROM wallet_deposits WHERE id=?", (deposit_id,)).fetchone()
                if not dep:
                    await query.message.reply_text(f"❌ طلب التعبئة #{deposit_id} غير موجود في قاعدة البيانات.")
                    return
                if dep["status"] != "pending":
                    await query.message.reply_text(f"ℹ️ طلب التعبئة #{deposit_id} تمت معالجته مسبقًا: {dep['status']}.")
                    return

                currency = (dep["currency"] or "DA").upper()
                is_usd = currency == "USD"
                credit = float(dep["amount_usd"] or 0) if is_usd else int(dep["amount"] or 0)
                paid = float(dep["paid_amount"] or 0)
                if paid <= 0:
                    paid = credit if is_usd else (int(round(credit * 1.18)) if "flexy" in str(dep["payment_method"]).lower() else credit)

                if approve:
                    col = "balance_usd" if is_usd else "balance"
                    user_row = conn.execute(f"SELECT COALESCE({col},0) AS bal FROM users WHERE user_id=?", (dep["user_id"],)).fetchone()
                    if not user_row:
                        raise RuntimeError(f"User {dep['user_id']} not found for deposit {deposit_id}")
                    before = float(user_row["bal"] or 0)
                    after = before + credit
                    updated = conn.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (after, dep["user_id"]))
                    if updated.rowcount != 1:
                        raise RuntimeError(f"Wallet update failed for user {dep['user_id']} deposit {deposit_id}")
                    conn.execute("""INSERT INTO wallet_transactions
                        (user_id,currency,kind,amount,balance_before,balance_after,note,admin_id,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (dep["user_id"], currency, "تعبئة رصيد", credit, before, after,
                         f"طلب #{deposit_id} عبر {dep['payment_method']} | المدفوع: {paid:g} {currency}", user_id, now_text()))
                    new_status = "approved"
                else:
                    before = after = 0
                    new_status = "rejected"

                changed = conn.execute("UPDATE wallet_deposits SET status=?,processed_at=? WHERE id=? AND status='pending'",
                                       (new_status, now_text(), deposit_id))
                if changed.rowcount != 1:
                    raise RuntimeError(f"Deposit {deposit_id} status changed concurrently")

            unit = "USD" if is_usd else "DA"
            if approve:
                customer_text = (f"✅ تمت الموافقة على تعبئة #{deposit_id}.\n"
                                 f"المبلغ المدفوع: {paid:g} {unit} عبر {dep['payment_method']}\n"
                                 f"المبلغ المضاف للمحفظة: {credit:g} {unit}\n"
                                 f"الرصيد السابق: {before:g} {unit}\nالرصيد الجديد: {after:g} {unit}.")
                admin_text = (f"✅ تمت الموافقة على تعبئة الرصيد #{deposit_id}\n"
                              f"المدفوع: {paid:g} {unit} | المضاف: {credit:g} {unit}\n"
                              f"الرصيد: {before:g} ← {after:g} {unit}\nالطريقة: {dep['payment_method']}\nالزبون: {dep['user_id']}")
            else:
                customer_text = f"❌ تم رفض تعبئة الرصيد #{deposit_id}. إذا كان هناك خطأ، تواصل مع الإدارة."
                admin_text = f"❌ تم رفض تعبئة الرصيد #{deposit_id}\nالطريقة: {dep['payment_method']}\nالزبون: {dep['user_id']}"

            try:
                await context.bot.send_message(dep["user_id"], customer_text)
            except Exception:
                logger.exception("تعذر إشعار صاحب طلب التعبئة %s", deposit_id)

            # Photo messages use caption editing; fall back to a normal reply if editing fails.
            try:
                await query.edit_message_caption(caption=admin_text, reply_markup=None)
            except Exception:
                logger.exception("تعذر تعديل رسالة طلب التعبئة %s", deposit_id)
                try:
                    await query.message.reply_text(admin_text, reply_markup=None)
                except Exception:
                    logger.exception("تعذر إرسال نتيجة معالجة التعبئة %s", deposit_id)
            return
        except Exception as exc:
            logger.exception("Deposit %s %s failed", deposit_id, "approval" if approve else "rejection")
            try:
                await query.message.reply_text(f"❌ تعذرت معالجة طلب التعبئة #{deposit_id}. لم يتم اعتماد العملية. راجع سجل أخطاء البوت.")
            except Exception:
                pass
            return

    if data.startswith("trader_requests_page:"):
        if not is_admin(user_id):
            await query.answer("⛔ هذا القسم خاص بالإدارة.", show_alert=True); return
        raw=data.split(":",1)[1]
        if raw == "noop": return
        try: page=max(0,int(raw))
        except ValueError: page=0
        per_page=8
        with db() as conn:
            total=int(conn.execute("SELECT COUNT(*) FROM users WHERE trader_requested=1 AND account_type!='trader'").fetchone()[0])
            rows=conn.execute("SELECT user_id,username,full_name FROM users WHERE trader_requested=1 AND account_type!='trader' ORDER BY user_id DESC LIMIT ? OFFSET ?",(per_page,page*per_page)).fetchall()
        pages=max(1,(total+per_page-1)//per_page)
        if page>=pages: page=pages-1
        buttons=[]
        for row in rows:
            label=(row['full_name'] or row['username'] or row['user_id'])
            buttons.append([InlineKeyboardButton(f"{label} — قبول",callback_data=f"trader_approve:{row['user_id']}"),InlineKeyboardButton("رفض",callback_data=f"trader_reject:{row['user_id']}")])
        nav=[]
        if page>0: nav.append(InlineKeyboardButton("⬅️ السابق",callback_data=f"trader_requests_page:{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{pages}",callback_data="trader_requests_page:noop"))
        if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️",callback_data=f"trader_requests_page:{page+1}"))
        buttons.append(nav); buttons.append([InlineKeyboardButton("🔙 رجوع",callback_data="adm_home")])
        await edit_query_message(query, f"🏪 طلبات حسابات التجار المعلّقة — {total}",reply_markup=InlineKeyboardMarkup(buttons))
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
        await edit_query_message(query, "✅ تم تفعيل حساب التاجر." if approved else "تم رفض طلب التاجر.")
        return

    # عرض إحصائيات الشهرين المحفوظة
    if data == "adm_archived_stats":
        await show_archived_stats(query)
        return

    # تصفير البيانات مع تأكيد مزدوج
    if data == "reset_data":
        await edit_query_message(query, 
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
            await edit_query_message(query, "❌ فشل تصفير البيانات. لم نؤكد نجاح العملية؛ راجع سجل السيرفر وقاعدة البيانات.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")]]))
            return
        await edit_query_message(query, 
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
    elif data.startswith("adm_orders"):
        if data.endswith(":noop"):
            return
        try: orders_page=int(data.split(":",1)[1]) if ":" in data else 0
        except ValueError: orders_page=0
        await admin_all_orders(query, orders_page)

    elif data == "adm_customers" or data.startswith("adm_customers_page:"):
        try: page = int(data.split(":",1)[1]) if ":" in data and not data.endswith(":noop") else 0
        except ValueError: page = 0
        if data.endswith(":noop"): return
        page=max(0,page); per_page=8
        with db() as conn:
            total=int(conn.execute("SELECT COUNT(*) FROM (SELECT user_id FROM orders GROUP BY user_id)").fetchone()[0])
            rows = conn.execute("SELECT u.user_id, u.username, u.full_name, COUNT(o.id) AS order_count, COALESCE(SUM(CASE WHEN o.status != 'rejected' THEN o.price ELSE 0 END), 0) AS total FROM users u JOIN orders o ON o.user_id = u.user_id GROUP BY u.user_id ORDER BY MAX(o.id) DESC LIMIT ? OFFSET ?",(per_page,page*per_page)).fetchall()
        pages=max(1,(total+per_page-1)//per_page)
        if page>=pages: page=pages-1
        buttons = [[InlineKeyboardButton(f"{(r['full_name'] or r['username'] or r['user_id'])} | {r['order_count']} طلب | {r['total']} DA"[:60], callback_data=f"customer_orders:{r['user_id']}")] for r in rows]
        nav=[]
        if page>0: nav.append(InlineKeyboardButton("⬅️ السابق",callback_data=f"adm_customers_page:{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{pages}",callback_data="adm_customers_page:noop"))
        if page+1<pages: nav.append(InlineKeyboardButton("التالي ➡️",callback_data=f"adm_customers_page:{page+1}"))
        buttons.append(nav); buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_home")])
        await edit_query_message(query, f"👤 اختر زبونًا — {total} زبون:", reply_markup=InlineKeyboardMarkup(buttons))

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
        await edit_query_message(query, f"✨ إيموجي Premium — {game['name']}{status}\n\nتقدر تتحكم في الإيموجي من هنا.", reply_markup=InlineKeyboardMarkup(buttons))

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
        await edit_query_message(query, "✨ إدارة إيموجيات Premium\n🟢 مفعّل | ⏸️ متوقف | ⚪ غير مضاف", reply_markup=InlineKeyboardMarkup(buttons))

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
        await edit_query_message(query, f"✨ إيموجي Premium — {game['name']}\nالإيموجي ID: {custom_id}\nالحالة: {state}", reply_markup=InlineKeyboardMarkup(buttons))
        return

    elif data.startswith("premium_delete:"):
        game_id = int(data.split(":", 1)[1])
        set_setting(f"premium_emoji_id_{game_id}", "")
        set_setting(f"premium_emoji_enabled_{game_id}", "1")
        await query.answer("تم حذف الإيموجي")
        with db() as conn:
            game = conn.execute("SELECT id, name FROM games WHERE id=?", (game_id,)).fetchone()
        buttons = [[InlineKeyboardButton("➕ إضافة إيموجي", callback_data=f"premium_set:{game_id}")], [InlineKeyboardButton("🔙 قائمة الإيموجيات", callback_data="premium_manage")]]
        await edit_query_message(query, f"✨ إيموجي Premium — {game['name']}\nمازال ما ضفت حتى إيموجي لهذه اللعبة.", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # إدارة طرق الشحن لكل لعبة أو تطبيق
    elif data.startswith("game_methods:"):
        game_id = int(data.split(":", 1)[1])
        with db() as conn:
            game = conn.execute("SELECT name FROM games WHERE id=?", (game_id,)).fetchone()
            methods = conn.execute("SELECT * FROM recharge_methods WHERE game_id=? ORDER BY id", (game_id,)).fetchall()
        if not game:
            await edit_query_message(query, "الخدمة غير موجودة."); return
        buttons = []
        for m in methods:
            method_label = ("🟢 " if m["active"] else "🔴 ") + m["title"] + f" ({ {'id':'ID','login':'تسجيل دخول','none':'بدون معلومات'}.get(m['method_type'],'ID') })"
            buttons.append([
                InlineKeyboardButton(method_label, callback_data=f"recharge_method_toggle:{m['id']}"),
                InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"recharge_method_rename:{m['id']}")
            ])
        buttons.append([InlineKeyboardButton("➕ إضافة طريقة شحن", callback_data=f"recharge_method_add:{game_id}")])
        buttons.append([InlineKeyboardButton("🔙 إدارة الألعاب", callback_data="adm_games")])
        await edit_query_message(query, f"🔀 طرق الشحن لـ {game['name']}\nاختر طريقة لتفعيلها/إيقافها أو أضف طريقة جديدة. كل طريقة لها عروض وأسعار مستقلة.", reply_markup=InlineKeyboardMarkup(buttons))

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
        await edit_query_message(query, "➕ أرسل بيانات العرض والأسعار لهذه الطريقة فقط:\nاسم العرض | سعر الزبون BaridiMob/CCP | سعر التاجر BaridiMob/CCP\n\nمثال: 100 Coins | 250 | 220\nسيُحسب سعر Flexy تلقائيًا بإضافة 18%. أرسل /cancel للإلغاء.")

    # إدارة الألعاب
    elif data == "adm_games":
        await admin_games(query, 0)
    elif data.startswith("adm_games_page:"):
        raw=data.split(":",1)[1]
        if raw != "noop": await admin_games(query, int(raw))

    # إدارة العروض
    elif data == "adm_offers":
        await admin_choose_manage_game(query, 0)
    elif data.startswith("adm_offers_page:"):
        raw=data.split(":",1)[1]
        if raw != "noop": await admin_choose_manage_game(query, int(raw))

    elif data.startswith("offer_manage:"):
        try:
            offer_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("معرّف العرض غير صالح.", show_alert=True)
            return
        await admin_offer_manage(query, offer_id)

    # تغيير ترتيب العرض داخل اللعبة
    elif data.startswith("offer_move:"):
        try:
            _, offer_id_text, direction = data.split(":", 2)
            offer_id = int(offer_id_text)
            if direction not in ("up", "down"):
                raise ValueError
        except (ValueError, TypeError):
            await query.answer("بيانات الترتيب غير صحيحة.", show_alert=True)
            return
        with db() as conn:
            current = conn.execute("SELECT id, game_id FROM offers WHERE id=?", (offer_id,)).fetchone()
            if not current:
                await query.answer("العرض غير موجود.", show_alert=True)
                return
            game_id = int(current["game_id"])
            rows = conn.execute("SELECT id FROM offers WHERE game_id=? ORDER BY CASE WHEN COALESCE(sort_order,0)>0 THEN sort_order ELSE 1000000+id END, id", (game_id,)).fetchall()
            ids = [int(r["id"]) for r in rows]
            idx = ids.index(offer_id)
            target = idx - 1 if direction == "up" else idx + 1
            if target < 0 or target >= len(ids):
                await query.answer("العرض موجود بالفعل في هذا الطرف من القائمة.", show_alert=True)
                return
            ids[idx], ids[target] = ids[target], ids[idx]
            conn.executemany("UPDATE offers SET sort_order=? WHERE id=?", [(position, item_id) for position, item_id in enumerate(ids, start=1)])
        await query.answer("✅ تم تحديث ترتيب العروض.")
        await admin_offer_manage(query, offer_id)

    # تغيير اسم عرض من لوحة التحكم
    elif data.startswith("offer_rename:"):
        try:
            offer_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("معرّف العرض غير صالح.", show_alert=True)
            return
        with db() as conn:
            offer = conn.execute("SELECT id, name, game_id FROM offers WHERE id=?", (offer_id,)).fetchone()
        if not offer:
            await query.answer("العرض غير موجود.", show_alert=True)
            return
        context.user_data["editing_offer_name"] = int(offer_id)
        await query.message.reply_text(
            f"✏️ أرسل الاسم الجديد للعرض الحالي: {offer['name']}\n\n"
            "سيُطبّق الاسم الجديد في قوائم اللعبة والطلبات الجديدة، دون تغيير الأسعار أو النقاط.\n"
            "أرسل /cancel للإلغاء."
        )
        await query.answer()

    # إعدادات الدفع
    elif data == "adm_payment":
        await admin_payment_settings(query)

    # اختيار لعبة لإضافة عرض
    elif data.startswith("adm_add_offer"):
        if data.endswith(":noop"): return
        try: page=int(data.split(":",1)[1]) if ":" in data else 0
        except ValueError: page=0
        await admin_choose_offer_game(query,page)

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
            await admin_offer_manage(query, offer_id)

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

        if query.message.chat.type in ("group", "supergroup") and new_status in ("completed", "rejected"):
            try:
                final_text = "✅ الطلب مكتمل" if new_status == "completed" else "❌ الطلب ملغي"
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(f"{final_text} — الطلب #{order_id}")
            except Exception:
                pass
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
    elif data.startswith("offers_game_page:"):
        parts=data.split(":")
        if len(parts)==3 and parts[1].isdigit() and parts[2].isdigit():
            await admin_offers(query, int(parts[1]), int(parts[2]))
        return
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
            await admin_offer_manage(query, offer_id)
        else:
            await edit_query_message(query, "❌ العرض غير موجود.")

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
            await edit_query_message(query, 
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
        await edit_query_message(query, "اختر طريقة الشحن التي سيخصّص لها هذا العرض وأسعاره:", reply_markup=InlineKeyboardMarkup(buttons))

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
            await edit_query_message(query, 
                "❌ العرض غير موجود."
            )
            return

        context.user_data["pending_offer_id"] = offer_id
        with db() as conn:
            price_row = conn.execute("SELECT price_baridi, price_flexy, price_baridi_trader, price_flexy_trader, price_usd_trader FROM offers WHERE id=?", (offer_id,)).fetchone()
            custom_methods = conn.execute("SELECT * FROM custom_payment_methods ORDER BY id").fetchall()
            offer_method_states = {int(r["method_id"]): int(r["enabled"] or 0) for r in conn.execute("SELECT method_id, enabled FROM offer_payment_methods WHERE offer_id=?", (offer_id,)).fetchall()}
        price_buttons = [
            [InlineKeyboardButton(f"{'✅' if get_setting(f'offer_payment_baridi_{offer_id}', '1') == '1' else '🚫'} BaridiMob / CCP — {'إيقاف' if get_setting(f'offer_payment_baridi_{offer_id}', '1') == '1' else 'تفعيل'} لهذا العرض", callback_data=f"offer_base_pay_toggle:{offer_id}:baridi")],
            [InlineKeyboardButton(f"{'✅' if get_setting(f'offer_payment_flexy_{offer_id}', '1') == '1' else '🚫'} Flexy — {'إيقاف' if get_setting(f'offer_payment_flexy_{offer_id}', '1') == '1' else 'تفعيل'} لهذا العرض", callback_data=f"offer_base_pay_toggle:{offer_id}:flexy")],
            [InlineKeyboardButton("👤 الزبون — BaridiMob/CCP", callback_data=f"offer_price_one:{offer_id}:price_baridi")],
            [InlineKeyboardButton("🏪 التاجر — BaridiMob/CCP", callback_data=f"offer_price_one:{offer_id}:price_baridi_trader")],
            [InlineKeyboardButton("💵 سعر الدولار للزبون", callback_data=f"offer_price_usd:{offer_id}:price_usd")],
            [InlineKeyboardButton("💵 سعر الدولار للتاجر", callback_data=f"offer_price_usd:{offer_id}:price_usd_trader")],
            [InlineKeyboardButton("✏️ تعديل سعري الزبون والتاجر معًا", callback_data=f"offer_price_all:{offer_id}")],
        ]
        if custom_methods:
            price_buttons.append([InlineKeyboardButton("— طرق الدفع المخصصة لهذا العرض —", callback_data=f"offer_payments_info:{offer_id}")])
            for cm in custom_methods:
                is_on = offer_method_states.get(int(cm["id"]), 1)
                price_buttons.append([InlineKeyboardButton(f"{'✅' if is_on else '🚫'} {cm['emoji']} {cm['name']} — {'إيقاف لهذا العرض' if is_on else 'تفعيل لهذا العرض'}", callback_data=f"offer_pay_toggle:{offer_id}:{cm['id']}")])
        await edit_query_message(query, 
            f"💰 تعديل سعر العرض: {offer['name']}\n\n"
            f"الأسعار الحالية: زبون Baridi {price_row['price_baridi']} DA | زبون Flexy {price_row['price_flexy']} DA\n"
            f"تاجر DA {price_row['price_baridi_trader']} DA | تاجر USD {price_row['price_usd_trader']} USD\n\n"
            "اختار السعر اللي تحب تبدله فقط؛ باقي الأسعار تبقى كما هي:",
            reply_markup=InlineKeyboardMarkup(price_buttons)
        )

    elif data.startswith("offer_base_pay_toggle:"):
        if not is_admin(user_id):
            return
        try:
            _, offer_id_text, method = data.split(":", 2)
            offer_id = int(offer_id_text)
        except (ValueError, TypeError):
            await query.answer("بيانات غير صحيحة.", show_alert=True)
            return
        if method not in ("baridi", "flexy"):
            await query.answer("طريقة دفع غير صحيحة.", show_alert=True)
            return
        with db() as conn:
            exists = conn.execute("SELECT 1 FROM offers WHERE id=?", (offer_id,)).fetchone()
        if not exists:
            await query.answer("العرض غير موجود.", show_alert=True)
            return
        key = f"offer_payment_{method}_{offer_id}"
        new_state = "0" if get_setting(key, "1") == "1" else "1"
        set_setting(key, new_state)
        await query.answer("تم إيقاف طريقة الدفع لهذا العرض." if new_state == "0" else "تم تفعيل طريقة الدفع لهذا العرض.")
        # أعد فتح لوحة أسعار العرض لتحديث أزرار الحالة
        with db() as conn:
            offer = conn.execute("SELECT name FROM offers WHERE id=?", (offer_id,)).fetchone()
            price_row = conn.execute("SELECT price_baridi, price_flexy, price_baridi_trader, price_flexy_trader, price_usd_trader FROM offers WHERE id=?", (offer_id,)).fetchone()
            custom_methods = conn.execute("SELECT * FROM custom_payment_methods ORDER BY id").fetchall()
            offer_method_states = {int(r["method_id"]): int(r["enabled"] or 0) for r in conn.execute("SELECT method_id, enabled FROM offer_payment_methods WHERE offer_id=?", (offer_id,)).fetchall()}
        price_buttons = [
            [InlineKeyboardButton(f"{'✅' if get_setting(f'offer_payment_baridi_{offer_id}', '1') == '1' else '🚫'} BaridiMob / CCP — {'إيقاف' if get_setting(f'offer_payment_baridi_{offer_id}', '1') == '1' else 'تفعيل'} لهذا العرض", callback_data=f"offer_base_pay_toggle:{offer_id}:baridi")],
            [InlineKeyboardButton(f"{'✅' if get_setting(f'offer_payment_flexy_{offer_id}', '1') == '1' else '🚫'} Flexy — {'إيقاف' if get_setting(f'offer_payment_flexy_{offer_id}', '1') == '1' else 'تفعيل'} لهذا العرض", callback_data=f"offer_base_pay_toggle:{offer_id}:flexy")],
            [InlineKeyboardButton("👤 الزبون — BaridiMob/CCP", callback_data=f"offer_price_one:{offer_id}:price_baridi")],
            [InlineKeyboardButton("🏪 التاجر — BaridiMob/CCP", callback_data=f"offer_price_one:{offer_id}:price_baridi_trader")],
            [InlineKeyboardButton("💵 سعر الدولار للزبون", callback_data=f"offer_price_usd:{offer_id}:price_usd")],
            [InlineKeyboardButton("💵 سعر الدولار للتاجر", callback_data=f"offer_price_usd:{offer_id}:price_usd_trader")],
            [InlineKeyboardButton("✏️ تعديل سعري الزبون والتاجر معًا", callback_data=f"offer_price_all:{offer_id}")],
        ]
        for cm in custom_methods:
            is_on = offer_method_states.get(int(cm["id"]), 1)
            price_buttons.append([InlineKeyboardButton(f"{'✅' if is_on else '🚫'} {cm['emoji']} {cm['name']} — {'إيقاف لهذا العرض' if is_on else 'تفعيل لهذا العرض'}", callback_data=f"offer_pay_toggle:{offer_id}:{cm['id']}")])
        price_buttons.append([InlineKeyboardButton("🔙 إدارة العرض", callback_data=f"offer_manage:{offer_id}")])
        await edit_query_message(query, f"💰 تعديل سعر العرض: {offer['name']}\n\nالأسعار الحالية: زبون Baridi {price_row['price_baridi']} DA | زبون Flexy {price_row['price_flexy']} DA\nتاجر Baridi {price_row['price_baridi_trader']} DA | Flexy {price_row['price_flexy_trader']} DA\n\nيمكنك تفعيل أو إيقاف طرق الدفع لهذا العرض فقط.", reply_markup=InlineKeyboardMarkup(price_buttons))

    elif data.startswith("offer_pay_toggle:"):
        if not is_admin(user_id):
            return
        try:
            _, offer_id_text, method_id_text = data.split(":", 2)
            offer_id, method_id = int(offer_id_text), int(method_id_text)
        except (ValueError, TypeError):
            await query.answer("بيانات غير صحيحة.", show_alert=True)
            return
        with db() as conn:
            exists = conn.execute("SELECT 1 FROM offers WHERE id=?", (offer_id,)).fetchone()
            method_row = conn.execute("SELECT id FROM custom_payment_methods WHERE id=?", (method_id,)).fetchone()
            if not exists or not method_row:
                await query.answer("العرض أو طريقة الدفع غير موجودة.", show_alert=True)
                return
            row = conn.execute("SELECT enabled FROM offer_payment_methods WHERE offer_id=? AND method_id=?", (offer_id, method_id)).fetchone()
            new_state = 0 if row and int(row["enabled"] or 0) else 1
            conn.execute("INSERT INTO offer_payment_methods (offer_id, method_id, enabled) VALUES (?, ?, ?) ON CONFLICT(offer_id, method_id) DO UPDATE SET enabled=excluded.enabled", (offer_id, method_id, new_state))
        await query.answer("تم تحديث طريقة الدفع لهذا العرض.")
        # Refresh the offer's price/payment controls
        with db() as conn:
            offer = conn.execute("SELECT name FROM offers WHERE id=?", (offer_id,)).fetchone()
            price_row = conn.execute("SELECT price_baridi, price_flexy, price_baridi_trader, price_flexy_trader, price_usd_trader FROM offers WHERE id=?", (offer_id,)).fetchone()
            custom_methods = conn.execute("SELECT * FROM custom_payment_methods ORDER BY id").fetchall()
            offer_method_states = {int(r["method_id"]): int(r["enabled"] or 0) for r in conn.execute("SELECT method_id, enabled FROM offer_payment_methods WHERE offer_id=?", (offer_id,)).fetchall()}
        price_buttons = [
            [InlineKeyboardButton(f"{'✅' if get_setting(f'offer_payment_baridi_{offer_id}', '1') == '1' else '🚫'} BaridiMob / CCP — {'إيقاف' if get_setting(f'offer_payment_baridi_{offer_id}', '1') == '1' else 'تفعيل'} لهذا العرض", callback_data=f"offer_base_pay_toggle:{offer_id}:baridi")],
            [InlineKeyboardButton(f"{'✅' if get_setting(f'offer_payment_flexy_{offer_id}', '1') == '1' else '🚫'} Flexy — {'إيقاف' if get_setting(f'offer_payment_flexy_{offer_id}', '1') == '1' else 'تفعيل'} لهذا العرض", callback_data=f"offer_base_pay_toggle:{offer_id}:flexy")],
            [InlineKeyboardButton("👤 الزبون — BaridiMob/CCP", callback_data=f"offer_price_one:{offer_id}:price_baridi")],
            [InlineKeyboardButton("🏪 التاجر — BaridiMob/CCP", callback_data=f"offer_price_one:{offer_id}:price_baridi_trader")],
            [InlineKeyboardButton("💵 سعر الدولار للزبون", callback_data=f"offer_price_usd:{offer_id}:price_usd")],
            [InlineKeyboardButton("💵 سعر الدولار للتاجر", callback_data=f"offer_price_usd:{offer_id}:price_usd_trader")],
            [InlineKeyboardButton("✏️ تعديل سعري الزبون والتاجر معًا", callback_data=f"offer_price_all:{offer_id}")],
        ]
        for cm in custom_methods:
            is_on = offer_method_states.get(int(cm["id"]), 1)
            price_buttons.append([InlineKeyboardButton(f"{'✅' if is_on else '🚫'} {cm['emoji']} {cm['name']} — {'إيقاف لهذا العرض' if is_on else 'تفعيل لهذا العرض'}", callback_data=f"offer_pay_toggle:{offer_id}:{cm['id']}")])
        await query.message.reply_text(f"💰 تعديل سعر العرض: {offer['name']}\n\nالأسعار الحالية: زبون Baridi {price_row['price_baridi']} DA | زبون Flexy {price_row['price_flexy']} DA\nتاجر Baridi {price_row['price_baridi_trader']} DA | Flexy {price_row['price_flexy_trader']} DA\n\nيمكنك تفعيل أو إيقاف طرق الدفع المخصصة لهذا العرض:", reply_markup=InlineKeyboardMarkup(price_buttons))

    elif data in ("pay_usd_rate", "pay_usd_sell_rate", "pay_usd_buy_rate"):
        if not is_admin(user_id):
            return
        which = "sell" if data == "pay_usd_sell_rate" else ("buy" if data == "pay_usd_buy_rate" else "sell")
        context.user_data["admin_step"] = f"set_usd_{which}_rate"
        operation = "يضرب في السعر" if which == "sell" else "يقسم على السعر"
        label = "بيع" if which == "sell" else "شراء"
        await query.message.reply_text(f"أرسل سعر {label} الدولار بالدينار الجزائري.\nمثال: 260\nالعملية: {operation}.\nأرسل /cancel للإلغاء.")

    elif data == "custom_pay_add":
        if not is_admin(user_id):
            return
        context.user_data["admin_step"] = "custom_payment_name"
        await query.message.reply_text("أرسل طريقة الدفع بهذا الشكل:\nاسم الطريقة | الإيموجي | USD أو DZD\nمثال: Binance | 🟡 | USD\nثم سأطلب منك تعليمات الدفع. للإلغاء /cancel")

    elif data.startswith("custom_pay_edit:"):
        if not is_admin(user_id):
            return
        try:
            custom_id = int(data.split(":", 1)[1])
        except ValueError:
            await query.answer("معرّف طريقة الدفع غير صحيح.", show_alert=True)
            return
        with db() as conn:
            method_row = conn.execute("SELECT name, instructions FROM custom_payment_methods WHERE id=?", (custom_id,)).fetchone()
        if not method_row:
            await query.answer("طريقة الدفع غير موجودة.", show_alert=True)
            return
        context.user_data["admin_step"] = "custom_payment_edit_instructions"
        context.user_data["pending_custom_payment_edit_id"] = custom_id
        await query.message.reply_text(
            f"✏️ تعليمات الدفع لطريقة {method_row['name']} الحالية:\n{method_row['instructions'] or 'غير محددة'}\n\n"
            "أرسل التعليمات الجديدة (رقم الحساب أو العنوان أو خطوات الدفع). أرسل /cancel للإلغاء."
        )
        await query.answer()

    elif data == "usd_pay_toggle_all":
        if not is_admin(user_id):
            return
        new_state = "0" if get_setting("usd_payments_enabled", "0") == "1" else "1"
        set_setting("usd_payments_enabled", new_state)
        # All USD methods are controlled as one group; no per-method enable/disable is needed.
        with db() as conn:
            usd_methods = conn.execute("SELECT id FROM custom_payment_methods WHERE upper(currency)='USD'").fetchall()
            conn.execute("UPDATE custom_payment_methods SET enabled=? WHERE upper(currency)='USD'", (int(new_state),))
            # The global switch also sets every USD method ON/OFF for every offer.
            offers = conn.execute("SELECT id FROM offers").fetchall()
            for method_row in usd_methods:
                for offer_row in offers:
                    conn.execute(
                        "INSERT INTO offer_payment_methods (offer_id, method_id, enabled) VALUES (?, ?, ?) "
                        "ON CONFLICT(offer_id, method_id) DO UPDATE SET enabled=excluded.enabled",
                        (int(offer_row["id"]), int(method_row["id"]), int(new_state)),
                    )
        await query.answer("تم إخفاء جميع طرق الدولار في كل العروض." if new_state == "0" else "تم تفعيل جميع طرق الدولار في كل العروض.")
        await admin_payment_settings(query)

    elif data.startswith("custom_pay_info:"):
        if not is_admin(user_id):
            return
        try:
            custom_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        with db() as conn:
            method = conn.execute("SELECT name, currency, instructions FROM custom_payment_methods WHERE id=?", (custom_id,)).fetchone()
        if not method:
            await query.answer("طريقة الدفع غير موجودة.", show_alert=True)
            return
        await query.answer()
        await query.message.reply_text(f"💳 {method['name']} ({method['currency']})\n\n{method['instructions'] or 'لم تتم إضافة تعليمات بعد.'}")

    elif data.startswith("custom_pay_toggle:"):
        if not is_admin(user_id):
            return
        try:
            custom_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        with db() as conn:
            row = conn.execute("SELECT enabled, currency FROM custom_payment_methods WHERE id=?", (custom_id,)).fetchone()
            if not row:
                await query.answer("طريقة الدفع غير موجودة.", show_alert=True)
                return
            if (row["currency"] or "USD").upper() == "USD":
                await query.answer("طرق الدولار تُدار كلها من الزر الجماعي.", show_alert=True)
                return
            conn.execute("UPDATE custom_payment_methods SET enabled=? WHERE id=?", (0 if int(row["enabled"] or 0) else 1, custom_id))
        await admin_payment_settings(query)

    # تشغيل/إخفاء طرق الدفع للزبائن
    elif data.startswith("pay_toggle:"):
        method = data.split(":", 1)[1]
        if method not in ("baridi", "flexy"):
            return
        key = f"payment_{method}_enabled"
        current = get_setting(key, "1") == "1"
        new_state = "0" if current else "1"
        set_setting(key, new_state)
        # جماعيًا: إعادة ضبط حالة هذه الطريقة في كل العروض إلى الحالة الجديدة.
        with db() as conn:
            offer_ids = conn.execute("SELECT id FROM offers").fetchall()
        for offer_row in offer_ids:
            set_setting(f"offer_payment_{method}_{int(offer_row['id'])}", new_state)
        await query.answer("تم إيقاف الطريقة في جميع العروض." if new_state == "0" else "تم تفعيل الطريقة في جميع العروض.")
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
                          o.currency, o.shipping_receipt_file_id, o.shipping_receipt_file_ids, o.completion_message,
                          g.name AS game_name, f.name AS offer_name
                   FROM orders o
                   LEFT JOIN games g ON g.id = o.game_id
                   LEFT JOIN offers f ON f.id = o.offer_id
                   WHERE o.id = ?""",
                (order_id,),
            ).fetchone()

            if not order:
                await edit_query_message(query, 
                    "❌ الطلب غير موجود."
                )
                return

            customer_id = order["user_id"]
            # Rewards are granted only once, on the first transition to completed.
            if new_status == "completed" and order["status"] != "completed" and not int(order["points_awarded"] or 0):
                amount = max(0.0, float(order["price"] or 0))
                account_row = conn.execute("SELECT account_type FROM users WHERE user_id=?", (customer_id,)).fetchone()
                reward_multiplier = 0.5 if account_row and account_row["account_type"] == "trader" else 1.0
                reward_points_granted = amount * reward_multiplier
                if str(order["currency"] or "DA").upper() == "USD":
                    conn.execute("UPDATE users SET points_usd=COALESCE(points_usd,0)+? WHERE user_id=?", (reward_points_granted, customer_id))
                else:
                    conn.execute("UPDATE users SET points_da=COALESCE(points_da,0)+? WHERE user_id=?", (reward_points_granted, customer_id))
                conn.execute("UPDATE orders SET points_awarded = 1 WHERE id = ?", (order_id,))
            # Refund wallet balance and redeemed points if an order is rejected.
            if new_status == "rejected" and order["status"] != "rejected":
                if int(order["wallet_charged"] or 0) and not int(order["wallet_refunded"] or 0):
                    refund_col = "balance_usd" if str(order["currency"] or "DA").upper() == "USD" else "balance"
                    conn.execute(f"UPDATE users SET {refund_col} = {refund_col} + ?, points = points + ? WHERE user_id = ?", (float(order["price"] or 0) if refund_col == "balance_usd" else int(order["price"] or 0), int(order["points_used"] or 0), customer_id))
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
                f"💰 المبلغ: {format_order_amount(order['price'], order['currency'])}\n"
                f"💳 طريقة الدفع: {payment_method}\n\n"
                "✅ تم إتمام طلبك بنجاح.\n"
                + (f"\n📝 رسالة من فريق الشحن:\n{order['completion_message']}\n" if order["completion_message"] else "")
                + (f"🎁 تمت إضافة {reward_points_granted} نقطة مكافأة إلى حسابك.\n" if reward_points_granted else "")
                + "❤️ شكراً لثقتك بـ SERADJ STORE!"
            )
        elif new_status == "rejected":
            customer_notice = (
                f"❌ تم إلغاء/رفض طلبك\n\n"
                f"🔢 رقم الطلب: {order_ref}\n"
                f"🎮 اللعبة: {game_name}\n"
                f"📦 العرض: {offer_name}\n"
                f"💰 المبلغ: {format_order_amount(order['price'], order['currency'])}\n"
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
                receipt_file_ids = context.user_data.pop(f"order_receipt_photos:{order_id}", None)
                if not receipt_file_ids:
                    try:
                        receipt_file_ids = json.loads(order["shipping_receipt_file_ids"] or "[]")
                    except Exception:
                        receipt_file_ids = []
                if not receipt_file_ids:
                    receipt_file_id = context.user_data.pop(f"order_receipt_photo:{order_id}", None) or order["shipping_receipt_file_id"]
                    receipt_file_ids = [receipt_file_id] if receipt_file_id else []
                if len(receipt_file_ids) > 1:
                    media = [InputMediaPhoto(media=fid, caption=customer_notice if i == 0 else None) for i, fid in enumerate(receipt_file_ids[:10])]
                    await context.bot.send_media_group(chat_id=customer_id, media=media)
                    await context.bot.send_message(chat_id=customer_id, text="🚀 شكراً لثقتك في SERADJ STORE!", reply_markup=cta_markup or main_keyboard(customer_id))
                elif receipt_file_ids:
                    await context.bot.send_photo(chat_id=customer_id, photo=receipt_file_ids[0], caption=customer_notice,
                                                 reply_markup=cta_markup or main_keyboard(customer_id))
                else:
                    await context.bot.send_message(chat_id=customer_id, text=customer_notice,
                                                   reply_markup=cta_markup or main_keyboard(customer_id))
            else:
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=customer_notice,
                    reply_markup=main_keyboard(customer_id),
                )
        except Exception:
            logger.exception("تعذر إرسال تحديث الطلب أو زر الشحن إلى الزبون (ID=%s)", customer_id)

        # Publish a generic successful-order example to the configured channel.
        # Always use the regular customer price, including orders placed by traders.
        if new_status == "completed" and order["status"] != "completed" and get_setting("order_channel_enabled", "0") == "1":
            channel_id = get_setting("order_channel_id", "").strip()
            if channel_id:
                try:
                    # Offers store retail prices separately by payment method; there is no
                    # generic offers.price column. Always publish the regular customer price,
                    # even when the completed order belongs to a trader.
                    payment_key = str(order["payment_method"] or "").strip().lower()
                    if any(token in payment_key for token in ("flexy", "جيزي", "جازي", "mobilis", "موبيليس", "ooredoo", "اوريدو", "أوريدو")):
                        retail_price_column = "price_flexy"
                    else:
                        retail_price_column = "price_baridi"
                    with db() as conn:
                        price_row = conn.execute(
                            f"SELECT {retail_price_column} AS retail_price FROM offers WHERE id = ?",
                            (order["offer_id"],),
                        ).fetchone() if order["offer_id"] else None
                    public_price = int(price_row["retail_price"] or 0) if price_row else int(order["price"] or 0)
                    channel_text = (
                        "🎉 تم إكمال طلبك بنجاح!\n\n"
                        f"🔢 رقم الطلب: {order_ref}\n"
                        f"🎮 اللعبة: {game_name}\n"
                        f"📦 العرض: {offer_name}\n"
                        f"💰 المبلغ: {public_price:,} DA\n"
                        f"💳 طريقة الدفع: {payment_method}\n\n"
                        "✅ تم إتمام طلبك بنجاح.\n"
                        + (f"🎁 تمت إضافة {reward_points_granted} نقطة مكافأة إلى حسابك.\n" if reward_points_granted else "")
                        + "❤️ شكراً لثقتك بـ SERADJ STORE!"
                    )
                    # The channel CTA opens the store bot directly; no customer data is published.
                    bot_username = get_setting("bot_username", "").strip().lstrip("@")
                    if not bot_username:
                        me = await context.bot.get_me()
                        bot_username = (me.username or "").strip().lstrip("@")
                        if bot_username:
                            set_setting("bot_username", bot_username)
                    channel_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 اشحن وانطلق!", url=f"https://t.me/{bot_username}")]
                    ]) if bot_username else None
                    await context.bot.send_message(
                        chat_id=channel_id, text=channel_text, reply_markup=channel_markup
                    )
                except Exception:
                    logger.exception("تعذر نشر الطلب المكتمل في قناة المتجر")

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
                        f"💰 المبلغ: {format_order_amount(order['price'], order['currency'])}\n"
                        f"💳 الدفع: {payment_method}\n"
                        f"📌 الحالة الجديدة: {status_text}"
                    ),
                )
            except Exception:
                logger.exception("تعذر إرسال إشعار تحديث الطلب إلى الإدارة")

        if group_order_terminal_action:
            try:
                await edit_query_message(query, 
                    f"{'✅ الطلب مكتمل' if new_status == 'completed' else '❌ الطلب ملغي'} — الطلب #{order_id}"
                )
            except Exception:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                    await query.message.reply_text(
                        f"{'✅ الطلب مكتمل' if new_status == 'completed' else '❌ الطلب ملغي'} — الطلب #{order_id}"
                    )
                except Exception:
                    logger.exception("Could not update group order message for order %s", order_id)
        else:
            await admin_order_details(query, order_id)

    # عرض قائمة الأسعار حسب طريقة الدفع
    elif data.startswith("price_view:"):
        parts = data.split(":")
        if len(parts) != 5 or parts[2] not in ("baridi", "flexy", "usd"):
            return
        try:
            game_id, method_id = int(parts[1]), int(parts[4])
        except ValueError:
            return
        platform = parts[3] if parts[3] in ("android", "ios") else None
        # Legacy price-view buttons are retired; return customers to the wallet-price catalogue.
        if not is_trader(query.from_user.id):
            await open_game(query, game_id, platform, method_id, "wallet_da")
        else:
            await open_game(query, game_id, platform, method_id, "wallet_da")

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
            await edit_query_message(query, "❌ هذا الخيار متاح لشحن TikTok فقط.")
            return
        context.user_data["tiktok_custom_request"] = {
            "game_id": game_id,
            "method_id": method_id,
            "platform": parts[3] if parts[3] in ("android", "ios") else "",
        }
        context.user_data["awaiting_tiktok_custom_amount"] = True
        tiktok_min, tiktok_max = tiktok_quantity_limits()
        await edit_query_message(query, 
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
            await edit_query_message(query, "❌ انتهت جلسة الطلب. ارجع للمتجر وابدأ من جديد.")
            return
        rate_method = "flexy" if method == "flexy" else "baridi"
        price_per_coin = tiktok_coin_price(rate_method, query.from_user.id)
        total = (price_per_coin * Decimal(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if price_per_coin <= 0 or total <= 0:
            await edit_query_message(query, "❌ سعر TikTok لهذه الفئة وطريقة الدفع غير مضبوط. تواصل مع الإدارة.")
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
                await edit_query_message(query, f"❌ رصيد محفظتك غير كافٍ.\nالسعر: {price} DA\nرصيدك: {balance} DA\n\nاختر BaridiMob / CCP أو Flexy، أو عبّئ محفظتك.")
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
        await edit_query_message(query, 
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
        if len(parts) not in (3, 4, 5):
            return
        try:
            game_id = int(parts[1])
            offer_id = int(parts[2])
        except ValueError:
            return
        platform = parts[3] if len(parts) >= 4 and parts[3] != "none" else None
        price_mode = parts[4] if len(parts) == 5 and parts[4] in ("baridi", "flexy", "usd", "trader_da", "trader_usd", "wallet_da") else "choose"
        context.user_data["selected_platform"] = platform or ""
        context.user_data["selected_price_mode"] = price_mode
        await open_offer(query, game_id, offer_id, platform, context, price_mode)

    # اختيار طريقة دفع تسديد القرض
    elif data.startswith("credit_repay_method:"):
        method = data.split(":", 1)[1]
        if method not in ("baridi", "flexy"):
            return
        context.user_data["credit_repay_method"] = "BaridiMob / CCP" if method == "baridi" else "Flexy"
        context.user_data["awaiting_credit_receipt"] = True
        details = get_setting("baridi_details" if method == "baridi" else "flexy_details", "تواصل مع الإدارة لمعرفة معلومات الدفع.")
        await edit_query_message(query, f"💳 معلومات الدفع لتسديد القرض:\n{details}\n\nالمبلغ: {context.user_data.get('credit_repay_amount', 0)} DA\n📸 أرسل صورة وصل الدفع. لن ينقص الدين حتى توافق الإدارة.")

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

    # Scheduled broadcast creation and feedback review
    if data == "scheduled_broadcast_confirm":
        if not is_admin(user_id):
            await query.answer("غير مسموح", show_alert=True); return
        body = context.user_data.get("pending_scheduled_text", "").strip()
        due = context.user_data.get("pending_scheduled_due", "").strip()
        if not body or not due:
            await query.answer("المعلومات ناقصة", show_alert=True); return
        entities_json = json.dumps(context.user_data.get("pending_scheduled_entities", []), ensure_ascii=False)
        with db() as conn:
            conn.execute("INSERT INTO scheduled_broadcasts(message,entities_json,due_at,created_at) VALUES(?,?,?,?)", (body, entities_json, due, now_text()))
        context.user_data.pop("pending_scheduled_text", None); context.user_data.pop("pending_scheduled_entities", None); context.user_data.pop("pending_scheduled_due", None); context.user_data.pop("admin_step", None)
        await edit_query_message(query, f"✅ تمت جدولة الإشعار بنجاح.\n📅 الموعد: {due}\nسيُرسل مرة واحدة تلقائيًا.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")]]))
        return
    if data.startswith("feedback_approve:") or data.startswith("feedback_reject:"):
        if not is_admin(user_id):
            await query.answer("غير مسموح", show_alert=True); return
        cid = int(data.split(":",1)[1]); approve = data.startswith("feedback_approve:")
        with db() as conn:
            row = conn.execute("SELECT comment FROM feedback_comments WHERE id=?", (cid,)).fetchone()
            if row:
                conn.execute("UPDATE feedback_comments SET approved=?, published=? WHERE id=?", (1 if approve else 0, 1 if approve else 0, cid))
        if row and approve:
            with db() as conn:
                users = [int(r[0]) for r in conn.execute("SELECT user_id FROM users WHERE COALESCE(is_banned,0)=0").fetchall()]
            for uid in users:
                try: await context.bot.send_message(chat_id=uid, text="💬 رأي أحد زبائن SERADJ STORE (بدون معلومات شخصية):\n\n" + row['comment'])
                except Exception: pass
        await edit_query_message(query, "✅ تم نشر التعليق بشكل مجهول." if approve else "🗑️ تم رفض التعليق.")
        return
    if data == "feedback_begin":
        context.user_data["feedback_waiting"] = True
        await query.message.reply_text("💬 ابعث رأيك في SERADJ STORE برسالة واحدة. سيتم إرساله للإدارة للمراجعة، ولن يظهر للناس إلا بعد الموافقة، وبدون أي معلومات عنك.")
        return
    if data == "feedback_review":
        if not is_admin(user_id): await query.answer("غير مسموح", show_alert=True); return
        with db() as conn:
            rows = conn.execute("SELECT id,comment,created_at FROM feedback_comments WHERE approved=0 ORDER BY id DESC LIMIT 30").fetchall()
        if not rows:
            await edit_query_message(query, "لا توجد تعليقات تنتظر المراجعة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")]])); return
        for row in rows:
            await query.message.reply_text("💬 تعليق للمراجعة (مجهول):\n\n" + row['comment'] + "\n\n" + str(row['created_at']), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ موافقة ونشر مجهول", callback_data=f"feedback_approve:{row['id']}"), InlineKeyboardButton("❌ رفض", callback_data=f"feedback_reject:{row['id']}")]]))
        return

    # اختيار وجهة الإشعار الجماعي
    elif data.startswith("notify_target:"):
        if not is_admin(user_id):
            await query.answer("غير مسموح", show_alert=True); return
        target = data.split(":", 1)[1]
        if target not in ("users", "channel", "both"):
            await query.answer("اختيار غير صالح", show_alert=True); return
        context.user_data["pending_broadcast_target"] = target
        context.user_data.pop("admin_step", None)
        channel_id = get_setting("broadcast_channel_id", "").strip()
        if target in ("channel", "both") and not channel_id:
            context.user_data["admin_step"] = "broadcast_channel_id"
            await query.message.reply_text(
                "📢 أرسل @username القناة أو ID القناة (مثال: -1001234567890).\\n"
                "تأكد أن البوت مسؤول في القناة ويملك صلاحية نشر الرسائل."
            )
            return
        await query.message.reply_text(
            "📨 معاينة الإشعار:\\n\\n" + context.user_data.get("pending_broadcast_text", ""),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="notify_broadcast_confirm")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="notify_cancel")]
            ])
        )
        return

    # تأكيد إرسال إشعار
    elif data == "notify_broadcast_confirm":
        broadcast_text = context.user_data.get("pending_broadcast_text", "")
        if not broadcast_text:
            await query.answer("ما كاين حتى نص للإرسال", show_alert=True)
            return
        target = context.user_data.get("pending_broadcast_target", "users")
        with db() as conn:
            recipients = [int(r[0]) for r in conn.execute(
                "SELECT user_id FROM users WHERE COALESCE(is_banned,0)=0"
            ).fetchall()] if target in ("users", "both") else []
        channel_id = get_setting("broadcast_channel_id", "").strip()
        sent = failed = 0
        failure_details = []
        raw_entities = context.user_data.get("pending_broadcast_entities", [])
        from telegram import MessageEntity
        from telegram.error import Forbidden, BadRequest, RetryAfter, NetworkError, TimedOut
        prefix = "📢 إشعار من SERADJ STORE:\n\n"
        # Telegram entity offsets use UTF-16 code units, not Python character count.
        prefix_utf16_len = len(prefix.encode("utf-16-le")) // 2
        buttons = context.user_data.get("pending_broadcast_buttons", [])
        # Callback buttons are converted to bot deep links. Telegram opens the bot
        # privately, then /start dispatches the chosen navigation callback there.
        bot_username = (await context.bot.get_me()).username
        keyboard_rows = []
        for b in buttons:
            if "url" in b:
                button = InlineKeyboardButton(b["text"], url=b["url"])
            else:
                raw_target = b["callback_data"]
                encoded_target = base64.urlsafe_b64encode(raw_target.encode("utf-8")).decode("ascii").rstrip("=")
                start_payload = "nav_" + encoded_target
                if len(start_payload) > 64:
                    raise ValueError(f"وجهة الزر طويلة ولا يمكن تحويلها إلى رابط بوت: {raw_target}")
                button = InlineKeyboardButton(b["text"], url=f"https://t.me/{bot_username}?start={start_payload}")
            keyboard_rows.append([button])
        keyboard = InlineKeyboardMarkup(keyboard_rows) if keyboard_rows else None
        for recipient in recipients:
            try:
                kwargs = {}
                if raw_entities:
                    kwargs["entities"] = [
                        MessageEntity.de_json({**item, "offset": int(item.get("offset", 0)) + prefix_utf16_len}, context.bot)
                        for item in raw_entities
                    ]
                broadcast_photo = context.user_data.get("pending_broadcast_photo_file_id")
                if broadcast_photo:
                    caption_text = prefix + broadcast_text
                    if len(caption_text) <= 1024:
                        await context.bot.send_photo(chat_id=recipient, photo=broadcast_photo,
                            caption=caption_text, reply_markup=keyboard)
                    else:
                        await context.bot.send_photo(chat_id=recipient, photo=broadcast_photo)
                        await context.bot.send_message(chat_id=recipient, text=caption_text,
                            reply_markup=keyboard, **kwargs)
                else:
                    await context.bot.send_message(chat_id=recipient, text=prefix + broadcast_text,
                        reply_markup=keyboard, **kwargs)
                sent += 1
            except Exception as exc:
                failed += 1
                if isinstance(exc, Forbidden):
                    reason = "البوت محظور أو لا يستطيع مراسلة المستخدم"
                elif isinstance(exc, RetryAfter):
                    reason = f"حدّ مؤقت للإرسال (انتظر {getattr(exc, 'retry_after', '?')} ثانية)"
                elif isinstance(exc, BadRequest):
                    reason = f"رفض تيليغرام الطلب: {str(exc)[:180]}"
                elif isinstance(exc, (NetworkError, TimedOut)):
                    reason = f"مشكلة شبكة/مهلة: {str(exc)[:180]}"
                else:
                    reason = f"{type(exc).__name__}: {str(exc)[:180]}"
                failure_details.append((recipient, reason))
                logger.warning("Broadcast failed for user_id=%s: %s: %s", recipient, type(exc).__name__, exc)
        if target in ("channel", "both"):
            try:
                if not channel_id:
                    raise ValueError("لم يتم ضبط قناة النشر")
                broadcast_photo = context.user_data.get("pending_broadcast_photo_file_id")
                if broadcast_photo:
                    if len(broadcast_text) <= 1024:
                        await context.bot.send_photo(chat_id=channel_id, photo=broadcast_photo,
                            caption=broadcast_text, reply_markup=keyboard)
                    else:
                        await context.bot.send_photo(chat_id=channel_id, photo=broadcast_photo)
                        await context.bot.send_message(chat_id=channel_id, text=broadcast_text, reply_markup=keyboard)
                else:
                    source_chat_id = context.user_data.get("pending_broadcast_source_chat_id")
                    source_message_id = context.user_data.get("pending_broadcast_source_message_id")
                    if source_chat_id and source_message_id:
                        await context.bot.copy_message(chat_id=channel_id, from_chat_id=source_chat_id,
                            message_id=source_message_id, reply_markup=keyboard)
                    else:
                        kwargs = {"entities": [MessageEntity.de_json(item, context.bot) for item in raw_entities]} if raw_entities else {}
                        await context.bot.send_message(chat_id=channel_id, text=broadcast_text, reply_markup=keyboard, **kwargs)
                sent += 1
            except Exception as exc:
                failed += 1
                failure_details.append(("القناة", f"{type(exc).__name__}: {str(exc)[:180]}"))
                logger.exception("Channel broadcast failed")
        for key in ("pending_broadcast_text", "pending_broadcast_entities", "pending_broadcast_buttons", "pending_broadcast_target", "pending_broadcast_source_chat_id", "pending_broadcast_source_message_id", "pending_broadcast_photo_file_id"):
            context.user_data.pop(key, None)
        context.user_data.pop("admin_step", None)
        summary = f"✅ انتهى إرسال الإشعار.\nوصل إلى: {sent}\nتعذّر الإرسال إلى: {failed}"
        if failure_details:
            summary += "\n\n🔎 تفاصيل أول 15 حالة فشل:\n" + "\n".join(
                f"• ID {uid}: {reason}" for uid, reason in failure_details[:15]
            )
            if len(failure_details) > 15:
                summary += f"\n... وهناك {len(failure_details) - 15} حالات أخرى. راجع سجلات FadeHost للتفاصيل."
        await edit_query_message(query, 
            summary,
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

            await edit_query_message(query, 
                "✅ تم إرسال الإشعار إلى الزبون بنجاح."
            )

        except Exception:
            logger.exception(
                "فشل إرسال إشعار الزبون"
            )

            await edit_query_message(query, 
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

        await edit_query_message(query, 
            "❌ تم إلغاء إرسال الإشعار."
        )

    # التنقل داخل المتجر: الرجوع إلى قائمة الألعاب/التطبيقات أو المستوى السابق.
    elif data in ("back_games", "back_apps") or data.startswith("store_list_page:"):
        if data.startswith("store_list_page:"):
            _, category, raw_page = data.split(":", 2)
            if category == "noop": return
            page = max(0, int(raw_page))
        else:
            category = "app" if data == "back_apps" else "game"
            page = 0
        per_page = 8
        with db() as conn:
            if category == "app":
                where = "(lower(trim(COALESCE(category,'')))='app' OR lower(trim(name)) IN ('tiktok','tik tok','snapchat+','snapchat plus','netflix','azar','app store','apple store','telegram premium','telegram','spotify','youtube premium','youtube','instagram','facebook','discord','capcut','chatgpt','canva','shahid','osn+','crunchyroll','imo','tinder','truecaller','google play','google play gift card'))"
            else:
                where = "COALESCE(NULLIF(trim(category),''),'game')='game'"
            total = int(conn.execute(f"SELECT COUNT(*) FROM games WHERE active=1 AND {where}").fetchone()[0])
            rows = conn.execute(f"SELECT * FROM games WHERE active=1 AND {where} ORDER BY id LIMIT ? OFFSET ?", (per_page, page*per_page)).fetchall()
        if not rows:
            await edit_query_message(query, "😕 لا توجد خدمات في هذا القسم حالياً.")
            return
        pages = max(1, (total + per_page - 1)//per_page)
        if page >= pages: page = pages - 1
        buttons = [[InlineKeyboardButton(game_button_label(g), callback_data=f"game:{g['id']}", **premium_button_kwargs(g['id']))] for g in rows]
        nav=[]
        if page > 0: nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"store_list_page:{category}:{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="store_list_page:noop:0"))
        if page+1 < pages: nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"store_list_page:{category}:{page+1}"))
        if nav: buttons.append(nav)
        buttons.append([InlineKeyboardButton("🔙 الأقسام", callback_data="back_main")])
        title = "🎮 قائمة الألعاب" if category == "game" else "📱 قائمة التطبيقات"
        await edit_query_message(query, f"{title} — {total} خدمة", reply_markup=InlineKeyboardMarkup(buttons))
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
        await edit_query_message(query, "اختر من القائمة الرئيسية: الألعاب أو التطبيقات.")
    elif data == "back_main":
        await edit_query_message(query, "القائمة الرئيسية:", reply_markup=main_keyboard(user_id))

    # إلغاء أو رجوع عام
    elif data == "cancel":
        context.user_data.pop("admin_step", None)
        context.user_data.pop("pending_game_id", None)
        context.user_data.pop("pending_offer_id", None)
        context.user_data.pop(
            "pending_payment_method", None
        )

        await edit_query_message(query, 
            "تم إلغاء العملية."
        )

# =========================
# معالجة رسائل الإدارة والزبائن
# =========================

def flexy_parse_sms(text):
    """Accept supported Djezzy 700 recharge notices; return amount or None."""
    raw = (text or "").strip()
    if not raw:
        return None

    # Ignore Djezzy offer-activation notices; they are not Flexy recharges.
    # Example: "Vous avez recu : 1500 DA pour activation de votre Offre."
    if re.search(r"pour\s+activation\s+de\s+votre\s+offre", raw, re.IGNORECASE):
        return None

    # SMS Bot may forward either of these Djezzy confirmation formats.
    body_pattern = re.compile(
        r"(?:Vous\s+venez\s+de\s+recharger|Vous\s+avez\s+Re[cç]u)"
        r"\s*:?\s*([0-9][0-9\s.,]*)\s*DA\b",
        re.IGNORECASE,
    )
    match = body_pattern.search(raw)
    if not match:
        return None

    # Accept the Djezzy sender code 700 or the configured sender phone number
    # in the forwarded header, before the SMS body.
    header = raw[:match.start()]
    sender_code_found = bool(re.search(r"(?<!\d)700(?!\d)", header))
    sender_phone_found = "+213656609796" in re.sub(r"[\s()-]", "", header)
    if not (sender_code_found or sender_phone_found):
        return None

    amount_text = re.sub(r"\s+", "", match.group(1)).replace(",", ".")
    try:
        amount = Decimal(amount_text)
        return amount if amount > 0 else None
    except InvalidOperation:
        return None


async def flexy_admin_panel(message):
    percent = get_setting("flexy_deduction_percent", "0")
    channel = get_setting("flexy_channel_id", "")
    with db() as conn:
        rows = conn.execute("SELECT slot,user_id,active,balance FROM flexy_subscribers ORDER BY slot").fetchall()
    active_count = sum(1 for r in rows if r["active"])
    body = ("💳 إدارة الفليكسي\n\n"
            f"📉 نسبة الاقتطاع الحالية: {percent}%\n"
            f"📢 قناة التعبئات: {channel or 'غير معيّنة'}\n"
            f"👥 المشتركين المعرّفين: {len(rows)} | النشطين: {active_count}\n\n"
            "اختر العملية:")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📉 تعديل نسبة الاقتطاع", callback_data="flexy_set_percent")],
        [InlineKeyboardButton("📢 تعيين قناة التعبئات", callback_data="flexy_set_channel_help")],
        [InlineKeyboardButton("👥 إدارة المشتركين 1-10", callback_data="flexy_subscribers")],
        [InlineKeyboardButton("💰 الأرصدة والسجل", callback_data="flexy_balances")],
        [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="adm_home")],
    ])
    await message.reply_text(body, reply_markup=keyboard)


async def flexy_receive_sms(update, context):
    """Process SMS notices posted in the configured source channel/group."""
    msg = update.effective_message
    chat = update.effective_chat
    logger.info("Flexy: update received update_id=%s channel_post=%s edited_channel_post=%s chat_id=%s",
                getattr(update, "update_id", None), bool(getattr(update, "channel_post", None)),
                bool(getattr(update, "edited_channel_post", None)), getattr(chat, "id", None))
    if not msg or not chat or chat.type not in ("group", "supergroup", "channel"):
        return False

    raw_text = msg.text or msg.caption or ""
    configured_source = get_setting("flexy_sms_source_chat_id", "").strip()
    if not configured_source:
        logger.warning("Flexy: source chat is not configured; received chat_id=%s", chat.id)
        return False
    if str(chat.id) != configured_source:
        logger.info("Flexy: ignored post from unconfigured chat_id=%s (configured=%s)", chat.id, configured_source)
        return False

    amount = flexy_parse_sms(raw_text)
    if amount is None:
        logger.info("Flexy: source post did not match recharge format. chat_id=%s message_id=%s text=%r", chat.id, msg.message_id, raw_text[:500])
        await send_system_log(context.bot, f"⚠️ منشور SMS لم يطابق صيغة التعبئة.\nالقناة: {chat.id}\nرقم المنشور: {msg.message_id}\nالنص: {raw_text[:500]}", "WARNING")
        return False

    channel_id = get_setting("flexy_channel_id", "").strip()
    if not channel_id:
        logger.error("Flexy: SMS matched but output channel is not configured")
        return True

    # Prefer the original SMS timestamp in the forwarded header (for example,
    # "💬 700 🕒 10:48 - djezzy ...") instead of Telegram's delayed arrival time.
    received_at = datetime.now(STORE_TZ)
    sms_time_match = re.search(r"🕒\s*(\d{1,2}):(\d{2})", raw_text)
    if sms_time_match:
        sms_hour, sms_minute = map(int, sms_time_match.groups())
        if 0 <= sms_hour <= 23 and 0 <= sms_minute <= 59:
            event_at = received_at.replace(hour=sms_hour, minute=sms_minute, second=0, microsecond=0)
        else:
            event_at = received_at
    else:
        # Older SMS forward formats may not include the original time.
        event_at = received_at
    created = event_at.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with db() as conn:
            existing_event = conn.execute(
                "SELECT id,status,gross_amount FROM flexy_sms_events WHERE source_chat_id=? AND source_message_id=?",
                (chat.id, msg.message_id),
            ).fetchone()
            if existing_event and existing_event["status"] != "pending":
                logger.info("Flexy: confirmed duplicate ignored chat_id=%s message_id=%s event_id=%s status=%s",
                            chat.id, msg.message_id, existing_event["id"], existing_event["status"])
                await send_system_log(context.bot,
                    f"🔁 تم تجاهل منشور سبق إتمام معالجته.\nالقناة: {chat.id}\nرقم المنشور: {msg.message_id}\nالعملية: {existing_event['id']}\nالحالة: {existing_event['status']}",
                    "WARNING")
                return True
            if existing_event and existing_event["status"] == "pending":
                # A previous run saved the event but may have failed before publishing it.
                # Retry publishing the SAME event; never create a second wallet-credit event.
                event_id = existing_event["id"]
                amount = Decimal(str(existing_event["gross_amount"]))
                logger.warning("Flexy: retrying publication of pending event_id=%s chat_id=%s message_id=%s",
                               event_id, chat.id, msg.message_id)
                await send_system_log(context.bot,
                    f"♻️ إعادة نشر تعبئة معلّقة لم تصل للقناة سابقًا أو لم يُؤكّد نشرها.\nالعملية: {event_id}\nرقم المنشور: {msg.message_id}\nالمبلغ: {amount:g} DA",
                    "WARNING")
            else:
                cur = conn.execute("""INSERT INTO flexy_sms_events
                    (source_chat_id,source_message_id,sender,gross_amount,message_text,created_at)
                    VALUES(?,?,?,?,?,?)""", (chat.id, msg.message_id, "700", float(amount), raw_text, created))
                event_id = cur.lastrowid
            subscribers = conn.execute("SELECT slot,display_name FROM flexy_subscribers WHERE active=1 AND user_id IS NOT NULL ORDER BY slot").fetchall()
        buttons = []
        for r in subscribers:
            slot = r["slot"]
            display_name = (r["display_name"] or "").strip() or f"المشترك {slot}"
            buttons.append([InlineKeyboardButton(display_name, callback_data=f"flexy_credit:{event_id}:{slot}")])
        if not buttons:
            buttons = [[InlineKeyboardButton("لا يوجد مشترك نشط", callback_data="flexy_noop")]]
        await context.bot.send_message(chat_id=int(channel_id),
            text=(f"📥 تعبئة فليكسي جديدة\n\n💰 المبلغ: {amount} DA\n🕒 التاريخ والوقت: {created}\n\nاختر المشترك لإضافة الرصيد إليه:"),
            reply_markup=InlineKeyboardMarkup(buttons))
        logger.info("Flexy: published event_id=%s amount=%s to channel_id=%s", event_id, amount, channel_id)
        await send_system_log(context.bot, f"📥 تم التعرف على تعبئة Flexy ونشرها.\nالمبلغ: {amount} DA\nرقم المنشور: {msg.message_id}\nمعرّف العملية: {event_id}", "SUCCESS")
    except Exception as exc:
        logger.exception("Flexy SMS processing/publishing failed")
        await send_system_log(context.bot, f"❌ فشل معالجة/نشر تعبئة Flexy.\nرقم المنشور: {msg.message_id}\nالخطأ: {str(exc)[:900]}", "ERROR")
    return True


async def set_flexy_source_command(update, context):
    user = update.effective_user
    if not user or not is_admin(user.id):
        return
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        set_setting("flexy_sms_source_chat_id", str(chat.id))
        await update.effective_message.reply_text("✅ تم ربط هذه المجموعة كمصدر رسائل SMS لنظام الفليكسي.")
        return
    if chat and chat.type == "private":
        context.user_data["flexy_admin_step"] = "source"
        await update.effective_message.reply_text("حوّل (Forward) رسالة SMS منشورة من قناة SMS إلى هنا، وسأحفظ معرّف القناة كمصدر للتعبئات. لا ترسل رسالة عادية.")
        return
    await update.effective_message.reply_text("استعمل الأمر في الخاص مع البوت ثم حوّل إليه رسالة من قناة SMS، أو استعمله داخل مجموعة SMS.")


async def set_log_channel_command(update, context):
    user = update.effective_user
    if not user or not is_admin(user.id):
        return
    context.user_data["system_log_channel_setup"] = True
    await update.effective_message.reply_text(
        "حوّل (Forward) أي منشور من قناة السجلات الخاصة إلى هنا.\n"
        "سأحفظ معرّف القناة وأرسل رسالة اختبار. تأكد أن البوت مشرف في القناة وله صلاحية النشر.\n"
        "للإلغاء أرسل /cancel."
    )


async def flexy_command(update, context):
    user = update.effective_user
    if not user:
        return
    if is_admin(user.id):
        await flexy_admin_panel(update.effective_message)
        return
    with db() as conn:
        row=conn.execute("SELECT slot,balance,active FROM flexy_subscribers WHERE user_id=?",(user.id,)).fetchone()
        history=conn.execute("SELECT kind,amount,balance_after,created_at FROM flexy_transactions WHERE user_id=? ORDER BY id DESC LIMIT 10",(user.id,)).fetchall()
    if not row or not row["active"]:
        await update.effective_message.reply_text("لا يوجد حساب فليكسي نشط مرتبط بحسابك. تواصل مع الإدارة.")
        return
    body=f"💳 محفظة الفليكسي — المشترك {row['slot']}\\nرصيدك الحالي: {row['balance']:g} DA\\n\\nآخر العمليات:\\n"
    body += "\\n".join(f"{r['created_at']} | {r['kind']} {r['amount']:g} DA | الرصيد {r['balance_after']:g}" for r in history) or "لا توجد عمليات بعد."
    await update.effective_message.reply_text(body)


async def text_handler(update, context):
    message = update.effective_message
    chat = update.effective_chat
    # Work groups only receive shop orders and shipping receipts. Do not show
    # customer keyboards or answer normal staff conversation with the shop fallback.
    if chat and chat.type in ("group", "supergroup"):
        # Flexy SMS listener is isolated from shop order workflows.
        try:
            await flexy_receive_sms(update, context)
        except Exception:
            logger.exception("Flexy SMS listener failed")
        if update.effective_user and message and context.user_data.get("awaiting_order_completion_text"):
            completion_order_id = int(context.user_data.get("awaiting_order_completion_text"))
            expected_chat = context.user_data.get("order_completion_chat_id")
            if expected_chat and message.chat_id != int(expected_chat):
                await message.reply_text("أرسل نص الإتمام في نفس قروب الطلب.")
                return
            completion_text = (message.text or "").strip()
            if completion_text.lower() == "/cancel":
                context.user_data.pop("awaiting_order_completion_text", None)
                context.user_data.pop("order_completion_chat_id", None)
                await message.reply_text("تم إلغاء كتابة رسالة الإتمام.")
                return
            if len(completion_text) < 2:
                await message.reply_text("اكتب رسالة واضحة من حرفين على الأقل.")
                return
            with db() as conn:
                row = conn.execute("SELECT claimed_by,status FROM orders WHERE id=?", (completion_order_id,)).fetchone()
                if not row or row["status"] in ("completed", "rejected"):
                    context.user_data.pop("awaiting_order_completion_text", None)
                    context.user_data.pop("order_completion_chat_id", None)
                    await message.reply_text("الطلب غير متاح أو تمت معالجته.")
                    return
                if int(row["claimed_by"] or 0) != update.effective_user.id:
                    await message.reply_text("إتمام الطلب برسالة متاح لمستلم الطلب فقط.")
                    return
                conn.execute("UPDATE orders SET completion_message=? WHERE id=?", (completion_text, completion_order_id))
            context.user_data.pop("awaiting_order_completion_text", None)
            context.user_data.pop("order_completion_chat_id", None)
            await message.reply_text(
                f"✅ تم حفظ رسالة الطلب #{completion_order_id}. اضغط لتأكيد الإتمام وإرسالها للزبون:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأكيد الإتمام وإرسال النص", callback_data=f"status:{completion_order_id}:completed")], [InlineKeyboardButton("❌ إلغاء", callback_data=f"order_finish_back:{completion_order_id}")]])
            )
        return
    if not update.effective_user or not message:
        return
    user_id = update.effective_user.id
    text = (message.text or "").strip()
    # Private system-log channel setup: admin forwards a post from the target channel.
    if is_admin(user_id) and context.user_data.get("system_log_channel_setup"):
        origin = getattr(message, "forward_origin", None)
        log_chat = getattr(origin, "chat", None) if origin else getattr(message, "forward_from_chat", None)
        if log_chat and getattr(log_chat, "type", None) == "channel":
            try:
                await context.bot.get_chat_member(log_chat.id, context.bot.id)
                set_setting("system_log_channel_id", str(log_chat.id))
                context.user_data.pop("system_log_channel_setup", None)
                await message.reply_text(f"✅ تم ربط قناة السجلات: {getattr(log_chat, 'title', 'قناة خاصة')}\nسأرسل إليها إشعارات التشغيل والأخطاء المهمة.")
                await send_system_log(context.bot, "🧪 رسالة اختبار: قناة السجلات تعمل بنجاح.", "TEST")
            except Exception as exc:
                await message.reply_text("❌ لم أتمكن من التحقق من القناة. تأكد أن البوت مشرف ويملك صلاحية نشر الرسائل، ثم أعد توجيه منشور منها.\n" + str(exc)[:300])
        else:
            await message.reply_text("❌ حوّل منشورًا مباشرة من قناة السجلات، وليس رابطًا أو نصًا منسوخًا. /cancel للإلغاء.")
        return

    # Set a subscriber's public button label (name only; no emoji).
    if is_admin(user_id) and context.user_data.get("flexy_label_slot") is not None:
        slot = int(context.user_data.get("flexy_label_slot"))
        if text.lower() == "/cancel":
            context.user_data.pop("flexy_label_slot", None)
            await message.reply_text("تم إلغاء تعديل اسم المشترك.")
            return
        display_name = text.strip()
        if len(display_name) < 2:
            await message.reply_text("❌ أرسل اسمًا من حرفين على الأقل.")
            return
        if len(display_name) > 30:
            await message.reply_text("❌ الاسم طويل جدًا. الحد الأقصى 30 حرفًا.")
            return
        with db() as conn:
            conn.execute("INSERT INTO flexy_subscribers(slot,active,display_name,updated_at) VALUES(?,0,?,?) ON CONFLICT(slot) DO UPDATE SET display_name=excluded.display_name,updated_at=excluded.updated_at",
                         (slot, display_name, now_text()))
        context.user_data.pop("flexy_label_slot", None)
        await message.reply_text(f"✅ تم حفظ اسم الزر: {display_name}")
        return

    # Flexy admin setup steps.
    if is_admin(user_id) and context.user_data.get("flexy_admin_step") == "source":
        origin = getattr(message, "forward_origin", None)
        source_chat = getattr(origin, "chat", None) if origin else getattr(message, "forward_from_chat", None)
        if source_chat and getattr(source_chat, "type", None) == "channel":
            set_setting("flexy_sms_source_chat_id", str(source_chat.id))
            context.user_data.pop("flexy_admin_step", None)
            await message.reply_text(f"✅ تم ربط قناة SMS كمصدر للتعبئات: {getattr(source_chat, 'title', 'قناة خاصة')}\nتأكد أن بوت SERADJ STORE مشرف في قناة المصدر.")
        else:
            await message.reply_text("❌ لم أتعرف على القناة. حوّل رسالة مباشرة من قناة SMS (Forward)، وليس نسخًا ولصقًا. /cancel للإلغاء.")
        return
    if is_admin(user_id) and context.user_data.get("flexy_admin_step") == "percent":
        try:
            pct=Decimal(text)
            if pct < 0 or pct > 100: raise ValueError
            set_setting("flexy_deduction_percent", str(pct.normalize()))
            context.user_data.pop("flexy_admin_step",None)
            await message.reply_text(f"✅ تم حفظ نسبة الاقتطاع: {pct.normalize()}%")
        except Exception:
            await message.reply_text("❌ أرسل رقمًا من 0 إلى 100، مثال 15. أو /cancel للإلغاء.")
        return
    if is_admin(user_id) and context.user_data.get("flexy_set_balance_slot") is not None:
        slot = int(context.user_data.get("flexy_set_balance_slot"))
        try:
            new_balance = Decimal(text.replace(",", "."))
            if not new_balance.is_finite() or new_balance < 0:
                raise ValueError
            with db() as conn:
                sub = conn.execute("SELECT user_id,balance FROM flexy_subscribers WHERE slot=?", (slot,)).fetchone()
                if not sub:
                    await message.reply_text("❌ هذا المشترك غير موجود. عيّن المشترك أولًا ثم أعد المحاولة.")
                    context.user_data.pop("flexy_set_balance_slot", None)
                    return
                before = Decimal(str(sub["balance"] or 0))
                after = new_balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                conn.execute(
                    "UPDATE flexy_subscribers SET balance=?,updated_at=? WHERE slot=?",
                    (float(after), now_text(), slot),
                )
                conn.execute(
                    "INSERT INTO flexy_transactions(slot,user_id,kind,amount,balance_before,balance_after,note,admin_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (slot, int(sub["user_id"] or 0), "تعيين رصيد", float(after), float(before), float(after),
                     f"تعيين يدوي من الإدارة إلى {after:g} DA", user_id, now_text()),
                )
            context.user_data.pop("flexy_set_balance_slot", None)
            await message.reply_text(
                f"✅ تم تعيين رصيد المشترك {slot}.\n\n"
                f"الرصيد السابق: {before:g} DA\n"
                f"الرصيد الجديد: {after:g} DA"
            )
            await send_system_log(
                context.bot,
                f"✏️ تعديل يدوي لرصيد Flexy\nالمشترك: {slot}\n"
                f"Telegram ID: {sub['user_id'] or '-'}\n"
                f"الرصيد السابق: {before:g} DA\nالرصيد الجديد: {after:g} DA\n"
                f"بواسطة الإدارة: {user_id}",
                "SUCCESS",
            )
        except (InvalidOperation, ValueError):
            await message.reply_text("❌ أرسل مبلغًا صحيحًا يساوي صفرًا أو أكثر. مثال: 15000 أو 15000.50.\nللإلغاء أرسل /cancel.")
        except Exception as exc:
            logger.exception("Flexy manual balance set failed")
            await message.reply_text("❌ حدث خطأ أثناء تعديل الرصيد. لم يتم تأكيد العملية.")
            await send_system_log(context.bot, f"❌ فشل تعيين رصيد Flexy للمشترك {slot}: {str(exc)[:500]}", "ERROR")
        return
    if is_admin(user_id) and context.user_data.get("flexy_assign_slot") is not None:
        slot=int(context.user_data.pop("flexy_assign_slot"))
        try:
            target=int(text)
            if target < 0: raise ValueError
            with db() as conn:
                if target == 0:
                    conn.execute("INSERT INTO flexy_subscribers(slot,user_id,active,updated_at) VALUES(?,NULL,0,?) ON CONFLICT(slot) DO UPDATE SET user_id=NULL,active=0,updated_at=excluded.updated_at",(slot,now_text()))
                else:
                    conn.execute("INSERT INTO flexy_subscribers(slot,user_id,active,created_at,updated_at) VALUES(?,?,1,?,?) ON CONFLICT(slot) DO UPDATE SET user_id=excluded.user_id,active=1,updated_at=excluded.updated_at",(slot,target,now_text(),now_text()))
            await message.reply_text("✅ تم حفظ تعيين المشترك." if target else "تم إلغاء تعيين المشترك.")
        except Exception:
            await message.reply_text("❌ Telegram ID غير صالح أو مستعمل في خانة أخرى. أعد فتح إدارة الفليكسي وحاول مجددًا.")
        return
    if is_admin(user_id) and context.user_data.get("flexy_admin_step") == "channel":
        origin=getattr(message,"forward_origin",None)
        chat_obj=getattr(origin,"chat",None) if origin else getattr(message,"forward_from_chat",None)
        if chat_obj and getattr(chat_obj,"type",None)=="channel":
            try:
                await context.bot.get_chat_member(chat_obj.id, context.bot.id)
                set_setting("flexy_channel_id",str(chat_obj.id))
                context.user_data.pop("flexy_admin_step",None)
                await message.reply_text(f"✅ تم تعيين قناة الفليكسي: {chat_obj.title}\nتأكد أن البوت مشرف فيها ويملك صلاحية نشر الرسائل.")
            except Exception:
                await message.reply_text("❌ لم أتمكن من التحقق من القناة. أضف البوت مشرفًا فيها ثم أعد توجيه رسالة منها.")
        else:
            await message.reply_text("أرسل رسالة مُعاد توجيهها من القناة نفسها، وليس رابطًا فقط.")
        return
    if context.user_data.pop("feedback_waiting", False):
        if len(text) > 1500:
            context.user_data["feedback_waiting"] = True
            await message.reply_text("التعليق طويل بزاف. اختصره إلى 1500 حرف كحد أقصى.")
            return
        with db() as conn:
            conn.execute("INSERT INTO feedback_comments(user_id,comment,created_at,approved,published) VALUES(?,?,?,0,0)", (update.effective_user.id, text, now_text()))
            cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text="💬 رأي جديد ينتظر الموافقة (هوية المشترك غير معروضة):\n\n" + text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ موافقة ونشر مجهول", callback_data=f"feedback_approve:{cid}"), InlineKeyboardButton("❌ رفض", callback_data=f"feedback_reject:{cid}")]]))
        except Exception:
            logger.exception("تعذر إرسال التعليق للإدارة")
        await message.reply_text("✅ وصل رأيك للإدارة. لن يظهر للناس إلا بعد الموافقة، وسيُنشر بدون اسم أو صورة أو اسم مستخدم.")
        return
    if context.user_data.get("expired_order_checkout") and text not in ("/start", "🛍️ المتجر", "🎮 الألعاب", "📱 التطبيقات"):
        context.user_data.pop("expired_order_checkout", None)
        await message.reply_text("⏰ انتهت مهلة الدفع (15 دقيقة)، وتم إلغاء العملية. ابدأ طلبًا جديدًا من المتجر.", reply_markup=main_keyboard(user_id))
        return

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

    if text == "📢 إعدادات النشر للقناة" and is_admin(user_id):
        enabled = get_setting("order_channel_enabled", "0") == "1"
        channel = get_setting("order_channel_id", "") or "غير محددة"
        await message.reply_text(
            f"📢 إعدادات نشر الطلبات\n\nالقناة الحالية: {channel}\nالنشر: {'مفعّل ✅' if enabled else 'متوقف ⏸️'}\n\nأرسل معرف القناة أو @username لتغييرها في أي وقت.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ تفعيل النشر", callback_data="order_channel_toggle:1"), InlineKeyboardButton("⏸️ إيقاف النشر", callback_data="order_channel_toggle:0")],
                [InlineKeyboardButton("🗑️ حذف القناة", callback_data="order_channel_clear:1")],
            ])
        )
        context.user_data["awaiting_order_channel_id"] = True
        return

    if context.user_data.get("awaiting_order_channel_id") and is_admin(user_id):
        channel_id = text.strip()
        if not (channel_id.startswith("@") or channel_id.lstrip("-").isdigit()):
            await message.reply_text("❌ أرسل @username للقناة أو رقم ID مثل -1001234567890.")
            return
        set_setting("order_channel_id", channel_id)
        context.user_data.pop("awaiting_order_channel_id", None)
        await message.reply_text("✅ تم حفظ القناة. تأكد أن البوت مشرف فيها ويملك صلاحية نشر الرسائل.")
        return

    if text in ("🏪 ترقية الحساب إلى تاجر", "ترقية الحساب", "طلب حساب تاجر"):
        if is_admin(user_id):
            await message.reply_text("أنت مالك المتجر، ولا تحتاج إلى طلب ترقية.")
            return
        with db() as conn:
            row = conn.execute("SELECT account_type, trader_requested, username, full_name FROM users WHERE user_id=?", (user_id,)).fetchone()
            if not row:
                await message.reply_text("أرسل /start أولاً لتسجيل حسابك.")
                return
            if row["account_type"] == "trader":
                await message.reply_text("✅ حسابك مفعّل كتاجر بالفعل.")
                return
            if int(row["trader_requested"] or 0):
                await message.reply_text("⏳ طلب الترقية تاعك راهو عند الإدارة، استنى الرد.")
                return
            conn.execute("UPDATE users SET trader_requested=1 WHERE user_id=?", (user_id,))
        username_text = f"@{row['username']}" if row["username"] else "غير موجود"
        admin_text = (
            "🏪 طلب جديد لترقية حساب إلى تاجر\n\n"
            f"👤 الاسم: {row['full_name'] or 'غير متوفر'}\n"
            f"🔗 username: {username_text}\n"
            f"🆔 Telegram ID: {user_id}\n"
            f"🔎 فتح الحساب: tg://user?id={user_id}"
        )
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ قبول الترقية", callback_data=f"trader_approve:{user_id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"trader_reject:{user_id}"),
                ]]),
            )
        except Exception:
            logger.exception("تعذر إرسال طلب ترقية التاجر للإدارة")
            with db() as conn:
                conn.execute("UPDATE users SET trader_requested=0 WHERE user_id=?", (user_id,))
            await message.reply_text("تعذر إرسال الطلب للإدارة حالياً. حاول مرة أخرى لاحقاً.")
            return
        await message.reply_text("✅ تم إرسال طلبك للإدارة. ستصلك رسالة عند قبول الطلب أو رفضه.")
        return

    if text == "🧪 الطلب التجريبي":
        with db() as conn:
            games = conn.execute("SELECT id, name, emoji FROM games WHERE active=1 ORDER BY id").fetchall()
        if not games:
            await message.reply_text("ما كاين حتى لعبة مفعّلة للتجربة.")
            return
        rows = [[InlineKeyboardButton(f"{g['emoji'] or '🎮'} {g['name']}", callback_data=f"test_order_game:{g['id']}")] for g in games]
        rows.append([InlineKeyboardButton("❌ إلغاء", callback_data="test_order_abort")])
        await message.reply_text("🧪 اختار اللعبة لإنشاء طلب تجريبي. لن يتم خصم أي رصيد ولن يتم تنفيذ شحن حقيقي:", reply_markup=InlineKeyboardMarkup(rows))
        return

    # إلغاء العملية الحالية
    if text in CANCEL_WORDS:
        task = CART_TIMEOUT_TASKS.pop(user_id, None)
        if task and not task.done(): task.cancel()
        context.user_data.pop("cart_checkout_active", None)
        context.user_data.pop("cart_checkout_token", None)
        context.user_data.pop("order_draft", None)
        context.user_data.pop("pending_player_id", None)
        context.user_data.pop("awaiting_payment_receipt", None)
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
        context.user_data.pop("editing_offer_name", None)
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
            await message.reply_text(f"✅ تم حفظ الإعداد: {value}", reply_markup=ReplyKeyboardMarkup([["🟢 تفعيل أوقات المتجر", "⚪ تعطيل أوقات المتجر"], ["⏰ تعديل وقت الافتتاح", "⏰ تعديل وقت الغلق"], ["📣 تعديل رسالة الافتتاح", "📣 تعديل رسالة الغلق"], ["🔙 إدارة البوت"]], resize_keyboard=True, is_persistent=True))
        else:
            await message.reply_text("✅ تم حفظ الرسالة الجديدة.", reply_markup=ReplyKeyboardMarkup([["🟢 تفعيل أوقات المتجر", "⚪ تعطيل أوقات المتجر"], ["⏰ تعديل وقت الافتتاح", "⏰ تعديل وقت الغلق"], ["📣 تعديل رسالة الافتتاح", "📣 تعديل رسالة الغلق"], ["🔙 إدارة البوت"]], resize_keyboard=True, is_persistent=True))
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

    if context.user_data.get("awaiting_deposit_amount_usd"):
        try:
            amount_usd = float(text.replace("USD", "").replace("usd", "").replace(",", ".").strip())
            if amount_usd <= 0 or amount_usd > 1000000: raise ValueError
        except ValueError:
            await message.reply_text("❌ أدخل مبلغًا صحيحًا بالدولار، مثل 10 أو 12.50 USD.")
            return
        context.user_data["deposit_amount_usd"] = round(amount_usd, 2)
        context.user_data.pop("awaiting_deposit_amount_usd", None)
        if get_setting("usd_payments_enabled", "0") != "1":
            await message.reply_text("❌ تعبئة محفظة الدولار متوقفة حاليًا. تواصل مع الإدارة.", reply_markup=main_keyboard(user_id)); return
        with db() as conn:
            methods = conn.execute("SELECT * FROM custom_payment_methods WHERE enabled=1 AND upper(currency)='USD' ORDER BY id").fetchall()
        rows = [[InlineKeyboardButton(f"{m['emoji']} {m['name']}", callback_data=f"deposit_usd_method:{int(m['id'])}")] for m in methods]
        if not rows:
            await message.reply_text("لا توجد طرق دفع بالدولار مفعّلة حاليًا. تواصل مع الإدارة.", reply_markup=main_keyboard(user_id)); return
        await message.reply_text(f"💵 تعبئة محفظة الدولار: {amount_usd:.2f} USD\nاختر طريقة الدفع:", reply_markup=InlineKeyboardMarkup(rows))
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
        context.user_data["deposit_currency"] = "DA"
        context.user_data.pop("awaiting_deposit_amount", None)
        await message.reply_text(
            f"💰 المبلغ الذي تريد إضافته إلى المحفظة: {amount} DA\nBaridiMob وCCP: تدفع {amount} DA.\nFlexy: تدفع {int(round(amount * 1.18))} DA (زيادة 18%) ويضاف للمحفظة {amount} DA كاملة.\nاختر طريقة الدفع:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("BaridiMob", callback_data="deposit_method:baridi"), InlineKeyboardButton("CCP", callback_data="deposit_method:ccp")],
                [InlineKeyboardButton("Flexy (+18%)", callback_data="deposit_method:flexy")],
            ]),
        )
        return

    if context.user_data.get("awaiting_login_email"):
        if context.user_data.get("cart_checkout_active") and not context.user_data.get("cart_checkout_token"):
            await message.reply_text("⏰ انتهت مهلة الطلب. ابدأ من جديد."); return
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
        if draft.get("payment_type") in ("balance", "balance_usd", "trader_wallet", "trader_wallet_usd"):
            await create_wallet_order(message, context, context.user_data["pending_player_id"])
            return
        if draft.get("payment_type") == "credit":
            await create_credit_order(message, context, context.user_data["pending_player_id"])
            return
        context.user_data["awaiting_payment_receipt"] = True
        await message.reply_text(
            "✅ تم استلام بيانات الحساب.\n\n"
            f"🎮 اللعبة: {draft['game_name']}\n📦 العرض: {draft['offer_name']}\n"
            f"💳 طريقة الدفع: {draft['method']}\n💰 المبلغ: {draft['price']} {draft.get('currency', 'DA')}\n\n"
            "📸 الآن أرسل صورة وصل الدفع لإتمام الطلب. تقدر ترسل عدة صور مع بعض كألبوم.\nلإلغاء العملية أرسل /cancel"
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

    if is_admin(user_id) and context.user_data.get("person_balance_usd_edit_target"):
        target = int(context.user_data.pop("person_balance_usd_edit_target"))
        try:
            new_balance = float(text.strip().upper().replace("USD", "").replace("$", "").replace(",", ".").strip())
            if new_balance < 0: raise ValueError
        except ValueError:
            context.user_data["person_balance_usd_edit_target"] = target
            await message.reply_text("❌ أرسل مبلغ USD صحيحًا يساوي صفرًا أو أكثر، مثل 12.50، أو /cancel."); return
        with db() as conn:
            person = conn.execute("SELECT full_name FROM users WHERE user_id=?", (target,)).fetchone()
            if not person:
                await message.reply_text("❌ المشترك غير موجود."); return
            old_row = conn.execute("SELECT COALESCE(balance_usd,0) AS bal FROM users WHERE user_id=?", (target,)).fetchone()
            old_balance = float(old_row["bal"] or 0)
            conn.execute("UPDATE users SET balance_usd=? WHERE user_id=?", (new_balance, target))
            conn.execute("INSERT INTO wallet_transactions(user_id,currency,kind,amount,balance_before,balance_after,note,admin_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (target,"USD","تعديل إداري",new_balance-old_balance,old_balance,new_balance,"تعديل يدوي للرصيد",user_id,now_text()))
        await message.reply_text(f"✅ تم تعديل رصيد الدولار للمشترك إلى {new_balance:.2f} USD.")
        try: await context.bot.send_message(target, f"ℹ️ حدّثت الإدارة رصيد الدولار في محفظتك. الرصيد الجديد: {new_balance:.2f} USD.")
        except Exception: logger.exception("تعذر إشعار المشترك بتعديل رصيد USD")
        return

    if is_admin(user_id) and context.user_data.get("person_balance_usd_target"):
        target = int(context.user_data.pop("person_balance_usd_target"))
        try:
            amount = float(text.strip().upper().replace("USD", "").replace("$", "").replace(",", ".").strip())
            if amount <= 0: raise ValueError
        except ValueError:
            context.user_data["person_balance_usd_target"] = target
            await message.reply_text("❌ أرسل مبلغ USD أكبر من صفر، مثل 10 أو 12.50، أو /cancel."); return
        with db() as conn:
            person = conn.execute("SELECT full_name FROM users WHERE user_id=?", (target,)).fetchone()
            if not person:
                await message.reply_text("❌ المشترك غير موجود."); return
            old_balance = float(conn.execute("SELECT COALESCE(balance_usd,0) FROM users WHERE user_id=?", (target,)).fetchone()[0] or 0)
            conn.execute("UPDATE users SET balance_usd=COALESCE(balance_usd,0)+? WHERE user_id=?", (amount, target))
            balance = conn.execute("SELECT balance_usd FROM users WHERE user_id=?", (target,)).fetchone()["balance_usd"]
            conn.execute("INSERT INTO wallet_transactions(user_id,currency,kind,amount,balance_before,balance_after,note,admin_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (target,"USD","إضافة إدارية",amount,old_balance,float(balance),"إضافة يدوية",user_id,now_text()))
        await message.reply_text(f"✅ تمت إضافة {amount:.2f} USD. رصيد الدولار الجديد: {float(balance):.2f} USD.")
        try: await context.bot.send_message(target, f"💵 أضافت الإدارة {amount:.2f} USD إلى محفظتك. رصيدك الجديد: {float(balance):.2f} USD.")
        except Exception: logger.exception("تعذر إشعار المشترك بإضافة رصيد USD")
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
            old_balance = int(conn.execute("SELECT COALESCE(balance,0) FROM users WHERE user_id=?", (target,)).fetchone()[0] or 0)
            conn.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, target))
            conn.execute("INSERT INTO wallet_transactions(user_id,currency,kind,amount,balance_before,balance_after,note,admin_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (target,"DA","تعديل إداري",new_balance-old_balance,old_balance,new_balance,"تعديل يدوي للرصيد",user_id,now_text()))
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
            old_balance = int(conn.execute("SELECT COALESCE(balance,0) FROM users WHERE user_id=?", (target,)).fetchone()[0] or 0)
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, target))
            conn.execute("INSERT INTO wallet_transactions(user_id,currency,kind,amount,balance_before,balance_after,note,admin_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (target,"DA","إضافة إدارية",amount,old_balance,old_balance+amount,"إضافة يدوية",user_id,now_text()))
        await message.reply_text(f"✅ تمت إضافة {amount} DA إلى رصيد المشترك {target}.")
        return

    # حفظ اسم العرض الجديد
    if is_admin(user_id):
        offer_id = context.user_data.get("editing_offer_name")
        if offer_id is not None:
            new_name = text.strip()
            if not new_name or len(new_name) > 100:
                await message.reply_text("❌ الاسم غير صالح. أرسل اسمًا من 1 إلى 100 حرف، أو /cancel للإلغاء.")
                return
            try:
                with db() as conn:
                    offer = conn.execute("SELECT id, game_id FROM offers WHERE id=?", (int(offer_id),)).fetchone()
                    if not offer:
                        context.user_data.pop("editing_offer_name", None)
                        await message.reply_text("❌ العرض غير موجود أو تم حذفه.")
                        return
                    duplicate = conn.execute(
                        "SELECT id FROM offers WHERE game_id=? AND lower(name)=lower(?) AND id<>?",
                        (int(offer["game_id"]), new_name, int(offer_id)),
                    ).fetchone()
                    if duplicate:
                        await message.reply_text("❌ يوجد عرض آخر بهذا الاسم في اللعبة نفسها. أرسل اسمًا مختلفًا أو /cancel.")
                        return
                    conn.execute("UPDATE offers SET name=? WHERE id=?", (new_name, int(offer_id)))
                context.user_data.pop("editing_offer_name", None)
                await message.reply_text("✅ تم تغيير اسم العرض بنجاح. الأسعار ونقاط المكافأة لم تتغير.")
            except Exception:
                logger.exception("فشل تغيير اسم العرض")
                await message.reply_text("❌ حدث خطأ أثناء تغيير اسم العرض.")
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

        if step == "bulk_game_prices":
            game_id = context.user_data.get("bulk_price_game_id")
            if not game_id:
                context.user_data.pop("admin_step", None)
                await message.reply_text("❌ انتهت جلسة تحديث الأسعار. افتحها من جديد.", reply_markup=admin_keyboard())
                return
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            parsed = []
            errors = []
            with db() as conn:
                db_offers = conn.execute("SELECT id,name FROM offers WHERE game_id=?", (int(game_id),)).fetchall()
            by_name = {str(r["name"]).strip().casefold(): r for r in db_offers}
            seen = set()
            for line_no, line in enumerate(lines, 1):
                parts = [part.strip() for part in line.split("|")]
                if len(parts) != 5:
                    errors.append(f"السطر {line_no}: لازم 5 خانات مفصولة بـ |.")
                    continue
                name = parts[0]
                row = by_name.get(name.casefold())
                if not row:
                    errors.append(f"السطر {line_no}: اسم العرض غير موجود: {name}")
                    continue
                offer_id = int(row["id"])
                if offer_id in seen:
                    errors.append(f"السطر {line_no}: العرض مكرر: {name}")
                    continue
                try:
                    values = [Decimal(v.replace(",", ".")) for v in parts[1:]]
                    if any((not v.is_finite()) or v < 0 or v > Decimal("100000000") for v in values):
                        raise InvalidOperation
                    retail_da, trader_da, retail_usd, trader_usd = values
                    # One source currency per account tier; zero means auto-convert counterpart.
                    if (retail_da == 0 and retail_usd == 0) or (trader_da == 0 and trader_usd == 0):
                        raise ValueError("كل فئة لازم يكون عندها سعر واحد على الأقل.")
                    if retail_da > 0 and retail_usd > 0:
                        raise ValueError("الزبون: خلي DA أو USD صفراً، ماشي الاثنين معاً.")
                    if trader_da > 0 and trader_usd > 0:
                        raise ValueError("التاجر: خلي DA أو USD صفراً، ماشي الاثنين معاً.")
                    if retail_da != retail_da.to_integral_value() or trader_da != trader_da.to_integral_value():
                        raise ValueError("أسعار DA لازم تكون أعداداً صحيحة.")
                except (InvalidOperation, ValueError) as exc:
                    errors.append(f"السطر {line_no} ({name}): {exc or 'سعر غير صالح'}")
                    continue
                parsed.append((offer_id, int(retail_da), int(round(retail_da * Decimal("1.18"))), int(trader_da), int(round(trader_da * Decimal("1.18"))), float(retail_usd), float(trader_usd)))
                seen.add(offer_id)
            missing = [str(r["name"]) for r in db_offers if int(r["id"]) not in seen]
            if missing:
                errors.append("العروض الناقصة من القائمة: " + "، ".join(missing[:30]))
            if errors:
                await message.reply_text("❌ لم يتم تغيير أي سعر بسبب أخطاء في القائمة:\n\n" + "\n".join(errors[:20]) + "\n\nصحح القائمة وأعد إرسالها. /cancel للإلغاء.")
                return
            if not parsed:
                await message.reply_text("❌ القائمة فارغة. أرسل سطرًا واحدًا على الأقل.")
                return
            with db() as conn:
                for item in parsed:
                    conn.execute(
                        "UPDATE offers SET price_baridi=?, price_flexy=?, price_baridi_trader=?, price_flexy_trader=?, price_usd=?, price_usd_trader=? WHERE id=? AND game_id=?",
                        (*item[1:], item[0], int(game_id))
                    )
            context.user_data.pop("admin_step", None)
            context.user_data.pop("bulk_price_game_id", None)
            await message.reply_text(
                f"✅ تم تحديث أسعار {len(parsed)} عرض بنجاح.\n"
                f"💵 سعر شراء الدولار: {usd_buy_rate()} DA\n"
                f"💱 سعر بيع الدولار: {usd_sell_rate()} DA\n"
                "أسعار Flexy محسوبة تلقائياً (+18%).",
                reply_markup=admin_keyboard()
            )
            return

        if step in ("set_usd_exchange_rate", "set_usd_sell_rate", "set_usd_buy_rate"):
            try:
                rate = Decimal(text.strip().replace(",", "."))
                if not rate.is_finite() or rate <= 0 or rate > Decimal("10000000"):
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                await message.reply_text("❌ السعر غير صحيح. أرسل رقمًا أكبر من صفر، مثال: 260.")
                return
            which = "buy" if step == "set_usd_buy_rate" else "sell"
            set_setting(f"usd_{which}_rate", format(rate.normalize(), "f"))
            # Keep the legacy setting synchronized with the sell rate for older integrations.
            if which == "sell":
                set_setting("usd_exchange_rate", format(rate.normalize(), "f"))
            context.user_data.pop("admin_step", None)
            operation = "القسمة على سعر الشراء" if which == "buy" else "الضرب في سعر البيع"
            await message.reply_text(
                f"✅ تم حفظ سعر {('شراء' if which == 'buy' else 'بيع')} الدولار: 1 USD = {rate} DA.\n"
                f"العملية المعتمدة: {operation}.\n"
                "سيُطبّق السعر على جميع المشتركين.", reply_markup=admin_keyboard())
            return

        if step == "custom_payment_edit_instructions":
            custom_id = context.user_data.get("pending_custom_payment_edit_id")
            if not custom_id:
                context.user_data.pop("admin_step", None)
                await message.reply_text("❌ انتهت عملية تعديل التعليمات. أعد المحاولة من إعدادات الدفع.")
                return
            with db() as conn:
                conn.execute("UPDATE custom_payment_methods SET instructions=? WHERE id=?", (text[:3500], int(custom_id)))
            context.user_data.pop("pending_custom_payment_edit_id", None)
            context.user_data.pop("admin_step", None)
            await message.reply_text("✅ تم حفظ تعليمات الدفع. يمكنك الآن تفعيل الطريقة من إعدادات الدفع.", reply_markup=admin_keyboard())
            return

        if step == "custom_payment_name":
            parts = [part.strip() for part in text.split("|")]
            if len(parts) != 3 or not parts[0] or not parts[1] or parts[2].upper() not in ("USD", "DZD", "DA"):
                await message.reply_text("❌ الصيغة غير صحيحة. مثال: Binance | 🟡 | USD")
                return
            context.user_data["pending_custom_payment"] = {"name": parts[0][:80], "emoji": parts[1][:12], "currency": "DZD" if parts[2].upper() in ("DZD", "DA") else "USD"}
            context.user_data["admin_step"] = "custom_payment_instructions"
            await message.reply_text("أرسل الآن تعليمات الدفع التي ستظهر للزبون (رقم الحساب، الرابط، أو خطوات الدفع).")
            return

        if step == "custom_payment_instructions":
            pending = context.user_data.get("pending_custom_payment") or {}
            if not pending:
                context.user_data.pop("admin_step", None)
                await message.reply_text("❌ انتهت عملية الإضافة. ابدأ من جديد.")
                return
            initial_enabled = 1 if pending["currency"] != "USD" or get_setting("usd_payments_enabled", "0") == "1" else 0
            with db() as conn:
                conn.execute("INSERT INTO custom_payment_methods (name, emoji, currency, instructions, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?)", (pending["name"], pending["emoji"], pending["currency"], text[:3500], initial_enabled, now_text()))
            context.user_data.pop("pending_custom_payment", None)
            context.user_data.pop("admin_step", None)
            await message.reply_text("✅ تمت إضافة طريقة الدفع. طرق الدولار تتحكم في ظهورها كلها معًا من إعدادات الدفع، أما طرق DZD فتُدار كل طريقة على حدة.", reply_markup=admin_keyboard())
            return

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

            if len(parts) not in (3, 4):
                await message.reply_text(
                    "❌ الصيغة غير صحيحة.\n\n"
                    "استعمل: اسم العرض | سعر الزبون BaridiMob | سعر التاجر BaridiMob\n"
                    "مثال: 100 Coins | 250 | 220"
                )
                return

            offer_name = parts[0]
            try:
                price_baridi = int(parts[1])
                price_baridi_trader = int(parts[2])
                reward_points = 0  # Loyalty points are calculated from completed order value.
                if not offer_name or min(price_baridi, price_baridi_trader) < 0:
                    raise ValueError
                # Match the existing wallet Flexy full-credit mode: customer pays 18% extra.
                price_flexy = int(round(price_baridi * 1.18))
                price_flexy_trader = int(round(price_baridi_trader * 1.18))
            except ValueError:
                await message.reply_text("❌ تأكد من اسم العرض والأسعار. الأسعار لازم تكون أرقامًا موجبة أو صفرًا.")
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
                    (game_id, recharge_method_id, name, price_baridi, price_flexy, price_baridi_trader, price_flexy_trader, reward_points, active, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, (SELECT COALESCE(MAX(sort_order),0)+1 FROM offers WHERE game_id=?))
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
                        game_id,
                    ),
                )

            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_game_id", None)
            context.user_data.pop("pending_recharge_method_id", None)

            await message.reply_text(
                f"✅ تمت إضافة العرض: {offer_name}\n\n"
                f"🏦 BaridiMob/CCP: {price_baridi} DA\n"
                f"📱 Flexy (محسوب +18%): {price_flexy} DA\n"
                f"🏪 التاجر — BaridiMob/CCP: {price_baridi_trader} DA | Flexy (محسوب +18%): {price_flexy_trader} DA",
                reply_markup=ReplyKeyboardMarkup(
                    ADMIN_PANEL_MENU,
                    resize_keyboard=True,
                ),
            )
            return

        if step == "edit_single_offer_usd_price":
            try:
                new_price = Decimal(text.strip().replace(",", "."))
                if not new_price.is_finite() or new_price < 0 or new_price > Decimal("10000000"):
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                await message.reply_text("❌ أرسل سعرًا صحيحًا بالدولار (0 أو أكثر).")
                return
            offer_id = context.user_data.get("pending_offer_id")
            column = context.user_data.get("pending_offer_usd_column")
            if column not in ("price_usd", "price_usd_trader") or not offer_id:
                context.user_data.pop("admin_step", None)
                await message.reply_text("❌ انتهت جلسة تعديل السعر. أعد فتح العرض.")
                return
            with db() as conn:
                # A USD price is a separate source currency: clear the matching
                # DZD source price so the USD amount can be used for conversion.
                if column == "price_usd":
                    conn.execute(
                        "UPDATE offers SET price_usd=?, price_baridi=0, price_flexy=0 WHERE id=?",
                        (float(new_price), int(offer_id)),
                    )
                else:
                    conn.execute(
                        "UPDATE offers SET price_usd_trader=?, price_baridi_trader=0, price_flexy_trader=0 WHERE id=?",
                        (float(new_price), int(offer_id)),
                    )
                result = conn.execute("SELECT changes() AS changed").fetchone()
                offer_name = conn.execute("SELECT name FROM offers WHERE id=?", (int(offer_id),)).fetchone()
            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_offer_id", None)
            context.user_data.pop("pending_offer_usd_column", None)
            await message.reply_text(f"✅ تم حفظ سعر الدولار {new_price} USD للعرض {offer_name['name'] if offer_name else ''}. سعر الدينار المقابل يُحسب تلقائيًا بسعر بيع الدولار.", reply_markup=admin_keyboard())
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
            if column not in ("price_baridi", "price_baridi_trader") or not offer_id:
                context.user_data.pop("admin_step", None)
                await message.reply_text("❌ انتهت جلسة تعديل السعر. افتح تعديل سعر العرض من جديد.")
                return
            flexy_column = "price_flexy" if column == "price_baridi" else "price_flexy_trader"
            with db() as conn:
                usd_column = "price_usd" if column == "price_baridi" else "price_usd_trader"
                # A newly entered DZD price becomes the active source price; clear any old USD override.
                result = conn.execute(
                    f"UPDATE offers SET {column}=?, {flexy_column}=?, {usd_column}=0 WHERE id=?",
                    (new_price, int(round(new_price * 1.18)), offer_id),
                )
                offer_name_row = conn.execute("SELECT name FROM offers WHERE id=?", (offer_id,)).fetchone()
            context.user_data.pop("admin_step", None)
            context.user_data.pop("pending_offer_id", None)
            context.user_data.pop("pending_offer_price_column", None)
            if not result.rowcount or not offer_name_row:
                await message.reply_text("❌ العرض غير موجود.", reply_markup=admin_keyboard())
            else:
                await message.reply_text(f"✅ تم تعديل سعر BaridiMob إلى {new_price} DA للعرض {offer_name_row['name']}، وتم حساب سعر Flexy تلقائيًا (+18%).", reply_markup=admin_keyboard())
            return

        # تعديل أسعار عرض
        if step == "edit_price_data":
            parts = [part.strip() for part in text.split("|")]

            if len(parts) != 2:
                await message.reply_text(
                    "❌ الصيغة غير صحيحة.\n\n"
                    "ابعث سعرين فقط: سعر الزبون BaridiMob | سعر التاجر BaridiMob.\n"
                    "مثال: 750 | 650\nسيُحسب Flexy تلقائيًا بإضافة 18%."
                )
                return

            try:
                price_baridi = int(parts[0])
                price_baridi_trader = int(parts[1])
                price_flexy = int(round(price_baridi * 1.18))
                price_flexy_trader = int(round(price_baridi_trader * 1.18))

                if min(price_baridi, price_baridi_trader) < 0:
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
                        price_baridi_trader = ?, price_flexy_trader = ?,
                        price_usd = 0, price_usd_trader = 0
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
                f"📱 Flexy (محسوب +18%): {price_flexy} DA\n"
                f"🏪 للتاجر — BaridiMob/CCP: {price_baridi_trader} DA | Flexy (محسوب +18%): {price_flexy_trader} DA",
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

        if step == "set_required_channel":
            value = text.strip()
            if not value or len(value) > 200:
                await message.reply_text("❌ معرّف غير صالح. جرّب مرة أخرى أو /cancel للإلغاء.")
                return
            set_setting("required_channel", value)
            context.user_data.pop("admin_step", None)
            await message.reply_text(f"✅ تم حفظ معرّف القناة: {value}\nتأكد أن البوت مشرف في القناة.", reply_markup=admin_keyboard())
            return
        if step == "set_required_channel_link":
            value = text.strip()
            if value and not (value.startswith("https://t.me/") or value.startswith("http://t.me/") or value.startswith("https://telegram.me/")):
                await message.reply_text("❌ الرابط لازم يكون رابط قناة تيليغرام مثل https://t.me/YourChannel.")
                return
            set_setting("required_channel_link", value)
            context.user_data.pop("admin_step", None)
            await message.reply_text("✅ تم حفظ رابط القناة.", reply_markup=admin_keyboard())
            return

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
            await message.reply_text("✅ تم حفظ إيموجي Premium وتفعيله. سيظهر في زر اللعبة وفي قائمة الألعاب إذا كان البوت/مالك البوت مؤهلاً لاستخدام الإيموجيات المخصصة.", reply_markup=ReplyKeyboardMarkup(ADMIN_PANEL_MENU, resize_keyboard=True, is_persistent=True))
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

        if step == "scheduled_broadcast_message":
            context.user_data["pending_scheduled_text"] = text
            # Keep Telegram Premium custom emoji and text-formatting entities from
            # either a text message or a media caption.
            source_entities = message.entities or message.caption_entities or []
            context.user_data["pending_scheduled_entities"] = [entity.to_dict() for entity in source_entities]
            context.user_data["admin_step"] = "scheduled_broadcast_datetime"
            await message.reply_text("📅 ابعث موعد الإرسال بهذا الشكل: YYYY-MM-DD HH:MM\nمثال: 2026-11-01 18:30\nالتوقيت حسب توقيت الجزائر.")
            return
        if step == "scheduled_broadcast_datetime":
            try:
                due_dt = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=STORE_TZ)
                if due_dt <= datetime.now(STORE_TZ): raise ValueError
            except ValueError:
                await message.reply_text("❌ التاريخ غير صحيح أو فات. استعمل YYYY-MM-DD HH:MM لموعد مستقبلي."); return
            due = due_dt.strftime("%Y-%m-%d %H:%M:%S")
            context.user_data["pending_scheduled_due"] = due
            context.user_data["admin_step"] = "scheduled_broadcast_confirm"
            preview_prefix = "📨 معاينة الإشعار المجدول:\n\n"
            preview_body = context.user_data.get("pending_scheduled_text", "")
            preview_suffix = f"\n\n📅 الموعد: {due}\nسيُرسل مرة واحدة لجميع المشتركين."
            # Telegram entity offsets are measured in UTF-16 code units. Shift the
            # original entities by the prefix length so Premium custom emoji render
            # correctly in the preview as well as in the final scheduled message.
            preview_entities = []
            prefix_utf16_len = len(preview_prefix.encode("utf-16-le")) // 2
            try:
                from telegram import MessageEntity
                for item in context.user_data.get("pending_scheduled_entities", []):
                    if not isinstance(item, dict):
                        continue
                    shifted = dict(item)
                    if shifted.get("offset") is not None:
                        shifted["offset"] = int(shifted["offset"]) + prefix_utf16_len
                    entity = MessageEntity.de_json(shifted, context.bot)
                    if entity:
                        preview_entities.append(entity)
            except Exception:
                logger.exception("Could not restore entities for scheduled broadcast preview")
            await message.reply_text(
                preview_prefix + preview_body + preview_suffix,
                entities=preview_entities or None,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأكيد الجدولة", callback_data="scheduled_broadcast_confirm"), InlineKeyboardButton("❌ إلغاء", callback_data="notify_cancel")]])
            )
            return

        if step == "broadcast_channel_id":
            channel_id = text.strip()
            if not (channel_id.startswith("@") or re.fullmatch(r"-100[0-9]+", channel_id)):
                await message.reply_text("❌ أرسل @username صحيح أو ID يبدأ بـ -100.")
                return
            set_setting("broadcast_channel_id", channel_id)
            context.user_data.pop("admin_step", None)
            await message.reply_text(
                "✅ تم حفظ القناة. اختر الآن وجهة الإشعار:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👥 المشتركين", callback_data="notify_target:users"),
                     InlineKeyboardButton("📢 القناة", callback_data="notify_target:channel")],
                    [InlineKeyboardButton("👥 + 📢 معًا", callback_data="notify_target:both")],
                    [InlineKeyboardButton("❌ إلغاء", callback_data="notify_cancel")]
                ])
            )
            return

        if step == "notify_broadcast_message":
            context.user_data["pending_broadcast_text"] = text
            context.user_data["pending_broadcast_entities"] = [
                entity.to_dict() for entity in (message.entities or [])
            ]
            # Keep the original Telegram message as the source so copy_message
            # preserves premium/custom emoji entities exactly in channel posts.
            context.user_data["pending_broadcast_source_chat_id"] = message.chat_id
            context.user_data["pending_broadcast_source_message_id"] = message.message_id
            context.user_data["admin_step"] = "notify_broadcast_photo"
            await message.reply_text(
                "✅ حفظت نص الإشعار.\n\nابعث صورة لإرفاقها بالإشعار، أو اكتب بدون إذا تحب إشعار نصّي فقط.\nللإلغاء ابعث /cancel."
            )
            return

        if step == "notify_broadcast_photo":
            if text.strip().lower() not in ("بدون", "لا", "no", "none"):
                await message.reply_text("ابعث صورة أو اكتب بدون للمتابعة.")
                return
            context.user_data.pop("pending_broadcast_photo_file_id", None)
            context.user_data["admin_step"] = "notify_broadcast_buttons"
            await message.reply_text(
                "تمام. إذا تحب تزيد أزرار، ابعث كل زر في سطر بهذا الشكل:\n"
                "رابط | اسم الزر | https://example.com\n"
                "قسم | اسم الزر | freefire أو store\n"
                "إذا ما تحتاجش أزرار ابعث: بدون"
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
            # Ask whether this broadcast should collect anonymous customer feedback.
            context.user_data["pending_broadcast_buttons"] = buttons
            context.user_data["admin_step"] = "notify_broadcast_feedback_choice"
            await message.reply_text("هل تحب تضيف زر لجمع آراء الزبائن مع هذا الإشعار؟\nاكتب نعم أو لا.")
            return

        if step == "notify_broadcast_feedback_choice":
            choice = text.strip().lower()
            if choice not in ("نعم", "لا", "yes", "no"):
                await message.reply_text("اكتب نعم أو لا فقط."); return
            buttons = context.user_data.get("pending_broadcast_buttons", [])
            if choice in ("نعم", "yes"):
                buttons.append({"text": "💬 شاركنا رأيك", "callback_data": "feedback_begin"})
            context.user_data["pending_broadcast_buttons"] = buttons
            context.user_data["admin_step"] = "notify_broadcast_confirm"
            with db() as conn:
                total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            preview_rows = [
                [InlineKeyboardButton(b["text"], **({"url": b["url"]} if "url" in b else {"callback_data": b["callback_data"]}))]
                for b in buttons
            ]
            preview_rows.append([
                InlineKeyboardButton("👥 المشتركين", callback_data="notify_target:users"),
                InlineKeyboardButton("📢 القناة", callback_data="notify_target:channel")
            ])
            preview_rows.append([
                InlineKeyboardButton("👥 + 📢 معًا", callback_data="notify_target:both"),
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
        await show_store(message, user_id, "game", context=context); return
    if text == "📱 التطبيقات":
        await show_store(message, user_id, "app", context=context); return
    if text in ("🎁 إشتري بنقاطي", "⭐ نقاطي"):
        await show_points_shop(message, user_id); return
    if text in ("🎯 الإحالة والنقاط", "🎯 الإحالة"):
        if not points_enabled(user_id):
            await message.reply_text("🎯 نظام الإحالة متاح لجميع المشترين.", reply_markup=main_keyboard(user_id)); return
        bot_username = get_setting("bot_username", "").strip()
        if not bot_username:
            try:
                me = await context.bot.get_me(); bot_username = me.username or ""
                if bot_username: set_setting("bot_username", bot_username)
            except Exception: bot_username = ""
        user_row = get_user_row(user_id)
        points_da = float(user_row["points_da"] or 0) if user_row else 0
        points_usd = float(user_row["points_usd"] or 0) if user_row else 0.0
        link = f"https://t.me/{bot_username}?start=ref_{user_id}" if bot_username else "تعذر إنشاء الرابط الآن؛ حاول لاحقاً."
        referral_ratio = 0.5 if user_row and user_row["account_type"] == "trader" else 1.0
        referral_da = 5 * referral_ratio
        referral_usd = 0.019 * referral_ratio
        await message.reply_text(f"🎯 نظام الإحالة والمكافآت\n\nرابط الإحالة الخاص بك:\n{link}\n\n🎁 عند تسجيل مشترك جديد عبر رابطك: {referral_da:g} DA إلى محفظة الدينار و{referral_usd:g} USD إلى محفظة الدولار.\n\n🇩🇿 نقاط DA: {points_da:g} | 💵 نقاط USD: {points_usd:.3f}")
        return
    if text == "✨ مزايا متجرنا":
        await message.reply_text(STORE_BENEFITS_TEXT, reply_markup=main_keyboard(user_id)); return
    if text in ("🔐 السياسات والخصوصية", "🔐 الخصوصية والسياسات", "🔐 Privacy & Policies"):
        policy_text = get_setting("privacy_policy", get_setting("terms_policy", TERMS_PRIVACY_TEXT))
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
        with db() as conn:
            pending_dep = conn.execute("SELECT id FROM wallet_deposits WHERE user_id=? AND status='pending' LIMIT 1", (user_id,)).fetchone()
        if pending_dep:
            await message.reply_text(f"⏳ لديك طلب تعبئة قيد المراجعة #{pending_dep['id']}، لا يمكنك إرسال طلب آخر حتى تتم معالجته.", reply_markup=main_keyboard(user_id))
            return
        for k in ("awaiting_deposit_amount", "awaiting_deposit_amount_usd", "deposit_amount", "deposit_amount_usd", "deposit_method", "deposit_currency", "awaiting_deposit_receipt"):
            context.user_data.pop(k, None)
        await message.reply_text("💰 اختر المحفظة التي تريد تعبئتها:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇩🇿 محفظة الدينار DA", callback_data="deposit_currency:DA")],
            [InlineKeyboardButton("💵 محفظة الدولار USD", callback_data="deposit_currency:USD")],
        ]))
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

    if text in ("📞 اتصل بالإدارة", "📞 Contact Admin", "📞 Contacter l’administration"):
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

        if text == "💳 إدارة الفليكسي":
            await flexy_admin_panel(message)
            return

        if text in ADMIN_SUBMENUS:
            await message.reply_text(
                f"{text}\n\nاختار العملية المطلوبة:",
                reply_markup=ReplyKeyboardMarkup(
                    ADMIN_SUBMENUS[text], resize_keyboard=True, is_persistent=True
                ),
            )
            return
        if text in ("🔙 لوحة الإدارة", "🔙 لوحة التحكم"):
            await show_admin_panel(update, context)
            return

        if text == "➕ إضافة":
            await message.reply_text("➕ اختار واش تحب تزيد:", reply_markup=ReplyKeyboardMarkup([["➕ إضافة لعبة", "➕ إضافة عرض"], ["🔙 لوحة الإدارة"]], resize_keyboard=True, is_persistent=True))
            return
        if text == "🛍️ المتجر":
            await message.reply_text("🛍️ إدارة الألعاب والتطبيقات:", reply_markup=ReplyKeyboardMarkup([["🎮 الألعاب", "📱 التطبيقات"], ["🔙 لوحة الإدارة"]], resize_keyboard=True, is_persistent=True))
            return
        if text == "📂 إدارة البوت":
            await message.reply_text("📂 إدارة البوت:", reply_markup=ReplyKeyboardMarkup([["📋 كل الطلبات", "🗑️ حذف جميع الطلبات"], ["💳 إعدادات الدفع", "📊 الإحصائيات"], ["📝 إدارة النصوص", "📇 إعدادات التواصل"], ["🕒 أوقات المتجر", "🧹 تصفير الحسابات والطلبات"], ["🛍️ التذكير التسويقي"], ["🔄 تحويل زبون / تاجر"], ["🔙 لوحة الإدارة"]], resize_keyboard=True, is_persistent=True))
            return
        if text == "⚙️ إعدادات البوت":
            enabled = get_setting("required_subscription_enabled", "1") == "1"
            channel = current_required_channel() or "غير محدد"
            link = current_required_channel_link() or "غير محدد"
            await message.reply_text(
                "⚙️ إعدادات البوت\n\n"
                f"🔒 الاشتراك الإجباري: {'مفعّل ✅' if enabled and current_required_channel() else 'متوقف ⏸️'}\n"
                f"🆔 معرّف القناة: {channel}\n🔗 رابط القناة: {link}\n\n"
                "اختار الإعداد الذي تريد تغييره:",
                reply_markup=ReplyKeyboardMarkup([
                    ["🔒 تفعيل الاشتراك الإجباري", "⏸️ إيقاف الاشتراك الإجباري"],
                    ["🆔 تغيير معرّف القناة", "🔗 تغيير رابط القناة"],
                    ["✅ اختبار إعدادات القناة"],
                    ["🔙 لوحة التحكم"]
                ], resize_keyboard=True)
            )
            return
        if text == "🔒 تفعيل الاشتراك الإجباري":
            if not current_required_channel():
                await message.reply_text("❌ أدخل معرّف القناة أولًا عبر زر «🆔 تغيير معرّف القناة».")
                return
            set_setting("required_subscription_enabled", "1")
            await message.reply_text("✅ تم تفعيل الاشتراك الإجباري.", reply_markup=admin_keyboard())
            return
        if text == "⏸️ إيقاف الاشتراك الإجباري":
            set_setting("required_subscription_enabled", "0")
            await message.reply_text("⏸️ تم إيقاف الاشتراك الإجباري.", reply_markup=admin_keyboard())
            return
        if text == "🆔 تغيير معرّف القناة":
            context.user_data["admin_step"] = "set_required_channel"
            await message.reply_text("ابعث معرّف القناة مثل @YourChannel أو -1001234567890. ابعث /cancel للإلغاء.")
            return
        if text == "🔗 تغيير رابط القناة":
            context.user_data["admin_step"] = "set_required_channel_link"
            await message.reply_text("ابعث رابط القناة مثل https://t.me/YourChannel. ابعث /cancel للإلغاء.")
            return
        if text == "✅ اختبار إعدادات القناة":
            channel = current_required_channel()
            if not channel:
                await message.reply_text("❌ معرّف القناة غير محدد.")
                return
            try:
                chat = await context.bot.get_chat(channel)
                me = await context.bot.get_chat_member(chat_id=channel, user_id=context.bot.id)
                status = getattr(me, "status", "unknown")
                await message.reply_text(f"✅ تم الوصول إلى القناة: {getattr(chat, 'title', channel)}\nحالة البوت: {status}\nلازم يكون البوت مشرفًا حتى يكون التحقق من الاشتراك موثوقًا.")
            except Exception as exc:
                logger.exception("Channel settings test failed")
                await message.reply_text("❌ تعذر الوصول إلى القناة. تأكد من المعرّف وأن البوت مشرف فيها.")
            return

        if text == "🛍️ التذكير التسويقي":
            enabled = get_setting("marketing_reminders_enabled", "1") == "1"
            await message.reply_text(
                "🛍️ إعدادات التذكير التسويقي\\n\\n"
                f"الحالة: {'مفعّل ✅' if enabled else 'متوقف ⏸️'}\\n"
                f"أول تذكير بعد: {get_setting('marketing_reminder_delay_minutes','60')} دقيقة\\n"
                f"عدد التذكيرات: {get_setting('marketing_reminder_count','2')}\\n"
                f"الفاصل بينها: {get_setting('marketing_reminder_interval_minutes','1440')} دقيقة\\n"
                f"النص الحالي: {get_setting('marketing_reminder_text','')}\\n\\nاختر الإعداد الذي تريد تغييره.",
                reply_markup=ReplyKeyboardMarkup([
                    ["🟢 تفعيل التذكير", "⚪ تعطيل التذكير"],
                    ["⏱️ مدة أول تذكير", "🔢 عدد التذكيرات"],
                    ["⏳ الفاصل بين التذكيرات", "✏️ نص التذكير"],
                    ["🔙 إدارة البوت"]
                ], resize_keyboard=True)
            )
            return
        if text == "🟢 تفعيل التذكير":
            set_setting("marketing_reminders_enabled", "1")
            await message.reply_text("✅ تم تفعيل التذكير التسويقي.", reply_markup=admin_keyboard())
            return
        if text == "⚪ تعطيل التذكير":
            set_setting("marketing_reminders_enabled", "0")
            await message.reply_text("⏸️ تم تعطيل التذكير التسويقي.", reply_markup=admin_keyboard())
            return
        reminder_steps = {
            "⏱️ مدة أول تذكير": ("marketing_reminder_delay_minutes", "أرسل مدة الانتظار بالدقائق (مثال 60)."),
            "🔢 عدد التذكيرات": ("marketing_reminder_count", "أرسل عدد التذكيرات من 0 إلى 10."),
            "⏳ الفاصل بين التذكيرات": ("marketing_reminder_interval_minutes", "أرسل الفاصل بين التذكيرات بالدقائق (مثال 1440)."),
            "✏️ نص التذكير": ("marketing_reminder_text", "أرسل نص رسالة التذكير الجديدة.")
        }
        if text in reminder_steps:
            key, prompt = reminder_steps[text]
            context.user_data["marketing_reminder_setting"] = key
            await message.reply_text(prompt + "\\nللإلغاء أرسل /cancel", reply_markup=cancel_keyboard())
            return
        if context.user_data.get("marketing_reminder_setting") and is_admin(user_id):
            key = context.user_data.pop("marketing_reminder_setting")
            value = text
            if key != "marketing_reminder_text":
                try:
                    number = int(value)
                    if number < 0 or (key != "marketing_reminder_count" and number < 1) or (key == "marketing_reminder_count" and number > 10):
                        raise ValueError
                except ValueError:
                    context.user_data["marketing_reminder_setting"] = key
                    await message.reply_text("❌ قيمة غير صحيحة. أرسل رقمًا صالحًا ضمن الحدود المطلوبة.")
                    return
            set_setting(key, value)
            await message.reply_text("✅ تم حفظ إعداد التذكير.", reply_markup=admin_keyboard())
            return

        if text == "🕒 أوقات المتجر":
            enabled = get_setting("store_hours_enabled", "0") == "1"
            opening = get_setting("store_open_time", "09:00")
            closing = get_setting("store_close_time", "23:00")
            await message.reply_text(
                f"🕒 إعداد أوقات المتجر (توقيت الجزائر)\n\nالحالة: {'مفعّل' if enabled else 'معطّل'}\nالافتتاح: {opening}\nالغلق: {closing}\n\nاختر إجراءً. عند التعطيل تبقى الطلبات متاحة دائمًا. عند التفعيل يمكن تصفح المتجر خارج الوقت لكن لا يمكن إرسال طلب جديد.",
                reply_markup=ReplyKeyboardMarkup([["🟢 تفعيل أوقات المتجر", "⚪ تعطيل أوقات المتجر"], ["⏰ تعديل وقت الافتتاح", "⏰ تعديل وقت الغلق"], ["📣 تعديل رسالة الافتتاح", "📣 تعديل رسالة الغلق"], ["🔙 إدارة البوت"]], resize_keyboard=True, is_persistent=True))
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
            await show_store(message, user_id, "app", context=context)
            return
        if text == "🎮 الألعاب":
            await show_store(message, user_id, "game", context=context)
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

        if text == "📬 طلبات الألعاب":
            with db() as conn:
                total = int(conn.execute("SELECT COUNT(*) FROM game_requests").fetchone()[0])
            if not total:
                await message.reply_text("📬 لا توجد طلبات ألعاب أو تطبيقات."); return
            await message.reply_text("📬 طلبات الألعاب والتطبيقات:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"عرض الطلبات ({total})", callback_data="game_requests_list:0")]])); return

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

        if text in ("💰 طلبات التعبئة", "💰 طلبات تعبئة الرصيد"):
            await show_pending_deposits(message, page=0)
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
            # Show the payment controls immediately from the reply-keyboard menu.
            # This avoids an extra intermediate button that could confuse admins.
            sell_rate = get_setting("usd_sell_rate", get_setting("usd_exchange_rate", "254"))
            buy_rate = get_setting("usd_buy_rate", get_setting("usd_exchange_rate", "254"))
            usd_on = get_setting("usd_payments_enabled", "0") == "1"
            payment_text = (
                "💳 <b>إعدادات الدفع</b>\n\n"
                f"💵 سعر بيع الدولار: 1 USD = {html.escape(str(sell_rate))} DA\n"
                "طريقة الحساب: سعر العرض بالدولار × سعر البيع = السعر بالدينار.\n\n"
                f"💱 سعر شراء الدولار: 1 USD = {html.escape(str(buy_rate))} DA\n"
                "طريقة الحساب: السعر بالدينار ÷ سعر الشراء = السعر بالدولار.\n\n"
                f"🌐 طرق الدفع بالدولار: {'مفعّلة ✅' if usd_on else 'مخفية ❌'}"
            )
            payment_buttons = [
                [InlineKeyboardButton("💵 تعديل سعر بيع الدولار (يضرب في)", callback_data="pay_usd_sell_rate")],
                [InlineKeyboardButton("💱 تعديل سعر شراء الدولار (يقسم على)", callback_data="pay_usd_buy_rate")],
                [InlineKeyboardButton(f"{'🙈 إخفاء كل طرق الدولار' if usd_on else '👁️ إظهار كل طرق الدولار'}", callback_data="usd_pay_toggle_all")],
                [InlineKeyboardButton("فتح باقي إعدادات الدفع", callback_data="adm_payment")],
            ]
            await message.reply_text(payment_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(payment_buttons))
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

        if text == "💰 ترتيب محافظ المشتركين":
            if not is_admin(user_id):
                await message.reply_text("⛔ هذا الخيار خاص بالإدارة.")
                return
            await message.reply_text(
                "اختر العملة لعرض جميع المحافظ مرتبة من الأكبر إلى الأصغر:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 محافظ الدينار DA", callback_data="wallet_rank:DA:0")],
                    [InlineKeyboardButton("💵 محافظ الدولار USD", callback_data="wallet_rank:USD:0")],
                ]),
            )
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
                total=int(conn.execute("SELECT COUNT(*) FROM (SELECT user_id FROM orders GROUP BY user_id)").fetchone()[0])
            if not total:
                await message.reply_text("لا توجد طلبات مسجلة.", reply_markup=admin_keyboard()); return
            await message.reply_text("👤 الطلبات مجمعة حسب الزبون:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"عرض الزبائن ({total})",callback_data="adm_customers")]])); return

        if text == "👥 إدارة التجار":
            with db() as conn:
                total=int(conn.execute("SELECT COUNT(*) FROM users WHERE trader_requested=1 AND account_type!='trader'").fetchone()[0])
            if not total:
                await message.reply_text("لا توجد طلبات تاجر معلّقة.", reply_markup=admin_keyboard()); return
            await message.reply_text("🏪 طلبات حسابات التجار:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"عرض الطلبات المعلّقة ({total})",callback_data="trader_requests_page:0")]])); return

        if text == "⏰ إشعار مجدول":
            context.user_data["admin_step"] = "scheduled_broadcast_message"
            await message.reply_text("⏰ ابعث نص الإشعار الذي تريد جدولته لإرساله مرة واحدة في موعد تختاره.\nللإلغاء ابعث /cancel.")
            return
        if text == "💬 مراجعة الآراء":
            with db() as conn:
                rows = conn.execute("SELECT id,comment,created_at FROM feedback_comments WHERE approved=0 ORDER BY id DESC LIMIT 30").fetchall()
            if not rows:
                await message.reply_text("لا توجد تعليقات تنتظر المراجعة.", reply_markup=admin_keyboard()); return
            for row in rows:
                await message.reply_text("💬 تعليق للمراجعة (مجهول):\n\n" + row['comment'] + "\n\n" + str(row['created_at']), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ موافقة ونشر مجهول", callback_data=f"feedback_approve:{row['id']}"), InlineKeyboardButton("❌ رفض", callback_data=f"feedback_reject:{row['id']}")]]))
            return

        if text == "📨 إرسال إشعار":
            context.user_data["admin_step"] = "notify_broadcast_message"
            await message.reply_text("📨 ابعث نص الإشعار الذي تريد إرساله لجميع المشتركين. بعده تقدر ترفق صورة.\n\nابعث /cancel للإلغاء.")
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
    # Give Telegram API requests more time and keep retrying during temporary
    # network outages (common on shared hosting).
    telegram_request = HTTPXRequest(
        connection_pool_size=20,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )
    telegram_updates_request = HTTPXRequest(
        connection_pool_size=10,
        connect_timeout=30.0,
        read_timeout=40.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )
    app = (
        Application.builder()
        .concurrent_updates(16)
        .token(TOKEN)
        .request(telegram_request)
        .get_updates_request(telegram_updates_request)
        .post_init(post_init)
        .build()
    )

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("id", myid))
    app.add_handler(CommandHandler("ids", ids_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("ordergames", order_games_command))
    app.add_handler(CommandHandler("setordergroup", set_order_group_command))
    app.add_handler(CommandHandler("settradergroup", set_trader_group_command))
    app.add_handler(CommandHandler("unsettradergroup", unset_trader_group_command))
    app.add_handler(CommandHandler("groupoffers", trader_group_offers_command))
    app.add_handler(CommandHandler("publish", trader_publish_command))
    app.add_handler(CommandHandler("history", trader_history_command))
    app.add_handler(CommandHandler("traderhistory", trader_history_command))
    app.add_handler(CommandHandler("flexy", flexy_command))
    app.add_handler(CommandHandler("setflexysource", set_flexy_source_command))
    app.add_handler(CommandHandler("setlogchannel", set_log_channel_command))
    # Channel posts are separate Telegram updates; ordinary text handlers do not receive them.
    app.add_handler(MessageHandler(
        filters.UpdateType.CHANNEL_POST | filters.UpdateType.EDITED_CHANNEL_POST,
        flexy_receive_sms,
    ))

    # أزرار Inline
    app.add_handler(CallbackQueryHandler(callback_handler))

    # مشاركة رقم الهاتف اختيارية؛ إذا أرسل المستخدم رقمه نحفظه
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    # استقبال صور وصل الدفع
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.VIDEO, photo_handler)
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

    app.add_error_handler(global_error_handler)

    logger.info("SERADJ STORE bot is starting...")

    # تشغيل البوت
    # Explicitly request channel_post updates from Telegram; relying on the
    # implicit getUpdates defaults can leave channel posts unobserved after
    # another deployment changed allowed_updates.
    app.run_polling(allowed_updates=Update.ALL_TYPES, bootstrap_retries=-1)


if __name__ == "__main__":
    main()

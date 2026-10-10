import os, sqlite3, logging, re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_TEXT = os.getenv("ADMIN_ID", "").strip()
ADMIN_ID = int(ADMIN_TEXT) if ADMIN_TEXT.isdigit() else None
DB_PATH = os.getenv("DB_PATH", "seradj_store.db")
STORE = "SERADJ STORE"

WHATSAPP_NUMBER = "213671629818"
CCP_NAME = "سراج مبارك"
CCP_NUMBER = "14411384"
CCP_KEY = "76"
BARIDIMOB_NAME = "سراج مبارك"
BARIDIMOB_RIP = "00799999001441138421"

GAMES = [
    "Free Fire", "PUBG Mobile", "eFootball", "FC Mobile",
    "Call of Duty Mobile", "Brawl Stars", "Roblox", "One State",
    "TikTok", "Blood Strike", "Snapchat+", "Netflix", "Azar", "App Store"
]
PAYMENTS = ["BaridiMob / CCP", "Flexy"]

# العروض الافتراضية تظهر كأزرار. أسعار الخدمات التي لا توجد لها أسعار معروفة
# تبقى "يحدده المتجر" حتى يضيفها المسؤول باستخدام /setprice.
PACKAGES = {
    "Free Fire": [
        "110 Diamonds", "231 Diamonds", "583 Diamonds", "1188 Diamonds", "2420 Diamonds",
        "الاشتراك الأسبوعي", "الاشتراك الشهري"
    ],
    "PUBG Mobile": ["60 UC", "325 UC", "660 UC", "1800 UC", "3850 UC", "8100 UC"],
    "eFootball": ["300 Coins", "550 Coins", "750 Coins", "1040 Coins", "2130 Coins", "3250 Coins", "5700 Coins", "12800 Coins"],
    "FC Mobile": ["40 FC Points", "100 FC Points", "520 FC Points", "1070 FC Points", "2200 FC Points", "5750 FC Points"],
    "Call of Duty Mobile": ["80 CP", "420 CP", "880 CP", "2400 CP", "5000 CP", "10800 CP"],
    "Brawl Stars": ["30 Gems", "80 Gems", "170 Gems", "360 Gems", "950 Gems", "2000 Gems"],
    "Roblox": ["80 Robux", "400 Robux", "800 Robux", "1700 Robux", "4500 Robux", "10000 Robux"],
    "One State": ["باقة صغيرة", "باقة متوسطة", "باقة كبيرة", "باقة مميزة"],
    "TikTok": ["عملات 70", "عملات 350", "عملات 700", "عملات 1400", "عملات 3500", "عملات 7000"],
    "Blood Strike": ["100 Gold", "300 Gold", "500 Gold", "1000 Gold", "2000 Gold", "5000 Gold"],
    "Snapchat+": ["شهر واحد", "3 أشهر", "6 أشهر", "12 شهرًا"],
    "Netflix": ["شهر واحد", "3 أشهر", "حساب خاص شهر", "شاشة/عضوية إضافية شهر"],
    "Azar": ["باقة صغيرة", "باقة متوسطة", "باقة كبيرة", "باقة مميزة"],
    "App Store": ["بطاقة 1$", "بطاقة 2$", "بطاقة 5$", "بطاقة 10$", "بطاقة 25$", "بطاقة 50$"],
}

# أسعار eFootball: (عدد العملات، BaridiMob/CCP، Flexy)
EF_PRICES = {
    300: (750, 900), 550: (1300, 1550), 750: (1700, 2050), 1040: (2300, 2750),
    2130: (4600, 5500), 3250: (6600, 7900), 5700: (11500, 13500), 12800: (22000, 25500)
}
# أسعار Free Fire: العرض، BaridiMob/CCP، Flexy
FF_PRICES = {
    "110 Diamonds": (280, 330), "231 Diamonds": (550, 680), "583 Diamonds": (1350, 1700),
    "1188 Diamonds": (2700, 3250), "2420 Diamonds": (5400, 6500),
    "الاشتراك الأسبوعي": (700, 850), "الاشتراك الشهري": (3000, 3600)
}

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT UNIQUE, user_id INTEGER,
        username TEXT, full_name TEXT, game TEXT, offer TEXT, player_id TEXT,
        payment TEXT, price INTEGER, status TEXT, created_at TEXT, proof_file_id TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS price_overrides(
        game TEXT, offer TEXT, payment TEXT, price INTEGER,
        UNIQUE(game,offer,payment))""")
        c.execute("""CREATE TABLE IF NOT EXISTS store_settings(
        setting TEXT PRIMARY KEY, value TEXT NOT NULL)""")
        c.execute("INSERT OR IGNORE INTO store_settings(setting,value) VALUES('flexy_number',?)",
                  (WHATSAPP_NUMBER,))
        c.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, phone TEXT,
        role TEXT NOT NULL DEFAULT 'customer', trader_status TEXT NOT NULL DEFAULT 'none',
        shop_name TEXT, wilaya TEXT, municipality TEXT, business_type TEXT, monthly_volume TEXT,
        created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS wallet(
        user_id INTEGER PRIMARY KEY, balance INTEGER NOT NULL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS wallet_transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
        kind TEXT, note TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS wallet_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
        payment TEXT, status TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS trader_price_overrides(
        game TEXT, offer TEXT, payment TEXT, price INTEGER,
        UNIQUE(game,offer,payment))""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT UNIQUE, user_id INTEGER,
        username TEXT, full_name TEXT, game TEXT, offer TEXT, player_id TEXT,
        payment TEXT, price INTEGER, status TEXT, created_at TEXT, proof_file_id TEXT)""")

def get_user(uid):
    with conn() as c:
        return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def save_user(u, phone=None):
    user = u.effective_user
    with conn() as c:
        existing = c.execute("SELECT * FROM users WHERE user_id=?", (user.id,)).fetchone()
        if existing:
            c.execute("UPDATE users SET username=?, full_name=?, phone=COALESCE(?,phone) WHERE user_id=?",
                      (user.username, user.full_name, phone, user.id))
        else:
            c.execute("INSERT INTO users(user_id,username,full_name,phone,role,trader_status,created_at) "
                      "VALUES(?,?,?,?, 'customer','none',?)",
                      (user.id, user.username, user.full_name, phone, datetime.now().strftime("%Y-%m-%d %H:%M")))
        c.execute("INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)", (user.id,))

def registered(uid):
    u = get_user(uid)
    return bool(u and u["phone"])

def trader(uid):
    u = get_user(uid)
    return bool(u and u["role"] == "trader" and u["trader_status"] == "approved")

def require_registration(update):
    return registered(update.effective_user.id)

def user_menu(uid):
    rows = [
        [InlineKeyboardButton("👤 الزبائن العاديون", callback_data="role:customer")],
        [InlineKeyboardButton("🏪 أصحاب المحلات", callback_data="role:trader")],
        [InlineKeyboardButton("📋 طلباتي", callback_data="myorders")],
        [InlineKeyboardButton("📱 WhatsApp", url=f"https://wa.me/{get_setting('flexy_number', WHATSAPP_NUMBER)}")]
    ]
    if trader(uid):
        rows.insert(1, [InlineKeyboardButton("💰 رصيدي", callback_data="wallet")])
    return InlineKeyboardMarkup(rows)

def phone_request_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("📱 مشاركة رقم هاتفي", request_contact=True)]],
                               resize_keyboard=True, one_time_keyboard=True)

def admin(uid):
    return ADMIN_ID is not None and uid == ADMIN_ID

def menu():
    rows = []
    for i in range(0, len(GAMES), 2):
        row = [InlineKeyboardButton(GAMES[i], callback_data="game:" + GAMES[i])]
        if i + 1 < len(GAMES):
            row.append(InlineKeyboardButton(GAMES[i+1], callback_data="game:" + GAMES[i+1]))
        rows.append(row)
    rows += [
        [InlineKeyboardButton("📋 طلباتي", callback_data="myorders")],
        [InlineKeyboardButton("📞 التواصل مع الإدارة", callback_data="contact")],
        [InlineKeyboardButton("📱 تواصل عبر WhatsApp", url=f"https://wa.me/{get_setting('flexy_number', WHATSAPP_NUMBER)}")],
        [InlineKeyboardButton("⬅️ الأقسام الرئيسية", callback_data="home")]
    ]
    return InlineKeyboardMarkup(rows)

def back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="home")]])

def payment_menu(uid=None):
    options = list(PAYMENTS)
    if uid is not None and trader(uid):
        options.append("رصيد المحل")
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(x, callback_data="pay:" + x)] for x in options] +
        [[InlineKeyboardButton("⬅️ رجوع", callback_data="back_packages")]]
    )

def admin_buttons(oid):
    return InlineKeyboardMarkup([
      [InlineKeyboardButton("💳 بانتظار الدفع", callback_data=f"status:{oid}:بانتظار الدفع"),
       InlineKeyboardButton("✅ تم الدفع", callback_data=f"status:{oid}:مدفوع")],
      [InlineKeyboardButton("⚙️ قيد التنفيذ", callback_data=f"status:{oid}:قيد التنفيذ"),
       InlineKeyboardButton("🎉 مكتمل", callback_data=f"status:{oid}:مكتمل")],
      [InlineKeyboardButton("❌ مرفوض", callback_data=f"status:{oid}:مرفوض")]])

def get_setting(key, default=""):
    with conn() as c:
        r = c.execute("SELECT value FROM store_settings WHERE setting=?", (key,)).fetchone()
    return r["value"] if r else default

def price_for(game, offer, payment):
    with conn() as c:
        r = c.execute("SELECT price FROM price_overrides WHERE game=? AND offer=? AND payment=?",
                      (game, offer, payment)).fetchone()
    if r:
        return r["price"]
    if payment == "Flexy":
        ix = 1
    elif payment == "BaridiMob / CCP":
        ix = 0
    else:
        return None
    if game == "eFootball":
        m = re.match(r"(\d+)", offer)
        if m and int(m.group(1)) in EF_PRICES:
            return EF_PRICES[int(m.group(1))][ix]
    if game == "Free Fire" and offer in FF_PRICES:
        return FF_PRICES[offer][ix]
    return None

def trader_price_for(game, offer, payment):
    with conn() as c:
        r = c.execute("SELECT price FROM trader_price_overrides WHERE game=? AND offer=? AND payment=?",
                      (game, offer, payment)).fetchone()
    if r:
        return r["price"]
    return price_for(game, offer, payment)

def price_label(game, offer, payment):
    p = trader_price_for(game, offer, payment) if payment in PAYMENTS else price_for(game, offer, payment)
    return f"{p} دج" if p is not None else "السعر يحدده المتجر"

def packages_keyboard(game):
    rows = []
    for offer in PACKAGES.get(game, []):
        # عروض الباقات داخل callback قصيرة وآمنة
        rows.append([InlineKeyboardButton(offer, callback_data="offer:" + offer)])
    rows.append([InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def package_prices_keyboard(game, payment):
    rows = []
    for offer in PACKAGES.get(game, []):
        label = f"{offer} — {price_label(game, offer, payment)}"
        rows.append([InlineKeyboardButton(label, callback_data="offer:" + offer)])
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back_packages")])
    return InlineKeyboardMarkup(rows)

def payment_details(payment):
    if payment == "رصيد المحل":
        return "💰 سيتم خصم قيمة الطلب من رصيد المحل بعد التأكيد."
    flexy_number = get_setting("flexy_number", WHATSAPP_NUMBER)
    if payment == "Flexy":
        return (f"🔵 معلومات الدفع عبر Flexy\n📱 الرقم الذي ترسل إليه: {flexy_number}\n"
                "بعد التحويل، أرسل صورة وصل الدفع داخل البوت.")
    if payment == "BaridiMob / CCP":
        return (f"🟢 معلومات الدفع عبر BaridiMob / CCP\n\n"
                f"📮 BaridiMob / RIP: {BARIDIMOB_RIP}\n👤 اسم صاحب الحساب: {BARIDIMOB_NAME}\n\n"
                f"🏦 CCP: {CCP_NUMBER}\n🔑 المفتاح: {CCP_KEY}\n👤 اسم صاحب الحساب: {CCP_NAME}\n\n"
                "بعد التحويل، أرسل صورة وصل الدفع داخل البوت.")
    return "ستؤكد الإدارة معلومات الدفع المناسبة معك."

def whatsapp_keyboard():
    number = get_setting("flexy_number", WHATSAPP_NUMBER)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 تواصل معنا عبر WhatsApp", url=f"https://wa.me/{number}")],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="home")]
    ])

def order_text(r):
    price = str(r["price"]) + " دج" if r["price"] is not None else "يحدده المتجر"
    return (f"🛒 طلب {r['order_no']} — {STORE}\n\n👤 {r['full_name'] or '—'}"
    f" (@{r['username'] or 'بدون username'})\n🆔 Telegram ID: {r['user_id']}\n"
    f"🎮 الخدمة: {r['game']}\n💎 العرض: {r['offer']}\n🪪 معرّف الشحن: {r['player_id'] or '—'}\n"
    f"💳 الدفع: {r['payment'] or '—'}\n💰 السعر: {price}\n"
    f"📌 الحالة: {r['status']}\n🕒 {r['created_at']}")

async def start(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = get_user(u.effective_user.id)
    if not user or not user["phone"]:
        ctx.user_data.clear()
        ctx.user_data["awaiting"] = "phone"
        return await u.message.reply_text(
            f"🎮 أهلاً بك في {STORE}!\\nللمتابعة، شارك رقم هاتفك مرة واحدة بالضغط على الزر أدناه.\\n"
            "لن يُطلب منك الرقم في كل طلب. لا ترسل أي كلمة مرور أو رمز تحقق.",
            reply_markup=phone_request_keyboard())
    await u.message.reply_text(f"🎮 أهلاً بك مجددًا في {STORE}!\\nاختر القسم:", reply_markup=user_menu(u.effective_user.id))

async def myid(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(f"Telegram ID: {u.effective_user.id}\nضع الرقم في ADMIN_ID على FadeHost إذا كنت مالك المتجر.")

async def cancel(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    if not registered(u.effective_user.id):
        ctx.user_data["awaiting"] = "phone"
        return await u.message.reply_text("يجب إكمال التسجيل بمشاركة رقم الهاتف للمتابعة.",
                                          reply_markup=phone_request_keyboard())
    await u.message.reply_text("تم إلغاء الخطوة الحالية.", reply_markup=user_menu(u.effective_user.id))

async def admin_help(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    await u.message.reply_text(
        "🛠️ أوامر إدارة SERADJ STORE:\n"
        "/orders — آخر 10 طلبات\n/stats — إحصائيات الطلبات\n"
        "/setprice اللعبة | العرض | الدفع | السعر\n"
        "مثال:\n/setprice PUBG Mobile | 60 UC | BaridiMob / CCP | 250\n"
        "/setflexy 213XXXXXXXXX — تغيير رقم Flexy وWhatsApp\n"
        "/paymentinfo — عرض معلومات الدفع\\n"
        "/traders — طلبات التجار الجديدة\\n"
        "/settraderprice اللعبة | العرض | الدفع | السعر\\n"
        "/walletadd TelegramID | المبلغ | ملاحظة — إضافة رصيد بعد التحقق من الدفع\\n"
        "/walletrequests — طلبات شحن الرصيد")

async def orders_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    with conn() as c:
        rs = c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10").fetchall()
    if not rs:
        return await u.message.reply_text("لا توجد طلبات.")
    for r in rs:
        await u.message.reply_text(order_text(r), reply_markup=admin_buttons(r["id"]))

async def stats_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    with conn() as c:
        total = c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"]
        done = c.execute("SELECT COUNT(*) n FROM orders WHERE status='مكتمل'").fetchone()["n"]
        pending = c.execute("SELECT COUNT(*) n FROM orders WHERE status NOT IN ('مكتمل','مرفوض')").fetchone()["n"]
    await u.message.reply_text(f"📊 {STORE}\nكل الطلبات: {total}\nقيد المتابعة: {pending}\nمكتملة: {done}")

async def setprice_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    raw = u.message.text.partition(" ")[2]
    parts = [x.strip() for x in raw.split("|")]
    if len(parts) != 4 or not parts[3].isdigit():
        return await u.message.reply_text(
            "الصيغة:\n/setprice اللعبة | العرض | الدفع | السعر\n"
            "طرق الدفع: BaridiMob / CCP أو Flexy")
    game, offer, pay, amount = parts
    if game not in GAMES or pay not in PAYMENTS:
        return await u.message.reply_text("اسم اللعبة أو طريقة الدفع غير صحيحة. استعمل الأسماء الظاهرة في القائمة.")
    if offer not in PACKAGES.get(game, []):
        return await u.message.reply_text("اسم العرض غير موجود في قائمة هذه الخدمة.")
    with conn() as c:
        c.execute("INSERT INTO price_overrides VALUES(?,?,?,?) "
                  "ON CONFLICT(game,offer,payment) DO UPDATE SET price=excluded.price",
                  (game, offer, pay, int(amount)))
    await u.message.reply_text(f"✅ تم حفظ السعر:\n{game} / {offer} / {pay} = {amount} دج")

async def setflexy_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    parts = u.message.text.split(maxsplit=1)
    if len(parts) != 2:
        return await u.message.reply_text("الصيغة: /setflexy 213XXXXXXXXX (أرقام فقط، دون +)")
    number = re.sub(r"[^0-9]", "", parts[1])
    if len(number) < 9 or len(number) > 15:
        return await u.message.reply_text("الرقم غير صحيح. أرسله مع رمز الدولة، أرقام فقط.")
    with conn() as c:
        c.execute("INSERT INTO store_settings(setting,value) VALUES('flexy_number',?) "
                  "ON CONFLICT(setting) DO UPDATE SET value=excluded.value", (number,))
    await u.message.reply_text(f"✅ تم تحديث رقم Flexy وWhatsApp إلى: {number}")

async def paymentinfo_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    await u.message.reply_text(payment_details("BaridiMob / CCP") + "\n\n" + payment_details("Flexy"),
                               reply_markup=whatsapp_keyboard())

async def traders_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    with conn() as c:
        rs = c.execute("SELECT * FROM users WHERE trader_status='pending' ORDER BY created_at").fetchall()
    if not rs:
        return await u.message.reply_text("لا توجد طلبات تجار قيد المراجعة.")
    for r in rs:
        text = (f"🏪 طلب تاجر\\nالاسم: {r['full_name']}\\nالهاتف: {r['phone']}\\n"
                f"المحل: {r['shop_name']}\\nالولاية: {r['wilaya']} / {r['municipality']}\\n"
                f"النشاط: {r['business_type']}\\nالحجم الشهري: {r['monthly_volume']}\\nID: {r['user_id']}")
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ قبول", callback_data=f"trader:{r['user_id']}:approved"),
            InlineKeyboardButton("❌ رفض", callback_data=f"trader:{r['user_id']}:rejected")
        ]])
        await u.message.reply_text(text, reply_markup=kb)

async def settraderprice_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    parts = [x.strip() for x in u.message.text.partition(" ")[2].split("|")]
    if len(parts) != 4 or not parts[3].isdigit():
        return await u.message.reply_text("الصيغة: /settraderprice اللعبة | العرض | الدفع | السعر")
    game, offer, pay, amount = parts
    if game not in GAMES or pay not in PAYMENTS or offer not in PACKAGES.get(game, []):
        return await u.message.reply_text("تأكد من اسم اللعبة والعرض وطريقة الدفع.")
    with conn() as c:
        c.execute("INSERT INTO trader_price_overrides VALUES(?,?,?,?) "
                  "ON CONFLICT(game,offer,payment) DO UPDATE SET price=excluded.price",
                  (game, offer, pay, int(amount)))
    await u.message.reply_text(f"✅ سعر التاجر محفوظ: {game} / {offer} / {pay} = {amount} دج")

async def walletadd_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    parts = [x.strip() for x in u.message.text.partition(" ")[2].split("|")]
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit() or int(parts[1]) <= 0:
        return await u.message.reply_text("الصيغة: /walletadd TelegramID | المبلغ | ملاحظة")
    uid, amount = int(parts[0]), int(parts[1])
    note = parts[2] if len(parts) > 2 else "إضافة رصيد بعد التحقق"
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)", (uid,))
        c.execute("UPDATE wallet SET balance=balance+? WHERE user_id=?", (amount, uid))
        c.execute("INSERT INTO wallet_transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",
                  (uid, amount, "credit", note, datetime.now().strftime("%Y-%m-%d %H:%M")))
        bal = c.execute("SELECT balance FROM wallet WHERE user_id=?", (uid,)).fetchone()["balance"]
    try:
        await ctx.bot.send_message(uid, f"✅ أُضيف {amount} دج إلى رصيدك.\\nرصيدك الحالي: {bal} دج")
    except Exception:
        pass
    await u.message.reply_text(f"تمت إضافة {amount} دج للحساب {uid}. الرصيد الحالي: {bal} دج")

async def walletrequests_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    with conn() as c:
        rs = c.execute("SELECT * FROM wallet_requests WHERE status='pending' ORDER BY id DESC LIMIT 20").fetchall()
    if not rs:
        return await u.message.reply_text("لا توجد طلبات شحن رصيد معلقة.")
    for r in rs:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ قبول وإضافة الرصيد", callback_data=f"walletreq:{r['id']}:approve"),
            InlineKeyboardButton("❌ رفض", callback_data=f"walletreq:{r['id']}:reject")
        ]])
        await u.message.reply_text(f"💰 طلب شحن رصيد #{r['id']}\\nUser ID: {r['user_id']}\\nالمبلغ: {r['amount']} دج\\nطريقة الدفع: {r['payment']}", reply_markup=kb)

async def buttons(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    d = q.data

    if d == "home":
        ctx.user_data.clear()
        return await q.edit_message_text(f"🎮 {STORE}\nاختر اللعبة أو الخدمة:", reply_markup=menu())

    if not registered(q.from_user.id):
        return await q.edit_message_text("للمتابعة، اكتب /start وشارك رقم هاتفك أولاً.", reply_markup=back())

    if d.startswith("role:"):
        role = d.split(":", 1)[1]
        if role == "customer":
            return await q.edit_message_text("👤 قسم الزبائن العاديين. اختر اللعبة أو الخدمة:", reply_markup=menu())
        if role == "trader":
            urow = get_user(q.from_user.id)
            if trader(q.from_user.id):
                with conn() as c:
                    balrow = c.execute("SELECT balance FROM wallet WHERE user_id=?", (q.from_user.id,)).fetchone()
                bal = balrow["balance"] if balrow else 0
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛍️ أسعار وطلبات التجار", callback_data="trader_catalog")],
                    [InlineKeyboardButton(f"💰 رصيدي: {bal} دج", callback_data="wallet")],
                    [InlineKeyboardButton("➕ طلب شحن الرصيد", callback_data="wallet_add")],
                    [InlineKeyboardButton("⬅️ رجوع", callback_data="home")]
                ])
                return await q.edit_message_text("🏪 أهلاً بك في قسم التجار.", reply_markup=kb)
            if urow and urow["trader_status"] == "pending":
                return await q.edit_message_text("⏳ طلبك قيد المراجعة. إلى حين الموافقة، استخدم قسم الزبائن العاديين.", reply_markup=user_menu(q.from_user.id))
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📩 تقديم طلب تاجر", callback_data="trader_apply")],
                                       [InlineKeyboardButton("⬅️ رجوع", callback_data="home")]])
            return await q.edit_message_text("🏪 تريد الاستفادة من أسعار خاصة بالمحلات؟ قدم طلب الانضمام، وستراجعه الإدارة.", reply_markup=kb)

    if d == "trader_apply":
        ctx.user_data["awaiting"] = "trader_shop"
        ctx.user_data["trader_form"] = {}
        return await q.edit_message_text("اكتب اسم المحل.")

    if d == "trader_catalog":
        if not trader(q.from_user.id):
            return await q.edit_message_text("هذا القسم متاح للتجار المقبولين فقط.", reply_markup=back())
        return await q.edit_message_text("اختر اللعبة أو الخدمة للحصول على أسعار التاجر:", reply_markup=menu())

    if d == "wallet":
        if not trader(q.from_user.id):
            return await q.edit_message_text("رصيد المحلات متاح للتجار المقبولين فقط.", reply_markup=back())
        with conn() as c:
            row = c.execute("SELECT balance FROM wallet WHERE user_id=?", (q.from_user.id,)).fetchone()
            tx = c.execute("SELECT amount,kind,note,created_at FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 5", (q.from_user.id,)).fetchall()
        balance = row["balance"] if row else 0
        hist = "\\n".join([f"{x['created_at']}: {x['kind']} {x['amount']} دج — {x['note']}" for x in tx]) or "لا توجد عمليات بعد."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("➕ طلب شحن الرصيد", callback_data="wallet_add")],
                                   [InlineKeyboardButton("⬅️ رجوع", callback_data="role:trader")]])
        return await q.edit_message_text(f"💰 رصيدك الحالي: {balance} دج\\n\\nآخر العمليات:\\n{hist}", reply_markup=kb)

    if d == "wallet_add":
        if not trader(q.from_user.id):
            return await q.edit_message_text("طلب شحن الرصيد متاح للتجار المقبولين فقط.", reply_markup=back())
        ctx.user_data["awaiting"] = "wallet_amount"
        return await q.edit_message_text("أرسل مبلغ شحن الرصيد بالدينار (100 دج على الأقل).")

    if d.startswith("trader:"):
        if not admin(q.from_user.id):
            return await q.answer("هذا الإجراء للإدارة فقط.", show_alert=True)
        _, uid_text, result = d.split(":", 2)
        uid = int(uid_text)
        with conn() as c:
            if result == "approved":
                c.execute("UPDATE users SET role='trader', trader_status='approved' WHERE user_id=?", (uid,))
                c.execute("INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)", (uid,))
                message = "🎉 تم قبول طلبك! أصبح حسابك حساب تاجر في SERADJ STORE."
            else:
                c.execute("UPDATE users SET role='customer', trader_status='rejected' WHERE user_id=?", (uid,))
                message = "تم رفض طلب الانضمام للتجار حاليًا. يمكنك استخدام قسم الزبائن العاديين."
        try:
            await ctx.bot.send_message(uid, message, reply_markup=user_menu(uid))
        except Exception:
            pass
        return await q.edit_message_text(f"تم تحديث حالة طلب التاجر إلى: {result}.")

    if d.startswith("walletreq:"):
        if not admin(q.from_user.id):
            return await q.answer("هذا الإجراء للإدارة فقط.", show_alert=True)
        _, rid_text, action = d.split(":", 2)
        rid = int(rid_text)
        with conn() as c:
            req = c.execute("SELECT * FROM wallet_requests WHERE id=?", (rid,)).fetchone()
            if not req or req["status"] != "pending":
                return await q.edit_message_text("تمت معالجة هذا الطلب سابقًا.")
            if action == "approve":
                c.execute("UPDATE wallet_requests SET status='approved' WHERE id=?", (rid,))
                c.execute("INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)", (req["user_id"],))
                c.execute("UPDATE wallet SET balance=balance+? WHERE user_id=?", (req["amount"], req["user_id"]))
                c.execute("INSERT INTO wallet_transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",
                          (req["user_id"], req["amount"], "credit", f"طلب شحن رصيد #{rid}", datetime.now().strftime("%Y-%m-%d %H:%M")))
                bal = c.execute("SELECT balance FROM wallet WHERE user_id=?", (req["user_id"],)).fetchone()["balance"]
                notice = f"✅ تمت الموافقة على شحن رصيدك بمبلغ {req['amount']} دج. رصيدك الحالي: {bal} دج."
            else:
                c.execute("UPDATE wallet_requests SET status='rejected' WHERE id=?", (rid,))
                notice = f"❌ تم رفض طلب شحن الرصيد #{rid}. تواصل مع الإدارة عند الحاجة."
        try:
            await ctx.bot.send_message(req["user_id"], notice)
        except Exception:
            pass
        return await q.edit_message_text(f"تمت معالجة طلب شحن الرصيد #{rid}: {action}.")

    if d == "contact":
        return await q.edit_message_text("📱 تواصل مع إدارة SERADJ STORE عبر WhatsApp.\nلا ترسل كلمة مرور أو رمز تحقق.",
                                         reply_markup=whatsapp_keyboard())

    if d == "myorders":
        with conn() as c:
            rs = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
                           (q.from_user.id,)).fetchall()
        if not rs:
            return await q.edit_message_text("لا توجد طلبات لهذا الحساب بعد.", reply_markup=back())
        msg = "📋 طلباتك:\n\n" + "\n\n".join(
            f"{r['order_no']} — {r['game']} / {r['offer']}\n"
            f"{str(r['price']) if r['price'] is not None else 'يحدد لاحقاً'} دج\nالحالة: {r['status']}"
            for r in rs)
        return await q.edit_message_text(msg, reply_markup=back())

    if d.startswith("status:"):
        if not admin(q.from_user.id):
            return await q.answer("غير مسموح", show_alert=True)
        _, oid, status = d.split(":", 2)
        with conn() as c:
            r = c.execute("SELECT * FROM orders WHERE id=?", (int(oid),)).fetchone()
            if not r:
                return await q.edit_message_text("الطلب غير موجود.")
            c.execute("UPDATE orders SET status=? WHERE id=?", (status, int(oid)))
            r = c.execute("SELECT * FROM orders WHERE id=?", (int(oid),)).fetchone()
        try:
            await ctx.bot.send_message(r["user_id"], f"🔔 تحديث طلبك {r['order_no']}\nالحالة الجديدة: {status}")
        except Exception:
            logging.exception("Customer notification failed")
        return await q.edit_message_text(order_text(r), reply_markup=admin_buttons(int(oid)))

    if d.startswith("game:"):
        if not registered(q.from_user.id):
            return await q.edit_message_text("للمتابعة، اكتب /start وشارك رقم هاتفك أولاً.", reply_markup=back())
        game = d.split(":", 1)[1]
        if game not in GAMES:
            return await q.edit_message_text("الخدمة غير موجودة.", reply_markup=menu())
        ctx.user_data.clear()
        ctx.user_data["order"] = {"game": game}
        return await q.edit_message_text(f"🎮 {game}\nاختر الباقة:", reply_markup=packages_keyboard(game))

    if d == "back_packages":
        o = ctx.user_data.get("order", {})
        game = o.get("game")
        if not game:
            return await q.edit_message_text("ابدأ من جديد عبر /start.", reply_markup=menu())
        return await q.edit_message_text(f"🎮 {game}\nاختر الباقة:", reply_markup=packages_keyboard(game))

    if d.startswith("offer:"):
        o = ctx.user_data.get("order")
        if not o:
            return await q.edit_message_text("انتهت الجلسة. اكتب /start.")
        offer = d.split(":", 1)[1]
        if offer not in PACKAGES.get(o.get("game"), []):
            return await q.edit_message_text("الباقة غير موجودة.", reply_markup=menu())
        o["offer"] = offer
        if o["game"] == "Free Fire":
            o["awaiting_payment_first"] = True
            return await q.edit_message_text("اختر طريقة الدفع:", reply_markup=payment_menu(q.from_user.id))
        o["price"] = None
        ctx.user_data["awaiting"] = "player_id"
        prompt = "أرسل Player ID أو المعرّف المطلوب للشحن. إذا لا يلزم اكتب: لا يوجد."
        if o["game"] in ("TikTok", "Snapchat+", "Netflix", "Azar", "App Store"):
            prompt = "أرسل المعلومات الضرورية لتفعيل/تسليم الخدمة فقط. لا ترسل كلمة مرور أو رمز تحقق."
        return await q.edit_message_text(f"اخترت: {offer}\n{prompt}", reply_markup=back())

    if d.startswith("pay:"):
        payment = d.split(":", 1)[1]
        if ctx.user_data.get("awaiting") == "wallet_payment":
            if payment not in PAYMENTS:
                return await q.edit_message_text("طريقة الدفع غير صحيحة.")
            amount = ctx.user_data.get("wallet_amount")
            if not amount or not trader(q.from_user.id):
                ctx.user_data.clear()
                return await q.edit_message_text("انتهت جلسة شحن الرصيد. ابدأ من قسم التجار.", reply_markup=user_menu(q.from_user.id))
            with conn() as c:
                cur = c.execute("INSERT INTO wallet_requests(user_id,amount,payment,status,created_at) VALUES(?,?,?,?,?)",
                                (q.from_user.id, amount, payment, "pending", datetime.now().strftime("%Y-%m-%d %H:%M")))
                rid = cur.lastrowid
            ctx.user_data.pop("awaiting", None)
            ctx.user_data.pop("wallet_amount", None)
            await q.edit_message_text(
                f"تم إنشاء طلب شحن الرصيد #{rid} بمبلغ {amount} دج عبر {payment}.\\n"
                "حوّل المبلغ ثم أرسل وصل الدفع في هذه المحادثة. لا ترسل كلمة مرور أو رمز تحقق.",
                reply_markup=whatsapp_keyboard())
            if ADMIN_ID:
                await ctx.bot.send_message(ADMIN_ID,
                    f"💰 طلب شحن رصيد جديد #{rid}\\nالمستخدم: {q.from_user.full_name}\\n"
                    f"Telegram ID: {q.from_user.id}\\nالمبلغ: {amount} دج\\nالدفع: {payment}\\n"
                    "تحقق من وصول المبلغ قبل قبول الطلب.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ قبول وإضافة الرصيد", callback_data=f"walletreq:{rid}:approve"),
                        InlineKeyboardButton("❌ رفض", callback_data=f"walletreq:{rid}:reject")
                    ]]))
            return
        o = ctx.user_data.get("order")
        if not o:
            return await q.edit_message_text("انتهت الجلسة. اكتب /start.")
        if payment not in PAYMENTS and payment != "رصيد المحل":
            return await q.edit_message_text("طريقة الدفع غير صحيحة.")
        if payment == "رصيد المحل" and not trader(q.from_user.id):
            return await q.edit_message_text("رصيد المحل متاح للتجار المقبولين فقط.")
        if payment == "رصيد المحل":
            if not trader(q.from_user.id):
                return await q.edit_message_text("رصيد المحل متاح للتجار المقبولين فقط.")
            o["payment"] = payment
            o["price"] = trader_price_for(o.get("game"), o.get("offer"), payment)
            ctx.user_data["awaiting"] = "player_id"
            return await q.edit_message_text(f"طريقة الدفع: رصيد المحل\\nالباقة: {o['offer']}\\nالسعر: {price_label(o['game'], o['offer'], payment)}\\nأرسل Player ID أو المعرّف المطلوب.")
        o["payment"] = payment
        o["price"] = trader_price_for(o.get("game"), o.get("offer"), payment) if trader(q.from_user.id) and payment != "رصيد المحل" else price_for(o.get("game"), o.get("offer"), payment)
        if o.get("awaiting_payment_first"):
            o.pop("awaiting_payment_first", None)
            ctx.user_data["awaiting"] = "player_id"
            return await q.edit_message_text(
                f"طريقة الدفع: {payment}\nالباقة: {o['offer']}\nالسعر: {price_label(o['game'], o['offer'], payment)}\n"
                "أرسل Player ID الخاص بك فقط، لا ترسل كلمة مرور أو رمز تحقق.",
                reply_markup=back())
        return await show_review_query(q, o)

    if d == "confirm":
        o = ctx.user_data.get("order")
        if not o or not o.get("offer") or not o.get("payment"):
            return await q.edit_message_text("لا يوجد طلب مكتمل للتأكيد. اكتب /start.")
        user = q.from_user
        if o.get("payment") == "رصيد المحل":
            if not trader(user.id):
                return await q.edit_message_text("رصيد المحل متاح للتجار المقبولين فقط.", reply_markup=back())
            amount = o.get("price")
            if amount is None:
                return await q.edit_message_text("لم يحدد المتجر سعر هذه الباقة بعد. تواصل مع الإدارة.", reply_markup=back())
            with conn() as c:
                row = c.execute("SELECT balance FROM wallet WHERE user_id=?", (user.id,)).fetchone()
                balance = row["balance"] if row else 0
                if balance < amount:
                    return await q.edit_message_text(
                        f"رصيدك غير كافٍ. السعر {amount} دج ورصيدك {balance} دج. يمكنك طلب شحن الرصيد من قسم التجار.",
                        reply_markup=back())
                c.execute("UPDATE wallet SET balance=balance-? WHERE user_id=?", (amount, user.id))
                c.execute("INSERT INTO wallet_transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",
                          (user.id, -amount, "debit", f"طلب {o['game']} / {o['offer']}", datetime.now().strftime("%Y-%m-%d %H:%M")))
        user = q.from_user
        no = f"SS-{datetime.utcnow().strftime('%y%m%d%H%M%S')}-{user.id%10000:04d}"
        with conn() as c:
            cur = c.execute(
                "INSERT INTO orders(order_no,user_id,username,full_name,game,offer,player_id,payment,price,status,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (no, user.id, user.username, user.full_name, o["game"], o["offer"], o.get("player_id"),
                 o.get("payment"), o.get("price"), "مدفوع" if o.get("payment") == "رصيد المحل" else "بانتظار الدفع", datetime.now().strftime("%Y-%m-%d %H:%M")))
            oid = cur.lastrowid
            r = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        try:
            if not ADMIN_ID:
                raise RuntimeError("ADMIN_ID missing")
            await ctx.bot.send_message(ADMIN_ID, order_text(r), reply_markup=admin_buttons(oid))
        except Exception:
            logging.exception("Admin notification failed")
            return await q.edit_message_text("⚠️ تعذر إشعار الإدارة. أخبر مالك المتجر بفحص ADMIN_ID.", reply_markup=back())
        ctx.user_data.clear()
        p = f"{r['price']} دج" if r["price"] is not None else "السعر يحدده المتجر"
        return await q.edit_message_text(
            f"✅ تم إرسال طلبك!\nرقم الطلب: {no}\nالسعر: {p}\nالحالة: بانتظار الدفع.\n"
            "أرسل وصل الدفع كصورة في هذه المحادثة بعد التحويل. لا ترسل كلمة مرور أو رمز تحقق.",
            reply_markup=whatsapp_keyboard())

async def show_review_query(q, o):
    p = price_label(o["game"], o["offer"], o.get("payment", ""))
    details = payment_details(o.get("payment", ""))
    msg = (f"🧾 راجع طلبك قبل التأكيد:\n\nالخدمة: {o['game']}\nالباقة: {o['offer']}\n"
           f"المعرّف/المعلومات: {o.get('player_id', '—')}\nالدفع: {o.get('payment')}\nالسعر: {p}\n\n"
           f"{details}\n\nتأكد من المعلومات ثم اضغط تأكيد. لا ترسل كلمة مرور أو رمز تحقق.")
    return await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 تواصل عبر WhatsApp", url=f"https://wa.me/{get_setting('flexy_number', WHATSAPP_NUMBER)}")],
        [InlineKeyboardButton("✅ تأكيد وإرسال", callback_data="confirm")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="home")]
    ]))

async def contact_handler(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    contact = u.message.contact
    if not contact or contact.user_id != u.effective_user.id:
        return await u.message.reply_text("من فضلك شارك رقم هاتفك من الزر الموجود في البوت، وليس رقم شخص آخر.",
                                          reply_markup=phone_request_keyboard())
    save_user(u, contact.phone_number)
    ctx.user_data.pop("awaiting", None)
    await u.message.reply_text("✅ تم تسجيل رقم هاتفك بنجاح. لن نطلبه منك مرة أخرى.", reply_markup=ReplyKeyboardRemove())
    await u.message.reply_text("اختر القسم الذي تريد الدخول إليه:", reply_markup=user_menu(u.effective_user.id))

async def text_handler(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text:
        return
    text = u.message.text.strip()
    step = ctx.user_data.get("awaiting")
    o = ctx.user_data.get("order", {})
    if not registered(u.effective_user.id):
        ctx.user_data["awaiting"] = "phone"
        return await u.message.reply_text("للمتابعة، شارك رقم هاتفك عبر الزر أدناه.", reply_markup=phone_request_keyboard())
    if step == "trader_shop":
        ctx.user_data["trader_form"] = {"shop_name": text[:100]}
        ctx.user_data["awaiting"] = "trader_wilaya"
        return await u.message.reply_text("اكتب الولاية والبلدية (مثال: الجزائر، باب الوادي).")
    if step == "trader_wilaya":
        bits = [x.strip() for x in text.split(",", 1)]
        ctx.user_data["trader_form"]["wilaya"] = bits[0][:80]
        ctx.user_data["trader_form"]["municipality"] = bits[1][:80] if len(bits) > 1 else "غير محددة"
        ctx.user_data["awaiting"] = "trader_business"
        return await u.message.reply_text("ما نوع نشاطك التجاري؟")
    if step == "trader_business":
        ctx.user_data["trader_form"]["business_type"] = text[:120]
        ctx.user_data["awaiting"] = "trader_volume"
        return await u.message.reply_text("ما حجم الشحن المتوقع شهريًا؟ (مثال: أقل من 20 طلب)")
    if step == "trader_volume":
        form = ctx.user_data.pop("trader_form", {})
        form["monthly_volume"] = text[:120]
        user = get_user(u.effective_user.id)
        with conn() as c:
            c.execute("UPDATE users SET trader_status='pending', shop_name=?, wilaya=?, municipality=?, business_type=?, monthly_volume=? WHERE user_id=?",
                      (form.get("shop_name"), form.get("wilaya"), form.get("municipality"),
                       form.get("business_type"), form.get("monthly_volume"), u.effective_user.id))
        ctx.user_data.pop("awaiting", None)
        await u.message.reply_text("✅ وصل طلبك للإدارة. إلى حين الموافقة، يمكنك استخدام قسم الزبائن العاديين.", reply_markup=user_menu(u.effective_user.id))
        if ADMIN_ID:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ قبول", callback_data=f"trader:{u.effective_user.id}:approved"),
                InlineKeyboardButton("❌ رفض", callback_data=f"trader:{u.effective_user.id}:rejected")
            ]])
            await ctx.bot.send_message(ADMIN_ID,
                f"🏪 طلب تاجر جديد\\nالاسم: {user['full_name']}\\nالهاتف: {user['phone']}\\n"
                f"المحل: {form.get('shop_name')}\\nالولاية/البلدية: {form.get('wilaya')} / {form.get('municipality')}\\n"
                f"النشاط: {form.get('business_type')}\\nالحجم الشهري: {form.get('monthly_volume')}\\n"
                f"Telegram ID: {u.effective_user.id}", reply_markup=kb)
        return
    if step == "wallet_amount":
        if not text.isdigit() or int(text) < 100:
            return await u.message.reply_text("أرسل مبلغًا صحيحًا بالدينار (100 دج على الأقل).")
        ctx.user_data["wallet_amount"] = int(text)
        ctx.user_data["awaiting"] = "wallet_payment"
        return await u.message.reply_text("اختر طريقة دفع طلب شحن الرصيد:", reply_markup=payment_menu(u.effective_user.id))
    if step == "player_id":
        if any(x in text.lower() for x in ["password", "mot de passe", "كلمة السر", "كلمة المرور", "رمز التحقق", "otp"]):
            return await u.message.reply_text("🔒 لا ترسل كلمة مرور أو رمز تحقق. أرسل المعرّف المطلوب فقط.")
        o["player_id"] = text[:160]
        ctx.user_data.pop("awaiting", None)
        if not o.get("payment"):
            ctx.user_data["awaiting"] = "payment"
            return await u.message.reply_text("اختر طريقة الدفع:", reply_markup=payment_menu(u.effective_user.id))
        return await show_review_message(u, o)
    await u.message.reply_text("استعمل الأزرار أو اكتب /start.", reply_markup=user_menu(u.effective_user.id))

async def show_review_message(u, o):
    p = price_label(o["game"], o["offer"], o.get("payment", ""))
    details = payment_details(o.get("payment", ""))
    msg = (f"🧾 راجع طلبك قبل التأكيد:\n\nالخدمة: {o['game']}\nالباقة: {o['offer']}\n"
           f"المعرّف/المعلومات: {o.get('player_id', '—')}\nالدفع: {o.get('payment')}\nالسعر: {p}\n\n"
           f"{details}\n\nتأكد من المعلومات ثم اضغط تأكيد. لا ترسل كلمة مرور أو رمز تحقق.")
    return await u.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 تواصل عبر WhatsApp", url=f"https://wa.me/{get_setting('flexy_number', WHATSAPP_NUMBER)}")],
        [InlineKeyboardButton("✅ تأكيد وإرسال", callback_data="confirm")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="home")]
    ]))

async def photo_handler(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID:
        return await u.message.reply_text("تعذر إرسال الوصل للإدارة حالياً.")
    user = u.effective_user
    with conn() as c:
        r = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1", (user.id,)).fetchone()
    if not r:
        return await u.message.reply_text("لم أجد طلباً سابقاً. ابدأ عبر /start.")
    try:
        await ctx.bot.send_photo(
            ADMIN_ID, u.message.photo[-1].file_id,
            caption=f"🧾 وصل دفع — الطلب {r['order_no']}\nالزبون: {user.full_name} / {user.id}\n"
                    "تحقق من الوصل يدوياً قبل تأكيد الدفع.",
            reply_markup=admin_buttons(r["id"]))
        with conn() as c:
            c.execute("UPDATE orders SET proof_file_id=? WHERE id=?", (u.message.photo[-1].file_id, r["id"]))
        await u.message.reply_text("✅ أُرسل الوصل للإدارة. هذا لا يعني أن الدفع تأكد بعد.")
    except Exception:
        logging.exception("Proof forwarding failed")
        await u.message.reply_text("تعذر إرسال الوصل. حاول لاحقاً.")

async def errors(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logging.error("Unhandled bot error: %s", ctx.error)

def main():
    if not TOKEN:
        raise RuntimeError("Missing BOT_TOKEN environment variable.")
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("admin", admin_help))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("setprice", setprice_cmd))
    app.add_handler(CommandHandler("setflexy", setflexy_cmd))
    app.add_handler(CommandHandler("paymentinfo", paymentinfo_cmd))
    app.add_handler(CommandHandler("traders", traders_cmd))
    app.add_handler(CommandHandler("settraderprice", settraderprice_cmd))
    app.add_handler(CommandHandler("walletadd", walletadd_cmd))
    app.add_handler(CommandHandler("walletrequests", walletrequests_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(errors)
    app.run_polling(drop_pending_updates=False)

if __name__ == "__main__":
    main()

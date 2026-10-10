import os, sqlite3, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_TEXT = os.getenv("ADMIN_ID", "").strip()
ADMIN_ID = int(ADMIN_TEXT) if ADMIN_TEXT.isdigit() else None
DB_PATH = os.getenv("DB_PATH", "seradj_store.db")
STORE = "SERADJ STORE"

GAMES = ["Free Fire","PUBG Mobile","Call of Duty Mobile","eFootball","FC Mobile","Brawl Stars",
"Roblox","One State","TikTok","Blood Strike","Snapchat+","Facebook / Instagram","WhatsApp",
"Netflix","App Store","Azar","SoulChill","Tango","Super Live","خدمة أخرى"]

PAYMENTS = ["BaridiMob","CCP","Flexy","أتواصل مع الإدارة لتحديد الدفع"]
FF_PAYMENTS = ["BaridiMob / CCP", "Flexy"]

EF = [(300,750,900),(550,1300,1550),(750,1700,2050),(1040,2300,2750),
      (2130,4600,5500),(3250,6600,7900),(5700,11500,13500),(12800,22000,25500)]

# Free Fire prices: (offer, BaridiMob/CCP price, Flexy price)
FF_PRICES = [
    ("110 Diamonds", 280, 330),
    ("231 Diamonds", 550, 680),
    ("583 Diamonds", 1350, 1700),
    ("1188 Diamonds", 2700, 3250),
    ("2420 Diamonds", 5400, 6500),
    ("الاشتراك الأسبوعي", 700, 850),
    ("الاشتراك الشهري", 3000, 3600),
]

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

def admin(uid):
    return ADMIN_ID is not None and uid == ADMIN_ID

def menu():
    rows = []
    for i in range(0, len(GAMES), 2):
        row = [InlineKeyboardButton(GAMES[i], callback_data="game:" + GAMES[i])]
        if i + 1 < len(GAMES):
            row.append(InlineKeyboardButton(GAMES[i+1], callback_data="game:" + GAMES[i+1]))
        rows.append(row)
    rows += [[InlineKeyboardButton("📋 طلباتي", callback_data="myorders")],
             [InlineKeyboardButton("📞 التواصل مع الإدارة", callback_data="contact")]]
    return InlineKeyboardMarkup(rows)

def back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="home")]])

def payment_menu(game=None):
    choices = FF_PAYMENTS if game == "Free Fire" else PAYMENTS
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(x, callback_data="pay:" + x)] for x in choices] +
        [[InlineKeyboardButton("⬅️ رجوع", callback_data="home")]]
    )

def admin_buttons(oid):
    return InlineKeyboardMarkup([
      [InlineKeyboardButton("💳 بانتظار الدفع", callback_data=f"status:{oid}:بانتظار الدفع"),
       InlineKeyboardButton("✅ تم الدفع", callback_data=f"status:{oid}:مدفوع")],
      [InlineKeyboardButton("⚙️ قيد التنفيذ", callback_data=f"status:{oid}:قيد التنفيذ"),
       InlineKeyboardButton("🎉 مكتمل", callback_data=f"status:{oid}:مكتمل")],
      [InlineKeyboardButton("❌ مرفوض", callback_data=f"status:{oid}:مرفوض")]])

def price_for(game, offer, payment):
    with conn() as c:
        r = c.execute("SELECT price FROM price_overrides WHERE game=? AND offer=? AND payment=?",
                      (game, offer, payment)).fetchone()
    if r:
        return r["price"]
    if game == "eFootball":
        try:
            coins = int(offer.split()[0])
        except (ValueError, IndexError):
            return None
        for n, b, f in EF:
            if coins == n:
                if payment == "Flexy":
                    return f
                if payment in ("BaridiMob", "CCP", "BaridiMob / CCP"):
                    return b
    if game == "Free Fire":
        for ff_offer, b, f in FF_PRICES:
            if offer == ff_offer:
                if payment == "Flexy":
                    return f
                if payment == "BaridiMob / CCP":
                    return b
    return None

def order_text(r):
    price = str(r["price"]) + " دج" if r["price"] is not None else "يحدده المتجر"
    return (f"🛒 طلب {r['order_no']} — {STORE}\n\n👤 {r['full_name'] or '—'}"
    f" (@{r['username'] or 'بدون username'})\n🆔 Telegram ID: {r['user_id']}\n"
    f"🎮 الخدمة: {r['game']}\n💎 العرض: {r['offer']}\n🪪 معرّف الشحن: {r['player_id'] or '—'}\n"
    f"💳 الدفع: {r['payment'] or '—'}\n💰 السعر: {price}\n"
    f"📌 الحالة: {r['status']}\n🕒 {r['created_at']}")

async def start(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await u.message.reply_text(
        f"🎮 أهلاً بك في {STORE}!\nاختر اللعبة أو الخدمة.\n\n"
        "🔒 لا ترسل كلمة مرور أو رمز تحقق أبداً. نطلب فقط Player ID أو المعلومات الضرورية للشحن.",
        reply_markup=menu())

async def myid(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(f"Telegram ID: {u.effective_user.id}\nضع الرقم في ADMIN_ID على FadeHost إذا كنت مالك المتجر.")

async def cancel(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await u.message.reply_text("تم إلغاء الخطوة الحالية.", reply_markup=menu())

async def admin_help(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not admin(u.effective_user.id):
        return await u.message.reply_text("هذا الأمر للإدارة فقط.")
    await u.message.reply_text(
        "أوامر الإدارة:\n/orders — آخر 10 طلبات\n/stats — إحصائيات\n"
        "/setprice اللعبة | العرض | الدفع | السعر\nمثال:\n"
        "/setprice Free Fire | 110 Diamonds | BaridiMob / CCP | 280")

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
    parts = [x.strip() for x in u.message.text.partition(" ")[2].split("|")]
    if len(parts) != 4 or not parts[3].isdigit():
        return await u.message.reply_text("الصيغة:\n/setprice اللعبة | العرض | الدفع | السعر")
    game, offer, pay, amount = parts
    allowed_payments = set(PAYMENTS + FF_PAYMENTS)
    if pay not in allowed_payments:
        return await u.message.reply_text("طريقة الدفع غير صحيحة.")
    with conn() as c:
        c.execute("INSERT INTO price_overrides VALUES(?,?,?,?) "
                  "ON CONFLICT(game,offer,payment) DO UPDATE SET price=excluded.price",
                  (game, offer, pay, int(amount)))
    await u.message.reply_text(f"✅ تم حفظ السعر: {game} / {offer} / {pay} = {amount} دج")

async def buttons(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    d = q.data

    if d == "home":
        ctx.user_data.clear()
        return await q.edit_message_text(f"🎮 {STORE}\nاختر الخدمة:", reply_markup=menu())

    if d == "contact":
        return await q.edit_message_text(
            "📞 أرسل طلبك أولاً وستتواصل معك الإدارة. لا ترسل كلمة مرور أو رمز تحقق.",
            reply_markup=back())

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
        game = d.split(":", 1)[1]
        ctx.user_data.clear()
        ctx.user_data["order"] = {"game": game}
        if game == "eFootball":
            rows = [[InlineKeyboardButton(f"{n} Coins", callback_data=f"coins:{n}")] for n, _, _ in EF]
            rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="home")])
            return await q.edit_message_text("⚽ اختر باقة eFootball:", reply_markup=InlineKeyboardMarkup(rows))
        if game == "Free Fire":
            return await q.edit_message_text(
                "🔥 Free Fire — اختر طريقة الدفع:\n\n"
                "🟢 BaridiMob / CCP\n🔵 Flexy",
                reply_markup=payment_menu(game))
        ctx.user_data["awaiting"] = "offer"
        return await q.edit_message_text(
            f"اخترت {game}.\nاكتب اسم العرض أو الكمية المطلوبة. السعر النهائي يؤكده المتجر.",
            reply_markup=back())

    if d.startswith("coins:"):
        n = int(d.split(":")[1])
        ctx.user_data["order"]["offer"] = f"{n} Coins"
        ctx.user_data["awaiting"] = "player_id"
        return await q.edit_message_text(f"اخترت {n} Coins.\nأرسل Player ID فقط، لا ترسل كلمة المرور.", reply_markup=back())

    if d.startswith("pay:"):
        o = ctx.user_data.get("order")
        if not o:
            return await q.edit_message_text("انتهت الجلسة. اكتب /start.")
        payment = d.split(":", 1)[1]
        o["payment"] = payment
        if o.get("game") == "Free Fire":
            rows = []
            for offer, b, f in FF_PRICES:
                price = f if payment == "Flexy" else b
                rows.append([InlineKeyboardButton(f"{offer} — {price} دج", callback_data="ffoffer:" + offer)])
            rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="game:Free Fire")])
            title = "🔵" if payment == "Flexy" else "🟢"
            return await q.edit_message_text(
                f"{title} Free Fire — {payment}\nاختر الباقة:",
                reply_markup=InlineKeyboardMarkup(rows))
        o["price"] = price_for(o["game"], o["offer"], payment)
        p = f"{o['price']} دج" if o["price"] is not None else "يؤكده المتجر قبل الدفع"
        msg = (f"🧾 راجع طلبك:\n\nالخدمة: {o['game']}\nالعرض: {o['offer']}\n"
               f"معرّف الشحن: {o.get('player_id','—')}\nالدفع: {o['payment']}\nالسعر: {p}\n\n"
               "لا ترسل كلمة مرور أو رمز تحقق.")
        return await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد وإرسال", callback_data="confirm")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="home")]]))

    if d.startswith("ffoffer:"):
        o = ctx.user_data.get("order")
        if not o or o.get("game") != "Free Fire" or not o.get("payment"):
            return await q.edit_message_text("انتهت الجلسة. اكتب /start.")
        offer = d.split(":", 1)[1]
        o["offer"] = offer
        o["price"] = price_for("Free Fire", offer, o["payment"])
        o["awaiting_player_id"] = True
        ctx.user_data["awaiting"] = "player_id"
        return await q.edit_message_text(
            f"اخترت: {offer}\nالسعر: {o['price']} دج\n\nأرسل Player ID الخاص بك فقط.\n"
            "لا ترسل كلمة مرور أو رمز تحقق.",
            reply_markup=back())

    if d == "confirm":
        o = ctx.user_data.get("order")
        if not o:
            return await q.edit_message_text("لا يوجد طلب قيد التأكيد. اكتب /start.")
        user = q.from_user
        no = f"SS-{datetime.utcnow().strftime('%y%m%d%H%M%S')}-{user.id%10000:04d}"
        with conn() as c:
            cur = c.execute(
                "INSERT INTO orders(order_no,user_id,username,full_name,game,offer,player_id,payment,price,status,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (no, user.id, user.username, user.full_name, o["game"], o["offer"], o.get("player_id"),
                 o.get("payment"), o.get("price"), "بانتظار الدفع", datetime.now().strftime("%Y-%m-%d %H:%M")))
            oid = cur.lastrowid
            r = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        try:
            if not ADMIN_ID:
                raise RuntimeError("ADMIN_ID missing")
            await ctx.bot.send_message(ADMIN_ID, order_text(r), reply_markup=admin_buttons(oid))
        except Exception:
            logging.exception("Admin notification failed")
            return await q.edit_message_text(
                "⚠️ تعذر إشعار الإدارة. أخبر مالك المتجر بفحص ADMIN_ID.", reply_markup=back())
        ctx.user_data.clear()
        p = f"{r['price']} دج" if r["price"] is not None else "يحدده المتجر"
        return await q.edit_message_text(
            f"✅ تم إرسال طلبك!\nرقم الطلب: {no}\nالسعر: {p}\nالحالة: بانتظار الدفع.\n"
            "ستتواصل معك الإدارة. لا ترسل كلمة مرور أو رمز تحقق.",
            reply_markup=back())

async def text_handler(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text:
        return
    text = u.message.text.strip()
    step = ctx.user_data.get("awaiting")
    o = ctx.user_data.get("order", {})
    if step == "offer":
        o["offer"] = text[:120]
        ctx.user_data["awaiting"] = "player_id"
        return await u.message.reply_text(
            "أرسل Player ID أو المعرّف الضروري للشحن. إن لم يلزم اكتب «لا يوجد». "
            "لا ترسل كلمة مرور أو رمز تحقق.")
    if step == "player_id":
        if any(x in text.lower() for x in ["password", "mot de passe", "كلمة السر", "كلمة المرور"]):
            return await u.message.reply_text("🔒 لا ترسل كلمة مرور. أرسل Player ID فقط أو «لا يوجد».")
        o["player_id"] = text[:160]
        ctx.user_data.pop("awaiting", None)
        if o.get("game") == "Free Fire":
            # Player ID is collected after selecting the pack; continue directly to review.
            p = f"{o['price']} دج" if o.get("price") is not None else "يؤكده المتجر قبل الدفع"
            msg = (f"🧾 راجع طلبك:\n\nالخدمة: {o['game']}\nالعرض: {o['offer']}\n"
                   f"معرّف الشحن: {o['player_id']}\nالدفع: {o['payment']}\nالسعر: {p}\n\n"
                   "الدفع مسبقًا ولا يوجد شحن مجاني.\nلا ترسل كلمة مرور أو رمز تحقق.")
            return await u.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ تأكيد وإرسال", callback_data="confirm")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="home")]]))
        ctx.user_data["awaiting"] = "payment"
        return await u.message.reply_text("اختر طريقة الدفع:", reply_markup=payment_menu())
    await u.message.reply_text("استعمل القائمة أو اكتب /start.", reply_markup=menu())

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
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(errors)
    app.run_polling(drop_pending_updates=False)

if __name__ == "__main__":
    main()
      

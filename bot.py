import os
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_TEXT = os.getenv("ADMIN_ID", "").strip()
ADMIN_ID = int(ADMIN_ID_TEXT) if ADMIN_ID_TEXT.isdigit() else None

STORE_NAME = "SERADJ STORE"

# eFootball prices supplied by the store owner (DA)
EFOOTBALL_OFFERS = [
    ("300 Coins — 750 دج (BaridiMob/CCP)", "300 Coins", 750),
    ("550 Coins — 1300 دج (BaridiMob/CCP)", "550 Coins", 1300),
    ("750 Coins — 1700 دج (BaridiMob/CCP)", "750 Coins", 1700),
    ("1040 Coins — 2300 دج (BaridiMob/CCP)", "1040 Coins", 2300),
    ("2130 Coins — 4600 دج (BaridiMob/CCP)", "2130 Coins", 4600),
    ("3250 Coins — 6600 دج (BaridiMob/CCP)", "3250 Coins", 6600),
    ("5700 Coins — 11500 دج (BaridiMob/CCP)", "5700 Coins", 11500),
    ("12800 Coins — 22000 دج (BaridiMob/CCP)", "12800 Coins", 22000),
]

GAMES = [
    "Free Fire", "PUBG Mobile", "Call of Duty Mobile", "eFootball",
    "FC Mobile", "Brawl Stars", "Roblox", "One State", "TikTok",
    "Blood Strike", "Snapchat+", "Facebook / Instagram", "WhatsApp",
    "Netflix", "App Store", "Azar", "SoulChill", "Tango", "Super Live",
    "خدمة أخرى"
]

PAYMENTS = ["BaridiMob", "CCP", "Flexy", "أتواصل مع الإدارة لتحديد الدفع"]

def main_menu():
    rows = []
    for i in range(0, len(GAMES), 2):
        row = [InlineKeyboardButton(GAMES[i], callback_data=f"game:{GAMES[i]}")]
        if i + 1 < len(GAMES):
            row.append(InlineKeyboardButton(GAMES[i + 1], callback_data=f"game:{GAMES[i+1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("📋 طلباتي", callback_data="myorders")])
    rows.append([InlineKeyboardButton("📞 التواصل مع الإدارة", callback_data="contact")])
    return InlineKeyboardMarkup(rows)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="home")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = (
        f"🎮 أهلاً بك في {STORE_NAME}!\n\n"
        "اختر اللعبة أو الخدمة التي تريد طلبها.\n"
        "بعد إرسال الطلب، ستتواصل مع الإدارة لإتمام الدفع والشحن.\n\n"
        "⚠️ لا ترسل كلمة مرور حسابك أبداً؛ نطلب فقط معرّف اللاعب أو المعلومات الضرورية للشحن."
    )
    await update.message.reply_text(text, reply_markup=main_menu())

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Telegram ID الخاص بك هو:\n{update.effective_user.id}\n\n"
        "لا ترسل Bot Token لأي شخص. إذا كنت تريد استقبال الطلبات على هذا الحساب، "
        "ضع هذا الرقم في متغير الاستضافة ADMIN_ID."
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("تم إلغاء الطلب. اكتب /start للبدء من جديد.", reply_markup=main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        context.user_data.clear()
        await query.edit_message_text(f"🎮 {STORE_NAME}\nاختر اللعبة أو الخدمة:", reply_markup=main_menu())
        return

    if data == "contact":
        if ADMIN_ID:
            await query.edit_message_text(
                "للتواصل بخصوص الدفع أو الطلب، أرسل طلبك أولاً وسيتواصل معك المتجر.\n"
                "يمكنك أيضاً كتابة /start لبدء طلب جديد.",
                reply_markup=back_keyboard()
            )
        else:
            await query.edit_message_text(
                "التواصل مع الإدارة سيكون متاحاً بعد ضبط إعدادات البوت.\nاكتب /start للعودة.",
                reply_markup=back_keyboard()
            )
        return

    if data == "myorders":
        orders = context.user_data.get("orders", [])
        if not orders:
            msg = "لا توجد طلبات محفوظة في هذه الجلسة بعد."
        else:
            msg = "📋 طلباتك في هذه الجلسة:\n" + "\n".join(
                f"• {o['game']} — {o['offer']} — {o['status']}" for o in orders[-10:]
            )
        await query.edit_message_text(msg, reply_markup=back_keyboard())
        return

    if data.startswith("game:"):
        game = data.split(":", 1)[1]
        context.user_data["order"] = {"game": game}
        if game == "eFootball":
            rows = []
            for idx, (label, offer, price) in enumerate(EFOOTBALL_OFFERS):
                rows.append([InlineKeyboardButton(label, callback_data=f"offer:{idx}")])
            rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="home")])
            await query.edit_message_text("⚽ اختر عرض eFootball:", reply_markup=InlineKeyboardMarkup(rows))
        else:
            await query.edit_message_text(
                f"🎮 اخترت: {game}\n\n"
                "اكتب اسم العرض أو الكمية التي تريدها (مثال: 100 جوهرة / اشتراك شهر). "
                "يمكنك تأكيد السعر مع الإدارة قبل الدفع.",
                reply_markup=back_keyboard()
            )
            context.user_data["awaiting"] = "custom_offer"
        return

    if data.startswith("offer:"):
        idx = int(data.split(":", 1)[1])
        label, offer, price = EFOOTBALL_OFFERS[idx]
        context.user_data["order"]["offer"] = offer
        context.user_data["order"]["price"] = price
        context.user_data.pop("awaiting", None)
        context.user_data["awaiting"] = "player_id"
        await query.edit_message_text(
            f"اخترت: {label}\n\nأرسل الآن معرّف اللاعب (Player ID) الخاص بك.",
            reply_markup=back_keyboard()
        )
        return

    if data.startswith("pay:"):
        payment = data.split(":", 1)[1]
        context.user_data["order"]["payment"] = payment
        context.user_data.pop("awaiting", None)
        await send_confirmation(query, context)
        return

    if data == "confirm":
        order = context.user_data.get("order")
        if not order:
            await query.edit_message_text("لم أجد طلباً قيد التأكيد. اكتب /start للبدء.")
            return

        user = query.from_user
        username = f"@{user.username}" if user.username else "لا يوجد username"
        price_text = f"{order['price']} دج" if order.get("price") else "يُحدّد مع الإدارة"
        order_no = f"SS-{user.id}-{query.message.message_id}"
        order["status"] = "في انتظار التواصل والدفع"
        order["order_no"] = order_no
        context.user_data.setdefault("orders", []).append({
            "game": order["game"], "offer": order["offer"],
            "status": order["status"]
        })

        admin_message = (
            f"🛒 طلب جديد — {STORE_NAME}\n\n"
            f"🆔 رقم الطلب: {order_no}\n"
            f"👤 الاسم: {user.full_name}\n"
            f"🔗 username: {username}\n"
            f"🆔 Telegram ID للزبون: {user.id}\n"
            f"🎮 اللعبة/الخدمة: {order['game']}\n"
            f"💎 العرض: {order['offer']}\n"
            f"🪪 معلومات الشحن: {order.get('player_id', 'لم تُطلب')}\n"
            f"💳 طريقة الدفع المفضلة: {order.get('payment', 'سيحددها مع الإدارة')}\n"
            f"💰 السعر: {price_text}\n"
            f"📌 الحالة: {order['status']}\n\n"
            f"للتواصل مع الزبون: tg://user?id={user.id}"
        )

        sent = False
        if ADMIN_ID:
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
                sent = True
            except Exception:
                logging.exception("Could not send order to ADMIN_ID")

        if sent:
            await query.edit_message_text(
                f"✅ تم إرسال طلبك بنجاح!\n\n"
                f"🆔 رقم الطلب: {order_no}\n"
                f"🎮 الخدمة: {order['game']}\n"
                f"💎 العرض: {order['offer']}\n"
                f"💰 السعر: {price_text}\n\n"
                "ستتواصل معك الإدارة لتأكيد الدفع وإتمام الشحن.\n"
                "لا ترسل كلمة مرور حسابك لأي شخص.",
                reply_markup=back_keyboard()
            )
        else:
            await query.edit_message_text(
                "⚠️ لم يتم ضبط حساب الإدارة بعد، لذلك لم يُرسل الطلب إلى المسؤول.\n"
                "أرسل /myid لمعرفة رقم Telegram ID الخاص بك، ثم اضبط ADMIN_ID في إعدادات الاستضافة.",
                reply_markup=back_keyboard()
            )
        return

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get("awaiting")
    text = update.message.text.strip()
    order = context.user_data.get("order", {})

    if awaiting == "custom_offer":
        order["offer"] = text
        context.user_data["awaiting"] = "player_id"
        await update.message.reply_text(
            "أرسل الآن Player ID أو معرّف الحساب المطلوب للشحن.\n"
            "إذا كانت الخدمة لا تحتاج معرّفاً، اكتب: لا يوجد"
        )
        return

    if awaiting == "player_id":
        order["player_id"] = text
        context.user_data["awaiting"] = "payment"
        rows = [[InlineKeyboardButton(p, callback_data=f"pay:{p}")] for p in PAYMENTS]
        await update.message.reply_text(
            "اختر طريقة الدفع المفضلة. ستتواصل مع الإدارة لإتمام الدفع:",
            reply_markup=InlineKeyboardMarkup(rows)
        )
        return

    await update.message.reply_text("استخدم القائمة لاختيار خدمة، أو اكتب /start للبدء.", reply_markup=main_menu())

async def send_confirmation(query, context):
    order = context.user_data.get("order", {})
    price_text = f"{order['price']} دج" if order.get("price") else "يُحدّد مع الإدارة"
    summary = (
        "🧾 راجع طلبك قبل الإرسال:\n\n"
        f"🎮 الخدمة: {order.get('game', '-')}\n"
        f"💎 العرض: {order.get('offer', '-')}\n"
        f"🪪 معرّف الحساب: {order.get('player_id', '-')}\n"
        f"💳 الدفع: {order.get('payment', '-')}\n"
        f"💰 السعر: {price_text}\n\n"
        "تأكد من صحة المعلومات. لا تكتب كلمة مرور حسابك."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد وإرسال الطلب", callback_data="confirm")],
        [InlineKeyboardButton("❌ إلغاء / القائمة", callback_data="home")]
    ])
    await query.edit_message_text(summary, reply_markup=keyboard)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN environment variable.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

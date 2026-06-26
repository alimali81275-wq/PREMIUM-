# ╔══════════════════════════════════════════════════════════════╗
# ║           💎  DIAMOND PREMIUM BOT  💎                       ║
# ║           Ultra Premium + Admin Panel Edition               ║
# ╚══════════════════════════════════════════════════════════════╝

import logging
import sqlite3
import random
from datetime import datetime
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)
import qrcode
from PIL import Image, ImageDraw, ImageFont

# ════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════
BOT_TOKEN = "8929816627:AAFqOrK7Wwj-g7lW8MyoaG7qgFO5VYjP-os"
OWNER_ID  = 8445317010   # Only owner can change UPI
ADMIN_ID  = 8445317010

PLANS = {
    "250":  {"price": 250,  "diamonds": 10_000,  "emoji": "🥉", "tag": "Starter", "note": "No refund on Starter plan."},
    "500":  {"price": 500,  "diamonds": 50_000,  "emoji": "🥈", "tag": "Popular", "note": "100% refund if not hit."},
    "1000": {"price": 1000, "diamonds": 1_00_000,"emoji": "🥇", "tag": "Premium", "note": "100% refund if not hit."},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("diamond-bot")

# ════════════════════════════════════════════════
#  DATABASE
# ════════════════════════════════════════════════
DB = sqlite3.connect("bot.db", check_same_thread=False)
C  = DB.cursor()

C.execute("""CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER PRIMARY KEY, username TEXT,
  diamonds INTEGER DEFAULT 0, joined_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
C.execute("""CREATE TABLE IF NOT EXISTS txns(
  txn_id TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER,
  diamonds INTEGER, status TEXT DEFAULT 'pending', created_at TEXT)""")
C.execute("""CREATE TABLE IF NOT EXISTS cards(
  id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, used INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP, used_at TEXT, txn_id TEXT, user_id INTEGER)""")
C.execute("""CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY, value TEXT)""")

# Default UPI
C.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('upi_id','alimturki10@oksbi')")
DB.commit()

# ════════════════════════════════════════════════
#  SETTINGS HELPERS
# ════════════════════════════════════════════════

def get_upi() -> str:
    C.execute("SELECT value FROM settings WHERE key='upi_id'")
    row = C.fetchone()
    return row[0] if row else "alimturki10@oksbi"

def set_upi(new_upi: str):
    C.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('upi_id',?)", (new_upi,))
    DB.commit()

# ════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════

def new_txn_id() -> str:
    ts  = datetime.now().strftime("%y%m%d%H%M%S")
    rnd = random.randint(1000, 9999)
    return f"DIA{ts}{rnd}"

def mask_card(line: str) -> str:
    digits = "".join(ch for ch in line if ch.isdigit())
    if len(digits) >= 12:
        return f"{digits[:4]} **** **** {digits[-4:]}"
    return line[:4] + "****" + line[-4:] if len(line) > 10 else line

def welcome_msg(name: str) -> str:
    return (
        f"『 💎 DIAMOND PREMIUM HUB 💎 』\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✨ Welcome back, *{name}*!\n\n"
        f"🏆 India's Most Trusted Diamond Store\n"
        f"⚡ Instant Delivery  |  🔒 100% Secure\n"
        f"💯 Verified & Trusted by 10,000+ Users\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *Choose Your Plan Below* 👇"
    )

def plan_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥉  STARTER  |  Rs.250  →  10,000 💎",   callback_data="plan_250")],
        [InlineKeyboardButton("🥈  POPULAR  |  Rs.500  →  50,000 💎",   callback_data="plan_500")],
        [InlineKeyboardButton("🥇  PREMIUM  |  Rs.1000 → 1,00,000 💎",  callback_data="plan_1000")],
        [
            InlineKeyboardButton("💎 My Balance",  callback_data="my_balance"),
            InlineKeyboardButton("📋 How To Use",  callback_data="how_to_use"),
        ],
        [InlineKeyboardButton("🌟 Why Choose Us?", callback_data="why_us")],
    ])

# ════════════════════════════════════════════════
#  QR GENERATOR
# ════════════════════════════════════════════════

def build_qr(upi: str, amount: int, note: str) -> BytesIO:
    url = f"upi://pay?pa={upi}&am={amount}&tn={note}&cu=INR"
    qr  = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=11, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=(15, 15, 35), back_color=(255, 255, 255)).convert("RGB")

    qw, qh  = qr_img.size
    pad     = 32
    top_bar = 48
    bot_bar = 80
    W       = qw + pad * 2
    H       = qh + pad * 2 + top_bar + bot_bar

    canvas = Image.new("RGB", (W, H), (13, 13, 30))
    for i in range(top_bar):
        r = int(80  + (i / top_bar) * 20)
        g = int(20  + (i / top_bar) * 10)
        b = int(180 + (i / top_bar) * 40)
        ImageDraw.Draw(canvas).line([(0, i), (W, i)], fill=(r, g, b))

    frame = Image.new("RGB", (qw + 16, qh + 16), (255, 255, 255))
    canvas.paste(frame, (pad - 8, top_bar + pad - 8))
    canvas.paste(qr_img, (pad, top_bar + pad))

    draw = ImageDraw.Draw(canvas)
    try:
        fnt_big   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        fnt_med   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        fnt_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        fnt_big = fnt_med = fnt_small = ImageFont.load_default()

    draw.text((W // 2, top_bar // 2), "DIAMOND PREMIUM HUB", fill=(255, 255, 255), font=fnt_med, anchor="mm")
    by = qh + top_bar + pad * 2 + 8
    draw.text((W // 2, by),      f"Pay  Rs.{amount}",         fill=(255, 215, 0),  font=fnt_big,   anchor="mm")
    draw.text((W // 2, by + 26), upi,                          fill=(180, 200, 255), font=fnt_small, anchor="mm")
    draw.text((W // 2, by + 46), "Scan & Pay via any UPI App", fill=(140, 140, 180), font=fnt_small, anchor="mm")

    buf = BytesIO()
    canvas.save(buf, "PNG")
    buf.seek(0)
    return buf

# ════════════════════════════════════════════════
#  USER HANDLERS
# ════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    C.execute("INSERT OR IGNORE INTO users(user_id, username) VALUES(?,?)", (u.id, u.username))
    DB.commit()
    name = u.first_name or "User"
    import asyncio
    msg = await update.message.reply_text("💎 Loading Diamond Hub...")
    await asyncio.sleep(0.6)
    await msg.edit_text("✨ Setting up your premium experience...")
    await asyncio.sleep(0.6)
    await msg.edit_text(welcome_msg(name), parse_mode="Markdown", reply_markup=plan_menu_kb())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    import asyncio

    if q.data == "my_balance":
        C.execute("SELECT diamonds FROM users WHERE user_id=?", (q.from_user.id,))
        row      = C.fetchone()
        diamonds = row[0] if row and row[0] else 0
        await q.message.reply_text(
            f"『 💎 YOUR BALANCE 』\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 User ID  : `{q.from_user.id}`\n"
            f"💎 Diamonds : *{diamonds:,}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 Secure · Verified · Trusted",
            parse_mode="Markdown",
        )
        return

    if q.data == "how_to_use":
        await q.edit_message_text(
            f"『 📋 HOW TO USE 』\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Step 1 — Add Card on YouTube*\n"
            f"  Open any YouTube Live stream\n"
            f"  Tap Super Chat option\n"
            f"  Add card: Number, MM/YY, CVV\n"
            f"  Name: Zenix\n"
            f"  Do NOT change country/address\n\n"
            f"*Step 2 — Payment*\n"
            f"  Choose plan from main menu\n"
            f"  Scan UPI QR and pay\n"
            f"  Screenshot the payment\n"
            f"  Send screenshot here\n\n"
            f"*Step 3 — Receive Card*\n"
            f"  Admin verifies payment\n"
            f"  Card sent instantly!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Plans", callback_data="back_main")]]),
        )
        return

    if q.data == "why_us":
        await q.edit_message_text(
            f"『 🌟 WHY CHOOSE US? 』\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅  Trusted by 10,000+ customers\n"
            f"⚡  Instant card delivery\n"
            f"🔒  100% secure transactions\n"
            f"💯  Verified UPI payments\n"
            f"🎁  Best rates guaranteed\n"
            f"📞  24/7 admin support\n"
            f"🏆  India's #1 Diamond Store\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Plans", callback_data="back_main")]]),
        )
        return

    if q.data == "back_main":
        name = q.from_user.first_name or "User"
        await q.edit_message_text(welcome_msg(name), parse_mode="Markdown", reply_markup=plan_menu_kb())
        return

    # ── Admin Panel Callbacks ────────────────────
    if q.data == "admin_panel":
        if q.from_user.id != OWNER_ID:
            await q.answer("Access Denied!", show_alert=True)
            return
        await show_admin_panel(q, context)
        return

    if q.data == "admin_change_upi":
        if q.from_user.id != OWNER_ID:
            await q.answer("Access Denied!", show_alert=True)
            return
        context.user_data["waiting_upi"] = True
        await q.edit_message_text(
            f"『 💳 CHANGE UPI ID 』\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Current UPI: `{get_upi()}`\n\n"
            f"Send new UPI ID in chat.\n"
            f"Example: `yourname@upi`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_panel")]]),
        )
        return

    if q.data == "admin_view_upi":
        if q.from_user.id != OWNER_ID:
            await q.answer("Access Denied!", show_alert=True)
            return
        upi = get_upi()
        await q.answer(f"Current UPI: {upi}", show_alert=True)
        return

    if q.data == "admin_stats":
        if q.from_user.id != OWNER_ID:
            await q.answer("Access Denied!", show_alert=True)
            return
        C.execute("SELECT COUNT(*) FROM users")
        total_users = C.fetchone()[0]
        C.execute("SELECT COUNT(*) FROM txns WHERE status='approved'")
        approved = C.fetchone()[0]
        C.execute("SELECT COUNT(*) FROM txns WHERE status='pending' OR status='submitted'")
        pending = C.fetchone()[0]
        C.execute("SELECT SUM(amount) FROM txns WHERE status='approved'")
        total_rev = C.fetchone()[0] or 0
        C.execute("SELECT COUNT(*) FROM cards WHERE used=0")
        cards_left = C.fetchone()[0]

        await q.edit_message_text(
            f"『 📊 BOT STATISTICS 』\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total Users    : {total_users}\n"
            f"✅ Approved Txns  : {approved}\n"
            f"⏳ Pending Txns   : {pending}\n"
            f"💰 Total Revenue  : Rs.{total_rev}\n"
            f"💳 Cards in Pool  : {cards_left}\n"
            f"🏦 Current UPI    : `{get_upi()}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Admin", callback_data="admin_panel")]]),
        )
        return

    # ── Plan Selection ───────────────────────────
    if q.data.startswith("plan_"):
        key  = q.data.replace("plan_", "", 1)
        plan = PLANS.get(key)
        if not plan:
            return

        t = new_txn_id()
        C.execute(
            "INSERT INTO txns(txn_id,user_id,amount,diamonds,status,created_at) VALUES(?,?,?,?,?,?)",
            (t, q.from_user.id, plan["price"], plan["diamonds"], "pending", datetime.now().isoformat()),
        )
        DB.commit()

        await q.edit_message_text(f"⚡ Generating your payment QR...")
        await asyncio.sleep(0.8)
        await q.edit_message_text(f"🔒 Securing transaction...")
        await asyncio.sleep(0.6)

        upi = get_upi()
        img = build_qr(upi, plan["price"], t)
        caption = (
            f"『 💳 PAYMENT QR CODE 』\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{plan['emoji']}  Plan      :  {plan['tag']}\n"
            f"💎  Diamonds :  {plan['diamonds']:,}\n"
            f"💵  Amount   :  Rs.{plan['price']}\n"
            f"🏦  UPI ID   :  `{upi}`\n"
            f"🔖  TXN ID   :  `{t}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_{plan['note']}_\n\n"
            f"*How to Pay:*\n"
            f"1  Scan QR or pay to UPI above\n"
            f"2  Screenshot your payment\n"
            f"3  Send screenshot here\n"
            f"4  Admin approves instantly\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 Secure · Verified · Trusted"
        )
        await context.bot.send_photo(q.from_user.id, photo=img, caption=caption, parse_mode="Markdown")
        await q.edit_message_text(
            f"✅ QR Ready for *{plan['tag']}* plan!\nCheck above for payment QR code.",
            parse_mode="Markdown",
        )


async def show_admin_panel(q, context):
    upi = get_upi()
    await q.edit_message_text(
        f"『 👑 ADMIN PANEL 』\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 Current UPI : `{upi}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Select an option below:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Change UPI ID",    callback_data="admin_change_upi")],
            [InlineKeyboardButton("👁 View Current UPI", callback_data="admin_view_upi")],
            [InlineKeyboardButton("📊 Bot Statistics",   callback_data="admin_stats")],
            [InlineKeyboardButton("💳 Card Pool Info",   callback_data="admin_stats")],
            [InlineKeyboardButton("Close Panel",         callback_data="back_main")],
        ]),
    )

# ════════════════════════════════════════════════
#  ADMIN COMMAND — /admin
# ════════════════════════════════════════════════

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("Access Denied.")
    upi = get_upi()
    await update.message.reply_text(
        f"『 👑 ADMIN PANEL 』\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 Current UPI : `{upi}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Select an option below:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Change UPI ID",    callback_data="admin_change_upi")],
            [InlineKeyboardButton("👁 View Current UPI", callback_data="admin_view_upi")],
            [InlineKeyboardButton("📊 Bot Statistics",   callback_data="admin_stats")],
            [InlineKeyboardButton("Close Panel",         callback_data="back_main")],
        ]),
    )

# ════════════════════════════════════════════════
#  TEXT HANDLER — UPI change + bulk cards
# ════════════════════════════════════════════════

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    text = (update.message.text or "").strip()

    # UPI change — only owner
    if context.user_data.get("waiting_upi") and uid == OWNER_ID:
        if "@" in text:
            old_upi = get_upi()
            set_upi(text)
            context.user_data["waiting_upi"] = False
            await update.message.reply_text(
                f"『 ✅ UPI UPDATED 』\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Old UPI : `{old_upi}`\n"
                f"New UPI : `{text}`\n\n"
                f"All new QR codes will use new UPI.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "Invalid UPI ID. Must contain @\nExample: `yourname@upi`",
                parse_mode="Markdown",
            )
        return

    # Bulk card mode
    if uid == ADMIN_ID and context.user_data.get("bulk_mode"):
        if text.lower() in ("/done", "done"):
            lines = [ln.strip() for ln in context.user_data.get("bulk_lines", []) if ln.strip()]
            for ln in lines:
                C.execute("INSERT INTO cards(data) VALUES(?)", (ln,))
            DB.commit()
            context.user_data["bulk_mode"]  = False
            context.user_data["bulk_lines"] = []
            return await update.message.reply_text(f"{len(lines)} card(s) added.")
        else:
            context.user_data.setdefault("bulk_lines", []).extend(text.splitlines())
            await update.message.reply_text(f"{len(text.splitlines())} line(s) queued.")

# ════════════════════════════════════════════════
#  PAYMENT PROOF
# ════════════════════════════════════════════════

async def payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return
    uid = update.effective_user.id
    C.execute(
        "SELECT txn_id, amount, diamonds FROM txns WHERE user_id=? AND status IN ('pending','submitted') ORDER BY created_at DESC LIMIT 1",
        (uid,),
    )
    row = C.fetchone()
    if not row:
        return await update.message.reply_text("No pending transaction found.\nUse /start and choose a plan first.")
    t, amount, diamonds = row[0], row[1], row[2]
    C.execute("UPDATE txns SET status='submitted' WHERE txn_id=?", (t,))
    DB.commit()

    admin_text = (
        f"NEW PAYMENT PROOF\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"User ID  : `{uid}`\n"
        f"Amount   : Rs.{amount}\n"
        f"Diamonds : {diamonds:,}\n"
        f"TXN ID   : `{t}`\n\n"
        f"/approve {t}\n"
        f"/reject {t}"
    )
    try:
        await context.bot.send_photo(ADMIN_ID, photo=update.message.photo[-1].file_id, caption=admin_text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"Admin notify failed: {e}")

    import asyncio
    msg = await update.message.reply_text("📤 Uploading screenshot...")
    await asyncio.sleep(0.7)
    await msg.edit_text("🔍 Sending to admin...")
    await asyncio.sleep(0.5)
    await msg.edit_text(
        f"✅ Screenshot received!\n\n"
        f"⏱ Admin is reviewing your payment.\n"
        f"You will be notified on approval.\n\n"
        f"TXN: `{t}`",
        parse_mode="Markdown",
    )

# ════════════════════════════════════════════════
#  ADMIN COMMANDS
# ════════════════════════════════════════════════

def parse_admin_cmd(text: str):
    t = (text or "").strip()
    lower = t.lower()
    for prefix in ("/approve", "/reject", "/cc_add_bulk", "/cc_add", "/cc_list"):
        if lower.startswith(prefix):
            return prefix.lstrip("/"), t[len(prefix):].strip()
    return None, None


async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    action, arg = parse_admin_cmd(update.message.text)
    if not action:
        return
    if action == "approve" and arg:
        await approve_txn(update, context, arg.split()[0])
    elif action == "reject" and arg:
        await reject_txn(update, context, arg.split()[0])
    elif action == "cc_add" and arg:
        C.execute("INSERT INTO cards(data) VALUES(?)", (arg.strip(),))
        DB.commit()
        await update.message.reply_text(f"Card added: `{mask_card(arg.strip())}`", parse_mode="Markdown")
    elif action == "cc_add_bulk":
        await update.message.reply_text("Bulk mode ON. Send cards. Send /done when finished.")
        context.user_data["bulk_mode"]  = True
        context.user_data["bulk_lines"] = []
    elif action == "cc_list":
        C.execute("SELECT COUNT(*) FROM cards WHERE used=0")
        available = C.fetchone()[0]
        C.execute("SELECT data FROM cards WHERE used=0 ORDER BY id LIMIT 5")
        sample = [f"`{mask_card(r[0])}`" for r in C.fetchall()]
        await update.message.reply_text(
            f"Card Pool: {available} available\n\n" + ("\n".join(sample) or "Empty."),
            parse_mode="Markdown",
        )


def pop_next_card(txn_id, user_id):
    C.execute("SELECT id, data FROM cards WHERE used=0 ORDER BY id LIMIT 1")
    row = C.fetchone()
    if not row:
        return None
    cid, data = row[0], row[1]
    C.execute("UPDATE cards SET used=1, used_at=datetime('now'), txn_id=?, user_id=? WHERE id=?", (txn_id, user_id, cid))
    DB.commit()
    return data


async def approve_txn(update, context, t: str):
    C.execute("SELECT user_id, amount, diamonds, status FROM txns WHERE txn_id=?", (t,))
    row = C.fetchone()
    if not row:
        return await update.message.reply_text(f"TXN {t} not found.")
    uid, amount, diamonds, status = row[0], row[1], row[2], row[3]
    if status not in ("pending", "submitted"):
        return await update.message.reply_text(f"Already {status}.")
    C.execute("UPDATE txns SET status='approved' WHERE txn_id=?", (t,))
    C.execute("UPDATE users SET diamonds = COALESCE(diamonds,0) + ? WHERE user_id=?", (diamonds, uid))
    DB.commit()
    card = pop_next_card(t, uid)
    user_msg = (
        f"『 🎉 PAYMENT APPROVED! 』\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  TXN ID   : `{t}`\n"
        f"💎  Diamonds : {diamonds:,} added!\n\n"
        + (f"🎁 *Your Card:*\n`{card}`\n" if card else "⚠️ Card will be sent shortly by admin.\n")
        + f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nThank you for choosing Diamond Premium Hub!"
    )
    try:
        await context.bot.send_message(uid, user_msg, parse_mode="Markdown")
    except Exception as e:
        log.error(f"User notify failed: {e}")
    await update.message.reply_text(f"Approved {t}" + ("" if card else " — WARNING: card pool empty!"))


async def reject_txn(update, context, t: str):
    C.execute("SELECT user_id FROM txns WHERE txn_id=?", (t,))
    row = C.fetchone()
    if not row:
        return await update.message.reply_text(f"TXN {t} not found.")
    uid = row[0]
    C.execute("UPDATE txns SET status='rejected' WHERE txn_id=?", (t,))
    DB.commit()
    try:
        await context.bot.send_message(
            uid,
            f"『 ❌ PAYMENT REJECTED 』\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"TXN `{t}` has been rejected.\n"
            f"Contact admin if this is an error.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
        )
    except Exception as e:
        log.error(f"User notify failed: {e}")
    await update.message.reply_text(f"Rejected {t}")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    C.execute("SELECT diamonds FROM users WHERE user_id=?", (uid,))
    row      = C.fetchone()
    diamonds = row[0] if row and row[0] else 0
    await update.message.reply_text(
        f"『 💎 YOUR BALANCE 』\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"User ID  : `{uid}`\n"
        f"Diamonds : *{diamonds:,}* 💎\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔒 Secure · Verified · Trusted",
        parse_mode="Markdown",
    )

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("admin",   admin_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^/(approve|reject|cc_add|cc_add_bulk|cc_list)"),
        admin_router,
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, payment_proof))

    log.info("Diamond Premium Bot ONLINE")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

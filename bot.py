import os
import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8732385669:AAHivCppEKDeF6IkouMLncqlHxeoR3xa57U")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://fwpruutdizlpfbcmjcei.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_qRSPTxNmdJbd8YX2gZ8cfA_X8MZWMLh")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "1234")

H = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def db_get(table, params=None):
    p = {"select": "*"}
    if params: p.update(params)
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=H, params=p)
    return r.json() if r.ok else []

def db_insert(table, data):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=H, json=data)
    return r.json() if r.ok else []

def db_update(table, data, params):
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=H, json=data, params=params)
    return r.ok

def db_delete(table, params):
    r = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}", headers=H, params=params)
    return r.ok

def today(): return datetime.now().strftime("%Y-%m-%d")
def now_str(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def now_time(): return datetime.now().strftime("%H:%M")

def fmt(n):
    try:
        n = float(n or 0)
        if n >= 1_000_000_000: return f"{n/1_000_000_000:.2f} mlrd so'm"
        if n >= 1_000_000: return f"{n/1_000_000:.1f} mln so'm"
        return f"{int(n):,} so'm".replace(",", " ")
    except: return "0 so'm"

# States
(LOGIN_ROLE, LOGIN_NAME, LOGIN_PASS, MAIN_MENU,
 ADD_PROD_TYPE, ADD_PROD_NAME, ADD_PROD_QTY, ADD_PROD_PRICE, ADD_PROD_COST,
 EDIT_PROD_SELECT, EDIT_PROD_FIELD, EDIT_PROD_VALUE,
 ADD_SALE_PROD, ADD_SALE_QTY, ADD_SALE_PRICE, ADD_SALE_CLIENT, ADD_SALE_PAY,
 ADD_EXP_TYPE, ADD_EXP_DESC, ADD_EXP_AMOUNT,
 ADD_WORKER_NAME, ADD_WORKER_ROLE, ADD_WORKER_LOGIN, ADD_WORKER_PASS,
 EDIT_WORKER_SELECT, EDIT_WORKER_FIELD, EDIT_WORKER_VALUE,
 ASSIGN_WORKER, ASSIGN_PROD, ASSIGN_QTY,
 WORKER_DONE_SELECT, WORKER_DONE_QTY,
 SET_RATE_WORKER, SET_RATE_PROD, SET_RATE_PRICE,
 PAY_SALARY_WORKER, PAY_SALARY_AMOUNT,
 CUT_ORDER_WORKER, CUT_ORDER_PROD, CUT_ORDER_QTY,
 SEW_RECEIPT_ORDER, SEW_RECEIPT_SEWER, SEW_RECEIPT_QTY,
 REPORT_PERIOD) = range(46)

def get_worker_by_chat(chat_id):
    ws = db_get("workers", {"chat_id": f"eq.{chat_id}"})
    return ws[0] if ws else None

# ========== MENUS ==========
def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🏠 Bosh sahifa"), KeyboardButton("📊 Hisobot")],
        [KeyboardButton("👔 Mahsulotlar"), KeyboardButton("🛒 Savdo")],
        [KeyboardButton("💸 Xarajat"), KeyboardButton("👷 Ishchilar")],
        [KeyboardButton("📋 Vazifa berish"), KeyboardButton("📦 Ombor holati")],
        [KeyboardButton("✂️ Bichiqchi buyurtma"), KeyboardButton("🪡 Tikuv qabul")],
        [KeyboardButton("💰 Maosh belgilash"), KeyboardButton("💳 Maosh to'lash")],
        [KeyboardButton("📈 Ishchi hisoboti"), KeyboardButton("🕐 Davomat")],
        [KeyboardButton("🚪 Chiqish")]
    ], resize_keyboard=True)

def worker_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ Ishga keldim"), KeyboardButton("🏠 Uydaman")],
        [KeyboardButton("🍽 Obedman"), KeyboardButton("🔚 Ishni tugatdim")],
        [KeyboardButton("📋 Mening vazifalarim"), KeyboardButton("✍️ Ish kiriting")],
        [KeyboardButton("💰 Mening daromadam"), KeyboardButton("📅 Mening tarixim")],
        [KeyboardButton("🚪 Chiqish")]
    ], resize_keyboard=True)

# ========== AUTH ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    chat_id = update.effective_chat.id
    w = get_worker_by_chat(chat_id)
    if w:
        context.user_data.update({"role": w["role"], "wid": w["id"], "name": w["name"]})
        await show_menu(update, context)
        return MAIN_MENU
    kb = ReplyKeyboardMarkup([
        [KeyboardButton("👑 Admin"), KeyboardButton("✂️ Bichiqchi")],
        [KeyboardButton("🪡 Tikuvchi"), KeyboardButton("📦 Omborchi")]
    ], resize_keyboard=True)
    await update.message.reply_text("👔 *Koylak Biznes Bot*\n\nRolingizni tanlang:", parse_mode="Markdown", reply_markup=kb)
    return LOGIN_ROLE

async def login_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rm = {"👑 Admin":"admin","✂️ Bichiqchi":"bichiqchi","🪡 Tikuvchi":"tikuvchi","📦 Omborchi":"omborchi"}
    role = rm.get(update.message.text)
    if not role: await update.message.reply_text("Tugmadan tanlang!"); return LOGIN_ROLE
    context.user_data["role"] = role
    if role == "admin":
        await update.message.reply_text("🔐 Admin parolini kiriting:", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
        return LOGIN_PASS
    await update.message.reply_text("👤 Loginингizni kiriting:", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
    return LOGIN_NAME

async def login_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login_input"] = update.message.text.strip()
    await update.message.reply_text("🔐 Parolни kiriting:")
    return LOGIN_PASS

async def login_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pwd = update.message.text.strip()
    role = context.user_data.get("role")
    chat_id = update.effective_chat.id
    if role == "admin":
        if pwd != ADMIN_PASS: await update.message.reply_text("❌ Parol noto'g'ri!"); return LOGIN_PASS
        context.user_data["name"] = "Admin"
        await show_menu(update, context); return MAIN_MENU
    li = context.user_data.get("login_input","")
    ws = db_get("workers", {"login": f"eq.{li}", "role": f"eq.{role}"})
    w = ws[0] if ws else None
    if not w or w.get("pass") != pwd:
        await update.message.reply_text("❌ Login yoki parol noto'g'ri!\n/start ni bosing."); return LOGIN_ROLE
    db_update("workers", {"chat_id": chat_id}, {"id": f"eq.{w['id']}"})
    context.user_data.update({"wid": w["id"], "name": w["name"]})
    await show_menu(update, context); return MAIN_MENU

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = context.user_data.get("role")
    name = context.user_data.get("name","")
    h = datetime.now().hour
    gr = "Xayrli tong" if h<12 else "Xayrli kun" if h<18 else "Xayrli kech"
    msg = update.message if update.message else update.callback_query.message
    if role == "admin":
        await msg.reply_text(f"👑 *{gr}, {name}!*\n\nAdmin paneliga xush kelibsiz.", parse_mode="Markdown", reply_markup=admin_kb())
    else:
        # Check attendance today
        wid = context.user_data.get("wid")
        att = db_get("attendance", {"worker_id": f"eq.{wid}", "work_date": f"eq.{today()}"})
        status_txt = ""
        if att:
            s = att[-1]["status"]
            sm = {"arrived":"✅ Ishda","home":"🏠 Uyda","lunch":"🍽 Obedda","finished":"🔚 Tugatgan"}
            status_txt = f"\nHolat: *{sm.get(s, s)}*"
        await msg.reply_text(f"👋 *{gr}, {name}!*{status_txt}", parse_mode="Markdown", reply_markup=worker_kb())

async def do_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    wid = context.user_data.get("wid")
    if wid:
        db_update("workers", {"chat_id": None}, {"id": f"eq.{wid}"})
    context.user_data.clear()
    await update.message.reply_text("👋 Chiqildi!", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
    return await start(update, context)

# ========== ATTENDANCE ==========
async def worker_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str):
    wid = context.user_data.get("wid")
    name = context.user_data.get("name","")
    now = datetime.now()

    status_labels = {"arrived":"✅ Ishga keldi","home":"🏠 Uyda","lunch":"🍽 Obedda","finished":"🔚 Ishni tugatdi"}
    status_emoji = {"arrived":"✅","home":"🏠","lunch":"🍽","finished":"🔚"}

    att_today = db_get("attendance", {"worker_id": f"eq.{wid}", "work_date": f"eq.{today()}"})

    if status == "arrived":
        if att_today and att_today[-1]["status"] == "arrived":
            await update.message.reply_text("⚠️ Siz allaqachon ishdasiz!")
            return
        db_insert("attendance", {
            "worker_id": wid, "worker_name": name,
            "status": status, "check_in": now_str(),
            "work_date": today()
        })
        await update.message.reply_text(f"✅ *{name}* ishga keldi!\n⏰ Vaqt: {now_time()}", parse_mode="Markdown")

    elif status in ("home", "lunch", "finished"):
        if not att_today:
            await update.message.reply_text("⚠️ Avval ishga kelganingizni belgilang!")
            return
        last = att_today[-1]
        minutes = 0
        if last.get("check_in"):
            try:
                ci = datetime.fromisoformat(last["check_in"])
                minutes = int((now - ci).total_seconds() / 60)
            except: pass

        total = (last.get("total_minutes") or 0) + minutes
        db_update("attendance", {
            "status": status, "check_out": now_str(), "total_minutes": total
        }, {"id": f"eq.{last['id']}"})

        h = total // 60; m = total % 60
        msg = f"{status_emoji[status]} *{name}* — {status_labels[status]}\n⏰ {now_time()}\n⏱ Bugun jami: {h} soat {m} daqiqa"
        await update.message.reply_text(msg, parse_mode="Markdown")

        if status == "finished":
            await update.message.reply_text("🎉 Yaxshi ish! Ertaga ko'rishguncha!")

# ========== ADMIN: BOSH SAHIFA ==========
async def do_home(update, context):
    prods = db_get("products")
    sales = db_get("sales", {"sale_date": f"eq.{today()}"})
    clients = db_get("clients")
    workers = db_get("workers")

    # Today attendance
    att = db_get("attendance", {"work_date": f"eq.{today()}"})
    working = [a for a in att if a["status"] == "arrived"]

    income = sum(s["total"] for s in sales if s.get("pay_type")!="nasiya")
    profit = sum(s.get("profit",0) or 0 for s in sales)
    koylak = sum(p["qty"] for p in prods if p["type"]=="koylak")
    mat = sum(p["qty"] for p in prods if p["type"]=="material")
    debt = sum(c["debt"] for c in clients)
    kv = sum(p["qty"]*p["price"] for p in prods if p["type"]=="koylak")
    mv = sum(p["qty"]*p["price"] for p in prods if p["type"]=="material")
    dv = sum(p["qty"]*p["price"] for p in prods if p["type"]=="detal")

    txt = f"🏠 *Bosh sahifa — {today()}*\n\n"
    txt += f"💰 Bugungi daromad: *{fmt(income)}*\n"
    txt += f"📈 Bugungi foyda: *{fmt(profit)}*\n"
    txt += f"👔 Koylak: *{koylak} dona*\n"
    txt += f"🧵 Material: *{mat} metr*\n"
    txt += f"⚠️ Qarzlar: *{fmt(debt)}*\n\n"
    txt += f"📦 Ombor jami: *{fmt(kv+mv+dv)}*\n"
    txt += f"👷 Jami ishchilar: *{len(workers)} ta*\n"
    txt += f"✅ Hozir ishda: *{len(working)} ta*\n\n"

    if working:
        txt += "👷 *Ishda bo'lganlar:*\n"
        for a in working:
            txt += f"  • {a['worker_name']} ({a.get('check_in','')[11:16]} dan)\n"

    await update.message.reply_text(txt, parse_mode="Markdown")

# ========== DAVOMAT (ADMIN) ==========
async def do_davomat(update, context):
    att = db_get("attendance", {"work_date": f"eq.{today()}"})
    workers = db_get("workers")

    txt = f"🕐 *Bugungi davomat — {today()}*\n\n"
    status_labels = {"arrived":"✅ Ishda","home":"🏠 Ketdi","lunch":"🍽 Obedda","finished":"🔚 Tugatdi"}

    for w in workers:
        w_att = [a for a in att if a["worker_id"] == w["id"]]
        if w_att:
            last = w_att[-1]
            st = status_labels.get(last["status"], last["status"])
            total = last.get("total_minutes", 0) or 0
            h = total // 60; m = total % 60
            ci = last.get("check_in","")
            ci_time = ci[11:16] if len(ci) > 11 else "-"
            txt += f"👤 *{w['name']}* ({w['role']})\n"
            txt += f"  {st} | Keldi: {ci_time} | {h}s {m}d\n\n"
        else:
            txt += f"👤 *{w['name']}* — ❌ Kelmadi\n\n"

    await update.message.reply_text(txt, parse_mode="Markdown")

# ========== MAHSULOTLAR ==========
async def do_products(update, context):
    prods = db_get("products")
    txt = "👔 *Mahsulotlar:*\n\n"
    for t,lb in [("koylak","👔 KOYLAKLAR"),("material","🧵 MATERIALLAR"),("detal","🔩 DETALLAR")]:
        items = [p for p in prods if p["type"]==t]
        if items:
            txt += f"*{lb}*\n"
            for p in items:
                w = "⚠️" if p["qty"]<5 else ""
                txt += f"  {w}*{p['name']}*\n    {p['qty']} dona | {fmt(p['price'])} | Jami: {fmt(p['qty']*p['price'])}\n"
            txt += "\n"
    kb = [[InlineKeyboardButton("➕ Qo'shish", callback_data="add_prod"),
           InlineKeyboardButton("✏️ Tahrirlash", callback_data="edit_prod")]]
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def cb_add_prod(update, context):
    await update.callback_query.answer()
    kb = [[InlineKeyboardButton("👔 Koylak", callback_data="pt_koylak")],
          [InlineKeyboardButton("🧵 Material", callback_data="pt_material")],
          [InlineKeyboardButton("🔩 Detal", callback_data="pt_detal")]]
    await update.callback_query.message.reply_text("Turini tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_PROD_TYPE

async def add_prod_type(update, context):
    await update.callback_query.answer()
    context.user_data["np"] = {"type": update.callback_query.data.replace("pt_","")}
    await update.callback_query.message.reply_text("Nomini kiriting:")
    return ADD_PROD_NAME

async def add_prod_name(update, context):
    context.user_data["np"]["name"] = update.message.text.strip()
    await update.message.reply_text("Miqdorini kiriting:")
    return ADD_PROD_QTY

async def add_prod_qty(update, context):
    try: context.user_data["np"]["qty"] = float(update.message.text.strip())
    except: await update.message.reply_text("❌ Raqam!"); return ADD_PROD_QTY
    await update.message.reply_text("Sotuv narxini kiriting (so'm):")
    return ADD_PROD_PRICE

async def add_prod_price(update, context):
    try: context.user_data["np"]["price"] = float(update.message.text.strip().replace(" ",""))
    except: await update.message.reply_text("❌ Raqam!"); return ADD_PROD_PRICE
    await update.message.reply_text("Tan narxini kiriting (so'm):")
    return ADD_PROD_COST

async def add_prod_cost(update, context):
    try: cost = float(update.message.text.strip().replace(" ",""))
    except: cost = 0
    p = context.user_data["np"]
    db_insert("products", {"type":p["type"],"name":p["name"],"qty":p["qty"],"price":p["price"],"cost":cost,"sold":0})
    await update.message.reply_text(f"✅ *Qo'shildi:* {p['name']}", parse_mode="Markdown")
    return MAIN_MENU

async def cb_edit_prod(update, context):
    await update.callback_query.answer()
    prods = db_get("products")
    ic = {"koylak":"👔","material":"🧵","detal":"🔩"}
    kb = [[InlineKeyboardButton(f"{ic.get(p['type'],'📦')} {p['name']} ({p['qty']})", callback_data=f"ep_{p['id']}")] for p in prods]
    await update.callback_query.message.reply_text("Qaysi mahsulot?", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_PROD_SELECT

async def edit_prod_select(update, context):
    await update.callback_query.answer()
    pid = int(update.callback_query.data.replace("ep_",""))
    ps = db_get("products", {"id": f"eq.{pid}"})
    p = ps[0] if ps else {}
    context.user_data["epid"] = pid
    kb = [[InlineKeyboardButton("📝 Nom", callback_data="epf_name"),InlineKeyboardButton("📦 Miqdor", callback_data="epf_qty")],
          [InlineKeyboardButton("💰 Narx", callback_data="epf_price"),InlineKeyboardButton("🏷 Tan narx", callback_data="epf_cost")],
          [InlineKeyboardButton("🗑️ O'chirish", callback_data="epf_delete")]]
    await update.callback_query.message.reply_text(
        f"✏️ *{p.get('name','')}*\n📦{p.get('qty',0)} | 💰{fmt(p.get('price',0))}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_PROD_FIELD

async def edit_prod_field(update, context):
    await update.callback_query.answer()
    f = update.callback_query.data.replace("epf_","")
    if f=="delete":
        db_delete("products", {"id": f"eq.{context.user_data['epid']}"})
        await update.callback_query.message.reply_text("🗑️ O'chirildi!")
        return MAIN_MENU
    context.user_data["epf"] = f
    lb = {"name":"yangi nomini","qty":"yangi miqdorini","price":"yangi narxini","cost":"yangi tan narxini"}
    await update.callback_query.message.reply_text(f"✏️ {lb[f]} kiriting:")
    return EDIT_PROD_VALUE

async def edit_prod_value(update, context):
    v = update.message.text.strip().replace(" ","")
    f = context.user_data["epf"]
    if f in ("qty","price","cost"):
        try: v = float(v)
        except: await update.message.reply_text("❌ Raqam!"); return EDIT_PROD_VALUE
    db_update("products", {f:v}, {"id": f"eq.{context.user_data['epid']}"})
    await update.message.reply_text("✅ Yangilandi!")
    return MAIN_MENU

# ========== SAVDO ==========
async def do_savdo(update, context):
    prods = db_get("products", {"type": "eq.koylak"})
    if not prods: await update.message.reply_text("❌ Koylak yo'q."); return MAIN_MENU
    context.user_data["sprods"] = prods
    kb = [[InlineKeyboardButton(f"👔 {p['name']} ({p['qty']} dona)", callback_data=f"sp_{p['id']}")] for p in prods]
    await update.message.reply_text("🛒 *Yangi sotuv* — Mahsulot:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_SALE_PROD

async def sale_prod_cb(update, context):
    await update.callback_query.answer()
    pid = int(update.callback_query.data.replace("sp_",""))
    p = next(x for x in context.user_data["sprods"] if x["id"]==pid)
    context.user_data["ns"] = {"pid":pid,"pname":p["name"],"pprice":p["price"],"pcost":p.get("cost",0),"pqty":p["qty"]}
    await update.callback_query.message.reply_text(f"👔 *{p['name']}*\n💰 {fmt(p['price'])} | 📦 {p['qty']} dona\n\nNechta?", parse_mode="Markdown")
    return ADD_SALE_QTY

async def sale_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Raqam!"); return ADD_SALE_QTY
    if qty > context.user_data["ns"]["pqty"]: await update.message.reply_text(f"❌ Faqat {context.user_data['ns']['pqty']} dona bor!"); return ADD_SALE_QTY
    context.user_data["ns"]["qty"] = qty
    await update.message.reply_text(f"💰 Narx (so'm):\n(Standart: {fmt(context.user_data['ns']['pprice'])})")
    return ADD_SALE_PRICE

async def sale_price(update, context):
    try: price = float(update.message.text.strip().replace(" ",""))
    except: await update.message.reply_text("❌ Raqam!"); return ADD_SALE_PRICE
    ns = context.user_data["ns"]
    ns["price"] = price; ns["total"] = price*ns["qty"]; ns["profit"] = (price-ns["pcost"])*ns["qty"]
    await update.message.reply_text(f"💳 Jami: *{fmt(ns['total'])}*\nFoyda: *{fmt(ns['profit'])}*\n\nMijoz ismi:", parse_mode="Markdown")
    return ADD_SALE_CLIENT

async def sale_client(update, context):
    context.user_data["ns"]["client"] = update.message.text.strip()
    kb = [[InlineKeyboardButton("💵 Naqd", callback_data="pay_naqd")],
          [InlineKeyboardButton("📋 Nasiya", callback_data="pay_nasiya")],
          [InlineKeyboardButton("💳 Karta", callback_data="pay_karta")]]
    await update.message.reply_text("To'lov turi:", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_SALE_PAY

async def sale_pay(update, context):
    await update.callback_query.answer()
    pay = update.callback_query.data.replace("pay_","")
    ns = context.user_data["ns"]
    db_insert("sales", {"product_name":ns["pname"],"prod_id":ns["pid"],"qty":ns["qty"],"price":ns["price"],"cost":ns["pcost"],"total":ns["total"],"profit":ns["profit"],"client":ns["client"],"pay_type":pay,"sale_date":today()})
    ps = db_get("products", {"id": f"eq.{ns['pid']}"})
    if ps: db_update("products", {"qty":ps[0]["qty"]-ns["qty"],"sold":(ps[0].get("sold")or 0)+ns["qty"]}, {"id": f"eq.{ns['pid']}"})
    if pay=="nasiya":
        ex = db_get("clients", {"name": f"eq.{ns['client']}"})
        if ex: db_update("clients", {"debt":ex[0]["debt"]+ns["total"]}, {"name": f"eq.{ns['client']}"})
        else: db_insert("clients", {"name":ns["client"],"debt":ns["total"]})
    pl = {"naqd":"💵 Naqd","nasiya":"📋 Nasiya","karta":"💳 Karta"}
    await update.callback_query.message.reply_text(
        f"✅ *Sotuv saqlandi!*\n\n👔 {ns['pname']} × {ns['qty']}\n💰 {fmt(ns['total'])}\n📈 Foyda: {fmt(ns['profit'])}\n👤 {ns['client']}\n{pl[pay]}",
        parse_mode="Markdown")
    return MAIN_MENU

# ========== XARAJAT ==========
async def do_xarajat(update, context):
    kb = [[InlineKeyboardButton("🧵 Material", callback_data="et_material")],
          [InlineKeyboardButton("🔩 Detal", callback_data="et_detal")],
          [InlineKeyboardButton("👷 Maosh", callback_data="et_maosh")],
          [InlineKeyboardButton("🏠 Ijara", callback_data="et_ijara")],
          [InlineKeyboardButton("📦 Boshqa", callback_data="et_boshqa")]]
    await update.message.reply_text("💸 *Yangi xarajat* — Tur:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_EXP_TYPE

async def exp_type(update, context):
    await update.callback_query.answer()
    context.user_data["ne"] = {"type": update.callback_query.data.replace("et_","")}
    await update.callback_query.message.reply_text("Tavsifini kiriting:")
    return ADD_EXP_DESC

async def exp_desc(update, context):
    context.user_data["ne"]["desc"] = update.message.text.strip()
    await update.message.reply_text("Summani kiriting (so'm):")
    return ADD_EXP_AMOUNT

async def exp_amount(update, context):
    try: amt = float(update.message.text.strip().replace(" ",""))
    except: await update.message.reply_text("❌ Raqam!"); return ADD_EXP_AMOUNT
    ne = context.user_data["ne"]
    db_insert("expenses", {"type":ne["type"],"description":ne["desc"],"amount":amt,"expense_date":today()})
    await update.message.reply_text(f"✅ *Xarajat saqlandi!*\n📝 {ne['desc']}\n💰 {fmt(amt)}", parse_mode="Markdown")
    return MAIN_MENU

# ========== HISOBOT ==========
async def do_hisobot(update, context):
    kb = [[InlineKeyboardButton("📅 Kunlik", callback_data="rep_daily"),
           InlineKeyboardButton("📆 Haftalik", callback_data="rep_weekly"),
           InlineKeyboardButton("🗓 Oylik", callback_data="rep_monthly")]]
    await update.message.reply_text("📊 Hisobot davri:", reply_markup=InlineKeyboardMarkup(kb))

async def cb_rep(update, context):
    await update.callback_query.answer()
    p = update.callback_query.data.replace("rep_","")
    d = datetime.now()
    df = today() if p=="daily" else (d-timedelta(days=7)).strftime("%Y-%m-%d") if p=="weekly" else d.strftime("%Y-%m-01")
    lb = {"daily":"Kunlik","weekly":"Haftalik","monthly":"Oylik"}[p]
    sales = db_get("sales", {"sale_date": f"gte.{df}"})
    exps = db_get("expenses", {"expense_date": f"gte.{df}"})
    clients = db_get("clients")
    prods = db_get("products")
    income = sum(s["total"] for s in sales if s.get("pay_type")!="nasiya")
    nasiya = sum(s["total"] for s in sales if s.get("pay_type")=="nasiya")
    profit = sum(s.get("profit",0)or 0 for s in sales)
    expense = sum(e["amount"] for e in exps)
    qty = sum(s["qty"] for s in sales)
    debt = sum(c["debt"] for c in clients)
    sv = sum(p["qty"]*p["price"] for p in prods)
    txt = f"📊 *{lb} hisobot*\n\n"
    txt += f"💰 Daromad: *{fmt(income)}*\n"
    txt += f"📈 Foyda: *{fmt(profit)}*\n"
    txt += f"📋 Nasiya: *{fmt(nasiya)}*\n"
    txt += f"💸 Xarajat: *{fmt(expense)}*\n"
    txt += f"👔 Sotildi: *{qty} dona*\n"
    txt += f"📦 Ombor: *{fmt(sv)}*\n"
    txt += f"⚠️ Qarzlar: *{fmt(debt)}*"
    await update.callback_query.message.reply_text(txt, parse_mode="Markdown")

# ========== OMBOR ==========
async def do_ombor(update, context):
    prods = db_get("products")
    txt = "📦 *Ombor holati*\n\n"
    tv = 0
    for t,lb in [("koylak","👔 KOYLAKLAR"),("material","🧵 MATERIALLAR"),("detal","🔩 DETALLAR")]:
        items = [p for p in prods if p["type"]==t]
        if items:
            tval = sum(p["qty"]*p["price"] for p in items); tv+=tval
            txt += f"*{lb}* — {fmt(tval)}\n"
            for p in items:
                w="⚠️ " if p["qty"]<5 else ""
                txt += f"  {w}*{p['name']}*\n    {p['qty']} × {fmt(p['price'])} = *{fmt(p['qty']*p['price'])}*\n"
            txt += "\n"
    txt += f"💎 *Jami: {fmt(tv)}*"
    await update.message.reply_text(txt, parse_mode="Markdown")

# ========== ISHCHILAR ==========
async def do_workers(update, context):
    ws = db_get("workers")
    if not ws: await update.message.reply_text("Ishchilar yo'q."); return MAIN_MENU
    ri = {"bichiqchi":"✂️","tikuvchi":"🪡","omborchi":"📦"}
    txt = "👷 *Ishchilar:*\n\n"
    for w in ws:
        jobs = db_get("worker_jobs", {"worker_id": f"eq.{w['id']}", "job_date": f"eq.{today()}"})
        total = sum(j["total"] for j in jobs); done = sum(j["done"] for j in jobs)
        pct = round(done/total*100) if total>0 else 0
        txt += f"{ri.get(w['role'],'👤')} *{w['name']}* ({w['role']})\n"
        txt += f"  Login: `{w['login']}` Parol: `{w['pass']}`\n"
        txt += f"  Bugun: {done}/{total} ({pct}%)\n\n"
    kb = [[InlineKeyboardButton("➕ Qo'shish", callback_data="add_worker"),
           InlineKeyboardButton("✏️ Tahrirlash", callback_data="edit_worker")]]
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return MAIN_MENU

async def cb_add_worker(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("👤 Ismini kiriting:")
    return ADD_WORKER_NAME

async def aw_name(update, context):
    context.user_data["nw"] = {"name": update.message.text.strip()}
    kb = [[InlineKeyboardButton("✂️ Bichiqchi",callback_data="wr_bichiqchi")],
          [InlineKeyboardButton("🪡 Tikuvchi",callback_data="wr_tikuvchi")],
          [InlineKeyboardButton("📦 Omborchi",callback_data="wr_omborchi")]]
    await update.message.reply_text("Lavozim:", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_WORKER_ROLE

async def aw_role(update, context):
    await update.callback_query.answer()
    context.user_data["nw"]["role"] = update.callback_query.data.replace("wr_","")
    await update.callback_query.message.reply_text("Login kiriting:")
    return ADD_WORKER_LOGIN

async def aw_login(update, context):
    lg = update.message.text.strip().lower()
    ex = db_get("workers", {"login": f"eq.{lg}"})
    if ex: await update.message.reply_text("❌ Bu login band!"); return ADD_WORKER_LOGIN
    context.user_data["nw"]["login"] = lg
    await update.message.reply_text("Parol kiriting:")
    return ADD_WORKER_PASS

async def aw_pass(update, context):
    nw = context.user_data["nw"]; nw["pass"] = update.message.text.strip()
    db_insert("workers", {"name":nw["name"],"role":nw["role"],"login":nw["login"],"pass":nw["pass"]})
    await update.message.reply_text(
        f"✅ *Ishchi qo'shildi!*\n\n👤 {nw['name']}\n🔑 Login: `{nw['login']}`\n🔐 Parol: `{nw['pass']}`\n\n📱 Bu ma'lumotlarni ishchiga yuboring.",
        parse_mode="Markdown")
    return MAIN_MENU

async def cb_edit_worker(update, context):
    await update.callback_query.answer()
    ws = db_get("workers")
    kb = [[InlineKeyboardButton(f"{w['name']} ({w['role']})", callback_data=f"ew_{w['id']}")] for w in ws]
    await update.callback_query.message.reply_text("Qaysi ishchi?", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_WORKER_SELECT

async def ew_select(update, context):
    await update.callback_query.answer()
    context.user_data["ewid"] = int(update.callback_query.data.replace("ew_",""))
    kb = [[InlineKeyboardButton("📝 Ism",callback_data="ewf_name"),InlineKeyboardButton("🔑 Login",callback_data="ewf_login")],
          [InlineKeyboardButton("🔐 Parol",callback_data="ewf_pass"),InlineKeyboardButton("🗑️ O'chirish",callback_data="ewf_delete")]]
    await update.callback_query.message.reply_text("Nimani o'zgartirish?", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_WORKER_FIELD

async def ew_field(update, context):
    await update.callback_query.answer()
    f = update.callback_query.data.replace("ewf_","")
    if f=="delete":
        db_delete("workers", {"id": f"eq.{context.user_data['ewid']}"})
        await update.callback_query.message.reply_text("🗑️ O'chirildi!")
        return MAIN_MENU
    context.user_data["ewf"] = f
    lb = {"name":"yangi ismini","login":"yangi loginini","pass":"yangi parolini"}
    await update.callback_query.message.reply_text(f"✏️ {lb[f]} kiriting:")
    return EDIT_WORKER_VALUE

async def ew_value(update, context):
    db_update("workers", {context.user_data["ewf"]:update.message.text.strip()}, {"id": f"eq.{context.user_data['ewid']}"})
    await update.message.reply_text("✅ Yangilandi!")
    return MAIN_MENU

# ========== MAOSH BELGILASH ==========
async def do_set_rate(update, context):
    ws = db_get("workers")
    kb = [[InlineKeyboardButton(f"{w['name']} ({w['role']})", callback_data=f"sr_{w['id']}")] for w in ws]
    await update.message.reply_text("💰 *Ish narxi belgilash*\n\nQaysi ishchi?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SET_RATE_WORKER

async def set_rate_worker(update, context):
    await update.callback_query.answer()
    wid = int(update.callback_query.data.replace("sr_",""))
    ws = db_get("workers", {"id": f"eq.{wid}"})
    context.user_data["sr_wid"] = wid
    context.user_data["sr_wname"] = ws[0]["name"] if ws else ""
    prods = db_get("products", {"type": "eq.koylak"})
    kb = [[InlineKeyboardButton(p["name"], callback_data=f"srp_{p['id']}_{p['name']}")] for p in prods]
    await update.callback_query.message.reply_text("Qaysi mahsulot uchun?", reply_markup=InlineKeyboardMarkup(kb))
    return SET_RATE_PROD

async def set_rate_prod(update, context):
    await update.callback_query.answer()
    data = update.callback_query.data.replace("srp_","")
    parts = data.split("_", 1)
    context.user_data["sr_pid"] = int(parts[0])
    context.user_data["sr_pname"] = parts[1] if len(parts)>1 else ""

    # Show current rate
    ex = db_get("worker_rates", {"worker_id": f"eq.{context.user_data['sr_wid']}", "prod_id": f"eq.{context.user_data['sr_pid']}"})
    cur = f"\nHozirgi narx: {fmt(ex[0]['rate'])}" if ex else "\nHozirgi narx: belgilanmagan"
    await update.callback_query.message.reply_text(
        f"💰 *{context.user_data['sr_wname']}* — *{context.user_data['sr_pname']}*{cur}\n\nYangi narxni kiriting (so'm/dona):",
        parse_mode="Markdown")
    return SET_RATE_PRICE

async def set_rate_price(update, context):
    try: rate = float(update.message.text.strip().replace(" ",""))
    except: await update.message.reply_text("❌ Raqam!"); return SET_RATE_PRICE
    wid = context.user_data["sr_wid"]; pid = context.user_data["sr_pid"]
    pname = context.user_data["sr_pname"]; wname = context.user_data["sr_wname"]
    ex = db_get("worker_rates", {"worker_id": f"eq.{wid}", "prod_id": f"eq.{pid}"})
    if ex: db_update("worker_rates", {"rate": rate}, {"id": f"eq.{ex[0]['id']}"})
    else: db_insert("worker_rates", {"worker_id":wid,"prod_id":pid,"prod_name":pname,"rate":rate})
    await update.message.reply_text(f"✅ *{wname}* — *{pname}*\nNarx: *{fmt(rate)}* / dona", parse_mode="Markdown")
    return MAIN_MENU

# ========== MAOSH TO'LASH ==========
async def do_pay_salary(update, context):
    ws = db_get("workers")
    txt = "💳 *Maosh to'lash*\n\nIshchilar balansi:\n\n"
    for w in ws:
        earnings = db_get("worker_earnings", {"worker_id": f"eq.{w['id']}"})
        payments = db_get("salary_payments", {"worker_id": f"eq.{w['id']}"})
        total_earned = sum(e["total"] for e in earnings)
        total_paid = sum(p["amount"] for p in payments)
        balance = total_earned - total_paid
        txt += f"👤 *{w['name']}*: {fmt(balance)} (to'lanmagan)\n"
    ws2 = db_get("workers")
    kb = [[InlineKeyboardButton(f"{w['name']}", callback_data=f"ps_{w['id']}")] for w in ws2]
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return PAY_SALARY_WORKER

async def pay_salary_worker(update, context):
    await update.callback_query.answer()
    wid = int(update.callback_query.data.replace("ps_",""))
    ws = db_get("workers", {"id": f"eq.{wid}"})
    w = ws[0] if ws else {}
    context.user_data["ps_wid"] = wid
    context.user_data["ps_wname"] = w.get("name","")
    earnings = db_get("worker_earnings", {"worker_id": f"eq.{wid}"})
    payments = db_get("salary_payments", {"worker_id": f"eq.{wid}"})
    total_earned = sum(e["total"] for e in earnings)
    total_paid = sum(p["amount"] for p in payments)
    balance = total_earned - total_paid
    await update.callback_query.message.reply_text(
        f"💳 *{w.get('name','')}*\n\nJami topdi: {fmt(total_earned)}\nTo'landi: {fmt(total_paid)}\n*Qoldi: {fmt(balance)}*\n\nNecha so'm to'laysiz?",
        parse_mode="Markdown")
    return PAY_SALARY_AMOUNT

async def pay_salary_amount(update, context):
    try: amt = float(update.message.text.strip().replace(" ",""))
    except: await update.message.reply_text("❌ Raqam!"); return PAY_SALARY_AMOUNT
    wid = context.user_data["ps_wid"]; wname = context.user_data["ps_wname"]
    db_insert("salary_payments", {"worker_id":wid,"worker_name":wname,"amount":amt,"period_from":today(),"period_to":today()})
    db_insert("expenses", {"type":"maosh","description":f"{wname} maoshi","amount":amt,"expense_date":today()})

    # Notify worker
    ws = db_get("workers", {"id": f"eq.{wid}"})
    if ws and ws[0].get("chat_id"):
        try:
            await context.bot.send_message(chat_id=ws[0]["chat_id"],
                text=f"💳 *Maosh to'landi!*\n\n💰 Summa: *{fmt(amt)}*\n📅 Sana: {today()}",
                parse_mode="Markdown")
        except: pass

    await update.message.reply_text(f"✅ *{wname}* ga {fmt(amt)} to'landi!", parse_mode="Markdown")
    return MAIN_MENU

# ========== ISHCHI HISOBOTI ==========
async def do_worker_report(update, context):
    ws = db_get("workers")
    kb = [[InlineKeyboardButton(f"{w['name']}", callback_data=f"wr2_{w['id']}")] for w in ws]
    kb.append([InlineKeyboardButton("📊 Barchasi", callback_data="wr2_all")])
    await update.message.reply_text("📈 *Ishchi hisoboti*\n\nQaysi ishchi?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def cb_worker_report(update, context):
    await update.callback_query.answer()
    data = update.callback_query.data.replace("wr2_","")

    if data == "all":
        ws = db_get("workers")
        txt = "📈 *Barcha ishchilar hisoboti*\n\n"
        for w in ws:
            earnings = db_get("worker_earnings", {"worker_id": f"eq.{w['id']}"})
            payments = db_get("salary_payments", {"worker_id": f"eq.{w['id']}"})
            total_earned = sum(e["total"] for e in earnings)
            total_paid = sum(p["amount"] for p in payments)
            balance = total_earned - total_paid
            total_qty = sum(e["qty"] for e in earnings)
            txt += f"👤 *{w['name']}* ({w['role']})\n"
            txt += f"  Tikdi: {total_qty} dona\n"
            txt += f"  Topdi: {fmt(total_earned)}\n"
            txt += f"  To'landi: {fmt(total_paid)}\n"
            txt += f"  Qoldi: *{fmt(balance)}*\n\n"
        await update.callback_query.message.reply_text(txt, parse_mode="Markdown")
        return MAIN_MENU

    wid = int(data)
    ws = db_get("workers", {"id": f"eq.{wid}"})
    w = ws[0] if ws else {}
    earnings = db_get("worker_earnings", {"worker_id": f"eq.{wid}"})
    payments = db_get("salary_payments", {"worker_id": f"eq.{wid}"})
    rates = db_get("worker_rates", {"worker_id": f"eq.{wid}"})
    att = db_get("attendance", {"worker_id": f"eq.{wid}"})

    total_earned = sum(e["total"] for e in earnings)
    total_paid = sum(p["amount"] for p in payments)
    balance = total_earned - total_paid
    total_qty = sum(e["qty"] for e in earnings)
    total_minutes = sum(a.get("total_minutes",0) or 0 for a in att)
    total_hours = total_minutes // 60

    txt = f"📈 *{w.get('name','')} hisoboti*\n\n"
    txt += f"👔 Jami tikdi: *{total_qty} dona*\n"
    txt += f"⏱ Jami ishladi: *{total_hours} soat*\n"
    txt += f"💰 Jami topdi: *{fmt(total_earned)}*\n"
    txt += f"💳 To'landi: *{fmt(total_paid)}*\n"
    txt += f"📊 Qoldi: *{fmt(balance)}*\n\n"

    if rates:
        txt += "💰 *Ish narxlari:*\n"
        for r in rates:
            txt += f"  • {r['prod_name']}: {fmt(r['rate'])}/dona\n"
        txt += "\n"

    if earnings:
        txt += "📋 *So'nggi ishlar:*\n"
        for e in earnings[-5:]:
            txt += f"  • {e['prod_name']}: {e['qty']} dona = {fmt(e['total'])}\n"

    await update.callback_query.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

# ========== BICHIQCHI BUYURTMA ==========
async def do_cut_order(update, context):
    ws = db_get("workers", {"role": "eq.bichiqchi"})
    if not ws: await update.message.reply_text("❌ Bichiqchi yo'q!"); return MAIN_MENU
    kb = [[InlineKeyboardButton(w["name"], callback_data=f"co_{w['id']}")] for w in ws]
    await update.message.reply_text("✂️ *Bichiqchi buyurtma*\n\nQaysi bichiqchi?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return CUT_ORDER_WORKER

async def cut_order_worker(update, context):
    await update.callback_query.answer()
    wid = int(update.callback_query.data.replace("co_",""))
    ws = db_get("workers", {"id": f"eq.{wid}"})
    context.user_data["co_wid"] = wid
    context.user_data["co_wname"] = ws[0]["name"] if ws else ""
    prods = db_get("products", {"type": "eq.koylak"})
    kb = [[InlineKeyboardButton(f"{p['name']} ({p['qty']}dona)", callback_data=f"cop_{p['id']}")] for p in prods]
    await update.callback_query.message.reply_text("Qaysi mahsulot?", reply_markup=InlineKeyboardMarkup(kb))
    return CUT_ORDER_PROD

async def cut_order_prod(update, context):
    await update.callback_query.answer()
    pid = int(update.callback_query.data.replace("cop_",""))
    ps = db_get("products", {"id": f"eq.{pid}"})
    p = ps[0] if ps else {}
    context.user_data["co_pid"] = pid
    context.user_data["co_pname"] = p.get("name","")
    await update.callback_query.message.reply_text(f"✂️ *{p.get('name','')}*\n\nNechta bichsin?", parse_mode="Markdown")
    return CUT_ORDER_QTY

async def cut_order_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Raqam!"); return CUT_ORDER_QTY
    wid = context.user_data["co_wid"]; wname = context.user_data["co_wname"]
    pid = context.user_data["co_pid"]; pname = context.user_data["co_pname"]
    result = db_insert("cutting_orders", {
        "prod_id":pid,"prod_name":pname,"qty":qty,
        "cutter_id":wid,"cutter_name":wname,
        "status":"assigned","order_date":today()
    })
    await update.message.reply_text(
        f"✅ *Buyurtma berildi!*\n\n✂️ {wname}\n👔 {pname}: *{qty} dona*\n📅 {today()}",
        parse_mode="Markdown")

    # Notify cutter
    ws = db_get("workers", {"id": f"eq.{wid}"})
    if ws and ws[0].get("chat_id"):
        oid = result[0]["id"] if result and isinstance(result, list) else ""
        try:
            await context.bot.send_message(chat_id=ws[0]["chat_id"],
                text=f"✂️ *Yangi buyurtma!*\n\n👔 {pname}: *{qty} dona*\n📅 {today()}\n\nBotdan tasdiqlang!",
                parse_mode="Markdown")
        except: pass
    return MAIN_MENU

# ========== TIKUV QABUL ==========
async def do_sew_receipt(update, context):
    orders = db_get("cutting_orders", {"status": "eq.sent", "order_date": f"eq.{today()}"})
    if not orders:
        # Show all today orders
        orders = db_get("cutting_orders", {"order_date": f"eq.{today()}"})
    if not orders: await update.message.reply_text("❌ Bugun buyurtma yo'q!"); return MAIN_MENU
    kb = [[InlineKeyboardButton(f"✂️{o['cutter_name']}: {o['prod_name']} ({o['qty']}dona)", callback_data=f"sr2_{o['id']}")] for o in orders]
    await update.message.reply_text("🪡 *Tikuv qabul*\n\nQaysi buyurtma?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SEW_RECEIPT_ORDER

async def sew_receipt_order(update, context):
    await update.callback_query.answer()
    oid = int(update.callback_query.data.replace("sr2_",""))
    orders = db_get("cutting_orders", {"id": f"eq.{oid}"})
    o = orders[0] if orders else {}
    context.user_data["sr2_oid"] = oid
    context.user_data["sr2_oname"] = o.get("prod_name","")
    context.user_data["sr2_oqty"] = o.get("qty",0)
    ws = db_get("workers", {"role": "eq.tikuvchi"})
    kb = [[InlineKeyboardButton(w["name"], callback_data=f"sr2w_{w['id']}")] for w in ws]
    await update.callback_query.message.reply_text(
        f"👔 *{o.get('prod_name','')}* — {o.get('qty',0)} dona\n\nQaysi tikuvchi qabul qildi?",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SEW_RECEIPT_SEWER

async def sew_receipt_sewer(update, context):
    await update.callback_query.answer()
    swid = int(update.callback_query.data.replace("sr2w_",""))
    ws = db_get("workers", {"id": f"eq.{swid}"})
    context.user_data["sr2_swid"] = swid
    context.user_data["sr2_swname"] = ws[0]["name"] if ws else ""
    await update.callback_query.message.reply_text(
        f"🪡 *{context.user_data['sr2_swname']}* nechta qabul qildi?\n(Jami: {context.user_data['sr2_oqty']} dona)")
    return SEW_RECEIPT_QTY

async def sew_receipt_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Raqam!"); return SEW_RECEIPT_QTY
    oid = context.user_data["sr2_oid"]; swid = context.user_data["sr2_swid"]
    swname = context.user_data["sr2_swname"]; pname = context.user_data["sr2_oname"]
    db_insert("sewing_receipts", {
        "cutting_order_id":oid,"sewer_id":swid,"sewer_name":swname,
        "received_qty":qty,"sewn_qty":0,"status":"in_progress","receipt_date":today()
    })

    # Add to worker_jobs
    ex = db_get("worker_jobs", {"worker_id": f"eq.{swid}", "job_date": f"eq.{today()}"})
    job_ex = [j for j in ex if j.get("prod_name")==pname]
    if job_ex: db_update("worker_jobs", {"total":job_ex[0]["total"]+qty}, {"id": f"eq.{job_ex[0]['id']}"})
    else:
        prods = db_get("cutting_orders", {"id": f"eq.{oid}"})
        pid = prods[0]["prod_id"] if prods else 0
        db_insert("worker_jobs", {"worker_id":swid,"prod_id":pid,"prod_name":pname,"total":qty,"done":0,"job_date":today()})

    await update.message.reply_text(
        f"✅ *Qabul saqlandi!*\n\n🪡 {swname}\n👔 {pname}: *{qty} dona*",
        parse_mode="Markdown")

    # Notify sewer
    ws = db_get("workers", {"id": f"eq.{swid}"})
    if ws and ws[0].get("chat_id"):
        try:
            await context.bot.send_message(chat_id=ws[0]["chat_id"],
                text=f"📋 *Yangi ish qabul qildingiz!*\n\n👔 {pname}: *{qty} dona*\n📅 {today()}",
                parse_mode="Markdown")
        except: pass
    return MAIN_MENU

# ========== VAZIFA BERISH ==========
async def do_assign(update, context):
    ws = db_get("workers")
    if not ws: await update.message.reply_text("Ishchilar yo'q!"); return MAIN_MENU
    kb = [[InlineKeyboardButton(f"{w['name']} ({w['role']})", callback_data=f"aw2_{w['id']}")] for w in ws]
    await update.message.reply_text("📋 *Vazifa berish* — Ishchi:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ASSIGN_WORKER

async def assign_worker_cb(update, context):
    await update.callback_query.answer()
    wid = int(update.callback_query.data.replace("aw2_",""))
    context.user_data["awid"] = wid
    ws = db_get("workers", {"id": f"eq.{wid}"})
    w = ws[0] if ws else {}
    context.user_data["awname"] = w.get("name","")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    txt = f"📋 *{w.get('name','')}* — bugun:\n"
    for j in jobs: txt += f"  • {j['prod_name']}: {j['done']}/{j['total']}\n"
    if not jobs: txt += "  Hali yo'q\n"
    prods = db_get("products", {"type": "eq.koylak"})
    context.user_data["awprods"] = prods
    kb = [[InlineKeyboardButton(f"👔 {p['name']}", callback_data=f"awp_{p['id']}")] for p in prods]
    await update.callback_query.message.reply_text(txt+"\nQaysi mahsulot?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ASSIGN_PROD

async def assign_prod_cb(update, context):
    await update.callback_query.answer()
    pid = int(update.callback_query.data.replace("awp_",""))
    p = next(x for x in context.user_data["awprods"] if x["id"]==pid)
    context.user_data["awprod"] = {"id":pid,"name":p["name"]}
    await update.callback_query.message.reply_text(f"👔 *{p['name']}*\n\nNechta?", parse_mode="Markdown")
    return ASSIGN_QTY

async def assign_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Raqam!"); return ASSIGN_QTY
    wid = context.user_data["awid"]; prod = context.user_data["awprod"]
    ex = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "prod_id": f"eq.{prod['id']}", "job_date": f"eq.{today()}"})
    if ex: db_update("worker_jobs", {"total":ex[0]["total"]+qty}, {"id": f"eq.{ex[0]['id']}"})
    else: db_insert("worker_jobs", {"worker_id":wid,"prod_id":prod["id"],"prod_name":prod["name"],"total":qty,"done":0,"job_date":today()})
    ws = db_get("workers", {"id": f"eq.{wid}"})
    w = ws[0] if ws else {}
    await update.message.reply_text(f"✅ *Vazifa berildi!*\n👤 {w.get('name','')}\n👔 {prod['name']}: {qty} ta", parse_mode="Markdown")
    if w.get("chat_id"):
        try:
            await context.bot.send_message(chat_id=w["chat_id"],
                text=f"📋 *Yangi vazifa!*\n👔 {prod['name']}: *{qty} ta*\n📅 {today()}", parse_mode="Markdown")
        except: pass
    return MAIN_MENU

# ========== WORKER: VAZIFALAR ==========
async def w_vazifalar(update, context):
    wid = context.user_data.get("wid")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    if not jobs: await update.message.reply_text("📋 Bugun vazifa yo'q!"); return MAIN_MENU
    txt = f"📋 *Bugungi vazifalarim — {today()}*\n\n"
    for j in jobs:
        pct = round(j["done"]/j["total"]*100) if j["total"]>0 else 0
        bar = "█"*int(pct/10)+"░"*(10-int(pct/10))
        txt += f"*{j['prod_name']}*\n{bar} {pct}%\n✅{j['done']} | 📦{j['total']} | 🔄{max(0,j['total']-j['done'])} qoldi\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def w_done_start(update, context):
    wid = context.user_data.get("wid")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    incomplete = [j for j in jobs if j["done"]<j["total"]]
    if not incomplete: await update.message.reply_text("🎉 Barcha vazifalar bajarildi!"); return MAIN_MENU
    context.user_data["wjobs"] = jobs
    kb = [[InlineKeyboardButton(f"👔 {j['prod_name']} ({j['total']-j['done']} qoldi)", callback_data=f"wdj_{j['id']}")] for j in incomplete]
    await update.message.reply_text("Qaysi mahsulot?", reply_markup=InlineKeyboardMarkup(kb))
    return WORKER_DONE_SELECT

async def w_done_sel(update, context):
    await update.callback_query.answer()
    jid = int(update.callback_query.data.replace("wdj_",""))
    job = next(j for j in context.user_data["wjobs"] if j["id"]==jid)
    context.user_data["wdj"] = job
    await update.callback_query.message.reply_text(
        f"👔 *{job['prod_name']}*\n✅ {job['done']} | 🔄 {job['total']-job['done']} qolgan\n\nNechta bajardingiz?",
        parse_mode="Markdown")
    return WORKER_DONE_QTY

async def w_done_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Raqam!"); return WORKER_DONE_QTY
    job = context.user_data["wdj"]
    wid = context.user_data.get("wid"); wname = context.user_data.get("name","")
    new_done = min(job["total"], job["done"]+qty)
    actual = new_done - job["done"]
    db_update("worker_jobs", {"done":new_done}, {"id": f"eq.{job['id']}"})

    # Save earnings
    rates = db_get("worker_rates", {"worker_id": f"eq.{wid}", "prod_id": f"eq.{job['prod_id']}"})
    if rates:
        rate = rates[0]["rate"]
        earning = actual * rate
        db_insert("worker_earnings", {"worker_id":wid,"worker_name":wname,"prod_name":job["prod_name"],"qty":actual,"rate":rate,"total":earning,"work_date":today()})
        earn_txt = f"\n💰 Bugungi daromad: +{fmt(earning)}"
    else:
        earn_txt = "\n⚠️ Ish narxi belgilanmagan (admin belgilaydi)"

    txt = f"✅ *{actual} ta saqlandi!*\n👔 {job['prod_name']}\n📊 {new_done}/{job['total']}{earn_txt}"
    all_jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    if all(j["done"]>=j["total"] for j in all_jobs):
        txt += "\n\n🎉 *BARCHA VAZIFALAR BAJARILDI!*"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

# ========== WORKER: DAROMAD ==========
async def w_daromad(update, context):
    wid = context.user_data.get("wid"); wname = context.user_data.get("name","")
    earnings = db_get("worker_earnings", {"worker_id": f"eq.{wid}"})
    payments = db_get("salary_payments", {"worker_id": f"eq.{wid}"})
    today_earn = [e for e in earnings if e["work_date"]==today()]
    total_earned = sum(e["total"] for e in earnings)
    total_paid = sum(p["amount"] for p in payments)
    today_total = sum(e["total"] for e in today_earn)
    balance = total_earned - total_paid

    txt = f"💰 *{wname} daromadi*\n\n"
    txt += f"📅 Bugun: *{fmt(today_total)}*\n"
    txt += f"💎 Jami topdi: *{fmt(total_earned)}*\n"
    txt += f"💳 To'landi: *{fmt(total_paid)}*\n"
    txt += f"📊 Qoldi: *{fmt(balance)}*\n\n"

    if today_earn:
        txt += "📋 *Bugungi ishlar:*\n"
        for e in today_earn:
            txt += f"  • {e['prod_name']}: {e['qty']} dona = {fmt(e['total'])}\n"

    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def w_tarix(update, context):
    wid = context.user_data.get("wid")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}"})
    if not jobs: await update.message.reply_text("📅 Tarix yo'q."); return MAIN_MENU
    jobs = sorted(jobs, key=lambda x: x["job_date"], reverse=True)[:20]
    txt = "📅 *So'nggi ishlarim:*\n\n"
    cur = None
    for j in jobs:
        if j["job_date"]!=cur: cur=j["job_date"]; txt+=f"📅 *{cur}*\n"
        pct = round(j["done"]/j["total"]*100) if j["total"]>0 else 0
        txt += f"  • {j['prod_name']}: {j['done']}/{j['total']} ({pct}%)\n"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

# ========== MAIN HANDLER ==========
async def main_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    role = context.user_data.get("role")
    if not role or t == "/start": return await start(update, context)

    # Logout
    if t == "🚪 Chiqish": return await do_logout(update, context)

    if role == "admin":
        if t=="🏠 Bosh sahifa": await do_home(update,context)
        elif t=="👔 Mahsulotlar": await do_products(update,context)
        elif t=="🛒 Savdo": return await do_savdo(update,context)
        elif t=="💸 Xarajat": return await do_xarajat(update,context)
        elif t=="📊 Hisobot": await do_hisobot(update,context)
        elif t=="👷 Ishchilar": await do_workers(update,context)
        elif t=="📋 Vazifa berish": return await do_assign(update,context)
        elif t=="📦 Ombor holati": await do_ombor(update,context)
        elif t=="✂️ Bichiqchi buyurtma": return await do_cut_order(update,context)
        elif t=="🪡 Tikuv qabul": return await do_sew_receipt(update,context)
        elif t=="💰 Maosh belgilash": return await do_set_rate(update,context)
        elif t=="💳 Maosh to'lash": return await do_pay_salary(update,context)
        elif t=="📈 Ishchi hisoboti": await do_worker_report(update,context)
        elif t=="🕐 Davomat": await do_davomat(update,context)
        else: await update.message.reply_text("Tugmalardan foydalaning 👆")
    else:
        if t=="✅ Ishga keldim": await worker_attendance(update,context,"arrived")
        elif t=="🏠 Uydaman": await worker_attendance(update,context,"home")
        elif t=="🍽 Obedman": await worker_attendance(update,context,"lunch")
        elif t=="🔚 Ishni tugatdim": await worker_attendance(update,context,"finished")
        elif t=="📋 Mening vazifalarim": await w_vazifalar(update,context)
        elif t=="✍️ Ish kiriting": return await w_done_start(update,context)
        elif t=="💰 Mening daromadam": await w_daromad(update,context)
        elif t=="📅 Mening tarixim": await w_tarix(update,context)
        else: await update.message.reply_text("Tugmalardan foydalaning 👆")
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)
    return MAIN_MENU

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOGIN_ROLE:[MessageHandler(filters.TEXT&~filters.COMMAND, login_role)],
            LOGIN_NAME:[MessageHandler(filters.TEXT&~filters.COMMAND, login_name)],
            LOGIN_PASS:[MessageHandler(filters.TEXT&~filters.COMMAND, login_pass)],
            MAIN_MENU:[
                MessageHandler(filters.TEXT&~filters.COMMAND, main_msg),
                CallbackQueryHandler(cb_add_prod,"^add_prod$"),
                CallbackQueryHandler(cb_edit_prod,"^edit_prod$"),
                CallbackQueryHandler(cb_rep,"^rep_"),
                CallbackQueryHandler(cb_add_worker,"^add_worker$"),
                CallbackQueryHandler(cb_edit_worker,"^edit_worker$"),
                CallbackQueryHandler(cb_worker_report,"^wr2_"),
            ],
            ADD_PROD_TYPE:[CallbackQueryHandler(add_prod_type,"^pt_")],
            ADD_PROD_NAME:[MessageHandler(filters.TEXT&~filters.COMMAND, add_prod_name)],
            ADD_PROD_QTY:[MessageHandler(filters.TEXT&~filters.COMMAND, add_prod_qty)],
            ADD_PROD_PRICE:[MessageHandler(filters.TEXT&~filters.COMMAND, add_prod_price)],
            ADD_PROD_COST:[MessageHandler(filters.TEXT&~filters.COMMAND, add_prod_cost)],
            EDIT_PROD_SELECT:[CallbackQueryHandler(edit_prod_select,"^ep_")],
            EDIT_PROD_FIELD:[CallbackQueryHandler(edit_prod_field,"^epf_")],
            EDIT_PROD_VALUE:[MessageHandler(filters.TEXT&~filters.COMMAND, edit_prod_value)],
            ADD_SALE_PROD:[CallbackQueryHandler(sale_prod_cb,"^sp_")],
            ADD_SALE_QTY:[MessageHandler(filters.TEXT&~filters.COMMAND, sale_qty)],
            ADD_SALE_PRICE:[MessageHandler(filters.TEXT&~filters.COMMAND, sale_price)],
            ADD_SALE_CLIENT:[MessageHandler(filters.TEXT&~filters.COMMAND, sale_client)],
            ADD_SALE_PAY:[CallbackQueryHandler(sale_pay,"^pay_")],
            ADD_EXP_TYPE:[CallbackQueryHandler(exp_type,"^et_")],
            ADD_EXP_DESC:[MessageHandler(filters.TEXT&~filters.COMMAND, exp_desc)],
            ADD_EXP_AMOUNT:[MessageHandler(filters.TEXT&~filters.COMMAND, exp_amount)],
            ADD_WORKER_NAME:[MessageHandler(filters.TEXT&~filters.COMMAND, aw_name)],
            ADD_WORKER_ROLE:[CallbackQueryHandler(aw_role,"^wr_")],
            ADD_WORKER_LOGIN:[MessageHandler(filters.TEXT&~filters.COMMAND, aw_login)],
            ADD_WORKER_PASS:[MessageHandler(filters.TEXT&~filters.COMMAND, aw_pass)],
            EDIT_WORKER_SELECT:[CallbackQueryHandler(ew_select,"^ew_")],
            EDIT_WORKER_FIELD:[CallbackQueryHandler(ew_field,"^ewf_")],
            EDIT_WORKER_VALUE:[MessageHandler(filters.TEXT&~filters.COMMAND, ew_value)],
            ASSIGN_WORKER:[CallbackQueryHandler(assign_worker_cb,"^aw2_")],
            ASSIGN_PROD:[CallbackQueryHandler(assign_prod_cb,"^awp_")],
            ASSIGN_QTY:[MessageHandler(filters.TEXT&~filters.COMMAND, assign_qty)],
            WORKER_DONE_SELECT:[CallbackQueryHandler(w_done_sel,"^wdj_")],
            WORKER_DONE_QTY:[MessageHandler(filters.TEXT&~filters.COMMAND, w_done_qty)],
            SET_RATE_WORKER:[CallbackQueryHandler(set_rate_worker,"^sr_")],
            SET_RATE_PROD:[CallbackQueryHandler(set_rate_prod,"^srp_")],
            SET_RATE_PRICE:[MessageHandler(filters.TEXT&~filters.COMMAND, set_rate_price)],
            PAY_SALARY_WORKER:[CallbackQueryHandler(pay_salary_worker,"^ps_")],
            PAY_SALARY_AMOUNT:[MessageHandler(filters.TEXT&~filters.COMMAND, pay_salary_amount)],
            CUT_ORDER_WORKER:[CallbackQueryHandler(cut_order_worker,"^co_")],
            CUT_ORDER_PROD:[CallbackQueryHandler(cut_order_prod,"^cop_")],
            CUT_ORDER_QTY:[MessageHandler(filters.TEXT&~filters.COMMAND, cut_order_qty)],
            SEW_RECEIPT_ORDER:[CallbackQueryHandler(sew_receipt_order,"^sr2_")],
            SEW_RECEIPT_SEWER:[CallbackQueryHandler(sew_receipt_sewer,"^sr2w_")],
            SEW_RECEIPT_QTY:[MessageHandler(filters.TEXT&~filters.COMMAND, sew_receipt_qty)],
        },
        fallbacks=[CommandHandler("cancel",cancel), CommandHandler("start",start)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    logger.info("✅ Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

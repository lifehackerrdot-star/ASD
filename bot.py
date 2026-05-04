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
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_rlWfnBW1wWGI1MSM32Kpgw_JyiTZyeL")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "1234")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def db_get(table, params=None):
    p = {"select": "*"}
    if params: p.update(params)
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, params=p)
    return r.json() if r.ok else []

def db_insert(table, data):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data)
    return r.json() if r.ok else []

def db_update(table, data, params):
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data, params=params)
    return r.ok

def db_delete(table, params):
    r = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, params=params)
    return r.ok

(LOGIN_ROLE, LOGIN_NAME, LOGIN_PASS, MAIN_MENU,
 ADD_PROD_TYPE, ADD_PROD_NAME, ADD_PROD_QTY, ADD_PROD_PRICE, ADD_PROD_COST,
 EDIT_PROD_SELECT, EDIT_PROD_FIELD, EDIT_PROD_VALUE,
 ADD_SALE_PROD, ADD_SALE_QTY, ADD_SALE_PRICE, ADD_SALE_CLIENT, ADD_SALE_PAY,
 ADD_EXP_TYPE, ADD_EXP_DESC, ADD_EXP_AMOUNT,
 ADD_WORKER_NAME, ADD_WORKER_ROLE, ADD_WORKER_LOGIN, ADD_WORKER_PASS,
 ASSIGN_WORKER, ASSIGN_PROD, ASSIGN_QTY,
 WORKER_DONE_SELECT, WORKER_DONE_QTY,
 EDIT_WORKER_SELECT, EDIT_WORKER_FIELD, EDIT_WORKER_VALUE) = range(32)

def today():
    return datetime.now().strftime("%Y-%m-%d")

def fmt(n):
    try:
        n = float(n or 0)
        if n >= 1_000_000_000: return f"{n/1_000_000_000:.2f} mlrd so'm"
        if n >= 1_000_000: return f"{n/1_000_000:.1f} mln so'm"
        return f"{int(n):,} so'm".replace(",", " ")
    except: return "0 so'm"

def get_worker_by_chat(chat_id):
    ws = db_get("workers", {"chat_id": f"eq.{chat_id}"})
    return ws[0] if ws else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    chat_id = update.effective_chat.id
    worker = get_worker_by_chat(chat_id)
    if worker:
        context.user_data.update({"role": worker["role"], "worker_id": worker["id"], "name": worker["name"]})
        await show_menu(update, context)
        return MAIN_MENU
    kb = [[KeyboardButton("👑 Admin"), KeyboardButton("✂️ Bichiqchi")],
          [KeyboardButton("🪡 Tikuvchi"), KeyboardButton("📦 Omborchi")]]
    await update.message.reply_text("👔 *Koylak Biznes Bot*\n\nRolingizni tanlang:",
        parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return LOGIN_ROLE

async def login_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rm = {"👑 Admin":"admin","✂️ Bichiqchi":"bichiqchi","🪡 Tikuvchi":"tikuvchi","📦 Omborchi":"omborchi"}
    role = rm.get(update.message.text)
    if not role:
        await update.message.reply_text("Tugmadan tanlang!")
        return LOGIN_ROLE
    context.user_data["role"] = role
    if role == "admin":
        await update.message.reply_text("🔐 Admin parolini kiriting:", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
        return LOGIN_PASS
    await update.message.reply_text("👤 Loginингizni kiriting:", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
    return LOGIN_NAME

async def login_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login_input"] = update.message.text.strip()
    await update.message.reply_text("🔐 Parolингizni kiriting:")
    return LOGIN_PASS

async def login_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pwd = update.message.text.strip()
    role = context.user_data.get("role")
    chat_id = update.effective_chat.id
    if role == "admin":
        if pwd != ADMIN_PASS:
            await update.message.reply_text("❌ Parol noto'g'ri!")
            return LOGIN_PASS
        context.user_data["name"] = "Admin"
        await show_menu(update, context)
        return MAIN_MENU
    li = context.user_data.get("login_input","")
    ws = db_get("workers", {"login": f"eq.{li}", "role": f"eq.{role}"})
    w = ws[0] if ws else None
    if not w or w.get("pass") != pwd:
        await update.message.reply_text("❌ Login yoki parol noto'g'ri!\n/start ni bosing.")
        return LOGIN_ROLE
    db_update("workers", {"chat_id": chat_id}, {"id": f"eq.{w['id']}"})
    context.user_data.update({"worker_id": w["id"], "name": w["name"]})
    await show_menu(update, context)
    return MAIN_MENU

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = context.user_data.get("role")
    name = context.user_data.get("name","")
    h = datetime.now().hour
    gr = "Xayrli tong" if h<12 else "Xayrli kun" if h<18 else "Xayrli kech"
    msg = update.message if update.message else update.callback_query.message
    if role == "admin":
        kb = [[KeyboardButton("🏠 Bosh sahifa"), KeyboardButton("📊 Hisobot")],
              [KeyboardButton("👔 Mahsulotlar"), KeyboardButton("🛒 Savdo")],
              [KeyboardButton("💸 Xarajat"), KeyboardButton("👷 Ishchilar")],
              [KeyboardButton("📋 Vazifa berish"), KeyboardButton("📦 Ombor holati")]]
        await msg.reply_text(f"👑 *{gr}, {name}!*", parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        kb = [[KeyboardButton("📋 Mening vazifalarim")],
              [KeyboardButton("✅ Bajarildi deb belgilash")],
              [KeyboardButton("📅 Mening tarixim")]]
        await msg.reply_text(f"👋 *{gr}, {name}!*", parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def do_home(update, context):
    prods = db_get("products")
    sales = db_get("sales", {"sale_date": f"eq.{today()}"})
    clients = db_get("clients")
    workers = db_get("workers")
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
    txt += f"📦 *Ombor jami:* {fmt(kv+mv+dv)}\n"
    txt += f"👷 Ishchilar: {len(workers)} ta"
    await update.message.reply_text(txt, parse_mode="Markdown")

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
    except:
        await update.message.reply_text("❌ Raqam kiriting!")
        return ADD_PROD_QTY
    await update.message.reply_text("Sotuv narxini kiriting (so'm):")
    return ADD_PROD_PRICE

async def add_prod_price(update, context):
    try: context.user_data["np"]["price"] = float(update.message.text.strip().replace(" ",""))
    except:
        await update.message.reply_text("❌ Raqam kiriting!")
        return ADD_PROD_PRICE
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
        except:
            await update.message.reply_text("❌ Raqam kiriting!")
            return EDIT_PROD_VALUE
    db_update("products", {f:v}, {"id": f"eq.{context.user_data['epid']}"})
    await update.message.reply_text("✅ Yangilandi!")
    return MAIN_MENU

async def do_savdo(update, context):
    prods = db_get("products", {"type": "eq.koylak"})
    if not prods:
        await update.message.reply_text("❌ Koylak yo'q.")
        return MAIN_MENU
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
    except:
        await update.message.reply_text("❌ Raqam!")
        return ADD_SALE_QTY
    if qty > context.user_data["ns"]["pqty"]:
        await update.message.reply_text(f"❌ Faqat {context.user_data['ns']['pqty']} dona bor!")
        return ADD_SALE_QTY
    context.user_data["ns"]["qty"] = qty
    await update.message.reply_text(f"💰 Narx (so'm):\n(Standart: {fmt(context.user_data['ns']['pprice'])})")
    return ADD_SALE_PRICE

async def sale_price(update, context):
    try: price = float(update.message.text.strip().replace(" ",""))
    except:
        await update.message.reply_text("❌ Raqam!")
        return ADD_SALE_PRICE
    ns = context.user_data["ns"]
    ns["price"] = price
    ns["total"] = price * ns["qty"]
    ns["profit"] = (price - ns["pcost"]) * ns["qty"]
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
    if ps:
        db_update("products", {"qty":ps[0]["qty"]-ns["qty"],"sold":(ps[0].get("sold")or 0)+ns["qty"]}, {"id": f"eq.{ns['pid']}"})
    if pay=="nasiya":
        ex = db_get("clients", {"name": f"eq.{ns['client']}"})
        if ex: db_update("clients", {"debt":ex[0]["debt"]+ns["total"]}, {"name": f"eq.{ns['client']}"})
        else: db_insert("clients", {"name":ns["client"],"debt":ns["total"]})
    pl = {"naqd":"💵 Naqd","nasiya":"📋 Nasiya","karta":"💳 Karta"}
    await update.callback_query.message.reply_text(
        f"✅ *Sotuv saqlandi!*\n\n👔 {ns['pname']} × {ns['qty']}\n💰 {fmt(ns['total'])}\n📈 Foyda: {fmt(ns['profit'])}\n👤 {ns['client']}\n{pl[pay]}",
        parse_mode="Markdown")
    return MAIN_MENU

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
    except:
        await update.message.reply_text("❌ Raqam!")
        return ADD_EXP_AMOUNT
    ne = context.user_data["ne"]
    db_insert("expenses", {"type":ne["type"],"description":ne["desc"],"amount":amt,"expense_date":today()})
    await update.message.reply_text(f"✅ *Xarajat saqlandi!*\n📝 {ne['desc']}\n💰 {fmt(amt)}", parse_mode="Markdown")
    return MAIN_MENU

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

async def do_workers(update, context):
    ws = db_get("workers")
    if not ws:
        await update.message.reply_text("Ishchilar yo'q.")
        return MAIN_MENU
    ri = {"bichiqchi":"✂️","tikuvchi":"🪡","omborchi":"📦"}
    txt = "👷 *Ishchilar:*\n\n"
    for w in ws:
        jobs = db_get("worker_jobs", {"worker_id": f"eq.{w['id']}", "job_date": f"eq.{today()}"})
        total = sum(j["total"] for j in jobs)
        done = sum(j["done"] for j in jobs)
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
    await update.callback_query.message.reply_text("Login kiriting (masalan: sardor01):")
    return ADD_WORKER_LOGIN

async def aw_login(update, context):
    lg = update.message.text.strip().lower()
    ex = db_get("workers", {"login": f"eq.{lg}"})
    if ex:
        await update.message.reply_text("❌ Bu login band! Boshqa kiriting:")
        return ADD_WORKER_LOGIN
    context.user_data["nw"]["login"] = lg
    await update.message.reply_text("Parol kiriting:")
    return ADD_WORKER_PASS

async def aw_pass(update, context):
    nw = context.user_data["nw"]
    nw["pass"] = update.message.text.strip()
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

async def do_assign(update, context):
    ws = db_get("workers")
    if not ws:
        await update.message.reply_text("Ishchilar yo'q!")
        return MAIN_MENU
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
    if jobs:
        for j in jobs: txt += f"  • {j['prod_name']}: {j['done']}/{j['total']}\n"
    else:
        txt += "  Hali yo'q\n"
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
    except:
        await update.message.reply_text("❌ Raqam!")
        return ASSIGN_QTY
    wid = context.user_data["awid"]
    prod = context.user_data["awprod"]
    ex = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "prod_id": f"eq.{prod['id']}", "job_date": f"eq.{today()}"})
    if ex:
        db_update("worker_jobs", {"total":ex[0]["total"]+qty}, {"id": f"eq.{ex[0]['id']}"})
    else:
        db_insert("worker_jobs", {"worker_id":wid,"prod_id":prod["id"],"prod_name":prod["name"],"total":qty,"done":0,"job_date":today()})
    ws = db_get("workers", {"id": f"eq.{wid}"})
    w = ws[0] if ws else {}
    await update.message.reply_text(f"✅ *Vazifa berildi!*\n👤 {w.get('name','')}\n👔 {prod['name']}: {qty} ta", parse_mode="Markdown")
    if w.get("chat_id"):
        try:
            await context.bot.send_message(chat_id=w["chat_id"],
                text=f"📋 *Yangi vazifa!*\n👔 {prod['name']}: *{qty} ta*\n📅 {today()}",
                parse_mode="Markdown")
        except: pass
    return MAIN_MENU

async def w_vazifalar(update, context):
    wid = context.user_data.get("worker_id")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    if not jobs:
        await update.message.reply_text("📋 Bugun vazifa yo'q hali. Admin vazifa berganda xabar keladi!")
        return MAIN_MENU
    txt = f"📋 *Bugungi vazifalarim — {today()}*\n\n"
    for j in jobs:
        pct = round(j["done"]/j["total"]*100) if j["total"]>0 else 0
        bar = "█"*int(pct/10)+"░"*(10-int(pct/10))
        txt += f"*{j['prod_name']}*\n{bar} {pct}%\n✅{j['done']} | 📦{j['total']} | 🔄{max(0,j['total']-j['done'])} qoldi\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def w_done_start(update, context):
    wid = context.user_data.get("worker_id")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    incomplete = [j for j in jobs if j["done"]<j["total"]]
    if not incomplete:
        await update.message.reply_text("🎉 Barcha vazifalar bajarildi!")
        return MAIN_MENU
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
        f"👔 *{job['prod_name']}*\n✅ {job['done']} bajarilgan | 🔄 {job['total']-job['done']} qolgan\n\nNechta bajardingiz?",
        parse_mode="Markdown")
    return WORKER_DONE_QTY

async def w_done_qty(update, context):
    try: qty = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ Raqam!")
        return WORKER_DONE_QTY
    job = context.user_data["wdj"]
    new_done = min(job["total"], job["done"]+qty)
    actual = new_done - job["done"]
    db_update("worker_jobs", {"done":new_done}, {"id": f"eq.{job['id']}"})
    txt = f"✅ *{actual} ta saqlandi!*\n👔 {job['prod_name']}\n📊 {new_done}/{job['total']}"
    wid = context.user_data.get("worker_id")
    all_jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    if all(j["done"]>=j["total"] for j in all_jobs):
        txt += "\n\n🎉 *BARCHA VAZIFALAR BAJARILDI! TABRIKLAYMIZ!*"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def w_tarix(update, context):
    wid = context.user_data.get("worker_id")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}"})
    if not jobs:
        await update.message.reply_text("📅 Tarix yo'q.")
        return MAIN_MENU
    jobs = sorted(jobs, key=lambda x: x["job_date"], reverse=True)[:20]
    txt = "📅 *So'nggi ishlarim:*\n\n"
    cur = None
    for j in jobs:
        if j["job_date"]!=cur:
            cur=j["job_date"]; txt+=f"📅 *{cur}*\n"
        pct = round(j["done"]/j["total"]*100) if j["total"]>0 else 0
        txt += f"  • {j['prod_name']}: {j['done']}/{j['total']} ({pct}%)\n"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def main_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    role = context.user_data.get("role")
    if not role:
        await start(update, context)
        return LOGIN_ROLE
    if role=="admin":
        if t=="🏠 Bosh sahifa": await do_home(update,context)
        elif t=="👔 Mahsulotlar": await do_products(update,context)
        elif t=="🛒 Savdo": return await do_savdo(update,context)
        elif t=="💸 Xarajat": return await do_xarajat(update,context)
        elif t=="📊 Hisobot": await do_hisobot(update,context)
        elif t=="👷 Ishchilar": await do_workers(update,context)
        elif t=="📋 Vazifa berish": return await do_assign(update,context)
        elif t=="📦 Ombor holati": await do_ombor(update,context)
        else: await update.message.reply_text("Tugmalardan foydalaning 👆")
    else:
        if t=="📋 Mening vazifalarim": await w_vazifalar(update,context)
        elif t=="✅ Bajarildi deb belgilash": return await w_done_start(update,context)
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
            ASSIGN_WORKER:[CallbackQueryHandler(assign_worker_cb,"^aw2_")],
            ASSIGN_PROD:[CallbackQueryHandler(assign_prod_cb,"^awp_")],
            ASSIGN_QTY:[MessageHandler(filters.TEXT&~filters.COMMAND, assign_qty)],
            WORKER_DONE_SELECT:[CallbackQueryHandler(w_done_sel,"^wdj_")],
            WORKER_DONE_QTY:[MessageHandler(filters.TEXT&~filters.COMMAND, w_done_qty)],
            EDIT_WORKER_SELECT:[CallbackQueryHandler(ew_select,"^ew_")],
            EDIT_WORKER_FIELD:[CallbackQueryHandler(ew_field,"^ewf_")],
            EDIT_WORKER_VALUE:[MessageHandler(filters.TEXT&~filters.COMMAND, ew_value)],
        },
        fallbacks=[CommandHandler("cancel",cancel), CommandHandler("start",start)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    logger.info("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

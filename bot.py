import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Тошкент вақти UTC+5
TZ = timezone(timedelta(hours=5))

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

def now_tz():
    return datetime.now(TZ)

def today():
    return now_tz().strftime("%Y-%m-%d")

def now_str():
    return now_tz().strftime("%Y-%m-%d %H:%M:%S")

def now_time():
    return now_tz().strftime("%H:%M")

def fmt(n):
    try:
        n = float(n or 0)
        if n >= 1_000_000_000: return f"{n/1_000_000_000:.2f} млрд сўм"
        if n >= 1_000_000: return f"{n/1_000_000:.1f} млн сўм"
        return f"{int(n):,} сўм".replace(",", " ")
    except: return "0 сўм"

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
 REPORT_PERIOD) = range(44)

def get_worker_by_chat(chat_id):
    ws = db_get("workers", {"chat_id": f"eq.{chat_id}"})
    return ws[0] if ws else None

def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🏠 Бош саҳифа"), KeyboardButton("📊 Ҳисобот")],
        [KeyboardButton("👔 Маҳсулотлар"), KeyboardButton("🛒 Савдо")],
        [KeyboardButton("💸 Харажат"), KeyboardButton("👷 Ишчилар")],
        [KeyboardButton("📋 Вазифа бериш"), KeyboardButton("📦 Омбор ҳолати")],
        [KeyboardButton("✂️ Бичиқчи буюртма"), KeyboardButton("🪡 Тикув қабул")],
        [KeyboardButton("💰 Маош белгилаш"), KeyboardButton("💳 Маош тўлаш")],
        [KeyboardButton("📈 Ишчи ҳисоботи"), KeyboardButton("🕐 Давомат")],
        [KeyboardButton("🚪 Чиқиш")]
    ], resize_keyboard=True)

def worker_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ Ишга келдим"), KeyboardButton("🏠 Уйдаман")],
        [KeyboardButton("🍽 Обеддаман"), KeyboardButton("🔚 Ишни тугаттим")],
        [KeyboardButton("📋 Менинг вазифаларим"), KeyboardButton("✍️ Иш киритиш")],
        [KeyboardButton("💰 Менинг даромадим"), KeyboardButton("📅 Менинг тарихим")],
        [KeyboardButton("🚪 Чиқиш")]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    chat_id = update.effective_chat.id
    w = get_worker_by_chat(chat_id)
    if w:
        context.user_data.update({"role": w["role"], "wid": w["id"], "name": w["name"]})
        await show_menu(update, context)
        return MAIN_MENU
    kb = ReplyKeyboardMarkup([
        [KeyboardButton("👑 Админ"), KeyboardButton("✂️ Бичиқчи")],
        [KeyboardButton("🪡 Тикувчи"), KeyboardButton("📦 Омборчи")]
    ], resize_keyboard=True)
    await update.message.reply_text(
        "👔 *Business Bot*\n\nРолингизни танланг:",
        parse_mode="Markdown", reply_markup=kb)
    return LOGIN_ROLE

async def login_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rm = {
        "👑 Админ": "admin",
        "✂️ Бичиқчи": "bichiqchi",
        "🪡 Тикувчи": "tikuvchi",
        "📦 Омборчи": "omborchi"
    }
    role = rm.get(update.message.text)
    if not role:
        await update.message.reply_text("Тугмадан танланг!")
        return LOGIN_ROLE
    context.user_data["role"] = role
    if role == "admin":
        await update.message.reply_text("🔐 Админ паролини киритинг:",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
        return LOGIN_PASS
    await update.message.reply_text("👤 Логинингизни киритинг:",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
    return LOGIN_NAME

async def login_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login_input"] = update.message.text.strip()
    await update.message.reply_text("🔐 Паролингизни киритинг:")
    return LOGIN_PASS

async def login_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pwd = update.message.text.strip()
    role = context.user_data.get("role")
    chat_id = update.effective_chat.id
    if role == "admin":
        if pwd != ADMIN_PASS:
            await update.message.reply_text("❌ Парол нотўғри!")
            return LOGIN_PASS
        context.user_data["name"] = "Админ"
        await show_menu(update, context)
        return MAIN_MENU
    li = context.user_data.get("login_input", "")
    ws = db_get("workers", {"login": f"eq.{li}", "role": f"eq.{role}"})
    w = ws[0] if ws else None
    if not w or w.get("pass") != pwd:
        await update.message.reply_text("❌ Логин ёки парол нотўғри!\n/start ни босинг.")
        return LOGIN_ROLE
    db_update("workers", {"chat_id": chat_id}, {"id": f"eq.{w['id']}"})
    context.user_data.update({"wid": w["id"], "name": w["name"]})
    await show_menu(update, context)
    return MAIN_MENU

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = context.user_data.get("role")
    name = context.user_data.get("name", "")
    h = now_tz().hour
    gr = "Хайрли тонг" if h < 12 else "Хайрли кун" if h < 18 else "Хайрли кеч"
    msg = update.message if update.message else update.callback_query.message
    if role == "admin":
        await msg.reply_text(
            f"👑 *{gr}, {name}!*\n\nАдмин панелига хуш келибсиз.",
            parse_mode="Markdown", reply_markup=admin_kb())
    else:
        wid = context.user_data.get("wid")
        att = db_get("attendance", {"worker_id": f"eq.{wid}", "work_date": f"eq.{today()}"})
        status_txt = ""
        if att:
            s = att[-1]["status"]
            sm = {"arrived": "✅ Ишда", "home": "🏠 Уйда", "lunch": "🍽 Обеддa", "finished": "🔚 Тугатган"}
            status_txt = f"\nҲолат: *{sm.get(s, s)}*"
        await msg.reply_text(
            f"👋 *{gr}, {name}!*{status_txt}",
            parse_mode="Markdown", reply_markup=worker_kb())

async def do_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wid = context.user_data.get("wid")
    if wid:
        db_update("workers", {"chat_id": None}, {"id": f"eq.{wid}"})
    context.user_data.clear()
    await update.message.reply_text("👋 Чиқилди!",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
    return await start(update, context)

async def worker_attendance(update, context, status):
    wid = context.user_data.get("wid")
    name = context.user_data.get("name", "")
    now = now_tz()
    att_today = db_get("attendance", {"worker_id": f"eq.{wid}", "work_date": f"eq.{today()}"})
    labels = {
        "arrived": "✅ Ишга келди",
        "home": "🏠 Кетди",
        "lunch": "🍽 Обедда",
        "finished": "🔚 Ишни тугатди"
    }
    if status == "arrived":
        if att_today and att_today[-1]["status"] == "arrived":
            await update.message.reply_text("⚠️ Сиз аллақачон ишдасиз!")
            return
        db_insert("attendance", {
            "worker_id": wid, "worker_name": name,
            "status": status, "check_in": now_str(),
            "work_date": today()
        })
        await update.message.reply_text(
            f"✅ *{name}* ишга келди!\n⏰ Вақт: {now_time()}", parse_mode="Markdown")
    elif status in ("home", "lunch", "finished"):
        if not att_today:
            await update.message.reply_text("⚠️ Аввал ишга келганингизни белгиланг!")
            return
        last = att_today[-1]
        minutes = 0
        if last.get("check_in"):
            try:
                ci = datetime.fromisoformat(last["check_in"])
                if ci.tzinfo is None:
                    ci = ci.replace(tzinfo=TZ)
                minutes = int((now - ci).total_seconds() / 60)
            except: pass
        total = (last.get("total_minutes") or 0) + minutes
        db_update("attendance", {
            "status": status, "check_out": now_str(), "total_minutes": total
        }, {"id": f"eq.{last['id']}"})
        h2 = total // 60; m2 = total % 60
        await update.message.reply_text(
            f"{labels[status]}\n👤 {name}\n⏰ {now_time()}\n⏱ Бугун жами: {h2} соат {m2} дақиқа",
            parse_mode="Markdown")

async def do_home(update, context):
    prods = db_get("products")
    sales = db_get("sales", {"sale_date": f"eq.{today()}"})
    clients = db_get("clients")
    workers = db_get("workers")
    att = db_get("attendance", {"work_date": f"eq.{today()}"})
    working = [a for a in att if a["status"] == "arrived"]
    income = sum(s["total"] for s in sales if s.get("pay_type") != "nasiya")
    profit = sum(s.get("profit", 0) or 0 for s in sales)
    koylak = sum(p["qty"] for p in prods if p["type"] == "koylak")
    mat = sum(p["qty"] for p in prods if p["type"] == "material")
    debt = sum(c["debt"] for c in clients)
    kv = sum(p["qty"] * p["price"] for p in prods if p["type"] == "koylak")
    mv = sum(p["qty"] * p["price"] for p in prods if p["type"] == "material")
    dv = sum(p["qty"] * p["price"] for p in prods if p["type"] == "detal")
    txt = f"🏠 *Бош саҳифа — {today()}*\n\n"
    txt += f"💰 Бугунги даромад: *{fmt(income)}*\n"
    txt += f"📈 Бугунги фойда: *{fmt(profit)}*\n"
    txt += f"👔 Кўйлак: *{koylak} дона*\n"
    txt += f"🧵 Материал: *{mat} метр*\n"
    txt += f"⚠️ Қарзлар: *{fmt(debt)}*\n\n"
    txt += f"📦 Омбор жами: *{fmt(kv+mv+dv)}*\n"
    txt += f"👷 Жами ишчилар: *{len(workers)} та*\n"
    txt += f"✅ Ҳозир ишда: *{len(working)} та*\n"
    if working:
        txt += "\n👷 *Ишда бўлганлар:*\n"
        for a in working:
            ci = a.get("check_in", "")
            t = ci[11:16] if len(ci) > 11 else "-"
            txt += f"  • {a['worker_name']} ({t} дан)\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def do_davomat(update, context):
    att = db_get("attendance", {"work_date": f"eq.{today()}"})
    workers = db_get("workers")
    sm = {"arrived": "✅ Ишда", "home": "🏠 Кетди", "lunch": "🍽 Обедда", "finished": "🔚 Тугатди"}
    txt = f"🕐 *Бугунги давомат — {today()}*\n\n"
    for w in workers:
        w_att = [a for a in att if a["worker_id"] == w["id"]]
        if w_att:
            last = w_att[-1]
            st = sm.get(last["status"], last["status"])
            total = last.get("total_minutes", 0) or 0
            h2 = total // 60; m2 = total % 60
            ci = last.get("check_in", "")
            ci_time = ci[11:16] if len(ci) > 11 else "-"
            txt += f"👤 *{w['name']}* ({w['role']})\n"
            txt += f"  {st} | Келди: {ci_time} | {h2}с {m2}д\n\n"
        else:
            txt += f"👤 *{w['name']}* — ❌ Келмади\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def do_products(update, context):
    prods = db_get("products")
    txt = "👔 *Маҳсулотлар:*\n\n"
    for t, lb in [("koylak", "👔 КЎЙЛАКЛАР"), ("material", "🧵 МАТЕРИАЛЛАР"), ("detal", "🔩 ДЕТАЛЛАР")]:
        items = [p for p in prods if p["type"] == t]
        if items:
            txt += f"*{lb}*\n"
            for p in items:
                w = "⚠️" if p["qty"] < 5 else ""
                txt += f"  {w}*{p['name']}*\n    {p['qty']} дона | {fmt(p['price'])} | Жами: {fmt(p['qty']*p['price'])}\n"
            txt += "\n"
    kb = [[InlineKeyboardButton("➕ Қўшиш", callback_data="add_prod"),
           InlineKeyboardButton("✏️ Таҳрирлаш", callback_data="edit_prod")]]
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def cb_add_prod(update, context):
    await update.callback_query.answer()
    kb = [[InlineKeyboardButton("👔 Кўйлак", callback_data="pt_koylak")],
          [InlineKeyboardButton("🧵 Материал", callback_data="pt_material")],
          [InlineKeyboardButton("🔩 Детал", callback_data="pt_detal")]]
    await update.callback_query.message.reply_text("Турини танланг:", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_PROD_TYPE

async def add_prod_type(update, context):
    await update.callback_query.answer()
    context.user_data["np"] = {"type": update.callback_query.data.replace("pt_", "")}
    await update.callback_query.message.reply_text("Номини киритинг:")
    return ADD_PROD_NAME

async def add_prod_name(update, context):
    context.user_data["np"]["name"] = update.message.text.strip()
    await update.message.reply_text("Миқдорини киритинг:")
    return ADD_PROD_QTY

async def add_prod_qty(update, context):
    try: context.user_data["np"]["qty"] = float(update.message.text.strip())
    except: await update.message.reply_text("❌ Рақам киритинг!"); return ADD_PROD_QTY
    await update.message.reply_text("Сотув нархини киритинг (сўм):")
    return ADD_PROD_PRICE

async def add_prod_price(update, context):
    try: context.user_data["np"]["price"] = float(update.message.text.strip().replace(" ", ""))
    except: await update.message.reply_text("❌ Рақам!"); return ADD_PROD_PRICE
    await update.message.reply_text("Тан нархини киритинг (сўм):")
    return ADD_PROD_COST

async def add_prod_cost(update, context):
    try: cost = float(update.message.text.strip().replace(" ", ""))
    except: cost = 0
    p = context.user_data["np"]
    db_insert("products", {"type": p["type"], "name": p["name"], "qty": p["qty"], "price": p["price"], "cost": cost, "sold": 0})
    await update.message.reply_text(f"✅ *Қўшилди:* {p['name']}", parse_mode="Markdown")
    return MAIN_MENU

async def cb_edit_prod(update, context):
    await update.callback_query.answer()
    prods = db_get("products")
    ic = {"koylak": "👔", "material": "🧵", "detal": "🔩"}
    kb = [[InlineKeyboardButton(f"{ic.get(p['type'],'📦')} {p['name']} ({p['qty']})", callback_data=f"ep_{p['id']}")] for p in prods]
    await update.callback_query.message.reply_text("Қайси маҳсулот?", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_PROD_SELECT

async def edit_prod_select(update, context):
    await update.callback_query.answer()
    pid = int(update.callback_query.data.replace("ep_", ""))
    ps = db_get("products", {"id": f"eq.{pid}"})
    p = ps[0] if ps else {}
    context.user_data["epid"] = pid
    kb = [[InlineKeyboardButton("📝 Ном", callback_data="epf_name"), InlineKeyboardButton("📦 Миқдор", callback_data="epf_qty")],
          [InlineKeyboardButton("💰 Нарх", callback_data="epf_price"), InlineKeyboardButton("🏷 Тан нарх", callback_data="epf_cost")],
          [InlineKeyboardButton("🗑️ Ўчириш", callback_data="epf_delete")]]
    await update.callback_query.message.reply_text(
        f"✏️ *{p.get('name','')}*\n📦{p.get('qty',0)} | 💰{fmt(p.get('price',0))}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_PROD_FIELD

async def edit_prod_field(update, context):
    await update.callback_query.answer()
    f = update.callback_query.data.replace("epf_", "")
    if f == "delete":
        db_delete("products", {"id": f"eq.{context.user_data['epid']}"})
        await update.callback_query.message.reply_text("🗑️ Ўчирилди!")
        return MAIN_MENU
    context.user_data["epf"] = f
    lb = {"name": "янги номини", "qty": "янги миқдорини", "price": "янги нархини", "cost": "янги тан нархини"}
    await update.callback_query.message.reply_text(f"✏️ {lb[f]} киритинг:")
    return EDIT_PROD_VALUE

async def edit_prod_value(update, context):
    v = update.message.text.strip().replace(" ", "")
    f = context.user_data["epf"]
    if f in ("qty", "price", "cost"):
        try: v = float(v)
        except: await update.message.reply_text("❌ Рақам!"); return EDIT_PROD_VALUE
    db_update("products", {f: v}, {"id": f"eq.{context.user_data['epid']}"})
    await update.message.reply_text("✅ Янгиланди!")
    return MAIN_MENU

async def do_savdo(update, context):
    prods = db_get("products", {"type": "eq.koylak"})
    if not prods: await update.message.reply_text("❌ Кўйлак йўқ."); return MAIN_MENU
    context.user_data["sprods"] = prods
    kb = [[InlineKeyboardButton(f"👔 {p['name']} ({p['qty']} дона)", callback_data=f"sp_{p['id']}")] for p in prods]
    await update.message.reply_text("🛒 *Янги сотув* — Маҳсулот:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_SALE_PROD

async def sale_prod_cb(update, context):
    await update.callback_query.answer()
    pid = int(update.callback_query.data.replace("sp_", ""))
    p = next(x for x in context.user_data["sprods"] if x["id"] == pid)
    context.user_data["ns"] = {"pid": pid, "pname": p["name"], "pprice": p["price"], "pcost": p.get("cost", 0), "pqty": p["qty"]}
    await update.callback_query.message.reply_text(
        f"👔 *{p['name']}*\n💰 {fmt(p['price'])} | 📦 {p['qty']} дона\n\nНечта?", parse_mode="Markdown")
    return ADD_SALE_QTY

async def sale_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Рақам!"); return ADD_SALE_QTY
    if qty > context.user_data["ns"]["pqty"]:
        await update.message.reply_text(f"❌ Фақат {context.user_data['ns']['pqty']} дона бор!")
        return ADD_SALE_QTY
    context.user_data["ns"]["qty"] = qty
    await update.message.reply_text(f"💰 Нарх (сўм):\n(Стандарт: {fmt(context.user_data['ns']['pprice'])})")
    return ADD_SALE_PRICE

async def sale_price(update, context):
    try: price = float(update.message.text.strip().replace(" ", ""))
    except: await update.message.reply_text("❌ Рақам!"); return ADD_SALE_PRICE
    ns = context.user_data["ns"]
    ns["price"] = price; ns["total"] = price * ns["qty"]; ns["profit"] = (price - ns["pcost"]) * ns["qty"]
    await update.message.reply_text(
        f"💳 Жами: *{fmt(ns['total'])}*\nФойда: *{fmt(ns['profit'])}*\n\nМижоз исми:", parse_mode="Markdown")
    return ADD_SALE_CLIENT

async def sale_client(update, context):
    context.user_data["ns"]["client"] = update.message.text.strip()
    kb = [[InlineKeyboardButton("💵 Нақд", callback_data="pay_naqd")],
          [InlineKeyboardButton("📋 Насия", callback_data="pay_nasiya")],
          [InlineKeyboardButton("💳 Карта", callback_data="pay_karta")]]
    await update.message.reply_text("Тўлов тури:", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_SALE_PAY

async def sale_pay(update, context):
    await update.callback_query.answer()
    pay = update.callback_query.data.replace("pay_", "")
    ns = context.user_data["ns"]
    db_insert("sales", {"product_name": ns["pname"], "prod_id": ns["pid"], "qty": ns["qty"],
                        "price": ns["price"], "cost": ns["pcost"], "total": ns["total"],
                        "profit": ns["profit"], "client": ns["client"], "pay_type": pay, "sale_date": today()})
    ps = db_get("products", {"id": f"eq.{ns['pid']}"})
    if ps: db_update("products", {"qty": ps[0]["qty"] - ns["qty"], "sold": (ps[0].get("sold") or 0) + ns["qty"]}, {"id": f"eq.{ns['pid']}"})
    if pay == "nasiya":
        ex = db_get("clients", {"name": f"eq.{ns['client']}"})
        if ex: db_update("clients", {"debt": ex[0]["debt"] + ns["total"]}, {"name": f"eq.{ns['client']}"})
        else: db_insert("clients", {"name": ns["client"], "debt": ns["total"]})
    pl = {"naqd": "💵 Нақд", "nasiya": "📋 Насия", "karta": "💳 Карта"}
    await update.callback_query.message.reply_text(
        f"✅ *Сотув сақланди!*\n\n👔 {ns['pname']} × {ns['qty']}\n💰 {fmt(ns['total'])}\n📈 Фойда: {fmt(ns['profit'])}\n👤 {ns['client']}\n{pl[pay]}",
        parse_mode="Markdown")
    return MAIN_MENU

async def do_xarajat(update, context):
    kb = [[InlineKeyboardButton("🧵 Материал", callback_data="et_material")],
          [InlineKeyboardButton("🔩 Детал", callback_data="et_detal")],
          [InlineKeyboardButton("👷 Маош", callback_data="et_maosh")],
          [InlineKeyboardButton("🏠 Ижара", callback_data="et_ijara")],
          [InlineKeyboardButton("📦 Бошқа", callback_data="et_boshqa")]]
    await update.message.reply_text("💸 *Янги харажат* — Тур:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_EXP_TYPE

async def exp_type(update, context):
    await update.callback_query.answer()
    context.user_data["ne"] = {"type": update.callback_query.data.replace("et_", "")}
    await update.callback_query.message.reply_text("Тавсифини киритинг:")
    return ADD_EXP_DESC

async def exp_desc(update, context):
    context.user_data["ne"]["desc"] = update.message.text.strip()
    await update.message.reply_text("Суммани киритинг (сўм):")
    return ADD_EXP_AMOUNT

async def exp_amount(update, context):
    try: amt = float(update.message.text.strip().replace(" ", ""))
    except: await update.message.reply_text("❌ Рақам!"); return ADD_EXP_AMOUNT
    ne = context.user_data["ne"]
    db_insert("expenses", {"type": ne["type"], "description": ne["desc"], "amount": amt, "expense_date": today()})
    await update.message.reply_text(f"✅ *Харажат сақланди!*\n📝 {ne['desc']}\n💰 {fmt(amt)}", parse_mode="Markdown")
    return MAIN_MENU

async def do_hisobot(update, context):
    kb = [[InlineKeyboardButton("📅 Кунлик", callback_data="rep_daily"),
           InlineKeyboardButton("📆 Ҳафталик", callback_data="rep_weekly"),
           InlineKeyboardButton("🗓 Ойлик", callback_data="rep_monthly")]]
    await update.message.reply_text("📊 Ҳисобот даври:", reply_markup=InlineKeyboardMarkup(kb))

async def cb_rep(update, context):
    await update.callback_query.answer()
    p = update.callback_query.data.replace("rep_", "")
    d = now_tz()
    df = today() if p == "daily" else (d - timedelta(days=7)).strftime("%Y-%m-%d") if p == "weekly" else d.strftime("%Y-%m-01")
    lb = {"daily": "Кунлик", "weekly": "Ҳафталик", "monthly": "Ойлик"}[p]
    sales = db_get("sales", {"sale_date": f"gte.{df}"})
    exps = db_get("expenses", {"expense_date": f"gte.{df}"})
    clients = db_get("clients")
    prods = db_get("products")
    income = sum(s["total"] for s in sales if s.get("pay_type") != "nasiya")
    nasiya = sum(s["total"] for s in sales if s.get("pay_type") == "nasiya")
    profit = sum(s.get("profit", 0) or 0 for s in sales)
    expense = sum(e["amount"] for e in exps)
    qty = sum(s["qty"] for s in sales)
    debt = sum(c["debt"] for c in clients)
    sv = sum(p["qty"] * p["price"] for p in prods)
    txt = f"📊 *{lb} ҳисобот*\n\n"
    txt += f"💰 Даромад: *{fmt(income)}*\n"
    txt += f"📈 Фойда: *{fmt(profit)}*\n"
    txt += f"📋 Насия: *{fmt(nasiya)}*\n"
    txt += f"💸 Харажат: *{fmt(expense)}*\n"
    txt += f"👔 Сотилди: *{qty} дона*\n"
    txt += f"📦 Омбор: *{fmt(sv)}*\n"
    txt += f"⚠️ Қарзлар: *{fmt(debt)}*"
    await update.callback_query.message.reply_text(txt, parse_mode="Markdown")

async def do_ombor(update, context):
    prods = db_get("products")
    txt = "📦 *Омбор ҳолати*\n\n"
    tv = 0
    for t, lb in [("koylak", "👔 КЎЙЛАКЛАР"), ("material", "🧵 МАТЕРИАЛЛАР"), ("detal", "🔩 ДЕТАЛЛАР")]:
        items = [p for p in prods if p["type"] == t]
        if items:
            tval = sum(p["qty"] * p["price"] for p in items); tv += tval
            txt += f"*{lb}* — {fmt(tval)}\n"
            for p in items:
                w = "⚠️ " if p["qty"] < 5 else ""
                txt += f"  {w}*{p['name']}*\n    {p['qty']} × {fmt(p['price'])} = *{fmt(p['qty']*p['price'])}*\n"
            txt += "\n"
    txt += f"💎 *Жами: {fmt(tv)}*"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def do_workers(update, context):
    ws = db_get("workers")
    if not ws: await update.message.reply_text("Ишчилар йўқ."); return MAIN_MENU
    ri = {"bichiqchi": "✂️", "tikuvchi": "🪡", "omborchi": "📦"}
    txt = "👷 *Ишчилар:*\n\n"
    for w in ws:
        jobs = db_get("worker_jobs", {"worker_id": f"eq.{w['id']}", "job_date": f"eq.{today()}"})
        total = sum(j["total"] for j in jobs); done = sum(j["done"] for j in jobs)
        pct = round(done / total * 100) if total > 0 else 0
        txt += f"{ri.get(w['role'],'👤')} *{w['name']}* ({w['role']})\n"
        txt += f"  Логин: `{w['login']}` Парол: `{w['pass']}`\n"
        txt += f"  Бугун: {done}/{total} ({pct}%)\n\n"
    kb = [[InlineKeyboardButton("➕ Қўшиш", callback_data="add_worker"),
           InlineKeyboardButton("✏️ Таҳрирлаш", callback_data="edit_worker")]]
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return MAIN_MENU

async def cb_add_worker(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("👤 Исмини киритинг:")
    return ADD_WORKER_NAME

async def aw_name(update, context):
    context.user_data["nw"] = {"name": update.message.text.strip()}
    kb = [[InlineKeyboardButton("✂️ Бичиқчи", callback_data="wr_bichiqchi")],
          [InlineKeyboardButton("🪡 Тикувчи", callback_data="wr_tikuvchi")],
          [InlineKeyboardButton("📦 Омборчи", callback_data="wr_omborchi")]]
    await update.message.reply_text("Лавозим:", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_WORKER_ROLE

async def aw_role(update, context):
    await update.callback_query.answer()
    context.user_data["nw"]["role"] = update.callback_query.data.replace("wr_", "")
    await update.callback_query.message.reply_text("Логин киритинг:")
    return ADD_WORKER_LOGIN

async def aw_login(update, context):
    lg = update.message.text.strip().lower()
    ex = db_get("workers", {"login": f"eq.{lg}"})
    if ex: await update.message.reply_text("❌ Бу логин банд!"); return ADD_WORKER_LOGIN
    context.user_data["nw"]["login"] = lg
    await update.message.reply_text("Парол киритинг:")
    return ADD_WORKER_PASS

async def aw_pass(update, context):
    nw = context.user_data["nw"]; nw["pass"] = update.message.text.strip()
    db_insert("workers", {"name": nw["name"], "role": nw["role"], "login": nw["login"], "pass": nw["pass"]})
    await update.message.reply_text(
        f"✅ *Ишчи қўшилди!*\n\n👤 {nw['name']}\n🔑 Логин: `{nw['login']}`\n🔐 Парол: `{nw['pass']}`\n\n📱 Бу маълумотларни ишчига юборинг.",
        parse_mode="Markdown")
    return MAIN_MENU

async def cb_edit_worker(update, context):
    await update.callback_query.answer()
    ws = db_get("workers")
    kb = [[InlineKeyboardButton(f"{w['name']} ({w['role']})", callback_data=f"ew_{w['id']}")] for w in ws]
    await update.callback_query.message.reply_text("Қайси ишчи?", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_WORKER_SELECT

async def ew_select(update, context):
    await update.callback_query.answer()
    context.user_data["ewid"] = int(update.callback_query.data.replace("ew_", ""))
    kb = [[InlineKeyboardButton("📝 Исм", callback_data="ewf_name"), InlineKeyboardButton("🔑 Логин", callback_data="ewf_login")],
          [InlineKeyboardButton("🔐 Парол", callback_data="ewf_pass"), InlineKeyboardButton("🗑️ Ўчириш", callback_data="ewf_delete")]]
    await update.callback_query.message.reply_text("Нимани ўзгартириш?", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_WORKER_FIELD

async def ew_field(update, context):
    await update.callback_query.answer()
    f = update.callback_query.data.replace("ewf_", "")
    if f == "delete":
        db_delete("workers", {"id": f"eq.{context.user_data['ewid']}"})
        await update.callback_query.message.reply_text("🗑️ Ўчирилди!")
        return MAIN_MENU
    context.user_data["ewf"] = f
    lb = {"name": "янги исмини", "login": "янги логинини", "pass": "янги паролини"}
    await update.callback_query.message.reply_text(f"✏️ {lb[f]} киритинг:")
    return EDIT_WORKER_VALUE

async def ew_value(update, context):
    db_update("workers", {context.user_data["ewf"]: update.message.text.strip()}, {"id": f"eq.{context.user_data['ewid']}"})
    await update.message.reply_text("✅ Янгиланди!")
    return MAIN_MENU

async def do_set_rate(update, context):
    ws = db_get("workers")
    kb = [[InlineKeyboardButton(f"{w['name']} ({w['role']})", callback_data=f"sr_{w['id']}")] for w in ws]
    await update.message.reply_text("💰 *Иш нархи белгилаш*\n\nҚайси ишчи?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SET_RATE_WORKER

async def set_rate_worker(update, context):
    await update.callback_query.answer()
    wid = int(update.callback_query.data.replace("sr_", ""))
    ws = db_get("workers", {"id": f"eq.{wid}"})
    context.user_data["sr_wid"] = wid
    context.user_data["sr_wname"] = ws[0]["name"] if ws else ""
    prods = db_get("products", {"type": "eq.koylak"})
    kb = [[InlineKeyboardButton(p["name"], callback_data=f"srp_{p['id']}_{p['name']}")] for p in prods]
    await update.callback_query.message.reply_text("Қайси маҳсулот учун?", reply_markup=InlineKeyboardMarkup(kb))
    return SET_RATE_PROD

async def set_rate_prod(update, context):
    await update.callback_query.answer()
    data = update.callback_query.data.replace("srp_", "")
    parts = data.split("_", 1)
    context.user_data["sr_pid"] = int(parts[0])
    context.user_data["sr_pname"] = parts[1] if len(parts) > 1 else ""
    ex = db_get("worker_rates", {"worker_id": f"eq.{context.user_data['sr_wid']}", "prod_id": f"eq.{context.user_data['sr_pid']}"})
    cur = f"\nҲозирги нарх: {fmt(ex[0]['rate'])}" if ex else "\nҲозирги нарх: белгиланмаган"
    await update.callback_query.message.reply_text(
        f"💰 *{context.user_data['sr_wname']}* — *{context.user_data['sr_pname']}*{cur}\n\nЯнги нархни киритинг (сўм/дона):",
        parse_mode="Markdown")
    return SET_RATE_PRICE

async def set_rate_price(update, context):
    try: rate = float(update.message.text.strip().replace(" ", ""))
    except: await update.message.reply_text("❌ Рақам!"); return SET_RATE_PRICE
    wid = context.user_data["sr_wid"]; pid = context.user_data["sr_pid"]
    pname = context.user_data["sr_pname"]; wname = context.user_data["sr_wname"]
    ex = db_get("worker_rates", {"worker_id": f"eq.{wid}", "prod_id": f"eq.{pid}"})
    if ex: db_update("worker_rates", {"rate": rate}, {"id": f"eq.{ex[0]['id']}"})
    else: db_insert("worker_rates", {"worker_id": wid, "prod_id": pid, "prod_name": pname, "rate": rate})
    await update.message.reply_text(f"✅ *{wname}* — *{pname}*\nНарх: *{fmt(rate)}* / дона", parse_mode="Markdown")
    return MAIN_MENU

async def do_pay_salary(update, context):
    ws = db_get("workers")
    txt = "💳 *Маош тўлаш*\n\nИшчилар баланси:\n\n"
    for w in ws:
        earnings = db_get("worker_earnings", {"worker_id": f"eq.{w['id']}"})
        payments = db_get("salary_payments", {"worker_id": f"eq.{w['id']}"})
        bal = sum(e["total"] for e in earnings) - sum(p["amount"] for p in payments)
        txt += f"👤 *{w['name']}*: {fmt(bal)}\n"
    kb = [[InlineKeyboardButton(w["name"], callback_data=f"ps_{w['id']}")] for w in ws]
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return PAY_SALARY_WORKER

async def pay_salary_worker(update, context):
    await update.callback_query.answer()
    wid = int(update.callback_query.data.replace("ps_", ""))
    ws = db_get("workers", {"id": f"eq.{wid}"})
    w = ws[0] if ws else {}
    context.user_data["ps_wid"] = wid
    context.user_data["ps_wname"] = w.get("name", "")
    earnings = db_get("worker_earnings", {"worker_id": f"eq.{wid}"})
    payments = db_get("salary_payments", {"worker_id": f"eq.{wid}"})
    total_earned = sum(e["total"] for e in earnings)
    total_paid = sum(p["amount"] for p in payments)
    balance = total_earned - total_paid
    await update.callback_query.message.reply_text(
        f"💳 *{w.get('name','')}*\n\nЖами топди: {fmt(total_earned)}\nТўланди: {fmt(total_paid)}\n*Қолди: {fmt(balance)}*\n\nНеча сўм тўлайсиз?",
        parse_mode="Markdown")
    return PAY_SALARY_AMOUNT

async def pay_salary_amount(update, context):
    try: amt = float(update.message.text.strip().replace(" ", ""))
    except: await update.message.reply_text("❌ Рақам!"); return PAY_SALARY_AMOUNT
    wid = context.user_data["ps_wid"]; wname = context.user_data["ps_wname"]
    db_insert("salary_payments", {"worker_id": wid, "worker_name": wname, "amount": amt, "period_from": today(), "period_to": today()})
    db_insert("expenses", {"type": "maosh", "description": f"{wname} маоши", "amount": amt, "expense_date": today()})
    ws = db_get("workers", {"id": f"eq.{wid}"})
    if ws and ws[0].get("chat_id"):
        try:
            await context.bot.send_message(chat_id=ws[0]["chat_id"],
                text=f"💳 *Маош тўланди!*\n\n💰 Сумма: *{fmt(amt)}*\n📅 Сана: {today()}", parse_mode="Markdown")
        except: pass
    await update.message.reply_text(f"✅ *{wname}* га {fmt(amt)} тўланди!", parse_mode="Markdown")
    return MAIN_MENU

async def do_worker_report(update, context):
    ws = db_get("workers")
    kb = [[InlineKeyboardButton(w["name"], callback_data=f"wr2_{w['id']}")] for w in ws]
    kb.append([InlineKeyboardButton("📊 Барчаси", callback_data="wr2_all")])
    await update.message.reply_text("📈 *Ишчи ҳисоботи*\n\nҚайси ишчи?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def cb_worker_report(update, context):
    await update.callback_query.answer()
    data = update.callback_query.data.replace("wr2_", "")
    if data == "all":
        ws = db_get("workers")
        txt = "📈 *Барча ишчилар ҳисоботи*\n\n"
        for w in ws:
            earnings = db_get("worker_earnings", {"worker_id": f"eq.{w['id']}"})
            payments = db_get("salary_payments", {"worker_id": f"eq.{w['id']}"})
            earned = sum(e["total"] for e in earnings)
            paid = sum(p["amount"] for p in payments)
            qty = sum(e["qty"] for e in earnings)
            txt += f"👤 *{w['name']}* ({w['role']})\n"
            txt += f"  Тикди: {qty} дона | Топди: {fmt(earned)}\n"
            txt += f"  Тўланди: {fmt(paid)} | Қолди: *{fmt(earned-paid)}*\n\n"
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
    total_qty = sum(e["qty"] for e in earnings)
    total_min = sum(a.get("total_minutes", 0) or 0 for a in att)
    txt = f"📈 *{w.get('name','')} ҳисоботи*\n\n"
    txt += f"👔 Жами тикди: *{total_qty} дона*\n"
    txt += f"⏱ Жами ишлади: *{total_min//60} соат*\n"
    txt += f"💰 Жами топди: *{fmt(total_earned)}*\n"
    txt += f"💳 Тўланди: *{fmt(total_paid)}*\n"
    txt += f"📊 Қолди: *{fmt(total_earned-total_paid)}*\n\n"
    if rates:
        txt += "💰 *Иш нархлари:*\n"
        for r in rates: txt += f"  • {r['prod_name']}: {fmt(r['rate'])}/дона\n"
    await update.callback_query.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def do_cut_order(update, context):
    ws = db_get("workers", {"role": "eq.bichiqchi"})
    if not ws: await update.message.reply_text("❌ Бичиқчи йўқ!"); return MAIN_MENU
    kb = [[InlineKeyboardButton(w["name"], callback_data=f"co_{w['id']}")] for w in ws]
    await update.message.reply_text("✂️ *Бичиқчи буюртма*\n\nҚайси бичиқчи?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return CUT_ORDER_WORKER

async def cut_order_worker(update, context):
    await update.callback_query.answer()
    wid = int(update.callback_query.data.replace("co_", ""))
    ws = db_get("workers", {"id": f"eq.{wid}"})
    context.user_data["co_wid"] = wid
    context.user_data["co_wname"] = ws[0]["name"] if ws else ""
    prods = db_get("products", {"type": "eq.koylak"})
    kb = [[InlineKeyboardButton(f"{p['name']} ({p['qty']}дона)", callback_data=f"cop_{p['id']}")] for p in prods]
    await update.callback_query.message.reply_text("Қайси маҳсулот?", reply_markup=InlineKeyboardMarkup(kb))
    return CUT_ORDER_PROD

async def cut_order_prod(update, context):
    await update.callback_query.answer()
    pid = int(update.callback_query.data.replace("cop_", ""))
    ps = db_get("products", {"id": f"eq.{pid}"})
    p = ps[0] if ps else {}
    context.user_data["co_pid"] = pid
    context.user_data["co_pname"] = p.get("name", "")
    await update.callback_query.message.reply_text(f"✂️ *{p.get('name','')}*\n\nНечта бичсин?", parse_mode="Markdown")
    return CUT_ORDER_QTY

async def cut_order_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Рақам!"); return CUT_ORDER_QTY
    wid = context.user_data["co_wid"]; wname = context.user_data["co_wname"]
    pid = context.user_data["co_pid"]; pname = context.user_data["co_pname"]
    db_insert("cutting_orders", {"prod_id": pid, "prod_name": pname, "qty": qty,
                                  "cutter_id": wid, "cutter_name": wname,
                                  "status": "assigned", "order_date": today()})
    await update.message.reply_text(
        f"✅ *Буюртма берилди!*\n\n✂️ {wname}\n👔 {pname}: *{qty} дона*\n📅 {today()}", parse_mode="Markdown")
    ws = db_get("workers", {"id": f"eq.{wid}"})
    if ws and ws[0].get("chat_id"):
        try:
            await context.bot.send_message(chat_id=ws[0]["chat_id"],
                text=f"✂️ *Янги буюртма!*\n\n👔 {pname}: *{qty} дона*\n📅 {today()}", parse_mode="Markdown")
        except: pass
    return MAIN_MENU

async def do_sew_receipt(update, context):
    orders = db_get("cutting_orders", {"order_date": f"eq.{today()}"})
    if not orders: await update.message.reply_text("❌ Бугун буюртма йўқ!"); return MAIN_MENU
    kb = [[InlineKeyboardButton(f"✂️{o['cutter_name']}: {o['prod_name']} ({o['qty']}дона)", callback_data=f"sr2_{o['id']}")] for o in orders]
    await update.message.reply_text("🪡 *Тикув қабул*\n\nҚайси буюртма?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SEW_RECEIPT_ORDER

async def sew_receipt_order(update, context):
    await update.callback_query.answer()
    oid = int(update.callback_query.data.replace("sr2_", ""))
    orders = db_get("cutting_orders", {"id": f"eq.{oid}"})
    o = orders[0] if orders else {}
    context.user_data["sr2_oid"] = oid
    context.user_data["sr2_oname"] = o.get("prod_name", "")
    context.user_data["sr2_oqty"] = o.get("qty", 0)
    ws = db_get("workers", {"role": "eq.tikuvchi"})
    kb = [[InlineKeyboardButton(w["name"], callback_data=f"sr2w_{w['id']}")] for w in ws]
    await update.callback_query.message.reply_text(
        f"👔 *{o.get('prod_name','')}* — {o.get('qty',0)} дона\n\nҚайси тикувчи қабул қилди?",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SEW_RECEIPT_SEWER

async def sew_receipt_sewer(update, context):
    await update.callback_query.answer()
    swid = int(update.callback_query.data.replace("sr2w_", ""))
    ws = db_get("workers", {"id": f"eq.{swid}"})
    context.user_data["sr2_swid"] = swid
    context.user_data["sr2_swname"] = ws[0]["name"] if ws else ""
    await update.callback_query.message.reply_text(
        f"🪡 *{context.user_data['sr2_swname']}* нечта қабул қилди?\n(Жами: {context.user_data['sr2_oqty']} дона)")
    return SEW_RECEIPT_QTY

async def sew_receipt_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Рақам!"); return SEW_RECEIPT_QTY
    oid = context.user_data["sr2_oid"]; swid = context.user_data["sr2_swid"]
    swname = context.user_data["sr2_swname"]; pname = context.user_data["sr2_oname"]
    db_insert("sewing_receipts", {"cutting_order_id": oid, "sewer_id": swid, "sewer_name": swname,
                                   "received_qty": qty, "sewn_qty": 0, "status": "in_progress", "receipt_date": today()})
    orders = db_get("cutting_orders", {"id": f"eq.{oid}"})
    pid = orders[0]["prod_id"] if orders else 0
    ex = db_get("worker_jobs", {"worker_id": f"eq.{swid}", "job_date": f"eq.{today()}"})
    job_ex = [j for j in ex if j.get("prod_name") == pname]
    if job_ex: db_update("worker_jobs", {"total": job_ex[0]["total"] + qty}, {"id": f"eq.{job_ex[0]['id']}"})
    else: db_insert("worker_jobs", {"worker_id": swid, "prod_id": pid, "prod_name": pname, "total": qty, "done": 0, "job_date": today()})
    await update.message.reply_text(
        f"✅ *Қабул сақланди!*\n\n🪡 {swname}\n👔 {pname}: *{qty} дона*", parse_mode="Markdown")
    ws = db_get("workers", {"id": f"eq.{swid}"})
    if ws and ws[0].get("chat_id"):
        try:
            await context.bot.send_message(chat_id=ws[0]["chat_id"],
                text=f"📋 *Янги иш қабул қилдингиз!*\n\n👔 {pname}: *{qty} дона*\n📅 {today()}", parse_mode="Markdown")
        except: pass
    return MAIN_MENU

async def do_assign(update, context):
    ws = db_get("workers")
    if not ws: await update.message.reply_text("Ишчилар йўқ!"); return MAIN_MENU
    kb = [[InlineKeyboardButton(f"{w['name']} ({w['role']})", callback_data=f"aw2_{w['id']}")] for w in ws]
    await update.message.reply_text("📋 *Вазифа бериш* — Ишчи:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ASSIGN_WORKER

async def assign_worker_cb(update, context):
    await update.callback_query.answer()
    wid = int(update.callback_query.data.replace("aw2_", ""))
    context.user_data["awid"] = wid
    ws = db_get("workers", {"id": f"eq.{wid}"})
    w = ws[0] if ws else {}
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    txt = f"📋 *{w.get('name','')}* — бугун:\n"
    for j in jobs: txt += f"  • {j['prod_name']}: {j['done']}/{j['total']}\n"
    if not jobs: txt += "  Ҳали йўқ\n"
    prods = db_get("products", {"type": "eq.koylak"})
    context.user_data["awprods"] = prods
    kb = [[InlineKeyboardButton(f"👔 {p['name']}", callback_data=f"awp_{p['id']}")] for p in prods]
    await update.callback_query.message.reply_text(txt + "\nҚайси маҳсулот?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ASSIGN_PROD

async def assign_prod_cb(update, context):
    await update.callback_query.answer()
    pid = int(update.callback_query.data.replace("awp_", ""))
    p = next(x for x in context.user_data["awprods"] if x["id"] == pid)
    context.user_data["awprod"] = {"id": pid, "name": p["name"]}
    await update.callback_query.message.reply_text(f"👔 *{p['name']}*\n\nНечта?", parse_mode="Markdown")
    return ASSIGN_QTY

async def assign_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Рақам!"); return ASSIGN_QTY
    wid = context.user_data["awid"]; prod = context.user_data["awprod"]
    ex = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "prod_id": f"eq.{prod['id']}", "job_date": f"eq.{today()}"})
    if ex: db_update("worker_jobs", {"total": ex[0]["total"] + qty}, {"id": f"eq.{ex[0]['id']}"})
    else: db_insert("worker_jobs", {"worker_id": wid, "prod_id": prod["id"], "prod_name": prod["name"], "total": qty, "done": 0, "job_date": today()})
    ws = db_get("workers", {"id": f"eq.{wid}"})
    w = ws[0] if ws else {}
    await update.message.reply_text(f"✅ *Вазифа берилди!*\n👤 {w.get('name','')}\n👔 {prod['name']}: {qty} та", parse_mode="Markdown")
    if w.get("chat_id"):
        try:
            await context.bot.send_message(chat_id=w["chat_id"],
                text=f"📋 *Янги вазифа!*\n👔 {prod['name']}: *{qty} та*\n📅 {today()}", parse_mode="Markdown")
        except: pass
    return MAIN_MENU

async def w_vazifalar(update, context):
    wid = context.user_data.get("wid")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    if not jobs: await update.message.reply_text("📋 Бугун вазифа йўқ!"); return MAIN_MENU
    txt = f"📋 *Бугунги вазифаларим — {today()}*\n\n"
    for j in jobs:
        pct = round(j["done"] / j["total"] * 100) if j["total"] > 0 else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        txt += f"*{j['prod_name']}*\n{bar} {pct}%\n✅{j['done']} | 📦{j['total']} | 🔄{max(0, j['total']-j['done'])} қолди\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def w_done_start(update, context):
    wid = context.user_data.get("wid")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    incomplete = [j for j in jobs if j["done"] < j["total"]]
    if not incomplete: await update.message.reply_text("🎉 Барча вазифалар бажарилди!"); return MAIN_MENU
    context.user_data["wjobs"] = jobs
    kb = [[InlineKeyboardButton(f"👔 {j['prod_name']} ({j['total']-j['done']} қолди)", callback_data=f"wdj_{j['id']}")] for j in incomplete]
    await update.message.reply_text("Қайси маҳсулот?", reply_markup=InlineKeyboardMarkup(kb))
    return WORKER_DONE_SELECT

async def w_done_sel(update, context):
    await update.callback_query.answer()
    jid = int(update.callback_query.data.replace("wdj_", ""))
    job = next(j for j in context.user_data["wjobs"] if j["id"] == jid)
    context.user_data["wdj"] = job
    await update.callback_query.message.reply_text(
        f"👔 *{job['prod_name']}*\n✅ {job['done']} | 🔄 {job['total']-job['done']} қолган\n\nНечта бажардингиз?",
        parse_mode="Markdown")
    return WORKER_DONE_QTY

async def w_done_qty(update, context):
    try: qty = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Рақам!"); return WORKER_DONE_QTY
    job = context.user_data["wdj"]
    wid = context.user_data.get("wid"); wname = context.user_data.get("name", "")
    new_done = min(job["total"], job["done"] + qty)
    actual = new_done - job["done"]
    db_update("worker_jobs", {"done": new_done}, {"id": f"eq.{job['id']}"})
    rates = db_get("worker_rates", {"worker_id": f"eq.{wid}", "prod_id": f"eq.{job.get('prod_id', 0)}"})
    if rates:
        rate = rates[0]["rate"]
        earning = actual * rate
        db_insert("worker_earnings", {"worker_id": wid, "worker_name": wname, "prod_name": job["prod_name"], "qty": actual, "rate": rate, "total": earning, "work_date": today()})
        earn_txt = f"\n💰 Даромад: +{fmt(earning)}"
    else:
        earn_txt = "\n⚠️ Иш нархи белгиланмаган"
    txt = f"✅ *{actual} та сақланди!*\n👔 {job['prod_name']}\n📊 {new_done}/{job['total']}{earn_txt}"
    all_jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}", "job_date": f"eq.{today()}"})
    if all(j["done"] >= j["total"] for j in all_jobs):
        txt += "\n\n🎉 *БАРЧА ВАЗИФАЛАР БАЖАРИЛДИ!*"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def w_daromad(update, context):
    wid = context.user_data.get("wid"); wname = context.user_data.get("name", "")
    earnings = db_get("worker_earnings", {"worker_id": f"eq.{wid}"})
    payments = db_get("salary_payments", {"worker_id": f"eq.{wid}"})
    today_earn = [e for e in earnings if e["work_date"] == today()]
    total_earned = sum(e["total"] for e in earnings)
    total_paid = sum(p["amount"] for p in payments)
    today_total = sum(e["total"] for e in today_earn)
    txt = f"💰 *{wname} даромади*\n\n"
    txt += f"📅 Бугун: *{fmt(today_total)}*\n"
    txt += f"💎 Жами топди: *{fmt(total_earned)}*\n"
    txt += f"💳 Тўланди: *{fmt(total_paid)}*\n"
    txt += f"📊 Қолди: *{fmt(total_earned-total_paid)}*\n\n"
    if today_earn:
        txt += "📋 *Бугунги ишлар:*\n"
        for e in today_earn: txt += f"  • {e['prod_name']}: {e['qty']} дона = {fmt(e['total'])}\n"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def w_tarix(update, context):
    wid = context.user_data.get("wid")
    jobs = db_get("worker_jobs", {"worker_id": f"eq.{wid}"})
    if not jobs: await update.message.reply_text("📅 Тарих йўқ."); return MAIN_MENU
    jobs = sorted(jobs, key=lambda x: x["job_date"], reverse=True)[:20]
    txt = "📅 *Сўнги ишларим:*\n\n"
    cur = None
    for j in jobs:
        if j["job_date"] != cur: cur = j["job_date"]; txt += f"📅 *{cur}*\n"
        pct = round(j["done"] / j["total"] * 100) if j["total"] > 0 else 0
        txt += f"  • {j['prod_name']}: {j['done']}/{j['total']} ({pct}%)\n"
    await update.message.reply_text(txt, parse_mode="Markdown")
    return MAIN_MENU

async def main_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    role = context.user_data.get("role")
    if not role or t == "/start": return await start(update, context)
    if t == "🚪 Чиқиш": return await do_logout(update, context)
    if role == "admin":
        if t == "🏠 Бош саҳифа": await do_home(update, context)
        elif t == "👔 Маҳсулотлар": await do_products(update, context)
        elif t == "🛒 Савдо": return await do_savdo(update, context)
        elif t == "💸 Харажат": return await do_xarajat(update, context)
        elif t == "📊 Ҳисобот": await do_hisobot(update, context)
        elif t == "👷 Ишчилар": await do_workers(update, context)
        elif t == "📋 Вазифа бериш": return await do_assign(update, context)
        elif t == "📦 Омбор ҳолати": await do_ombor(update, context)
        elif t == "✂️ Бичиқчи буюртма": return await do_cut_order(update, context)
        elif t == "🪡 Тикув қабул": return await do_sew_receipt(update, context)
        elif t == "💰 Маош белгилаш": return await do_set_rate(update, context)
        elif t == "💳 Маош тўлаш": return await do_pay_salary(update, context)
        elif t == "📈 Ишчи ҳисоботи": await do_worker_report(update, context)
        elif t == "🕐 Давомат": await do_davomat(update, context)
        else: await update.message.reply_text("Тугмалардан фойдаланинг 👆")
    else:
        if t == "✅ Ишга келдим": await worker_attendance(update, context, "arrived")
        elif t == "🏠 Уйдаман": await worker_attendance(update, context, "home")
        elif t == "🍽 Обеддаман": await worker_attendance(update, context, "lunch")
        elif t == "🔚 Ишни тугаттим": await worker_attendance(update, context, "finished")
        elif t == "📋 Менинг вазифаларим": await w_vazifalar(update, context)
        elif t == "✍️ Иш киритиш": return await w_done_start(update, context)
        elif t == "💰 Менинг даромадим": await w_daromad(update, context)
        elif t == "📅 Менинг тарихим": await w_tarix(update, context)
        else: await update.message.reply_text("Тугмалардан фойдаланинг 👆")
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)
    return MAIN_MENU

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOGIN_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_role)],
            LOGIN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_name)],
            LOGIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_pass)],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_msg),
                CallbackQueryHandler(cb_add_prod, "^add_prod$"),
                CallbackQueryHandler(cb_edit_prod, "^edit_prod$"),
                CallbackQueryHandler(cb_rep, "^rep_"),
                CallbackQueryHandler(cb_add_worker, "^add_worker$"),
                CallbackQueryHandler(cb_edit_worker, "^edit_worker$"),
                CallbackQueryHandler(cb_worker_report, "^wr2_"),
            ],
            ADD_PROD_TYPE: [CallbackQueryHandler(add_prod_type, "^pt_")],
            ADD_PROD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_name)],
            ADD_PROD_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_qty)],
            ADD_PROD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_price)],
            ADD_PROD_COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_cost)],
            EDIT_PROD_SELECT: [CallbackQueryHandler(edit_prod_select, "^ep_")],
            EDIT_PROD_FIELD: [CallbackQueryHandler(edit_prod_field, "^epf_")],
            EDIT_PROD_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_prod_value)],
            ADD_SALE_PROD: [CallbackQueryHandler(sale_prod_cb, "^sp_")],
            ADD_SALE_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sale_qty)],
            ADD_SALE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sale_price)],
            ADD_SALE_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sale_client)],
            ADD_SALE_PAY: [CallbackQueryHandler(sale_pay, "^pay_")],
            ADD_EXP_TYPE: [CallbackQueryHandler(exp_type, "^et_")],
            ADD_EXP_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_desc)],
            ADD_EXP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_amount)],
            ADD_WORKER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, aw_name)],
            ADD_WORKER_ROLE: [CallbackQueryHandler(aw_role, "^wr_")],
            ADD_WORKER_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, aw_login)],
            ADD_WORKER_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, aw_pass)],
            EDIT_WORKER_SELECT: [CallbackQueryHandler(ew_select, "^ew_")],
            EDIT_WORKER_FIELD: [CallbackQueryHandler(ew_field, "^ewf_")],
            EDIT_WORKER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ew_value)],
            ASSIGN_WORKER: [CallbackQueryHandler(assign_worker_cb, "^aw2_")],
            ASSIGN_PROD: [CallbackQueryHandler(assign_prod_cb, "^awp_")],
            ASSIGN_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, assign_qty)],
            WORKER_DONE_SELECT: [CallbackQueryHandler(w_done_sel, "^wdj_")],
            WORKER_DONE_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, w_done_qty)],
            SET_RATE_WORKER: [CallbackQueryHandler(set_rate_worker, "^sr_")],
            SET_RATE_PROD: [CallbackQueryHandler(set_rate_prod, "^srp_")],
            SET_RATE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_rate_price)],
            PAY_SALARY_WORKER: [CallbackQueryHandler(pay_salary_worker, "^ps_")],
            PAY_SALARY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_salary_amount)],
            CUT_ORDER_WORKER: [CallbackQueryHandler(cut_order_worker, "^co_")],
            CUT_ORDER_PROD: [CallbackQueryHandler(cut_order_prod, "^cop_")],
            CUT_ORDER_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, cut_order_qty)],
            SEW_RECEIPT_ORDER: [CallbackQueryHandler(sew_receipt_order, "^sr2_")],
            SEW_RECEIPT_SEWER: [CallbackQueryHandler(sew_receipt_sewer, "^sr2w_")],
            SEW_RECEIPT_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sew_receipt_qty)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    logger.info("✅ Business Bot ишга тушди!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

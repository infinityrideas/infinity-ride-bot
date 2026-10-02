
import os
import asyncio
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

TEXTS = {
    "ar": {
        "choose_lang": "اختر لغتك:",
        "welcome": "أهلاً بك في بوت سائقي Infinity Ride AS.",
        "not_registered": "حسابك غير مسجّل بعد. تواصل مع الإدارة.",
        "menu": "القائمة الرئيسية",
        "checkin": "استلام السيارة",
        "checkout": "تسليم السيارة",
        "earnings": "دخلي",
        "report": "تبليغ ضرر / مخالفة",
        "language": "تغيير اللغة",
        "help": "مساعدة",
        "checked_in": "تم تسجيل الاستلام.",
        "checked_out": "تم تسجيل التسليم.",
        "already_open": "عندك وردية مفتوحة. سلّم السيارة أولاً.",
        "no_open": "ما في وردية مفتوحة.",
        "earnings_soon": "عرض الأرباح التفصيلي رح يتفعل بعد رفع تقارير المنصات.",
        "report_ask": "اكتب وصف الضرر أو المخالفة، ويمكنك إرسال صورة بعدها.",
        "report_saved": "تم تسجيل البلاغ. الإدارة راح تراجعه.",
        "help_text": "قبل الوردية: استلام السيارة.\nبعد الوردية: تسليم السيارة.\nبلّغ فوراً عن أي ضرر أو مخالفة.",
        "lang_saved": "تم حفظ اللغة.",
        "choose_car": "اختر السيارة:",
        "no_cars": "ما في سيارات متاحة. تواصل مع الإدارة.",
    },
    "en": {
        "choose_lang": "Choose your language:",
        "welcome": "Welcome to the Infinity Ride AS driver bot.",
        "not_registered": "Your account is not registered yet. Contact management.",
        "menu": "Main menu",
        "checkin": "Car check-in",
        "checkout": "Car check-out",
        "earnings": "My earnings",
        "report": "Report damage / fine",
        "language": "Change language",
        "help": "Help",
        "checked_in": "Check-in saved.",
        "checked_out": "Check-out saved.",
        "already_open": "You already have an open shift. Check out first.",
        "no_open": "No open shift.",
        "earnings_soon": "Detailed earnings will be available after platform reports are uploaded.",
        "report_ask": "Write a short description of the damage or fine. You can send a photo after.",
        "report_saved": "Report saved. Management will review it.",
        "help_text": "Before shift: check in.\nAfter shift: check out.\nReport damage or fines immediately.",
        "lang_saved": "Language saved.",
        "choose_car": "Choose the car:",
        "no_cars": "No cars available. Contact management.",
    },
    "no": {
        "choose_lang": "Velg språk:",
        "welcome": "Velkommen til Infinity Ride AS-sjåførboten.",
        "not_registered": "Kontoen din er ikke registrert ennå. Kontakt ledelsen.",
        "menu": "Hovedmeny",
        "checkin": "Overta bil",
        "checkout": "Levere bil",
        "earnings": "Mine inntekter",
        "report": "Meld skade / bot",
        "language": "Bytt språk",
        "help": "Hjelp",
        "checked_in": "Innsjekk lagret.",
        "checked_out": "Utsjekk lagret.",
        "already_open": "Du har allerede et åpent skift. Sjekk ut først.",
        "no_open": "Ingen åpent skift.",
        "earnings_soon": "Detaljerte inntekter kommer når rapportene er lastet opp.",
        "report_ask": "Skriv en kort beskrivelse av skade eller bot. Du kan sende bilde etterpå.",
        "report_saved": "Rapport lagret. Ledelsen vil se på den.",
        "help_text": "Før skift: sjekk inn.\nEtter skift: sjekk ut.\nMeld skade eller bot med en gang.",
        "lang_saved": "Språk lagret.",
        "choose_car": "Velg bil:",
        "no_cars": "Ingen biler tilgjengelig. Kontakt ledelsen.",
    },
    "ro": {
        "choose_lang": "Alege limba:",
        "welcome": "Bine ai venit la botul șoferilor Infinity Ride AS.",
        "not_registered": "Contul nu este înregistrat. Contactează administrația.",
        "menu": "Meniu principal",
        "checkin": "Preluare mașină",
        "checkout": "Predare mașină",
        "earnings": "Veniturile mele",
        "report": "Raportează daună / amendă",
        "language": "Schimbă limba",
        "help": "Ajutor",
        "checked_in": "Preluarea a fost salvată.",
        "checked_out": "Predarea a fost salvată.",
        "already_open": "Ai deja un schimb deschis. Predă mașina mai întâi.",
        "no_open": "Nu există schimb deschis.",
        "earnings_soon": "Veniturile detaliate vor apărea după încărcarea rapoartelor.",
        "report_ask": "Scrie o descriere scurtă. Poți trimite o poză după.",
        "report_saved": "Raportul a fost salvat.",
        "help_text": "Înainte de tură: preluare.\nDupă tură: predare.\nRaportează imediat orice daună sau amendă.",
        "lang_saved": "Limba a fost salvată.",
        "choose_car": "Alege mașina:",
        "no_cars": "Nu sunt mașini disponibile. Contactează administrația.",
    },
}

CHECKLIST = [
    "interior_clean",
    "exterior_clean",
    "battery",
    "charge_cable",
    "tires",
    "lights",
    "damage",
]


def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)


def get_driver(telegram_id: int):
    res = db.table("drivers").select("*").eq("telegram_id", str(telegram_id)).limit(1).execute()
    return res.data[0] if res.data else None


def car_label(car: dict) -> str:
    for key in ("plate", "plate_number", "registration", "name"):
        if car.get(key):
            return str(car[key])
    return str(car.get("id", "car"))[:8]


def list_cars():
    res = db.table("cars").select("*").execute()
    cars = res.data or []
    active = [c for c in cars if c.get("active") is not False]
    return active or cars


def lang_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("العربية", callback_data="lang:ar"),
                InlineKeyboardButton("English", callback_data="lang:en"),
            ],
            [
                InlineKeyboardButton("Norsk", callback_data="lang:no"),
                InlineKeyboardButton("Română", callback_data="lang:ro"),
            ],
        ]
    )


def menu_keyboard(lang: str):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t(lang, "checkin"), callback_data="menu:checkin")],
            [InlineKeyboardButton(t(lang, "checkout"), callback_data="menu:checkout")],
            [InlineKeyboardButton(t(lang, "earnings"), callback_data="menu:earnings")],
            [InlineKeyboardButton(t(lang, "report"), callback_data="menu:report")],
            [
                InlineKeyboardButton(t(lang, "language"), callback_data="menu:language"),
                InlineKeyboardButton(t(lang, "help"), callback_data="menu:help"),
            ],
        ]
    )


def cars_keyboard(cars):
    rows = []
    for car in cars:
        rows.append(
            [InlineKeyboardButton(car_label(car), callback_data=f"car:{car['id']}")]
        )
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TEXTS["en"]["choose_lang"], reply_markup=lang_keyboard())


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("lang:"):
        language = data.split(":")[1]
        driver = get_driver(user_id)
        if driver:
            db.table("drivers").update({"language": language}).eq("id", driver["id"]).execute()
        else:
            context.user_data["language"] = language
        await query.edit_message_text(t(language, "lang_saved"))
        if not driver:
            await query.message.reply_text(t(language, "not_registered"))
            return
        await query.message.reply_text(t(language, "menu"), reply_markup=menu_keyboard(language))
        return

    driver = get_driver(user_id)
    lang = driver["language"] if driver else context.user_data.get("language", "en")
    if not driver:
        await query.message.reply_text(t(lang, "not_registered"))
        return

    if data == "menu:language":
        await query.message.reply_text(t(lang, "choose_lang"), reply_markup=lang_keyboard())
        return

    if data == "menu:help":
        await query.message.reply_text(t(lang, "help_text"))
        return

    if data == "menu:earnings":
        await query.message.reply_text(t(lang, "earnings_soon"))
        return

    if data == "menu:report":
        context.user_data["awaiting_report"] = True
        await query.message.reply_text(t(lang, "report_ask"))
        return

    if data == "menu:checkin":
        open_shifts = (
            db.table("shifts")
            .select("*")
            .eq("driver_id", driver["id"])
            .eq("status", "open")
            .execute()
        )
        if open_shifts.data:
            await query.message.reply_text(t(lang, "already_open"))
            return
        cars = list_cars()
        if not cars:
            await query.message.reply_text(t(lang, "no_cars"))
            return
        await query.message.reply_text(t(lang, "choose_car"), reply_markup=cars_keyboard(cars))
        return

    if data.startswith("car:"):
        car_id = data.split(":", 1)[1]
        open_shifts = (
            db.table("shifts")
            .select("*")
            .eq("driver_id", driver["id"])
            .eq("status", "open")
            .execute()
        )
        if open_shifts.data:
            await query.message.reply_text(t(lang, "already_open"))
            return
        cars = list_cars()
        car = next((c for c in cars if str(c["id"]) == car_id), None)
        if not car:
            await query.message.reply_text(t(lang, "no_cars"))
            return
        shift = (
            db.table("shifts")
            .insert(
                {
                    "driver_id": driver["id"],
                    "car_id": car["id"],
                    "shift_type": driver.get("shift_type"),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "status": "open",
                }
            )
            .execute()
        )
        shift_id = shift.data[0]["id"]
        db.table("checklists").insert(
            {
                "shift_id": shift_id,
                "type": "checkin",
                "items": {item: True for item in CHECKLIST},
                "notes": "basic check-in",
            }
        ).execute()
        await query.message.reply_text(f"{t(lang, 'checked_in')} {car_label(car)}")
        return

    if data == "menu:checkout":
        open_shifts = (
            db.table("shifts")
            .select("*")
            .eq("driver_id", driver["id"])
            .eq("status", "open")
            .execute()
        )
        if not open_shifts.data:
            await query.message.reply_text(t(lang, "no_open"))
            return
        shift = open_shifts.data[0]
        db.table("shifts").update(
            {
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "status": "closed",
            }
        ).eq("id", shift["id"]).execute()
        db.table("checklists").insert(
            {
                "shift_id": shift["id"],
                "type": "checkout",
                "items": {item: True for item in CHECKLIST},
                "notes": "basic check-out",
            }
        ).execute()
        await query.message.reply_text(t(lang, "checked_out"))
        return


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_report"):
        return
    driver = get_driver(update.effective_user.id)
    if not driver:
        return
    lang = driver.get("language", "en")
    db.table("deductions").insert(
        {
            "driver_id": driver["id"],
            "type": "report",
            "amount": 0,
            "reported_by": "driver",
            "status": "pending",
        }
    ).execute()
    context.user_data["awaiting_report"] = False
    await update.message.reply_text(t(lang, "report_saved"))
    if ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=int(ADMIN_TELEGRAM_ID),
            text=f"New driver report from {driver['name']}: {update.message.text}",
        )


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()


if __name__ == "__main__":
    main()

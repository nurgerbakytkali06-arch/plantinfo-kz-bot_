import asyncio
import json
import os
from pathlib import Path
from contextlib import suppress

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, FSInputFile
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
AUTHOR = os.getenv("BOT_AUTHOR", "ХБ-31").strip()
PORT = int(os.getenv("PORT", "10000"))

BASE = Path(__file__).resolve().parent
DATA_FILE = BASE / "plants_kk.json"
IMAGE_DIR = BASE

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env файлына енгізілуі керек.")

with DATA_FILE.open("r", encoding="utf-8") as f:
    PLANTS = json.load(f)

PLANT_BY_ID = {int(p["id"]): p for p in PLANTS}

CATEGORIES = {
    "trees": range(1, 25),
    "flowers": range(25, 66),
    "field": range(66, 101),
    "lower": range(101, 116),
}

TEXT = {
    "welcome": "🌿 Өсімдіктер энциклопедиясы",
    "menu": "🌿 Өсімдіктер энциклопедиясы\n\nҚажетті бөлімді таңдаңыз:",
    "plants": "🌱 Өсімдіктер",
    "trees": "🌳 Ағаштар мен бұталар",
    "flowers": "🌸 Гүлді және шөптесін өсімдіктер",
    "field": "🌾 Дала және ауылшаруашылық өсімдіктері",
    "lower": "🌿 Мүк, плаун және қырықжапырақтәрізділер",
    "search": "🔎 Іздеу",
    "about": "ℹ️ Бот туралы",
    "back": "🔙 Артқа",
    "menu_back": "🏠 Негізгі мәзір",
    "search_help": "🔎 Өсімдіктің қазақша немесе латынша атауын жазыңыз:\nМысалы: Қарағайлы шырша",
    "not_found": "Өсімдік табылмады.",
    "about_text": "Бұл бот берілген оқу материалдары негізінде 115 өсімдік туралы ақпаратты қарауға арналған.",
    "source": "Дереккөз: ұсынылған оқу материалдары.",
    "no_text": "Бұл түр бойынша бастапқы материалда толық сипаттама мәтіні берілмеген.",
    "choose_plant": "Өсімдікті таңдаңыз:",
}

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXT["plants"], callback_data="plants")],
        [InlineKeyboardButton(text=TEXT["search"], callback_data="search")],
        [InlineKeyboardButton(text=TEXT["about"], callback_data="about")],
    ])

def category_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXT["trees"], callback_data="cat:trees")],
        [InlineKeyboardButton(text=TEXT["flowers"], callback_data="cat:flowers")],
        [InlineKeyboardButton(text=TEXT["field"], callback_data="cat:field")],
        [InlineKeyboardButton(text=TEXT["lower"], callback_data="cat:lower")],
        [InlineKeyboardButton(text=TEXT["back"], callback_data="menu")],
    ])

def category_keyboard(category: str):
    rows = []
    for pid in CATEGORIES[category]:
        p = PLANT_BY_ID[pid]
        rows.append([
            InlineKeyboardButton(
                text=p["name_kk"][:50],
                callback_data=f"plant:{pid}"
            )
        ])
    rows.append([
        InlineKeyboardButton(text=TEXT["back"], callback_data="plants")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def plant_text(plant_id: int):
    plant = PLANT_BY_ID[plant_id]
    return f"🌿 <b>{plant_id}. {plant['name_kk']}</b>"

def chunks(text: str, limit: int = 3900):
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < 500:
            cut = limit
        yield text[:cut]
        text = text[cut:].lstrip()
    if text:
        yield text

def image_for(plant_id: int):
    stem = f"plant_{plant_id:03d}"
    matches = list(IMAGE_DIR.glob(stem + ".*"))
    return matches[0] if matches else None

async def send_plant(bot: Bot, chat_id: int, plant_id: int):
    text = plant_text(plant_id)
    parts = list(chunks(text))
    img = image_for(plant_id)

    if img:
        await bot.send_photo(
            chat_id,
            FSInputFile(img),
            caption=parts[0][:1024],
            parse_mode="HTML"
        )
        for part in parts[1:]:
            await bot.send_message(chat_id, part, parse_mode="HTML")
    else:
        for part in parts:
            await bot.send_message(chat_id, part, parse_mode="HTML")

    await bot.send_message(
        chat_id,
        "Қажетті бөлімді таңдаңыз:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔤 Ғылыми атауы (Латынша атауы)", callback_data=f"latin:{plant_id}")],
            [InlineKeyboardButton(text="🖼 Суретті көру", callback_data=f"image:{plant_id}")],
            [InlineKeyboardButton(text="🌱 Өсімдік сипаттамасы", callback_data=f"desc:{plant_id}")],
            [InlineKeyboardButton(text="🔙 Артқа", callback_data="plants")],
        ]),
    )

dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        f"{TEXT['welcome']}\n\n"
        f"Сәлем! Ботқа қош келдіңіз.\n\n"
        f"{TEXT['menu']}",
        reply_markup=main_menu(),
    )

@dp.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    await call.message.edit_text(
        TEXT["menu"],
        reply_markup=main_menu()
    )
    await call.answer()

@dp.callback_query(F.data == "plants")
async def cb_plants(call: CallbackQuery):
    await call.message.edit_text(
        f"🌱 {TEXT['plants']}\n\n{TEXT['choose_plant']}",
        reply_markup=category_menu()
    )
    await call.answer()

@dp.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery):
    cat = call.data.split(":", 1)[1]

    if cat not in CATEGORIES:
        await call.answer()
        return

    await call.message.edit_text(
        f"{TEXT[cat]}\n\n{TEXT['choose_plant']}",
        reply_markup=category_keyboard(cat)
    )
    await call.answer()

@dp.callback_query(F.data.startswith("plant:"))
async def cb_plant(call: CallbackQuery):
    try:
        pid = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer()
        return

    if pid in PLANT_BY_ID:
        await send_plant(call.bot, call.from_user.id, pid)

    await call.answer()

@dp.callback_query(F.data.startswith("desc:"))
async def cb_description(call: CallbackQuery):
    try:
        pid = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer()
        return

    plant = PLANT_BY_ID.get(pid)
    if not plant:
        await call.answer()
        return

    text = plant.get("description_kk", "").strip() or TEXT["no_text"]
    parts = list(chunks(f"🌱 <b>{plant['name_kk']}</b>\n\n{text}"))
    for part in parts:
        await call.message.answer(part, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data.startswith("latin:"))
async def cb_latin(call: CallbackQuery):
    try:
        pid = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer()
        return

    plant = PLANT_BY_ID.get(pid)
    if not plant:
        await call.answer()
        return

    latin = plant.get("latin_name")
    if latin:
        await call.message.answer(f"🔤 <b>Латынша атауы:</b> <i>{latin}</i>", parse_mode="HTML")
    else:
        await call.message.answer("🔤 Бұл өсімдік бойынша латынша атау бастапқы материалда нақты көрсетілмеген.")
    await call.answer()

@dp.callback_query(F.data.startswith("image:"))
async def cb_image(call: CallbackQuery):
    try:
        pid = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer()
        return

    img = image_for(pid)
    if img:
        await call.message.answer_photo(FSInputFile(img), caption=f"🖼 {PLANT_BY_ID[pid]['name_kk']}")
    else:
        await call.message.answer("Бұл өсімдікке сурет табылмады.")
    await call.answer()

@dp.callback_query(F.data == "search")
async def cb_search(call: CallbackQuery):
    await call.message.edit_text(
        TEXT["search_help"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=TEXT["back"], callback_data="menu")]
        ]),
    )
    await call.answer()

@dp.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery):
    await call.message.edit_text(
        TEXT["about_text"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=TEXT["back"], callback_data="menu")]
        ]),
    )
    await call.answer()

@dp.message(F.text)
async def search_message(message: Message):
    if not message.text or message.text.startswith("/"):
        return

    q = message.text.strip().casefold()

    if len(q) < 2:
        await message.answer(TEXT["not_found"])
        return

    results = []

    for p in PLANTS:
        name = p.get("name_kk", "")
        source = p.get("description_kk", "")

        hay = [
            name.casefold(),
            source.casefold(),
        ]

        if any(q in s for s in hay):
            results.append(p)

    if not results:
        await message.answer(
            TEXT["not_found"],
            reply_markup=main_menu()
        )
        return

    rows = []

    for p in results[:30]:
        rows.append([
            InlineKeyboardButton(
                text=f"{p['id']}. {p['name_kk'][:48]}",
                callback_data=f"plant:{p['id']}"
            )
        ])

    rows.append([
        InlineKeyboardButton(text=TEXT["back"], callback_data="menu")
    ])

    await message.answer(
        "🔎 Нәтижелер:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )

async def health_server():
    from aiohttp import web

    app = web.Application()

    async def health(_request):
        return web.Response(text="OK")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()

async def main():
    bot = Bot(BOT_TOKEN)

    try:
        await asyncio.gather(
            dp.start_polling(bot),
            health_server()
        )
    finally:
        await bot.session.close()

if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())

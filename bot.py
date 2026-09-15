import asyncio
import html
import json
import os
from contextlib import suppress
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
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
    "welcome": "🌿 <b>Өсімдіктер энциклопедиясы</b>",
    "menu": "🌿 <b>Өсімдіктер энциклопедиясы</b>\n\nҚажетті бөлімді таңдаңыз:",
    "plants": "🌱 Өсімдіктер",
    "trees": "🌳 Ағаштар мен бұталар",
    "flowers": "🌸 Гүлді және шөптесін өсімдіктер",
    "field": "🌾 Дала және ауылшаруашылық өсімдіктері",
    "lower": "🌿 Мүк, плаун және қырықжапырақтәрізділер",
    "search": "🔎 Іздеу",
    "about": "ℹ️ Бот туралы",
    "back": "🔙 Артқа",
    "menu": "🏠 Негізгі мәзір",
    "choose_plant": "Өсімдікті таңдаңыз:",
    "search_help": "🔎 Өсімдіктің қазақша немесе латынша атауын жазыңыз:",
    "not_found": "Өсімдік табылмады.",
    "about_text": (
        "🌿 <b>Бот туралы</b>\n\n"
        "Бұл бот берілген оқу материалдары негізінде "
        "115 өсімдік туралы ақпаратты қарауға арналған."
    ),
    "source": "📚 Дереккөз: ұсынылған оқу материалдары.",
    "no_text": "Бұл өсімдік бойынша сипаттама бастапқы материалда көрсетілмеген.",
    "no_latin": "Бұл өсімдік бойынша латынша атау бастапқы материалда нақты көрсетілмеген.",
    "no_image": "Бұл өсімдікке сурет табылмады.",
}

# Telegram чатында әрқашан көрініп тұратын негізгі батырма.
# Пайдаланушы /start жазбай-ақ ботты осы батырмамен қайта бастай алады.
START_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌿 Ботты бастау")],
        [KeyboardButton(text="🛠 Тех. қолдау")]
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# Әр чатта бот жіберген соңғы хабарламалардың ID-лерін сақтаймыз.
# Навигация кезінде сол хабарламалар өшіріліп, чат шашылмайды.
CHAT_MESSAGES: dict[int, list[int]] = {}


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
        [InlineKeyboardButton(text=TEXT["menu"], callback_data="menu")],
    ])


def category_keyboard(category: str, page: int = 0):
    ids = list(CATEGORIES[category])
    per_page = 10
    total_pages = max(1, (len(ids) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))

    current = ids[page * per_page:(page + 1) * per_page]
    rows = []

    # Екі баған: экранға ықшам әрі көзге жеңіл.
    for i in range(0, len(current), 2):
        row = []
        for pid in current[i:i + 2]:
            p = PLANT_BY_ID[pid]
            row.append(
                InlineKeyboardButton(
                    text=f"{pid}. {p['name_kk']}"[:32],
                    callback_data=f"plant:{pid}",
                )
            )
        rows.append(row)

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅️ Алдыңғы", callback_data=f"page:{category}:{page-1}")
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(text="Келесі ➡️", callback_data=f"page:{category}:{page+1}")
        )
    if nav:
        rows.append(nav)

    rows.append([
        InlineKeyboardButton(text="🔙 Артқа", callback_data="plants"),
        InlineKeyboardButton(text=TEXT["menu"], callback_data="menu"),
    ])

    rows.append([
        InlineKeyboardButton(
            text=f"Бет {page + 1}/{total_pages}",
            callback_data="noop"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def plant_keyboard(plant_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔤 Ғылыми атауы",
            callback_data=f"latin:{plant_id}"
        )],
        [InlineKeyboardButton(
            text="🖼 Суретті көру",
            callback_data=f"image:{plant_id}"
        )],
        [InlineKeyboardButton(
            text="🌱 Өсімдік сипаттамасы",
            callback_data=f"desc:{plant_id}"
        )],
        [
            InlineKeyboardButton(text="🔙 Артқа", callback_data="plants"),
            InlineKeyboardButton(text=TEXT["menu"], callback_data="menu"),
        ],
    ])

def detail_keyboard(plant_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔤 Ғылыми атауы",
            callback_data=f"latin:{plant_id}"
        )],
        [InlineKeyboardButton(
            text="🖼 Суретті көру",
            callback_data=f"image:{plant_id}"
        )],
        [InlineKeyboardButton(
            text="🌱 Өсімдік сипаттамасы",
            callback_data=f"desc:{plant_id}"
        )],
        [
            InlineKeyboardButton(text="🔙 Артқа", callback_data=f"plant:{plant_id}"),
            InlineKeyboardButton(text="🌱 Өсімдіктер", callback_data="plants"),
        ],
        [
            InlineKeyboardButton(text=TEXT["menu"], callback_data="menu"),
        ],
    ])

def plant_title(plant_id: int):
    plant = PLANT_BY_ID[plant_id]
    return f"🌿 <b>{plant_id}. {html.escape(plant['name_kk'])}</b>"


def description_text(plant_id: int):
    plant = PLANT_BY_ID[plant_id]
    name = html.escape(plant["name_kk"])
    text = plant.get("description_kk", "").strip() or TEXT["no_text"]
    return f"🌱 <b>{name}</b>\n\n{html.escape(text)}\n\n{TEXT['source']}"


def latin_text(plant_id: int):
    plant = PLANT_BY_ID[plant_id]
    name = html.escape(plant["name_kk"])
    latin = html.escape(str(plant.get("latin_name") or "").strip())

    if latin:
        return f"🔤 <b>{name}</b>\n\n<i>{latin}</i>"
    return f"🔤 <b>{name}</b>\n\n{TEXT['no_latin']}"


def image_for(plant_id: int):
    stem = f"plant_{plant_id:03d}"
    matches = sorted(IMAGE_DIR.glob(stem + ".*"))
    return matches[0] if matches else None


async def clear_chat(bot: Bot, chat_id: int):
    """Боттың осы чатта өзі жіберген алдыңғы хабарламаларын өшіреді."""
    ids = CHAT_MESSAGES.get(chat_id, [])
    if not ids:
        return

    for message_id in ids:
        with suppress(Exception):
            await bot.delete_message(chat_id, message_id)

    CHAT_MESSAGES[chat_id] = []


def remember(chat_id: int, message_id: int):
    CHAT_MESSAGES.setdefault(chat_id, []).append(message_id)


async def send_clean(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup=None,
):
    await clear_chat(bot, chat_id)
    msg = await bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )
    remember(chat_id, msg.message_id)
    return msg


async def send_clean_photo(
    bot: Bot,
    chat_id: int,
    image_path: Path,
    caption: str,
    reply_markup=None,
):
    await clear_chat(bot, chat_id)
    msg = await bot.send_photo(
        chat_id,
        FSInputFile(image_path),
        caption=caption,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )
    remember(chat_id, msg.message_id)
    return msg


dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    # /start басылса, бот өзінің бұрынғы хабарламаларын тазалап,
    # бірден негізгі мәзірден бастайды.
    await clear_chat(message.bot, message.chat.id)

    msg = await message.answer(
        "🌿 <b>Сәлеметсіз бе!</b>\n\n"
        "Өсімдіктер энциклопедиясы ботына қош келдіңіз!\n\n"
        "Төмендегі негізгі мәзірден қажетті бөлімді таңдаңыз:",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
    remember(message.chat.id, msg.message_id)


@dp.message(F.text == "🌿 Ботты бастау")
async def start_button(message: Message):
    await clear_chat(message.bot, message.chat.id)
    msg = await message.answer(
        "🌿 <b>Сәлеметсіз бе!</b>\n\n"
        "Өсімдіктер энциклопедиясы ботына қош келдіңіз!\n\n"
        "Төмендегі негізгі мәзірден қажетті бөлімді таңдаңыз:",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
    remember(message.chat.id, msg.message_id)


@dp.message(F.text == "🛠 Тех. қолдау")
async def technical_support(message: Message):
    await clear_chat(message.bot, message.chat.id)
    msg = await message.answer(
        "🛠 <b>Техникалық қолдау</b>\n\n"
        "Ботқа қатысты сұрақтар немесе ақаулар бойынша хабарласыңыз:\n"
        "📞 <b>+7 776 915 6327</b>",
        parse_mode="HTML",
        reply_markup=START_KEYBOARD,
    )
    remember(message.chat.id, msg.message_id)


@dp.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    await send_clean(call.bot, call.message.chat.id, TEXT["menu"], main_menu())
    await call.answer()


@dp.callback_query(F.data == "plants")
async def cb_plants(call: CallbackQuery):
    text = f"🌱 <b>{TEXT['plants']}</b>\n\n{TEXT['choose_plant']}"
    await send_clean(call.bot, call.message.chat.id, text, category_menu())
    await call.answer()


@dp.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery):
    cat = call.data.split(":", 1)[1]

    if cat not in CATEGORIES:
        await call.answer()
        return

    text = f"{TEXT[cat]}\n\n{TEXT['choose_plant']}"
    await send_clean(
        call.bot,
        call.message.chat.id,
        text,
        category_keyboard(cat, 0),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("page:"))
async def cb_page(call: CallbackQuery):
    try:
        _, category, page_text = call.data.split(":", 2)
        page = int(page_text)
    except (ValueError, IndexError):
        await call.answer()
        return

    if category not in CATEGORIES:
        await call.answer()
        return

    await call.message.edit_reply_markup(
        reply_markup=category_keyboard(category, page)
    )
    await call.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


@dp.callback_query(F.data.startswith("plant:"))
async def cb_plant(call: CallbackQuery):
    try:
        pid = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer()
        return

    if pid not in PLANT_BY_ID:
        await call.answer("Өсімдік табылмады.", show_alert=True)
        return

    await send_clean(
        call.bot,
        call.message.chat.id,
        plant_title(pid),
        plant_keyboard(pid),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("latin:"))
async def cb_latin(call: CallbackQuery):
    try:
        pid = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer()
        return

    if pid not in PLANT_BY_ID:
        await call.answer()
        return

    await send_clean(
        call.bot,
        call.message.chat.id,
        latin_text(pid),
        detail_keyboard(pid),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("desc:"))
async def cb_description(call: CallbackQuery):
    try:
        pid = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer()
        return

    if pid not in PLANT_BY_ID:
        await call.answer()
        return

    text = description_text(pid)

    # Telegram бір хабарламаға 4096 таңбаға дейін қабылдайды.
    # Сипаттама ұзын болса, бірнеше бөлікке бөлінеді.
    # Олардың барлығы CHAT_MESSAGES арқылы кейін тазаланады.
    await clear_chat(call.bot, call.message.chat.id)

    limit = 4000
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < 1000:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    parts.append(text)

    for i, part in enumerate(parts):
        markup = detail_keyboard(pid) if i == len(parts) - 1 else None
        msg = await call.bot.send_message(
            call.message.chat.id,
            part,
            parse_mode="HTML",
            reply_markup=markup,
        )
        remember(call.message.chat.id, msg.message_id)

    await call.answer()


@dp.callback_query(F.data.startswith("image:"))
async def cb_image(call: CallbackQuery):
    try:
        pid = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer()
        return

    if pid not in PLANT_BY_ID:
        await call.answer()
        return

    img = image_for(pid)

    if not img:
        await send_clean(
            call.bot,
            call.message.chat.id,
            TEXT["no_image"],
            detail_keyboard(pid),
        )
        await call.answer()
        return

    name = html.escape(PLANT_BY_ID[pid]["name_kk"])
    await send_clean_photo(
        call.bot,
        call.message.chat.id,
        img,
        f"🖼 <b>{name}</b>",
        detail_keyboard(pid),
    )
    await call.answer()


@dp.callback_query(F.data == "search")
async def cb_search(call: CallbackQuery):
    await send_clean(
        call.bot,
        call.message.chat.id,
        TEXT["search_help"],
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=TEXT["back"], callback_data="menu")],
        ]),
    )
    await call.answer()


@dp.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery):
    await send_clean(
        call.bot,
        call.message.chat.id,
        TEXT["about_text"],
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=TEXT["back"], callback_data="menu")],
        ]),
    )
    await call.answer()


@dp.message(F.text)
async def search_message(message: Message):
    if not message.text or message.text.startswith("/"):
        return

    q = message.text.strip().casefold()

    if len(q) < 2:
        return

    results = []

    for p in PLANTS:
        name = p.get("name_kk", "")
        latin = p.get("latin_name", "")
        source = p.get("description_kk", "")

        if any(
            q in value.casefold()
            for value in (name, latin, source)
            if isinstance(value, str)
        ):
            results.append(p)

    if not results:
        await send_clean(
            message.bot,
            message.chat.id,
            TEXT["not_found"],
            main_menu(),
        )
        return

    rows = []
    for p in results[:30]:
        rows.append([
            InlineKeyboardButton(
                text=f"{p['id']}. {p['name_kk']}"[:60],
                callback_data=f"plant:{p['id']}",
            )
        ])

    rows.append([
        InlineKeyboardButton(text=TEXT["menu"], callback_data="menu")
    ])

    await send_clean(
        message.bot,
        message.chat.id,
        f"🔎 <b>Нәтижелер:</b> {len(results)}",
        InlineKeyboardMarkup(inline_keyboard=rows),
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
            health_server(),
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())

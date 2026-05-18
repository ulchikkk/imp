"""
Импортэкс — бот расчёта доставки (бесплатная версия, без AI)
Пошаговый ввод данных, только python-telegram-bot
"""

import os
import math
import logging
import random
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

# ─── Шаги диалога ────────────────────────────────────────────────────────────
(
    STEP_PLACES,
    STEP_WEIGHT,
    STEP_DIMS_ASK,
    STEP_DIMS,
    STEP_VOLUME,
    STEP_SVKH,
    STEP_DEST,
    STEP_VEHICLE_ASK,
    STEP_VEHICLE,
) = range(9)

# ─── Данные ──────────────────────────────────────────────────────────────────
SVKH_COORDS = {
    "ВОРСИНО":     {"lat": 55.2167, "lon": 37.0167},
    "ЭЛЕКТРОУГЛИ": {"lat": 55.7167, "lon": 38.2167},
    "КОЛОМНА":     {"lat": 55.0833, "lon": 38.7833},
    "ВАРШАВКА":    {"lat": 55.5667, "lon": 37.6167},
}

CITY_COORDS = {
    "ПОДОЛЬСК":       {"lat": 55.4242, "lon": 37.5442},
    "ОДИНЦОВО":       {"lat": 55.6783, "lon": 37.2797},
    "КРАСНОЗНАМЕНСК": {"lat": 55.5953, "lon": 37.0383},
    "НОГИНСК":        {"lat": 55.8553, "lon": 38.4361},
    "РАМЕНСКОЕ":      {"lat": 55.5689, "lon": 38.2297},
    "СЕРГИЕВ ПОСАД":  {"lat": 56.3100, "lon": 38.1300},
    "ЗЕЛЕНОГРАД":     {"lat": 55.9839, "lon": 37.1964},
    "СОЛНЕЧНОГОРСК":  {"lat": 56.1878, "lon": 36.9931},
    "МЫТИЩИ":         {"lat": 55.9119, "lon": 37.7306},
    "ХИМКИ":          {"lat": 55.8897, "lon": 37.4303},
}

# Дополнительные населённые пункты МО для поиска ближайшего города
EXTRA_COORDS = {
    "КРАСНОГОРСК":    {"lat": 55.8219, "lon": 37.3408},
    "ЖУКОВСКИЙ":      {"lat": 55.5978, "lon": 38.1161},
    "БАЛАШИХА":       {"lat": 55.7959, "lon": 37.9384},
    "КОРОЛЁВ":        {"lat": 55.9167, "lon": 37.8333},
    "ДОМОДЕДОВО":     {"lat": 55.4420, "lon": 37.7706},
    "ЩЁЛКОВО":        {"lat": 55.9225, "lon": 38.0183},
    "ЛЮБЕРЦЫ":        {"lat": 55.6781, "lon": 37.8933},
    "ЭЛЕКТРОСТАЛЬ":   {"lat": 55.7833, "lon": 38.4500},
    "ПУШКИНО":        {"lat": 56.0167, "lon": 37.8667},
    "СЕРПУХОВ":       {"lat": 54.9167, "lon": 37.4167},
    "ВИДНОЕ":         {"lat": 55.5500, "lon": 37.7000},
    "ДМИТРОВ":        {"lat": 56.3500, "lon": 37.5167},
    "КЛИН":           {"lat": 56.3333, "lon": 36.7333},
    "ПОДУШКИНО":      {"lat": 55.7200, "lon": 37.2100},
    "БАРВИХА":        {"lat": 55.7500, "lon": 37.2667},
    "ИСТРА":          {"lat": 55.9167, "lon": 36.8500},
    "ЧЕХОВ":          {"lat": 55.1500, "lon": 37.4667},
    "ВОСКРЕСЕНСК":    {"lat": 55.3167, "lon": 38.6833},
    "КОЛОМНА":        {"lat": 55.0833, "lon": 38.7667},
    "ОРЕХОВО-ЗУЕВО":  {"lat": 55.8000, "lon": 38.9833},
    "РУБЛЁВО":        {"lat": 55.7667, "lon": 37.3167},
    "ЗВЕНИГОРОД":     {"lat": 55.7333, "lon": 36.8500},
    "НАРО-ФОМИНСК":   {"lat": 55.3833, "lon": 36.7333},
    "АПРЕЛЕВКА":      {"lat": 55.5333, "lon": 37.0667},
    "ТРОИЦК":         {"lat": 55.4833, "lon": 37.3000},
    "РЕУТОВ":         {"lat": 55.7606, "lon": 37.8578},
    "ЖЕЛЕЗНОДОРОЖНЫЙ": {"lat": 55.7469, "lon": 38.0014},
    "ФРЯЗЕВО":        {"lat": 55.7833, "lon": 38.3500},
    "ЛЫТКАРИНО":      {"lat": 55.5833, "lon": 37.9000},
    "ДЗЕРЖИНСКИЙ":    {"lat": 55.6333, "lon": 37.8500},
}

RATES = {
    "ПОДОЛЬСК":       {"авто": {"ВОРСИНО": 12, "ЭЛЕКТРОУГЛИ": 12, "КОЛОМНА": 14.5, "ВАРШАВКА": 11}, "газель": {"ВОРСИНО": 16.5, "ЭЛЕКТРОУГЛИ": 15.5, "КОЛОМНА": 17, "ВАРШАВКА": 14}, "газон": {"ВОРСИНО": 25, "ЭЛЕКТРОУГЛИ": 23, "КОЛОМНА": 29, "ВАРШАВКА": 19}, "7т": {"ВОРСИНО": 31.5, "ЭЛЕКТРОУГЛИ": 28, "КОЛОМНА": 37, "ВАРШАВКА": 26}, "фура": {"ВОРСИНО": 40, "ЭЛЕКТРОУГЛИ": 38.5, "КОЛОМНА": 46, "ВАРШАВКА": 36}},
    "ОДИНЦОВО":       {"авто": {"ВОРСИНО": 12, "ЭЛЕКТРОУГЛИ": 12, "КОЛОМНА": 16, "ВАРШАВКА": 11}, "газель": {"ВОРСИНО": 16.5, "ЭЛЕКТРОУГЛИ": 15.5, "КОЛОМНА": 21, "ВАРШАВКА": 15}, "газон": {"ВОРСИНО": 23, "ЭЛЕКТРОУГЛИ": 25, "КОЛОМНА": 35, "ВАРШАВКА": 21}, "7т": {"ВОРСИНО": 31.5, "ЭЛЕКТРОУГЛИ": 30, "КОЛОМНА": 40, "ВАРШАВКА": 28.5}, "фура": {"ВОРСИНО": 38, "ЭЛЕКТРОУГЛИ": 39.5, "КОЛОМНА": 51, "ВАРШАВКА": 38.5}},
    "КРАСНОЗНАМЕНСК": {"авто": {"ВОРСИНО": 12, "ЭЛЕКТРОУГЛИ": 17.5, "КОЛОМНА": 16, "ВАРШАВКА": 12}, "газель": {"ВОРСИНО": 16.5, "ЭЛЕКТРОУГЛИ": 18, "КОЛОМНА": 21, "ВАРШАВКА": 15}, "газон": {"ВОРСИНО": 20, "ЭЛЕКТРОУГЛИ": 27, "КОЛОМНА": 35, "ВАРШАВКА": 23.5}, "7т": {"ВОРСИНО": 31.5, "ЭЛЕКТРОУГЛИ": 34, "КОЛОМНА": 40, "ВАРШАВКА": 31}, "фура": {"ВОРСИНО": 40, "ЭЛЕКТРОУГЛИ": 46.5, "КОЛОМНА": 53, "ВАРШАВКА": 41}},
    "НОГИНСК":        {"авто": {"ВОРСИНО": 17.5, "ЭЛЕКТРОУГЛИ": 12, "КОЛОМНА": 14.5, "ВАРШАВКА": 12}, "газель": {"ВОРСИНО": 23, "ЭЛЕКТРОУГЛИ": 13, "КОЛОМНА": 17, "ВАРШАВКА": 15}, "газон": {"ВОРСИНО": 33.5, "ЭЛЕКТРОУГЛИ": 21, "КОЛОМНА": 29, "ВАРШАВКА": 23.5}, "7т": {"ВОРСИНО": 40, "ЭЛЕКТРОУГЛИ": 23, "КОЛОМНА": 37, "ВАРШАВКА": 36}, "фура": {"ВОРСИНО": 53, "ЭЛЕКТРОУГЛИ": 38.5, "КОЛОМНА": 46, "ВАРШАВКА": 46}},
    "РАМЕНСКОЕ":      {"авто": {"ВОРСИНО": 12, "ЭЛЕКТРОУГЛИ": 12, "КОЛОМНА": 14.5, "ВАРШАВКА": 12}, "газель": {"ВОРСИНО": 21, "ЭЛЕКТРОУГЛИ": 13, "КОЛОМНА": 15, "ВАРШАВКА": 15}, "газон": {"ВОРСИНО": 33.5, "ЭЛЕКТРОУГЛИ": 21, "КОЛОМНА": 27, "ВАРШАВКА": 23.5}, "7т": {"ВОРСИНО": 40, "ЭЛЕКТРОУГЛИ": 23, "КОЛОМНА": 31.5, "ВАРШАВКА": 31}, "фура": {"ВОРСИНО": 53, "ЭЛЕКТРОУГЛИ": 38.5, "КОЛОМНА": 45, "ВАРШАВКА": 41}},
    "СЕРГИЕВ ПОСАД":  {"авто": {"ВОРСИНО": 17.5, "ЭЛЕКТРОУГЛИ": 17.5, "КОЛОМНА": 20, "ВАРШАВКА": 15}, "газель": {"ВОРСИНО": 23, "ЭЛЕКТРОУГЛИ": 17, "КОЛОМНА": 23, "ВАРШАВКА": 19}, "газон": {"ВОРСИНО": 35.5, "ЭЛЕКТРОУГЛИ": 30.5, "КОЛОМНА": 40, "ВАРШАВКА": 28}, "7т": {"ВОРСИНО": 42.5, "ЭЛЕКТРОУГЛИ": 31.5, "КОЛОМНА": 46, "ВАРШАВКА": 36.5}, "фура": {"ВОРСИНО": 53, "ЭЛЕКТРОУГЛИ": 49, "КОЛОМНА": 56.5, "ВАРШАВКА": 46.5}},
    "ЗЕЛЕНОГРАД":     {"авто": {"ВОРСИНО": 16, "ЭЛЕКТРОУГЛИ": 10, "КОЛОМНА": 18, "ВАРШАВКА": 14}, "газель": {"ВОРСИНО": 21, "ЭЛЕКТРОУГЛИ": 21, "КОЛОМНА": 21, "ВАРШАВКА": 17}, "газон": {"ВОРСИНО": 30.5, "ЭЛЕКТРОУГЛИ": 26.5, "КОЛОМНА": 37, "ВАРШАВКА": 26}, "7т": {"ВОРСИНО": 42.5, "ЭЛЕКТРОУГЛИ": 30.5, "КОЛОМНА": 34, "ВАРШАВКА": 32.5}, "фура": {"ВОРСИНО": 47.5, "ЭЛЕКТРОУГЛИ": 49, "КОЛОМНА": 51, "ВАРШАВКА": 42.5}},
    "СОЛНЕЧНОГОРСК":  {"авто": {"ВОРСИНО": 17.5, "ЭЛЕКТРОУГЛИ": 15, "КОЛОМНА": 20, "ВАРШАВКА": 15}, "газель": {"ВОРСИНО": 21, "ЭЛЕКТРОУГЛИ": 21, "КОЛОМНА": 23, "ВАРШАВКА": 19}, "газон": {"ВОРСИНО": 30.5, "ЭЛЕКТРОУГЛИ": 30.5, "КОЛОМНА": 37, "ВАРШАВКА": 28}, "7т": {"ВОРСИНО": 42.5, "ЭЛЕКТРОУГЛИ": 35, "КОЛОМНА": 42, "ВАРШАВКА": 31}, "фура": {"ВОРСИНО": 47.5, "ЭЛЕКТРОУГЛИ": 51, "КОЛОМНА": 53, "ВАРШАВКА": 41}},
    "МЫТИЩИ":         {"авто": {"ВОРСИНО": 15, "ЭЛЕКТРОУГЛИ": 12, "КОЛОМНА": 15, "ВАРШАВКА": 12}, "газель": {"ВОРСИНО": 21, "ЭЛЕКТРОУГЛИ": 15, "КОЛОМНА": 19, "ВАРШАВКА": 15}, "газон": {"ВОРСИНО": 28.5, "ЭЛЕКТРОУГЛИ": 21, "КОЛОМНА": 29, "ВАРШАВКА": 23.5}, "7т": {"ВОРСИНО": 37, "ЭЛЕКТРОУГЛИ": 31.5, "КОЛОМНА": 37, "ВАРШАВКА": 28.5}, "фура": {"ВОРСИНО": 47.5, "ЭЛЕКТРОУГЛИ": 38.5, "КОЛОМНА": 49, "ВАРШАВКА": 38.5}},
    "ХИМКИ":          {"авто": {"ВОРСИНО": 15, "ЭЛЕКТРОУГЛИ": 15, "КОЛОМНА": 16, "ВАРШАВКА": 12}, "газель": {"ВОРСИНО": 19, "ЭЛЕКТРОУГЛИ": 15, "КОЛОМНА": 19, "ВАРШАВКА": 15}, "газон": {"ВОРСИНО": 28.5, "ЭЛЕКТРОУГЛИ": 25, "КОЛОМНА": 31, "ВАРШАВКА": 23.5}, "7т": {"ВОРСИНО": 37, "ЭЛЕКТРОУГЛИ": 31.5, "КОЛОМНА": 37, "ВАРШАВКА": 28.5}, "фура": {"ВОРСИНО": 47.5, "ЭЛЕКТРОУГЛИ": 42.5, "КОЛОМНА": 49, "ВАРШАВКА": 38.5}},
}

VEHICLE_SPECS = {
    "авто":   {"label": "Авто (до 1т / 5м³)",      "maxW": 1,   "maxV": 5,  "floorL": 2.5,  "floorW": 1.5,  "maxH": 1.5},
    "газель": {"label": "Газель (до 1,7т / 18м³)", "maxW": 1.7, "maxV": 18, "floorL": 4.2,  "floorW": 1.9,  "maxH": 1.8},
    "газон":  {"label": "Газон (до 5т / 35м³)",    "maxW": 5,   "maxV": 35, "floorL": 6.1,  "floorW": 2.4,  "maxH": 2.0},
    "7т":     {"label": "7 тонн (до 7т / 50м³)",   "maxW": 7,   "maxV": 50, "floorL": 7.5,  "floorW": 2.45, "maxH": 2.2},
    "фура":   {"label": "Фура (до 20т / 92м³)",    "maxW": 20,  "maxV": 92, "floorL": 13.6, "floorW": 2.45, "maxH": 2.7},
}

SVKH_KEYS   = ["ВОРСИНО", "ЭЛЕКТРОУГЛИ", "КОЛОМНА", "ВАРШАВКА"]
VEHICLE_KEYS = ["авто", "газель", "газон", "7т", "фура"]

THINKING_PHRASES = [
    "🧠 Анализирую ставки, расстояние и уровень хаоса...",
    "📞 Делаю вид, что обзваниваю перевозчиков...",
    "🔍 Ищу адекватного подрядчика...",
    "☕ Проверяю уровень кофеина логиста...",
    "📊 Считаю вероятность фразы \'слишком дорого\'...",
    "🚛 Прогреваю газель...",
    "📦 Проверяю, влезет ли груз в реальность...",
    "💸 Анализирую бюджет клиента...",
    "😵 Сверяю ставки с уровнем боли...",
    "📍 Ищу машину в квантовой суперпозиции...",
    "📞 Спрашиваю водителя 'где машина?'...",
    "🗂️ Перекладываю документы из одной папки в другую...",
    "🚦 Согласовываю маршрут с богами логистики...",
    "🤖 Симулирую интеллект...",
    "📈 Натягиваю экономику на ставку..."
]


# ─── Математика ───────────────────────────────────────────────────────────────

def haversine(a, b):
    R = 6371
    dlat = math.radians(b["lat"] - a["lat"])
    dlon = math.radians(b["lon"] - a["lon"])
    s = math.sin(dlat/2)**2 + math.cos(math.radians(a["lat"])) * math.cos(math.radians(b["lat"])) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(s), math.sqrt(1-s))


def find_dest_coords(name: str):
    """Ищет координаты введённого города — сначала в таблице, потом в расширенном списке."""
    n = name.strip().upper()
    if n in CITY_COORDS:
        return CITY_COORDS[n], n, 0.0
    if n in EXTRA_COORDS:
        coords = EXTRA_COORDS[n]
        base, dist = nearest_city(coords)
        return coords, base, max(0.0, dist - 3)
    return None, None, 0.0


def nearest_city(coords):
    best, best_dist = None, float("inf")
    for city, cc in CITY_COORDS.items():
        d = haversine(coords, cc)
        if d < best_dist:
            best_dist = d
            best = city
    return best, best_dist


def price_per_km(svkh, vehicle):
    entries = []
    for city, cc in CITY_COORDS.items():
        r = RATES.get(city, {}).get(vehicle, {}).get(svkh)
        if r:
            entries.append({"rate": float(r), "dist": haversine(SVKH_COORDS[svkh], cc)})
    deltas = []
    for i in range(len(entries)):
        for j in range(i+1, len(entries)):
            dr = abs(entries[i]["rate"] - entries[j]["rate"])
            dk = abs(entries[i]["dist"] - entries[j]["dist"])
            if dk > 5:
                deltas.append(dr / dk)
    if not deltas:
        return 0.15
    deltas.sort()
    return deltas[len(deltas)//2]


def pick_vehicle(weight_kg, volume_m3, dims):
    w = weight_kg / 1000 if weight_kg else None
    max_h = max((d["h"] for d in dims), default=None)
    floor_area = sum(d["l"] * d["w"] for d in dims) if dims else None
    for key, spec in VEHICLE_SPECS.items():
        floor_cap = spec["floorL"] * spec["floorW"]
        if (not w or w <= spec["maxW"]) and \
           (not volume_m3 or volume_m3 <= spec["maxV"]) and \
           (not max_h or max_h <= spec["maxH"]) and \
           (not floor_area or floor_area <= floor_cap):
            return key
    return "фура"


def fmt(val):
    if val is None:
        return "—"
    return f"{int(val)} тр" if val % 1 == 0 else f"{val:.1f} тр"


def bar(pct, width=10):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def kb(buttons, one_time=True):
    """Вспомогательная функция для клавиатуры."""
    return ReplyKeyboardMarkup(
        [[b] for b in buttons],
        resize_keyboard=True,
        one_time_keyboard=one_time,
    )


def kb2(buttons, one_time=True):
    """Клавиатура в 2 колонки."""
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=one_time)



def get_complexity(data):
    score = 0
    if data.get("places", 1) > 8:
        score += 1
    if data.get("weight_kg") and data["weight_kg"] > 3000:
        score += 1
    if data.get("volume_m3") and data["volume_m3"] > 20:
        score += 1
    if data.get("extra_km", 0) > 20:
        score += 1
    if data.get("vehicle") in ["7т", "фура"]:
        score += 2
    dims = data.get("dims", [])
    if dims:
        max_h = max(d["h"] for d in dims)
        if max_h > 2:
            score += 2
    if score <= 1:
        return "✅"
    elif score <= 3:
        return "🟡"
    return "💀"


async def cmd_boss(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["boss_mode"] = True
    await update.message.reply_text(
        '👔 Режим согласования ставки активирован.\n'
        'Ответ: "слишком дорого" будет отправлен после ввода всех данных.\n\n'
        'Чтобы отключить режим босса — /normal'
    )


async def cmd_normal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["boss_mode"] = False
    await update.message.reply_text("🙂 Режим босса отключён.")


# ─── Финальный расчёт и вывод ─────────────────────────────────────────────────

def build_result(d: dict) -> str:
    svkh     = d["svkh"]
    dest     = d["dest_input"]
    base_city= d["base_city"]
    extra_km = d.get("extra_km", 0.0)
    vehicle  = d["vehicle"]
    weight   = d.get("weight_kg")
    volume   = d.get("volume_m3")
    dims     = d.get("dims", [])
    places   = d.get("places", 1)

    spec = VEHICLE_SPECS[vehicle]

    # Загрузка пола
    floor_area = sum(x["l"] * x["w"] for x in dims) if dims else None
    floor_cap  = spec["floorL"] * spec["floorW"]
    max_h      = max((x["h"] for x in dims), default=None)

    # Ставка
    base_rate = RATES.get(base_city, {}).get(vehicle, {}).get(svkh)
    if base_rate is None:
        return "⚠️ Ставка не найдена для этого маршрута."
    base_rate = float(base_rate)
    pkm       = price_per_km(svkh, vehicle) if extra_km > 0.5 else 0
    surcharge = extra_km * pkm
    total     = base_rate + surcharge

    lines = ["📦 *РАСЧЁТ ДОСТАВКИ ИМПОРТЭКС*", ""]

    # Параметры
    lines.append("*Груз:*")
    lines.append(f"  Мест: {places}")
    if weight:
        lines.append(f"  Вес: {weight} кг")
    if volume:
        lines.append(f"  Объём: {volume} м³")
    if dims:
        for i, dm in enumerate(dims):
            lines.append(f"  #{i+1}: {int(dm['l']*100)}×{int(dm['w']*100)}×{int(dm['h']*100)} см")

    lines.append("")
    lines.append(f"*Маршрут:* {svkh} → {dest}")
    if base_city != dest.upper():
        extra_str = f" (+{extra_km:.1f} км нул. пробег)" if extra_km > 0.5 else ""
        lines.append(f"*Опорный город:* {base_city}{extra_str}")
    lines.append(f"*Тип ТС:* {spec['label']}")
    complexity = get_complexity(d)
    lines.append(f"*Сложность груза:* {complexity}")

    # Загрузка пола
    if floor_area is not None:
        pct = min(100, floor_area / floor_cap * 100)
        lines.append("")
        lines.append(f"*Загрузка пола:* {floor_area:.2f} м² / {floor_cap:.1f} м²")
        lines.append(f"`{bar(pct)}` {pct:.0f}%")
        if max_h:
            ok = max_h <= spec["maxH"]
            lines.append(
                f"{'✅' if ok else '⚠️'} Высота: {int(max_h*100)} см "
                f"({'влезает' if ok else 'НЕ ВЛЕЗАЕТ — выбери ТС побольше'})"
            )

    lines.append("")
    lines.append("─" * 26)
    lines.append("")

    if surcharge > 0.05:
        lines.append(f"  База ({base_city}): *{fmt(base_rate)}*")
        lines.append(f"  Нул. пробег +{extra_km:.1f} км × {pkm:.2f} тр/км: *+{fmt(surcharge)}*")
        lines.append("")

    lines.append(f"💰 *ИТОГО: {fmt(total)}*")
    if total > 30:
        lines.append("💀 Это уже не доставка, это инвестиция.")
    lines.append(f"_{svkh} → {dest} · {spec['label']}_")

    return "\n".join(lines)


# ─── Шаги ConversationHandler ────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    ctx.user_data["calc_count"] = ctx.user_data.get("calc_count", 0)
    await update.message.reply_text(
        "👋 *Привет мои дорогие коллеги!*\n\n"
        "Этого ботика сделала Я (@ul4ikkk), и сейчас мы посчитаем реально актуальные "
        "ставочки на автовывоз по Москве и МО 🚛\n\n"
        "Отвечай на вопросы по очереди.\n"
        "Для отмены в любой момент — /cancel\n\n"
        "*Шаг 1/7* — Сколько мест?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return STEP_PLACES


async def step_places(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        n = int(text)
        if n < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи целое число, например: `3`", parse_mode="Markdown")
        return STEP_PLACES

    ctx.user_data["places"] = n
    await update.message.reply_text(
        "*Шаг 2/7* — Суммарный вес груза (кг)?\n"
        "Например: `2800`\n\n"
        "_Если не знаешь — отправь_ `0`",
        parse_mode="Markdown",
    )
    return STEP_WEIGHT


async def step_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        w = float(text.replace(",", "."))
        if w < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи число, например: `2800`", parse_mode="Markdown")
        return STEP_WEIGHT

    ctx.user_data["weight_kg"] = w if w > 0 else None
    await update.message.reply_text(
        "*Шаг 3/7* — Есть габариты мест (длина×ширина×высота)?",
        parse_mode="Markdown",
        reply_markup=kb(["Да, введу", "Нет, пропустить"]),
    )
    return STEP_DIMS_ASK


async def step_dims_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if "нет" in text.lower() or "пропустить" in text.lower():
        ctx.user_data["dims"] = []
        await update.message.reply_text(
            "*Шаг 4/7* — Суммарный объём груза (м³)?\n"
            "Например: `4.5`\n\n"
            "_Если не знаешь — отправь_ `0`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return STEP_VOLUME
    else:
        places = ctx.user_data.get("places", 1)
        ctx.user_data["dims"] = []
        ctx.user_data["dims_left"] = places
        ctx.user_data["dims_current"] = 1
        await update.message.reply_text(
            f"*Место #1 из {places}*\n"
            "Введи габариты в формате: `длина ширина высота` (в см)\n"
            "Например: `100 150 210`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return STEP_DIMS


async def step_dims(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace("×", " ").replace("*", " ").replace(",", ".")
    parts = text.split()
    try:
        if len(parts) != 3:
            raise ValueError
        l, w, h = [float(p) for p in parts]
        if l <= 0 or w <= 0 or h <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Введи три числа через пробел: `длина ширина высота`\n"
            "Например: `100 150 210`",
            parse_mode="Markdown",
        )
        return STEP_DIMS

    # Высота — наибольший из трёх размеров
    sizes = sorted([l, w, h])
    dims_m = {"l": sizes[1]/100, "w": sizes[0]/100, "h": sizes[2]/100}
    ctx.user_data["dims"].append(dims_m)

    left = ctx.user_data["dims_left"] - 1
    current = ctx.user_data["dims_current"] + 1
    ctx.user_data["dims_left"] = left
    ctx.user_data["dims_current"] = current

    if left > 0:
        places = ctx.user_data.get("places", 1)
        await update.message.reply_text(
            f"✅ Место #{current-1} записано.\n\n"
            f"*Место #{current} из {places}*\n"
            "Введи габариты: `длина ширина высота` (см)",
            parse_mode="Markdown",
        )
        return STEP_DIMS

    # Все места введены — считаем объём из габаритов
    total_vol = sum(d["l"] * d["w"] * d["h"] for d in ctx.user_data["dims"])
    ctx.user_data["volume_m3"] = round(total_vol, 3)

    await update.message.reply_text(
        f"✅ Все места записаны.\n"
        f"Объём по габаритам: *{ctx.user_data['volume_m3']} м³*",
        parse_mode="Markdown",
    )
    # Пропускаем шаг ввода объёма вручную
    await ask_svkh(update, ctx)
    return STEP_SVKH


async def step_volume(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")
    try:
        v = float(text)
        if v < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи число, например: `4.5`", parse_mode="Markdown")
        return STEP_VOLUME

    ctx.user_data["volume_m3"] = v if v > 0 else None
    await ask_svkh(update, ctx)
    return STEP_SVKH


async def ask_svkh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Шаг 5/7* — СВХ отправки?",
        parse_mode="Markdown",
        reply_markup=kb2(SVKH_KEYS),
    )


async def step_svkh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if text not in SVKH_KEYS:
        await update.message.reply_text(
            "❌ Выбери один из вариантов на кнопках.",
            reply_markup=kb2(SVKH_KEYS),
        )
        return STEP_SVKH

    ctx.user_data["svkh"] = text
    await update.message.reply_text(
        "*Шаг 6/7* — Город/посёлок доставки?\n"
        "Введи название (любой нас. пункт МО)\n"
        "Например: `Химки`, `Красногорск`, `Подушкино`",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return STEP_DEST


async def step_dest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    coords, base_city, extra_km = find_dest_coords(text)

    if coords is None:
        # Пробуем найти как ближайший к тому что написали
        # Ищем по частичному совпадению
        text_up = text.upper()
        found = None
        for name in list(CITY_COORDS.keys()) + list(EXTRA_COORDS.keys()):
            if text_up in name or name in text_up:
                found = name
                break
        if found:
            if found in CITY_COORDS:
                coords = CITY_COORDS[found]
                base_city = found
                extra_km = 0.0
            else:
                coords = EXTRA_COORDS[found]
                base_city, dist = nearest_city(coords)
                extra_km = max(0.0, dist - 3)
        else:
            await update.message.reply_text(
                f"❌ Не нашёл *{text}* в базе МО.\n\n"
                "Попробуй написать иначе или укажи ближайший крупный город:\n"
                "Химки, Одинцово, Мытищи, Раменское, Ногинск, Подольск, "
                "Красногорск, Жуковский, Балашиха, Королёв, Люберцы...",
                parse_mode="Markdown",
            )
            return STEP_DEST

    ctx.user_data["dest_input"] = text
    ctx.user_data["dest_coords"] = coords
    ctx.user_data["base_city"] = base_city
    ctx.user_data["extra_km"] = extra_km

    # Авто-подбор ТС
    auto_vehicle = pick_vehicle(
        ctx.user_data.get("weight_kg"),
        ctx.user_data.get("volume_m3"),
        ctx.user_data.get("dims", []),
    )
    ctx.user_data["auto_vehicle"] = auto_vehicle
    auto_label = VEHICLE_SPECS[auto_vehicle]["label"]

    await update.message.reply_text(
        f"*Шаг 7/7* — Тип транспортного средства\n\n"
        f"По параметрам груза подходит: *{auto_label}*\n"
        f"Оставить или выбрать другой?",
        parse_mode="Markdown",
        reply_markup=kb(["✅ Оставить подобранный"] + VEHICLE_KEYS),
    )
    return STEP_VEHICLE


async def step_vehicle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "оставить" in text.lower() or "✅" in text:
        vehicle = ctx.user_data["auto_vehicle"]
    elif text.lower() in VEHICLE_KEYS:
        vehicle = text.lower()
    else:
        await update.message.reply_text(
            "❌ Выбери вариант из списка.",
            reply_markup=kb(["✅ Оставить подобранный"] + VEHICLE_KEYS),
        )
        return STEP_VEHICLE

    ctx.user_data["vehicle"] = vehicle

    msg = await update.message.reply_text(random.choice(THINKING_PHRASES))
    for _ in range(5):
        await asyncio.sleep(1)
        try:
            await msg.edit_text(random.choice(THINKING_PHRASES))
        except:
            pass

    ctx.user_data["calc_count"] += 1
    achievements = []
    if ctx.user_data["calc_count"] == 5:
        achievements.append("🔥 5 расчётов подряд")
    ctx.user_data["achievements"] = achievements

    result = build_result(ctx.user_data)
    if ctx.user_data.get("achievements"):
        result += "\n\n" + "\n".join(ctx.user_data["achievements"])
    if ctx.user_data.get("boss_mode"):
        result += '\n\n👔 *Слишком дорого.*'


    await update.message.reply_text(
        result,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [["🔄 Новый расчёт"]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return ConversationHandler.END


async def new_calc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Кнопка 'Новый расчёт' — перезапускает диалог."""
    return await cmd_start(update, ctx)


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    ctx.user_data["calc_count"] = ctx.user_data.get("calc_count", 0)
    await update.message.reply_text(
        "❌ Расчёт отменён. Нажми /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ─── Запуск ──────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("boss", cmd_boss))
    app.add_handler(CommandHandler("normal", cmd_normal))

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.Regex("^🔄 Новый расчёт$"), new_calc),
        ],
        states={
            STEP_PLACES:     [MessageHandler(filters.TEXT & ~filters.COMMAND, step_places)],
            STEP_WEIGHT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, step_weight)],
            STEP_DIMS_ASK:   [MessageHandler(filters.TEXT & ~filters.COMMAND, step_dims_ask)],
            STEP_DIMS:       [MessageHandler(filters.TEXT & ~filters.COMMAND, step_dims)],
            STEP_VOLUME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, step_volume)],
            STEP_SVKH:       [MessageHandler(filters.TEXT & ~filters.COMMAND, step_svkh)],
            STEP_DEST:       [MessageHandler(filters.TEXT & ~filters.COMMAND, step_dest)],
            STEP_VEHICLE_ASK:[MessageHandler(filters.TEXT & ~filters.COMMAND, step_vehicle)],
            STEP_VEHICLE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, step_vehicle)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    logger.info("Бот запущен (бесплатная версия)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

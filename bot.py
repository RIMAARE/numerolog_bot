# -*- coding: utf-8 -*-
"""
Нумерологический Telegram-бот «Путь через Числа» на базе ChatGPT.
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from openai import OpenAI

# ======================= НАСТРОЙКИ =======================

# ======================= НАСТРОЙКИ =======================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL       = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")  # по умолчанию

STATE_MATRIX = "matrix_birth_date"
STATE_COMPAT = "compat_dates"
STATE_YEAR   = "year_number"

user_states: Dict[int, str] = {}

# Простая проверка, чтобы бот не запускался молча без ключей
if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError(
        "Не заданы TELEGRAM_BOT_TOKEN или OPENAI_API_KEY в переменных окружения. "
        "На сервере их нужно добавить в настройках (Environment)."
    )

# Инициализация OpenAI-клиента
client = OpenAI(api_key=OPENAI_API_KEY)

STATE_MATRIX = "matrix_birth_date"
STATE_COMPAT = "compat_dates"
STATE_YEAR   = "year_number"

user_states: Dict[int, str] = {}

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ======================= СИСТЕМНЫЙ ПРОМПТ =======================

SYSTEM_PROMPT = """
Ты — внимательный, доброжелательный нумеролог-практик, работающий на базе модели ChatGPT.
Ты общаешься на русском языке, живым, понятным и уважительным тоном.

ТВОЯ РОЛЬ:
- Помогать пользователю через нумерологию мягко разобраться в себе и своих задачах.
- Давать структурные, логичные разборы, без мистического фанатизма.
- Объяснять значения чисел простым языком, с примерами из жизни.
- Указывать, что нумерология — это инструмент самопознания, а не «приговор судьбы».

ОБЩИЕ ПРАВИЛА ОТВЕТОВ:
- Всегда пиши по-русски.
- Структурируй ответ: заголовки, списки, логичные блоки.
- Не давай медицинских, юридических и финансовых диагнозов/рекомендаций.
- Не пугай пользователя. Формулируй мягко: «тенденции», «склонности», «варианты развития».
- В конце ответа добавляй небольшой вывод или совет по саморазвитию.
"""

# ======================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =======================

def looks_like_date(text: str) -> bool:
    text = text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        return True
    except ValueError:
        return False


def build_prompt_for_matrix(birth_date: str) -> str:
    return (
        f"Сделай подробный, но понятный нумерологический разбор матрицы судьбы "
        f"по дате рождения {birth_date}. "
        f"Структурируй ответ по блокам: характер, таланты, задачи, отношения, здоровье (без диагнозов), "
        f"финансы/реализация, рекомендации по саморазвитию."
    )


def build_prompt_for_compat(text: str) -> str:
    return (
        "Сделай нумерологический разбор совместимости по двум датам рождения.\n"
        f"Данные пользователя: {text}\n\n"
        "1) Кратко опиши каждого партнёра.\n"
        "2) Опиши общие тенденции пары (ресурсы и потенциальные точки напряжения).\n"
        "3) Дай практические советы, как мягко выровнять сложные моменты и усилить сильные стороны пары."
    )


def build_prompt_for_year(text: str) -> str:
    return (
        "Сделай разбор личного года и ближайшего периода по нумерологии.\n"
        f"Данные пользователя: {text}\n\n"
        "1) Определи личное число года.\n"
        "2) Опиши основные темы и задачи этого периода.\n"
        "3) Дай рекомендации, на что лучше направить энергию, от чего воздержаться.\n"
        "4) В конце сделай небольшой вдохновляющий вывод."
    )


def build_prompt_for_chat(text: str) -> str:
    return (
        "Пользователь задал вопрос нумерологу.\n"
        "Ответь как нумерологический коуч: мягко, по-делу, на основе нумерологии и здравого смысла.\n\n"
        f"Вопрос пользователя: {text}"
    )


def _call_openai_sync(prompt: str) -> str:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=1600,
    )
    return response.choices[0].message.content.strip()


async def call_openai(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_openai_sync, prompt)


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💜 Рассчитать матрицу судьбы по дате рождения")],
            [KeyboardButton(text="💞 Совместимость по датам рождения")],
            [KeyboardButton(text="🌀 Число года и ближайший период")],
            [KeyboardButton(text="✨ Просто поговорить")],
        ],
        resize_keyboard=True,
    )

# ======================= ОБРАБОТЧИКИ БОТА =======================

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_states.pop(message.from_user.id, None)
    text = (
        "Привет! Я нумерологический бот на базе ChatGPT 🔮\n\n"
        "Что можем сделать:\n"
        "• посчитать матрицу судьбы по дате рождения;\n"
        "• посмотреть совместимость по датам;\n"
        "• разобрать число года и ближайший период;\n"
        "• или просто поболтать на любую тему.\n\n"
        "Выбери пункт в меню ниже или напиши свой вопрос ✨"
    )
    await message.answer(text, reply_markup=main_keyboard())

@dp.message(F.text == "💜 Рассчитать матрицу судьбы по дате рождения")
async def btn_matrix(message: Message):
    user_states[message.from_user.id] = STATE_MATRIX
    await message.answer(
        "Напиши, пожалуйста, дату рождения в формате **ДД.ММ.ГГГГ**.\n"
        "Например: `14.11.2003`",
        parse_mode="Markdown",
    )

@dp.message(F.text == "💞 Совместимость по датам рождения")
async def btn_compat(message: Message):
    user_states[message.from_user.id] = STATE_COMPAT
    await message.answer(
        "Напиши две даты рождения для совместимости.\n\n"
        "Пример:\n"
        "`Она: 14.11.2003, он: 05.07.1998`\n"
        "или\n"
        "`14.11.2003 и 05.07.1998`",
        parse_mode="Markdown",
    )

@dp.message(F.text == "🌀 Число года и ближайший период")
async def btn_year(message: Message):
    user_states[message.from_user.id] = STATE_YEAR
    await message.answer(
        "Напиши свою дату рождения и, при желании, год, который интересует.\n\n"
        "Например:\n"
        "`14.11.2003, интересует 2025 год`\n"
        "или просто дату — тогда разберём текущий год.",
        parse_mode="Markdown",
    )

@dp.message(F.text == "✨ Просто поговорить")
async def btn_chat(message: Message):
    user_states.pop(message.from_user.id, None)
    await message.answer(
        "Пиши любой вопрос или ситуацию — отвечу как нумерологический помощник 💫"
    )

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    state = user_states.get(user_id)

    if state == STATE_MATRIX:
        if not looks_like_date(text):
            await message.answer(
                "Похоже, это не дата в формате **ДД.ММ.ГГГГ** 🤔\n"
                "Попробуй ещё раз. Например: `14.11.2003`",
                parse_mode="Markdown",
            )
            return
        await message.answer("Делаю нумерологический разбор… 🔮")
        prompt = build_prompt_for_matrix(text)
        try:
            reply = await call_openai(prompt)
            await message.answer(reply)
        except Exception as e:
            logging.exception("Ошибка при обращении к OpenAI (матрица судьбы)")
            await message.answer(
                "Техническая ошибка при обращении к ChatGPT:\n"
                f"`{repr(e)}`",
                parse_mode="Markdown",
            )
        finally:
            user_states.pop(user_id, None)
        return

    if state == STATE_COMPAT:
        await message.answer("Считаю совместимость, подожди немного… 💞")
        prompt = build_prompt_for_compat(text)
        try:
            reply = await call_openai(prompt)
            await message.answer(reply)
        except Exception as e:
            logging.exception("Ошибка при обращении к OpenAI (совместимость)")
            await message.answer(
                "Техническая ошибка при обращении к ChatGPT:\n"
                f"`{repr(e)}`",
                parse_mode="Markdown",
            )
        finally:
            user_states.pop(user_id, None)
        return

    if state == STATE_YEAR:
        await message.answer("Смотрю число года и ближайший период… 🌀")
        prompt = build_prompt_for_year(text)
        try:
            reply = await call_openai(prompt)
            await message.answer(reply)
        except Exception as e:
            logging.exception("Ошибка при обращении к OpenAI (личный год)")
            await message.answer(
                "Техническая ошибка при обращении к ChatGPT:\n"
                f"`{repr(e)}`",
                parse_mode="Markdown",
            )
        finally:
            user_states.pop(user_id, None)
        return

    prompt = build_prompt_for_chat(text)
    try:
        reply = await call_openai(prompt)
        await message.answer(reply)
    except Exception as e:
        logging.exception("Ошибка при обращении к OpenAI (общий чат)")
        await message.answer(
            "Техническая ошибка при обращении к ChatGPT:\n"
            f"`{repr(e)}`",
            parse_mode="Markdown",
        )

async def main():
    logging.info("Запускаем бота…")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")

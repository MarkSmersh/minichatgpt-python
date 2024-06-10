import asyncio
import sys
if sys.platform == 'win32':
    from asyncio import WindowsSelectorEventLoopPolicy
import base64

from aiogram import Dispatcher, Bot, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command

from openai import AsyncOpenAI

from dotenv import load_dotenv
from os import getenv

from db import db
from models import users, transactions, User, Transaction

load_dotenv()

bot = Bot(token=getenv('BOT_TOKEN'))
dp = Dispatcher()
r = Router()

client = AsyncOpenAI(api_key=getenv('OPENAI_TOKEN'))

TEMPORARY_VALUE_price_per_million_tokens_for_one_dollar = 50000

class F(StatesGroup):
    start = State("start")
    ready = State("ready")
    processing = State("processing")


@r.startup()
async def startup():
    admins: list[User] = await users.findmany(2)
    if admins:
        for admin in admins:
            await bot.send_message(admin["chat_id"], f'Bot {(await bot.get_me()).first_name} has started')

    print(f'Bot {(await bot.get_me()).first_name} has started')


@r.message(F.start)
@r.message(CommandStart())
async def start(m: Message, state: FSMContext):
    if await state.get_state() != F.ready:
        await state.set_state(F.start)

    if (await state.get_state()) == F.processing:
        await m.answer("Wait until request processing will end")
        return

    user = await users.findone(m.chat.id)

    if not user:
        user: User = await users.create(m.chat.id, m.from_user.first_name, m.from_user.last_name, await state.get_state())

    print(user)

    if user['access'] != 0:
        await m.answer(f"Welcome, {m.from_user.first_name}", reply_markup=ReplyKeyboardRemove())
        await state.set_state(F.ready)
    else:
        await m.answer(f"You are not supposed to be here, {m.from_user.first_name}")
        admins: list[User] = await users.findmany(2)
        if admins:
            for admin in admins:
                await bot.send_message(admin["chat_id"], f"Someone tried to use the bot ({m.chat.id})")

@r.message(Command("usage"))
async def usage(m: Message, state: FSMContext):
    user = await users.findone(m.chat.id)

    if not user:
        user: User = await users.create(m.chat.id, m.from_user.first_name, m.from_user.last_name, await state.get_state())

    user_transactions: list[Transaction] = await transactions.findmany(m.chat.id)
    tokens: int = 0

    for transaction in user_transactions:
        print(transaction)
        tokens += transaction['tokens']

    await m.answer(f"Current balance: {user['balance']}\nEstimated remaining tokens: {user['balance']*TEMPORARY_VALUE_price_per_million_tokens_for_one_dollar}\nTokens used for the whole time: {tokens}")

@r.message(F.ready)
async def accept(m: Message, state: FSMContext):
    user: User = await users.findone(m.chat.id)
    if user['access'] == 0:
        print(f"Your access is denied. Farewell, {m.from_user.first_name}")

    if user['balance'] == 0:
        print(f"Your balance is empty. Keep in touch with admin to solve this problem.")

    await state.set_state(F.processing)

    message = await m.answer("Processing...", reply_to_message_id=m.message_id)

    messages = [
        {"role": "system", "content": "ANSWER AS SHORT AS POSSIBLE. YOUR NAME IS MiniChatGPT. USE LATEX ONLY FOR MATH EXPRESSIONS. MAX ANSWER LENGTH ARE 4096 SYMBOLS."},
    ]

    print(m)

    if m.reply_to_message:
        if m.reply_to_message.from_user.id == (await bot.get_me()).id:
            messages.append({"role": "assistant", "content": m.reply_to_message.text})
        else:
            if m.reply_to_message.photo:
                messages.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"https://api.telegram.org/file/bot{getenv('BOT_TOKEN')}/{(await bot.get_file(file_id=m.reply_to_message.photo[-1].file_id)).file_path}", "detail": "low"}}, {"type": "text", "text": m.reply_to_message.caption or ""}]})
            elif not m.text:
                return
            else:
                messages.append({"role": "user", "content": m.reply_to_message.text})

    if m.photo:
        messages.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"https://api.telegram.org/file/bot{getenv('BOT_TOKEN')}/{(await bot.get_file(file_id=m.photo[-1].file_id)).file_path}", "detail": "low"}}, {"type": "text", "text": m.caption or ""}]})
    elif not m.text:
        return
    else:
        messages.append({"role": "user", "content": m.text})

    print(messages)

    result = None

    try:
        res = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )

        await transactions.create(m.chat.id, res.usage.total_tokens, res.model)

        result = res
    except Exception as e:
        print(e)

    encode_message = base64.b64encode(result.choices[0].message.content.encode())

    try:
        print(f"https://marksmersh.github.io/?text={encode_message}")
        print(encode_message)

        await message.edit_text(result.choices[0].message.content,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                    InlineKeyboardButton(text="Open via HTML", web_app=WebAppInfo(title="Open via HTML", url=f"https://marksmersh.github.io/?text={encode_message}"))
                                ]]))
    except Exception:
        await message.edit_text(result.choices[0].message.content)

    await state.set_state(F.ready)


async def main():
    dp.include_router(r)
    await db.start()
    await dp.start_polling(bot)


if __name__ == '__main__':
    print(sys.platform)
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

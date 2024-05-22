import asyncio

from aiogram import Dispatcher, Bot, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.methods.send_message import SendMessage
from aiogram.methods.get_me import GetMe
from aiogram.methods.get_file import GetFile

from openai import AsyncOpenAI

from dotenv import load_dotenv
from os import getenv


load_dotenv()

bot = Bot(token=getenv('BOT_TOKEN'))
dp = Dispatcher()
r = Router()

client = AsyncOpenAI(api_key=getenv('OPENAI_TOKEN'))


class F(StatesGroup):
    accept = State()


@r.message(CommandStart())
async def start(m: Message, state: FSMContext):
    admin = getenv("ADMIN")
    users = getenv("USERS").split(",")

    if str(m.from_user.id) == admin or str(m.from_user.id) in users:
        await m.answer(f"Welcome, {m.from_user.first_name}")
        await state.set_state(F.accept)
    else:
        await m.answer(f"You are not supposed to be here, {m.from_user.first_name}")
        await bot(SendMessage(chat_id=m.chat.id, text=f"Someone tried to use the bot ({m.chat.id})"))


@r.message(F.accept)
async def accept(m: Message):
    messages = [
        {"role": "system", "content": "ANSWER AS SHORT AS POSSIBLE. YOUR NAME IS MiniChatGPT. MAX ANSWER LENGTH ARE 2048 SYMBOLS."},
    ]

    print(m)

    if m.reply_to_message:
        if m.reply_to_message.from_user.id == (await bot(GetMe())).id:
            messages.append({"role": "assistant", "content": m.reply_to_message.text})
        else:
            messages.append({"role": "user", "content": m.reply_to_message.text})

    if m.photo:
        messages.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"https://api.telegram.org/file/bot{getenv('BOT_TOKEN')}/{(await bot(GetFile(file_id=m.photo[-1].file_id))).file_path}", "detail": "low"}}, {"type": "text", "text": m.caption or ""}]})
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

        result = res
    except Exception as e:
        print(e)

    try:
        await m.answer(result.choices[0].message.content, reply_to_message_id=m.message_id, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await m.answer(result.choices[0].message.content, reply_to_message_id=m.message_id)


async def main():
    dp.include_router(r)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

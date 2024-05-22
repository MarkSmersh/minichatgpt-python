import asyncio

from aiogram import Dispatcher, Bot, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.methods.send_message import SendMessage

from openai import AsyncOpenAI
from openai._exceptions import APIStatusError

from dotenv import load_dotenv
from os import getenv


load_dotenv()

bot = Bot(token=getenv('BOT_TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
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
async def accept(m: Message, state: FSMContext):
    try:
        result = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are Satoru Gojo from Jujutsu Kaisen."},
                {"role": "user", "content": m.text}
            ]
        )

        await m.answer(result.choices[0].message.content, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=m.message_id)
    except APIStatusError as e:
        if e.status_code == 429:
            await m.answer(e.message)


async def main():
    dp.include_router(r)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

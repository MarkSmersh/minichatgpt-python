import asyncio

from aiogram import Dispatcher, Bot, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart

from openai import AsyncOpenAI

from dotenv import load_dotenv
from os import getenv


load_dotenv()

bot = Bot(token=getenv('BOT_TOKEN'))
dp = Dispatcher()
r = Router()

client = AsyncOpenAI(api_key=getenv('OPENAI_TOKEN'))


class F(StatesGroup):
    ready = State()
    processing = State()


@r.startup()
async def startup():
    print(f'Bot {(await bot.get_me()).first_name} has started')


@r.message(CommandStart())
async def start(m: Message, state: FSMContext):
    if (await state.get_state()) == F.processing:
        await m.answer("Wait until request processing will end")
        return

    admin = getenv("ADMIN")
    users = getenv("USERS").split(",")

    if str(m.from_user.id) == admin or str(m.from_user.id) in users:
        await m.answer(f"Welcome, {m.from_user.first_name}", reply_markup=ReplyKeyboardRemove())
        await state.set_state(F.ready)
    else:
        await m.answer(f"You are not supposed to be here, {m.from_user.first_name}")
        await bot.send_message(chat_id=m.chat.id, text=f"Someone tried to use the bot ({m.chat.id})")


@r.message(F.ready)
async def accept(m: Message, state: FSMContext):
    await state.set_state(F.processing)

    message = await m.answer("Processing...", reply_to_message_id=m.message_id)

    messages = [
        {"role": "system", "content": "ANSWER AS SHORT AS POSSIBLE. YOUR NAME IS MiniChatGPT. MAX ANSWER LENGTH ARE 2048 SYMBOLS."},
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

        result = res
    except Exception as e:
        print(e)

    try:
        await message.edit_text(result.choices[0].message.content, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await message.edit_text(result.choices[0].message.content)

    await state.set_state(F.ready)


async def main():
    dp.include_router(r)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

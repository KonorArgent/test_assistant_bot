import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import ChatMemberUpdatedFilter

load_dotenv()
#TOKEN = os.getenv("8582998870:AAEzli24WLpfwxxLpbOMuCvHq5uFn_NjQ5s")
TOKEN = "8582998870:AAEzli24WLpfwxxLpbOMuCvHq5uFn_NjQ5s"
CLIENT_CHAT_ID = 702658010  # Замените на ваш ID
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.chat.id == CLIENT_CHAT_ID)
async def handle_client_message(message):
    print(f"Получено сообщение: {message.text}")
    await message.reply("Задача принята!")  # Стандартный ответ

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

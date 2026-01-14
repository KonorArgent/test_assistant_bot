import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()
#TOKEN = os.getenv("8582998870:AAEzli24WLpfwxxLpbOMuCvHq5uFn_NjQ5s")
TOKEN = "8582998870:AAEzli24WLpfwxxLpbOMuCvHq5uFn_NjQ5s"
CLIENT_CHAT_ID = 702658010  # Замените на ваш ID
OPENROUTER_API_KEY = "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"

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def get_ai_response(message: str) -> str:
    """Получить ответ от нейросети"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-r1:free",  # Бесплатная модель
        "messages": [
            {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко и по делу."},
            {"role": "user", "content": message}
        ],
        "max_tokens": 500
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                result = await resp.json()
                return result['choices'][0]['message']['content']
    except Exception as e:
        return f"Ошибка AI: {str(e)}"

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! Отправь мне сообщение, и я отвечу с помощью ИИ 🤖")

@dp.message(F.text)
async def ai_handler(message: types.Message):
    await message.answer("🤔 Думаю...")
    
    response = await get_ai_response(message.text)
    await message.answer(response)

#@dp.message(F.chat.id == CLIENT_CHAT_ID)
#async def handle_client_message(message):
#    print(f"Получено сообщение: {message.text}")
#    await message.reply("Задача принята!")  # Стандартный ответ

async def main():
    print("🚀 Бот с ИИ запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

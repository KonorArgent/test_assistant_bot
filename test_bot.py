import asyncio
import logging
import aiohttp
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from dotenv import load_dotenv
from typing import Dict, List, Tuple
import os

logging.basicConfig(level=logging.INFO)
load_dotenv()

TOKEN = "8582998870:AAEzli24WLpfwxxLpbOMuCvHq5uFn_NjQ5s"
OPENROUTER_API_KEY = "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"
SHEETS_CREDENTIALS = "credentials.json"  # Ваш JSON файл
SHEET_NAME = "AI_test"
SHEET_ID = "1fnNkUc0SG1FYQJUSH7K05nztSRg91bENqhukKLz4jYE"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Google Sheets подключение
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(SHEETS_CREDENTIALS, scope)
sheets_client = gspread.authorize(creds)

async def load_competencies() -> Dict:
    try:
        spreadsheet = sheets_client.open_by_key(SHEET_ID)
        sheet = spreadsheet.sheet1  # Первый лист
        
        logging.info(f"✅ Таблица: {spreadsheet.title}")
        headers = [str(h).strip() for h in sheet.row_values(1) if str(h).strip()]
        rows = sheet.get_all_values()[1:]
        
        competencies = {}
        for row in rows:
            if len(row) < 2 or not str(row[0]).strip():
                continue
            category = str(row[0]).strip()
            responsible = str(row[1]).strip()
            scores = {}
            for i in range(2, min(10, len(row))):
                if i < len(headers) and row[i]:
                    try:
                        scores[headers[i]] = float(str(row[i]))
                    except:
                        pass
            competencies[category] = {'responsible': responsible, 'scores': scores}
        
        logging.info(f"✅ Загружено: {len(competencies)} компетенций")
        return competencies
    except Exception as e:
        logging.error(f"Sheets: {e}")
        return {"Тест": {"responsible": "Иванов", "scores": {"Иванов": 5}}}

async def extract_competencies(text: str, all_competencies: Dict) -> List[str]:
    """AI определяет нужные компетенции"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    comp_list = ", ".join(all_competencies.keys())
    
    data = {
        "model": "deepseek/deepseek-chat-v3-0324",
        "messages": [{
            "role": "user",
            "content": f"""Доступные компетенции 1С-специалистов: {comp_list}

Правила:
1. Если это ТЕХНИЧЕСКАЯ заявка 1С (ошибки, отчеты, формы, API, интеграции) → выбери 1-3 РЕЛЕВАНТНЫХ компетенций
2. Если по запросу клиента не получается определить компетенцию по списку доступных компетенций, то выбери самую подходящую
3. Если НЕ техническая заявка (приветствие, вопросы боту) → верни ПУСТУЮ строку

Заявка: "{text}"

Ответь ТОЛЬКО названиями компетенций через запятую (точно как в списке) или ПУСТОЙ строкой:"""
        }],
        "max_tokens": 100,
        "temperature": 0.1  # Более точные ответы
    }
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://your-site.com",  # Требует OpenRouter
        "X-Title": "1C Competency Bot"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    raw_comps = result['choices'][0]['message']['content'].strip()
                    
                    logging.info(f"🤖 AI ответ: '{raw_comps}'")
                    
                    # Только точные совпадения
                    found = [c.strip() for c in raw_comps.split(',') 
                            if c.strip() in all_competencies]
                    
                    logging.info(f"✅ Найдено: {found}")
                    return found[:3]
    except Exception as e:
        logging.error(f"AI ошибка: {e}")
    
    return []

def rank_employees(competencies: Dict, required_comps: List[str]) -> List[Tuple[str, float]]:
    """ТОП-4 по среднему баллу + бонус ответственному"""
    if not required_comps:
        return []
    
    scores = {}
    
    for comp in required_comps:
        if comp not in competencies:
            continue
            
        data = competencies[comp]
        
        # Средний балл по компетенциям
        for emp, score in data['scores'].items():
            scores[emp] = scores.get(emp, 0) + score / len(required_comps)
        
        # Бонус +1 ответственному
        resp = data['responsible']
        scores[resp] = scores.get(resp, 0) + 1.0
    
    # ТОП-4
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:4]

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 **Бот анализа компетенций 1С**\n\n"
        "📝 Напишите заявку (например: «1С выдает ошибку при отчете»)\n"
        "⚡ Я найду ТОП-4 исполнителей по таблице компетенций!"
    )

@dp.message(F.text)
async def handle_request(message: types.Message):
    logging.info(f"📨 Заявка: {message.text}")
    
    # Загружаем компетенции
    competencies = await load_competencies()
    if not competencies:
        await message.answer("❌ Не удалось загрузить таблицу компетенций")
        return
    
    # AI определяет компетенции
    required_comps = await extract_competencies(message.text, competencies)
    
    if not required_comps:
        await message.answer(
            "ℹ️ **Компетенции не определены**\n\n"
            f"💬 Заявка: `{message.text}`\n\n"
            "🔄 Попробуйте описать подробнее!"
            , parse_mode="Markdown"
        )
        return
    
    # Ранжируем
    top_employees = rank_employees(competencies, required_comps)
    
    # Ответ пользователю
    top_list = "\n".join([
        f"{i+1}. **{emp}** ({score:.1f} баллов)" 
        for i, (emp, score) in enumerate(top_employees)
    ])
    
    response = (
        f"✅ **Анализ завершен!**\n\n"
        f"📋 **Необходимые компетенции:** {', '.join(required_comps)}\n\n"
        f"👥 **ТОП-4 исполнителей:**\n```\n{top_list}\n```\n\n"
        f"💬 **Заявка:** `{message.text}`"
    )
    
    await message.answer(response, parse_mode="Markdown")

async def main():
    logging.info("🚀 Бот компетенций запущен! Пишите в ЛС.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import logging
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message
from dotenv import load_dotenv
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Загрузка переменных окружения
load_dotenv("./.env")

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

# Получаем токен из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env файле")

# Создаем объект бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь ключевых слов и сообщений для ответа
keywords = {
    "тт": ("10 мин уже прошло", 60 * 10),
    "кур": ("5 мин уже прошло", 60 * 5),
    "маг": ("10 мин уже прошло", 60 * 10),
    "мин": ("2 мин уже прошло", 10),
    "мин из дома": ("5 мин уже прошло", 60 * 5),
    "куш": ("25 мин уже прошло", 60 * 25),
    "овкатланиш": ("30 мин уже прошло", 60 * 30),
    "kush": ("25 мин уже прошло", 60 * 25),
    "tt": ("10 мин уже прошло", 60 * 10),
    "kur": ("5 мин уже прошло", 60 * 5),
    "min": ("2 мин уже прошло", 60 * 2),
    "mag": ("10 мин уже прошло", 60 * 10),
    "серв": ("ты уже проверил сервер?", 60 * 5),
}

# Хранилище для отслеживания сообщений
messages_to_auto_reply = {}
counter_message_tasks = {}

# Подключение к Google Sheets
def setup_google_sheet():
    print("Подключение к Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    print("Авторизация успешна.")
    sheet = client.open_by_key("1Rl7v_FRsVwex64sfy94I0LBUDQMPOys7UnleR6z2YLY").worksheet("Отчёты")
    print("Лист найден.")
    return sheet

# Функция записи в Google Таблицу
def write_to_google_sheet(sheet, date, username, user_message, bot_reply):
    sheet.append_row([date, username, user_message, bot_reply])


# Обработчик текстовых сообщений
@dp.message(F.text)
async def handle_message(message: Message):
    # Проверяем текст сообщения
    text = message.text.lower()

    # Проверяем, является ли сообщение ответом с текстом '+'
    if message.reply_to_message and message.reply_to_message.from_user.id == message.from_user.id:
        if message.text.strip() == "+":
            print("Сообщение '+' — бот не отвечает")
            # Отменяем задачу автоответа, если она существует
            task = counter_message_tasks.pop(message.reply_to_message.message_id, None)
            if task:
                task.cancel()
                print(f"Отменена задача автоответа для сообщения {message.reply_to_message.message_id}")
            return

    # Проверяем ключевые слова
    for keyword, (reply_message, timeout) in keywords.items():
        if keyword in text:
            # Проверяем, если сообщение еще не обработано
            if message.message_id not in messages_to_auto_reply:
                messages_to_auto_reply[message.message_id] = reply_message

                # Запускаем таймер на автоматический ответ
                task = asyncio.create_task(
                    auto_reply(
                        message.message_id,
                        message.chat.id,
                        reply_message,
                        timeout,
                    )
                )
                counter_message_tasks[message.message_id] = task
                print(
                    "Task is created and stored ----- number of tasks to be waited:  ",
                    len(counter_message_tasks.keys()),
                )
            break


# Асинхронная функция для автоматического ответа
async def auto_reply(message_id, chat_id, reply_message, timeout):
    await asyncio.sleep(timeout)

    # Проверяем, был ли уже отправлен ответ на это сообщение
    if message_id in messages_to_auto_reply:
        del messages_to_auto_reply[message_id]

        # Отправляем автоматический ответ
        sent_message = await bot.send_message(
            chat_id=chat_id, text=reply_message, reply_to_message_id=message_id
        )
        print("Sending auto reply")

        # Подключаем Google Таблицу
        sheet = setup_google_sheet()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username = sent_message.chat.username or "Unknown"
        user_message = sent_message.reply_to_message.text
        write_to_google_sheet(sheet, date, username, user_message, reply_message)


# Основная функция
async def main():
    # Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot is running...")
    await dp.start_polling(bot)


# Точка входа
if __name__ == "__main__":
    asyncio.run(main())

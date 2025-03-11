import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime

TOKEN = "7856922433:AAElQHxJiNJarqrDTABRIIseRgBYBl5KmtM"
IMAGE_PATH = "/Users/oleggojdenko/Documents/ключи/key.jpg"  # Убедись, что путь правильный
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определение состояний
class KeyStates(StatesGroup):
    take_key_time = State()
    return_key_time = State()

# Переменная для хранения всех пользователей
subscribed_users = set()

# Переменная для хранения времени возврата и информации о пользователях
key_schedule = {}

async def send_key_menu(chat_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Скиньте ключ", callback_data="get_key")],
        [InlineKeyboardButton(text="📅 Забрать ключ", callback_data="take_key")],
        [InlineKeyboardButton(text="📅 Расписание ключа", callback_data="schedule_key")]
    ])
    
    try:
        photo = FSInputFile(IMAGE_PATH)
        await bot.send_photo(chat_id, photo, caption="Выберите действие:", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка при отправке изображения: {e}")
        await bot.send_message(chat_id, "🔑 Выберите действие:", reply_markup=keyboard)

@dp.message(F.text == "/start")
async def start(message: types.Message):
    subscribed_users.add(message.chat.id)
    await send_key_menu(message.chat.id)

@dp.callback_query()
async def handle_callbacks(callback_query: types.CallbackQuery, state: FSMContext):
    global key_schedule
    now = datetime.now()

    if callback_query.data == "get_key":
        for user_id in subscribed_users:
            try:
                await bot.send_message(user_id, "🔑 Ключ доступен для использования!")
            except Exception as e:
                logging.error(f"Ошибка при оповещении пользователя {user_id}: {e}")

    elif callback_query.data == "take_key":
        await callback_query.message.answer("Введите дату и время взятия ключа (например, 12.03.2025 14:00):")
        await state.set_state(KeyStates.take_key_time)

    elif callback_query.data == "schedule_key":
        if key_schedule:
            schedule_message = "🗓 Расписание ключа:\n"
            for user_id, data in key_schedule.items():
                take_time = data["take_time"].strftime("%d.%m.%Y %H:%M")
                return_time = data["return_time"].strftime("%d.%m.%Y %H:%M") if data["return_time"] else "Не возвращен"
                schedule_message += f"Пользователь {user_id}: Забор - {take_time}, Возврат - {return_time}\n"
            await callback_query.message.answer(schedule_message)
        else:
            await callback_query.message.answer("Расписание пусто. Пока нет записей.")
    
    await callback_query.answer()

@dp.message(KeyStates.take_key_time)
async def handle_take_key_time(message: types.Message, state: FSMContext):
    user_id = message.chat.id
    try:
        take_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        key_schedule[user_id] = {"take_time": take_time, "return_time": None}
        await message.answer(f"Вы забрали ключ в {take_time.strftime('%d.%m.%Y %H:%M')}. Теперь укажите дату и время возврата:")
        await state.set_state(KeyStates.return_key_time)
    except ValueError:
        await message.answer("Неверный формат! Используйте ДД.ММ.ГГГГ ЧЧ:ММ.")

@dp.message(KeyStates.return_key_time)
async def handle_return_key_time(message: types.Message, state: FSMContext):
    user_id = message.chat.id
    try:
        return_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        if user_id in key_schedule:
            key_schedule[user_id]["return_time"] = return_time
            
            for other_user_id, data in key_schedule.items():
                if other_user_id != user_id and data["return_time"] and data["take_time"] < return_time:
                    if data["return_time"] >= return_time:
                        key_schedule[other_user_id] = {"take_time": data["take_time"], "return_time": return_time}
                        await bot.send_message(other_user_id, "❗ Ваша запись была перезаписана другим пользователем, потому что его время возврата было более быстрым.")
            
            await message.answer(f"Вы вернули ключ в {return_time.strftime('%d.%m.%Y %H:%M')}. Запись удалится автоматически, когда время возврата наступит.")
            await state.clear()

            # Запускаем проверку на автоматическое удаление
            while datetime.now() < return_time:
                await asyncio.sleep(60)  # Проверяем каждую минуту
            if user_id in key_schedule and key_schedule[user_id]["return_time"] == return_time:
                del key_schedule[user_id]
                await bot.send_message(user_id, "✅ Ваша запись о ключе была удалена, так как время возврата наступило.")
        else:
            await message.answer("Ошибка! Сначала нужно забрать ключ.")
    except ValueError:
        await message.answer("Неверный формат! Используйте ДД.ММ.ГГГГ ЧЧ:ММ.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

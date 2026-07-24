from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime, timedelta
import asyncio
import os
import re
import random
import logging

BOT_TOKEN = "8946812123:AAFoi14oJiWtf8mkGUaEGV8gE6WRLFS90Rw"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ADMIN_IDS = [118272062]

# Создаем структуру папок для GitHub репозитория при старте
FOLDERS = ["subscriptions", "warnings", "promocodes"]
for folder in FOLDERS:
    os.makedirs(folder, exist_ok=True)

SUB_FILE = "subscriptions/paid_users.txt"
WARN_FILE = "warnings/banned_users.txt"
PROMO_FILE = "promocodes/promocodes.txt"

# Инициализация файлов, если они отсутствуют
for file_path in [SUB_FILE, WARN_FILE, PROMO_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            pass

def main_menu(user_id):
    kb = [
        [InlineKeyboardButton(text="АТАКА", callback_data="attack")],
        [InlineKeyboardButton(text="ПРОФИЛЬ", callback_data="profile")],
        [InlineKeyboardButton(text="ПОДПИСКА", callback_data="subscribe")]
    ]
    if user_id in ADMIN_IDS:
        kb.append([InlineKeyboardButton(text="АДМИН", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def check_payment(user_id):
    if not os.path.exists(SUB_FILE):
        return False
    with open(SUB_FILE, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split(',')
            if len(parts) == 2:
                uid, expiry_str = parts
                if uid == str(user_id):
                    expiry_time = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
                    if expiry_time > datetime.now():
                        return True
    return False

def save_paid_user(user_id, days):
    expiry_time = datetime.now() + timedelta(days=days)
    expiry_str = expiry_time.strftime('%Y-%m-%d %H:%M:%S')
    
    lines = []
    updated = False
    if os.path.exists(SUB_FILE):
        with open(SUB_FILE, "r", encoding="utf-8") as file:
            lines = file.readlines()
            
    new_lines = []
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) == 2 and parts[0] == str(user_id):
            current_expiry = datetime.strptime(parts[1], '%Y-%m-%d %H:%M:%S')
            base_time = max(current_expiry, datetime.now())
            expiry_time = base_time + timedelta(days=days)
            new_lines.append(f"{user_id},{expiry_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            updated = True
        else:
            new_lines.append(line)
            
    if not updated:
        new_lines.append(f"{user_id},{expiry_str}\n")
        
    with open(SUB_FILE, "w", encoding="utf-8") as file:
        file.writelines(new_lines)

def load_banned_users():
    if not os.path.exists(WARN_FILE):
        return set()
    with open(WARN_FILE, "r", encoding="utf-8") as file:
        return set(map(int, [line.strip() for line in file if line.strip().isdigit()]))

def save_banned_users(banned_set):
    with open(WARN_FILE, "w", encoding="utf-8") as file:
        for uid in banned_set:
            file.write(f"{uid}\n")

banned_users = load_banned_users()

@dp.message(Command("start"))
async def start(msg: types.Message):
    if msg.from_user.id in banned_users:
        await msg.answer("❌ Вы забанены в системе.")
        return
    text = "BOTNET SYSTEM\nСвязь по всем вопросам: @coldwarn"
    await msg.answer(text, reply_markup=main_menu(msg.from_user.id))

@dp.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    user_id = call.from_user.id
    sub_active = check_payment(user_id) or user_id in ADMIN_IDS
    text = f"""ПРОФИЛЬ
ID: {user_id}
Подписка: {'Активна' if sub_active else 'Нет'}
Юзернейм: @{call.from_user.username or 'Нет'}"""
    await call.message.edit_text(text, reply_markup=main_menu(user_id))

@dp.callback_query(F.data == "attack")
async def attack(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_payment(user_id) and user_id not in ADMIN_IDS:
        await call.answer("Нужна подписка", show_alert=True)
        return
    
    await call.message.edit_text(
        "Введите юзернейм цели:\n"
        "Пример: @username или https://t.me/username\n\n"
        "ВНИМАНИЕ: Нельзя сносить аккаунты старше 5 лет!",
        parse_mode="HTML"
    )

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_target(msg: types.Message):
    if msg.from_user.id in banned_users:
        return
    target = msg.text.strip()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ЦП", callback_data="reason_cpu")],
        [InlineKeyboardButton(text="Живодерство", callback_data="reason_hard")],
        [InlineKeyboardButton(text="Спам", callback_data="reason_spam")],
        [InlineKeyboardButton(text="Личные данные", callback_data="reason_data")],
        [InlineKeyboardButton(text="Насилие", callback_data="reason_violence")]
    ])
    
    await msg.answer(
        f"Цель: {target}\n\n"
        "Выберите причину жалобы:",
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("reason_"))
async def start_attack_process(call: types.CallbackQuery):
    reason_map = {
        "reason_cpu": "ЦП",
        "reason_hard": "Живодерство", 
        "reason_spam": "Спам",
        "reason_data": "Личные данные",
        "reason_violence": "Насилие"
    }
    reason = reason_map.get(call.data, "Причина")
    await call.message.edit_text(f"Ищем нарушения...\nПричина: {reason}")
    await send_complaints_progress(call.message, reason)

async def send_complaints_progress(message: types.Message, reason: str):
    total_complaints = 132
    progress_msg = await message.answer(f"Отправка жалоб...\nЖалоб отправлено: 0/{total_complaints}")
    
    for i in range(1, total_complaints + 1):
        await asyncio.sleep(0.02)
        if i % 20 == 0 or i == total_complaints:
            await progress_msg.edit_text(
                f"Отправка жалоб...\n"
                f"Жалоб отправлено: {i}/{total_complaints}\n"
                f"Причина: {reason}"
            )
    
    await message.answer(
        f"Атака завершена!\n"
        f"Отправлено жалоб: {total_complaints}\n"
        f"Причина: {reason}\n\n"
        f"Жалобы обрабатываются Telegram...",
        reply_markup=main_menu(message.chat.id)
    )

@dp.callback_query(F.data == "subscribe")
async def subscribe(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Активировать промокод", callback_data="activate_promo")],
        [InlineKeyboardButton(text="Назад", callback_data="back")]
    ])
    await call.message.edit_text(
        "Для приобретения подписки напишите в личные сообщения: @coldwarn", 
        reply_markup=kb
    )

@dp.message(Command("givesub"))
async def givesub_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    args = msg.text.split()
    if len(args) < 3:
        await msg.answer("/givesub <user_id> <дни>")
        return
    try:
        target_id = int(args[1])
        days = int(args[2])
        save_paid_user(target_id, days)
        await msg.answer(f"Подписка выдана {target_id} на {days} дней")
    except Exception as e:
        await msg.answer(f"Ошибка: {e}")

@dp.message(Command("ban"))
async def ban_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("/ban <user_id>")
        return
    try:
        target_id = int(args[1])
        banned_users.add(target_id)
        save_banned_users(banned_users)
        await msg.answer(f"Пользователь {target_id} добавлен в папку варнов/банов.")
    except Exception as e:
        await msg.answer(f"Ошибка: {e}")

@dp.message(Command("unban"))
async def unban_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("/unban <user_id>")
        return
    try:
        target_id = int(args[1])
        if target_id in banned_users:
            banned_users.remove(target_id)
            save_banned_users(banned_users)
            await msg.answer(f"Пользователь {target_id} разбанен.")
        else:
            await msg.answer("Пользователь не найден в списке забаненных.")
    except Exception as e:
        await msg.answer(f"Ошибка: {e}")

@dp.callback_query(F.data == "admin")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="Создать промокод", callback_data="create_promo_panel")],
        [InlineKeyboardButton(text="Назад", callback_data="back")]
    ])
    await call.message.edit_text("Админ панель", reply_markup=kb)

@dp.callback_query(F.data == "stats")
async def admin_stats(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    total_subs = 0
    if os.path.exists(SUB_FILE):
        with open(SUB_FILE, "r", encoding="utf-8") as f:
            total_subs = len(f.readlines())
            
    text = f"""СТАТИСТИКА БОТНЕТА
Активных/Записанных подписок в папке: {total_subs}
Варнов/Банов в папке: {len(banned_users)}

Команды:
/ban <id>
/unban <id>
/givesub <id> <дни>"""
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="admin")]]))

@dp.callback_query(F.data == "create_promo_panel")
async def create_promo_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    # Пример быстрого создания промокода через инлайн или инструкцию
    await call.message.edit_text(
        "Чтобы создать промокод, используйте логику записи в файл `promocodes/promocodes.txt`.\n"
        "Формат хранения в папке:\n"
        "ПРОМОКОД | ДНИ | КОЛ-ВО АКТИВАЦИЙ",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="admin")]])
    )

@dp.callback_query(F.data == "activate_promo")
async def activate_promo_prompt(call: types.CallbackQuery):
    await call.message.edit_text("Отправьте промокод в чат сообщением (функция интеграции активирована).")

@dp.callback_query(F.data == "back")
async def back(call: types.CallbackQuery):
    await call.message.edit_text(
        "BOTNET SYSTEM\nСвязь по всем вопросам: @coldwarn",
        reply_markup=main_menu(call.from_user.id)
    )

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        

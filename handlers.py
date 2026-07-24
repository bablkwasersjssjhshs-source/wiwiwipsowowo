import tracemalloc
from aiogram import Router, F
from aiogram.types import FSInputFile, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from config import photo_path, ADMIN
from keyboards.keyboards import *
from backend.snos import *
from backend.database import *
from backend.buySub import *

tracemalloc.start()
router = Router()
photo = FSInputFile(photo_path)

class States(StatesGroup):
    VIOLATIONLINK = State()
    GIVESUBID = State()
    GIVESUBDAYS = State()
    CLOSESUB = State()

@router.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    await checkUser(userid=user_id)
    subStatus = await checkSubStatus(userid=user_id)
    if subStatus:
        date = await subDate(userid=user_id)
        status = f'Активна до {date}'
    else:
        status = 'Неактивна'
    
    markup = markupAdmin if user_id == ADMIN else markupUser
    await message.answer_photo(
        photo,
        f"<b>💼 Мой профиль\n➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"🆔 ID профиля: {user_id}\n"
        f"💎 Подписка: {status}\n➖➖➖➖➖➖➖➖➖➖➖➖</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=markup
    )

@router.callback_query(F.data == 'snos')
async def handlerSnos(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    await callback.answer()
    await callback.message.delete()

    # Check the subscription status for the user
    checkStatus = await checkSubStatus(userid=user_id)


    if checkStatus:
        if await checkSubDate(userid=user_id):
            await callback.message.answer_photo(
                photo,
                "<b>📝 Отправьте ссылку на нарушение</b>",
                parse_mode=ParseMode.HTML
            )
            await state.set_state(States.VIOLATIONLINK)
        else:
            await callback.message.answer_photo(
                photo,
                "<b>❌ У вас отсутствует подписка</b>",
                parse_mode=ParseMode.HTML
            )
    else:
        await callback.message.answer_photo(
            photo,
            "<b>❌ У вас отсутствует подписка</b>",
            parse_mode=ParseMode.HTML
        )

@router.message(States.VIOLATIONLINK)
async def getViolationLink(message: Message, state: FSMContext):
    await state.clear()
    link = message.text.strip()
    start = await message.answer_photo(
        photo,
        "<b>😶‍🌫️ Начинаю подачу жалоб</b>",
        parse_mode=ParseMode.HTML
    )
    result = await report(link)
    await start.delete()
    await message.answer_photo(
        photo,
        f"<b>📄 Отчет:\n{result}</b>",
        parse_mode=ParseMode.HTML
    )
    await message.bot.send_photo(
        ADMIN,
        photo,
        caption=f"<b>📄 Отчет о жалобе от пользователя {message.from_user.id}:\n{result}</b>",
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == 'adminpanel')
async def handlerAdmin(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer_photo(
        photo,
        "<b>🚀 Выберите действие</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=markupAdminPanel
    )

@router.callback_query(F.data == 'giveSub')
async def handlerGiveSub(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer_photo(
        photo,
        "<b>📝 Отправьте ID пользователя</b>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(States.GIVESUBID)

@router.message(States.GIVESUBID)
async def giveId(message: Message, state: FSMContext):
    user_id = message.text.strip()
    await state.update_data(userid=user_id)
    await message.answer_photo(
        photo,
        "<b>📝 Отправьте количество дней подписки</b>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(States.GIVESUBDAYS)

@router.message(States.GIVESUBDAYS)
async def giveDays(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('userid')
    days = message.text.strip()
    await giveSub(user_id, days)
    await state.clear()
    await message.answer_photo(
        photo,
        f'<b>✅ Подписка пользователю {user_id} выдана</b>',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == 'closeSub')
async def handlerCloseSub(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer_photo(
        photo,
        "<b>📝 Отправьте ID пользователя</b>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(States.CLOSESUB)

@router.message(States.CLOSESUB)
async def closeSubscription(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.text.strip()
    if await checkSubStatus(user_id):
        await closeSub(user_id)
        await message.answer_photo(
            photo,
            f"<b>Подписка пользователя {user_id} закрыта</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer_photo(
            photo,
            f"<b>❌ У пользователя {user_id} отсутствует подписка</b>",
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data == 'buySub')
async def buySubMenu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer_photo(
        photo,
        "<b>💎 Выберите время подписки</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=markupBuySub
    )
@router.callback_query(F.data == 'BuySub3')
async def buySub3(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    userid = callback.from_user.id
    invoice_url, invoice_id = await createCheck(userid=userid, amount=3.0)
    await callback.message.answer_photo(
        photo,
        f"<b>🧾 Оплатите чек {invoice_url} в течение 60 секунд</b>",
        parse_mode=ParseMode.HTML
        )
    await asyncio.sleep(60)
    payment_status = await check_payment(user_id=userid, days=7, invoice_id=invoice_id)
    if payment_status:
        await callback.message.answer_photo(
            photo,
            "<b>✅ Оплата прошла успешно, подписка выдана</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.answer_photo(
            photo,
            "<b>❌ Оплата не прошла в течение 60 секунд</b>",
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data == 'BuySub6')
async def buySub6(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    userid = callback.from_user.id
    invoice_url, invoice_id = await createCheck(userid=userid, amount=6.0)
    await callback.message.answer_photo(
        photo,
        f"<b>🧾 Оплатите чек {invoice_url} в течение 60 секунд</b>",
        parse_mode=ParseMode.HTML
        )
    await asyncio.sleep(60)
    payment_status = await check_payment(user_id=userid, days=30, invoice_id=invoice_id)
    if payment_status:
        await callback.message.answer_photo(
            photo,
            "<b>✅ Оплата прошла успешно, подписка выдана</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.answer_photo(
            photo,
            "<b>❌ Оплата не прошла в течение 60 секунд</b>",
            parse_mode=ParseMode.HTML
        )
@router.callback_query(F.data == 'BuySub9')
async def buySub9(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    userid = callback.from_user.id
    invoice_url, invoice_id = await createCheck(userid=userid, amount=9.0)
    await callback.message.answer_photo(
        photo,
        f"<b>🧾 Оплатите чек {invoice_url} в течение 60 секунд</b>",
        parse_mode=ParseMode.HTML
        )
    await asyncio.sleep(60)
    payment_status = await check_payment(user_id=userid, days=365, invoice_id=invoice_id)
    if payment_status:
        await callback.message.answer_photo(
            photo,
            "<b>✅ Оплата прошла успешно, подписка выдана</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.answer_photo(
            photo,
            "<b>❌ Оплата не прошла в течение 60 секунд</b>",
            parse_mode=ParseMode.HTML
        )
@router.callback_query(F.data == 'BuySub3')
async def buySub15(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    userid = callback.from_user.id
    invoice_url, invoice_id = await createCheck(userid=userid, amount=15.0)
    await callback.message.answer_photo(
        photo,
        f"<b>🧾 Оплатите чек {invoice_url} в течение 60 секунд</b>",
        parse_mode=ParseMode.HTML
        )
    await asyncio.sleep(60)
    payment_status = await check_payment(user_id=userid, days=10000, invoice_id=invoice_id)
    if payment_status:
        await callback.message.answer_photo(
            photo,
            "<b>✅ Оплата прошла успешно, подписка выдана</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.answer_photo(
            photo,
            "<b>❌ Оплата не прошла в течение 60 секунд</b>",
            parse_mode=ParseMode.HTML
        )

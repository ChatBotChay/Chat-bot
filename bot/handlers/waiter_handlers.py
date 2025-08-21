from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database.dao import DAO
from database.engine import async_session_maker
from bot.utils import send_dish_card_to_tech_group
from bot.keyboards.reply import get_keyboard

waiter_router = Router()

class WaiterMenuStates(StatesGroup):
    waiting_for_choice = State()
    waiting_for_category = State()
    waiting_for_dish = State()
    viewing_dish = State()

@waiter_router.message(CommandStart())
async def universal_start(message: Message, state: FSMContext, user):
    if not user:
        await message.answer("У вас нет доступа к этому боту. Обратитесь к администратору.")
        return
    if user.role == "waiter":
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Тест"), KeyboardButton(text="Меню")]],
            resize_keyboard=True
        )
        await message.answer("Выберите действие:", reply_markup=kb)
        await state.set_state(WaiterMenuStates.waiting_for_choice)
    elif user.role in ("admin", "superadmin"):
        kb = get_keyboard(
            "🍽️ Блюдо",
            "📂 Категории",
            "🤝 Сделать приглашение",
            "🧑‍🤝‍🧑 Штат",
            sizes=(2, 2)
        )
        await message.answer(f"Добро пожаловать, {user.first_name}! Вы вошли как {user.role}.", reply_markup=kb)
        # Можно добавить state для админа, если нужно
    else:
        await message.answer("У вас нет доступа к этому боту. Обратитесь к администратору.")


@waiter_router.message(WaiterMenuStates.waiting_for_choice)
async def waiter_choice(message: Message, state: FSMContext, user):
    if message.text.lower() == "меню":
        async with async_session_maker() as session:
            dao = DAO(session)
            categories = await dao.get_categories_by_restaurant(user.restaurant_id)
        if not categories:
            await message.answer("Нет категорий.")
            return
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=c.name, callback_data=f"waiter_cat_{c.id}") for c in categories]]
        )
        await message.answer("Выберите категорию:", reply_markup=kb)
        await state.set_state(WaiterMenuStates.waiting_for_category)
    elif message.text.lower() == "тест":
        await message.answer("Тестирование пока не реализовано.")
    else:
        await message.answer("Пожалуйста, выберите действие через кнопки.")

@waiter_router.callback_query(F.data.startswith("waiter_cat_"), WaiterMenuStates.waiting_for_category)
async def waiter_choose_category(call: CallbackQuery, state: FSMContext, user):
    cat_id = int(call.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    async with async_session_maker() as session:
        dao = DAO(session)
        dishes = await dao.get_dishes_by_category(cat_id)
    if not dishes:
        await call.message.edit_text("В этой категории нет блюд.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=d.name, callback_data=f"waiter_dish_{d.id}") for d in dishes]] + [[InlineKeyboardButton(text="Назад", callback_data="waiter_back_cat")]]
    )
    try:
        await call.message.edit_text("Выберите блюдо:", reply_markup=kb)
    except Exception:
        await call.message.delete()
        await call.message.answer("Выберите блюдо:", reply_markup=kb)
    await state.set_state(WaiterMenuStates.waiting_for_dish)
    await call.answer()

@waiter_router.callback_query(F.data == "waiter_back_cat", WaiterMenuStates.waiting_for_dish)
async def waiter_back_to_categories(call: CallbackQuery, state: FSMContext, user):
    async with async_session_maker() as session:
        dao = DAO(session)
        categories = await dao.get_categories_by_restaurant(user.restaurant_id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=c.name, callback_data=f"waiter_cat_{c.id}") for c in categories]]
    )
    try:
        await call.message.edit_text("Выберите категорию:", reply_markup=kb)
    except Exception:
        await call.message.delete()
        await call.message.answer("Выберите категорию:", reply_markup=kb)
    await state.set_state(WaiterMenuStates.waiting_for_category)
    await call.answer()

@waiter_router.callback_query(F.data.startswith("waiter_dish_"), WaiterMenuStates.waiting_for_dish)
async def waiter_choose_dish(call: CallbackQuery, state: FSMContext, user):
    dish_id = int(call.data.split("_")[2])
    await state.update_data(dish_id=dish_id, dish_page=0, dish_media="photo")
    async with async_session_maker() as session:
        dao = DAO(session)
        dish = await dao.get_dish_by_id(dish_id)
    if not dish:
        await call.message.edit_text("Блюдо не найдено.")
        return
    from aiogram.types.input_file import FSInputFile
    from aiogram.types import InputMediaPhoto, InputMediaVideo
    dish_media = "photo"  # Для карточки блюда всегда фото
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="waiter_prev_dish"), InlineKeyboardButton(text="➡️ Далее", callback_data="waiter_next_dish")],
            [InlineKeyboardButton(text="📸 Фотография", callback_data="waiter_toggle_media")],
            [InlineKeyboardButton(text="🔙 К категориям", callback_data="waiter_back_dishes")]
        ]
    )
    # Форматируем состав блюда (ингредиенты)
    if dish.composition:
        import re
        raw_ingredients = re.split(r",\s*|\s{2,}", dish.composition)
        ingredients_text = '\n'.join([f"• {i.strip()}" for i in raw_ingredients if i.strip()])
    else:
        ingredients_text = "Нет данных"
    caption = f"<b>{dish.name} 🍽️</b>\n\n<b>Состав:</b>\n{ingredients_text}\n\n<b>Описание:</b>\n{dish.description}"
    # При первом показе блюда всегда фото
    if dish.ready_photo_url:
        media = InputMediaPhoto(media=FSInputFile(dish.ready_photo_url), caption=caption, parse_mode="HTML")
        await call.message.edit_media(media=media, reply_markup=kb)
    else:
        await call.message.edit_text(caption, parse_mode="HTML", reply_markup=kb)
    await state.set_state(WaiterMenuStates.viewing_dish)
    await call.answer()

@waiter_router.callback_query(F.data == "waiter_toggle_media", WaiterMenuStates.viewing_dish)
async def waiter_toggle_media(call: CallbackQuery, state: FSMContext, user):
    data = await state.get_data()
    dish_id = data.get("dish_id")
    dish_media = data.get("dish_media", "photo")
    async with async_session_maker() as session:
        dao = DAO(session)
        dish = await dao.get_dish_by_id(dish_id)
    # Кнопка переключения медиа всегда чередуется
    next_media_text = "📸 Фотография" if dish_media == "video" else "🎬 Видео"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="waiter_prev_dish"), InlineKeyboardButton(text="➡️ Далее", callback_data="waiter_next_dish")],
            [InlineKeyboardButton(text=next_media_text, callback_data="waiter_toggle_media")],
            [InlineKeyboardButton(text="🔙 К категориям", callback_data="waiter_back_dishes")]
        ]
    )
    from aiogram.types.input_file import FSInputFile
    from aiogram.types import InputMediaPhoto, InputMediaVideo
    # Форматируем состав блюда (ингредиенты)
    if dish.composition:
        import re
        raw_ingredients = re.split(r",\s*|\s{2,}", dish.composition)
        ingredients_text = '\n'.join([f"• {i.strip()}" for i in raw_ingredients if i.strip()])
    else:
        ingredients_text = "Нет данных"
    caption = f"<b>{dish.name} 🍽️</b>\n\n<b>Состав:</b>\n{ingredients_text}\n\n<b>Описание:</b>\n{dish.description}"
    # Для видео и фото всегда используем caption
    if dish_media == "photo" and dish.video_url:
        media = InputMediaVideo(media=FSInputFile(dish.video_url), caption=caption, parse_mode="HTML")
        await call.message.edit_media(media=media, reply_markup=kb)
        await state.update_data(dish_media="video")
    elif dish_media == "video" and dish.ready_photo_url:
        media = InputMediaPhoto(media=FSInputFile(dish.ready_photo_url), caption=caption, parse_mode="HTML")
        await call.message.edit_media(media=media, reply_markup=kb)
        await state.update_data(dish_media="photo")
    else:
        await call.message.answer("Нет медиа для переключения.")
    await call.answer()

@waiter_router.callback_query(F.data == "waiter_back_dishes", WaiterMenuStates.viewing_dish)
async def waiter_back_to_dishes(call: CallbackQuery, state: FSMContext, user):
    data = await state.get_data()
    cat_id = data.get("category_id")
    async with async_session_maker() as session:
        dao = DAO(session)
        dishes = await dao.get_dishes_by_category(cat_id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"{d.name} 🍽️", callback_data=f"waiter_dish_{d.id}") for d in dishes]] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="waiter_back_cat")]]
    )
    try:
        await call.message.edit_text("Выберите блюдо:", reply_markup=kb)
    except Exception:
        await call.message.delete()
        await call.message.answer("Выберите блюдо:", reply_markup=kb)
    await state.set_state(WaiterMenuStates.waiting_for_dish)
    await call.answer()

import secrets
import tempfile
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import DAO
from database.engine import async_session_maker
from bot.keyboards.reply import get_keyboard
from database.invite_token_service import InviteTokenService
from bot.utils import make_video_from_image_and_audio, send_video_to_tech_group
invite_service = InviteTokenService()

admin_router = Router()

admin_kb = get_keyboard(
	"🍽️ Блюдо",
	"📂 Категории",
	"🤝 Сделать приглашение",
	"🧑‍🤝‍🧑 Штат",
	sizes=(2, 2)
)


class CategoryEditStates(StatesGroup):
	waiting_for_category = State()
	waiting_for_new_name = State()


class DishEditStates(StatesGroup):
	waiting_for_id = State()
	waiting_for_name = State()
	waiting_for_category = State()
	waiting_for_composition = State()
	waiting_for_description = State()
	waiting_for_ingredients_photo = State()
	waiting_for_ready_photo = State()
	waiting_for_audio = State()
	waiting_for_video = State()


class AddDishStates(StatesGroup):
	waiting_for_name = State()
	waiting_for_ingredients = State()
	waiting_for_description = State()
	waiting_for_video = State()
	waiting_for_category = State()


class WaiterRegisterStates(StatesGroup):
	waiting_for_first_name = State()
	waiting_for_last_name = State()


class CategoryCreateStates(StatesGroup):
	waiting_for_name = State()

async def is_user_allowed(tg_id: str, session: AsyncSession) -> bool:
	dao = DAO(session)
	user = await dao.get_user_by_tg_id(tg_id)
	return user is not None and user.role in ("admin", "superadmin")


@admin_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user):
	args = message.text.split()
	if len(args) > 1:
		# Обработка приглашения по токену
		token = args[1]
		restaurant_id = await invite_service.get_restaurant_id(token)
		print(f"Получен токен: {token}, restaurant_id: {restaurant_id}")
		if restaurant_id:
			await state.update_data(invite_token=token, restaurant_id=restaurant_id)
			await message.answer("Введите ваше имя:")
			await state.set_state(WaiterRegisterStates.waiting_for_first_name)
			return
		await message.answer("Ссылка недействительна или устарела.")
		return
	if not user or user.role not in ("admin", "superadmin", "waiter"):
		await message.answer("У вас нет доступа к этому боту. Обратитесь к администратору.")
		return

	kb = admin_kb if user.role == "admin" else None
	await message.answer(f"Добро пожаловать, {user.first_name}! Вы вошли как {user.role}.", reply_markup=kb)


############_______FSM: регистрация официанта по приглашению_____############################
@admin_router.message(WaiterRegisterStates.waiting_for_first_name)
async def waiter_first_name(message: Message, state: FSMContext):
	await state.update_data(first_name=message.text)
	await message.answer("Введите вашу фамилию:")
	await state.set_state(WaiterRegisterStates.waiting_for_last_name)


@admin_router.message(WaiterRegisterStates.waiting_for_last_name)
async def waiter_last_name(message: Message, state: FSMContext):

	data = await state.get_data()

	rest_id = data.get("restaurant_id")
	if not rest_id or rest_id == "None":
		await message.answer("Ошибка регистрации: не удалось определить ресторан. Обратитесь к администратору.")
		await state.clear()
		return

	async with async_session_maker() as session:
		dao = DAO(session)
		# Проверяем, не зарегистрирован ли уже этот tg_id
		user = await dao.get_user_by_tg_id(str(message.from_user.id))
		if user:
			await message.answer("Вы уже зарегистрированы.")
			await state.clear()
			return
		# Регистрируем официанта
		await dao.create_user(
			first_name=data["first_name"],
			last_name=message.text,
			tg_username=message.from_user.username,
			tg_id=str(message.from_user.id),
			role="waiter",
			restaurant_id=int(rest_id)
		)

	await invite_service.delete_token(data['invite_token'])
	await message.answer("Вы успешно зарегистрированы как официант! Теперь вы можете пользоваться ботом.")
	await state.clear()


@admin_router.message(F.text.lower() == "🍽️ блюдо")
async def show_dishes_menu(message: Message, user):
	if not user or user.role != "admin":
		await message.answer("Только админ может работать с блюдами.")
		return
	async with async_session_maker() as session:
		dao = DAO(session)
		dishes = await dao.get_dishes_by_restaurant(user.restaurant_id)
	kb = InlineKeyboardMarkup(
		inline_keyboard=[
			[InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="add_dish")],
			*[[
				InlineKeyboardButton(text=f"👁️ {d.name}", callback_data=f"viewdish_{d.id}"),
				InlineKeyboardButton(text="✏️", callback_data=f"editdish_{d.id}"),
				InlineKeyboardButton(text="🗑️", callback_data=f"deldish_{d.id}")
			] for d in dishes]
		]
	)
	await message.answer("Меню блюд:", reply_markup=kb)

# --- Просмотр блюда ---
@admin_router.callback_query(F.data.startswith("viewdish_"))
async def admin_view_dish(call: CallbackQuery, user):
	dish_id = int(call.data.split("_")[1])
	async with async_session_maker() as session:
		dao = DAO(session)
		dish = await dao.get_dish_by_id(dish_id)
	if not dish or dish.restaurant_id != user.restaurant_id:
		await call.message.answer("Блюдо не найдено или нет доступа.")
		await call.answer()
		return
	# Формируем карточку блюда
	from aiogram.types.input_file import FSInputFile
	from aiogram.types import InputMediaPhoto
	import re
	if dish.composition:
		raw_ingredients = re.split(r",\s*|\s{2,}", dish.composition)
		ingredients_text = '\n'.join([f"• {i.strip()}" for i in raw_ingredients if i.strip()])
	else:
		ingredients_text = "Нет данных"
	caption = f"<b>{dish.name} 🍽️</b>\n\n<b>Состав:</b>\n{ingredients_text}\n\n<b>Описание:</b>\n{dish.description}"
	if dish.ready_photo_url:
		try:
			media = InputMediaPhoto(media=FSInputFile(dish.ready_photo_url), caption=caption, parse_mode="HTML")
			await call.message.answer_photo(photo=FSInputFile(dish.ready_photo_url), caption=caption, parse_mode="HTML")
		except Exception:
			await call.message.answer(caption, parse_mode="HTML")
	else:
		await call.message.answer(caption, parse_mode="HTML")
	await call.answer()

# --- Удаление блюда ---
@admin_router.callback_query(F.data.startswith("deldish_"))
async def admin_delete_dish(call: CallbackQuery, user):
	dish_id = int(call.data.split("_")[1])
	async with async_session_maker() as session:
		dao = DAO(session)
		dish = await dao.get_dish_by_id(dish_id)
		if not dish or dish.restaurant_id != user.restaurant_id:
			await call.answer("Нет доступа или блюдо не найдено", show_alert=True)
			return
		await session.delete(dish)
		await session.commit()
	await call.message.answer("Блюдо удалено.")
	await call.answer()

@admin_router.message(F.text.lower() == "📂 категории")
async def show_categories_menu(message: Message, user):
	if not user or user.role != "admin":
		await message.answer("Только админ может работать с категориями.")
		return
	async with async_session_maker() as session:
		dao = DAO(session)
		categories = await dao.get_categories_by_restaurant(user.restaurant_id)
	kb = InlineKeyboardMarkup(
		inline_keyboard=[
			[InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_category")],
			*[[
				InlineKeyboardButton(text=f"✏️ {c.name}", callback_data=f"editcat_{c.id}"),
				InlineKeyboardButton(text="🗑️", callback_data=f"delcat_{c.id}")
			] for c in categories]
		]
	)
	await message.answer("Меню категорий:", reply_markup=kb)


# ------------------------------ РАБОТА С МЕНЮ --------------------------------------------------------------------------------------

@admin_router.message(F.text.lower() == "📋 меню")
async def show_categories(message: Message, user):
	if not user or user.role != "admin":
		await message.answer("Только админ может просматривать категории.")
		return
	async with async_session_maker() as session:
		dao = DAO(session)
		categories = await dao.get_categories_by_restaurant(user.restaurant_id)
	if not categories:
		await message.answer("В вашем ресторане нет категорий.")
		return
	for c in categories:
		kb = InlineKeyboardMarkup(inline_keyboard=[
			[InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delcat_{c.id}")]
		])
		await message.answer(f"Категория: 📂 {c.name} (id: {c.id})", reply_markup=kb)


# ----------------------------- СОЗДАНИЕ/РЕДАКТИРОВАНИЕ КАТЕГОРИИ ---------------------------------------------------------------





# --- СОЗДАНИЕ КАТЕГОРИИ ---
@admin_router.message(F.text.lower() == "Категории")
async def category_edit_start(message: Message, state: FSMContext, user):
	if not user or user.role != "admin":
		await message.answer("Только админ может редактировать категории.")
		return
	async with async_session_maker() as session:
		dao = DAO(session)
		categories = await dao.get_categories_by_restaurant(user.restaurant_id)
	if not categories:
		await message.answer("Нет категорий для редактирования.")
		return
	kb = InlineKeyboardMarkup(
		inline_keyboard=[[InlineKeyboardButton(text=f"📂 {c.name}", callback_data=f"editcat_{c.id}")] for c in categories]
	)
	await message.answer("Выберите категорию для редактирования:", reply_markup=kb)
	await state.set_state(CategoryEditStates.waiting_for_category)

@admin_router.message(CategoryCreateStates.waiting_for_name)
async def category_create_name(message: Message, state: FSMContext, user):
	async with async_session_maker() as session:
		dao = DAO(session)
		category = await dao.create_category(message.text, user.restaurant_id)
	await message.answer(f"Категория '{category.name}' успешно создана!")
	await state.clear()


@admin_router.callback_query(F.data.startswith("delcat_"))
async def delete_category_callback(call: CallbackQuery, *, user):
	if not user or user.role != "admin":
		await call.answer("Нет прав", show_alert=True)
		return
	cat_id = int(call.data.split("_")[1])
	async with async_session_maker() as session:
		dao = DAO(session)
		categories = await dao.get_categories_by_restaurant(user.restaurant_id)
		category = next((c for c in categories if c.id == cat_id), None)
		if not category:
			await call.answer("Нет такой категории", show_alert=True)
			return
		await session.delete(category)
		await session.commit()
	await call.message.edit_text("Категория удалена.")



@admin_router.callback_query(F.data.startswith("editcat_"), CategoryEditStates.waiting_for_category)
async def category_edit_choose(call: CallbackQuery, state: FSMContext, *, user):
    cat_id = int(call.data.split("_")[1])
    await state.update_data(edit_id=cat_id)
    await call.message.answer("Введите новое название категории:")
    await state.set_state(CategoryEditStates.waiting_for_new_name)
    await call.answer()

@admin_router.message(CategoryEditStates.waiting_for_new_name)
async def category_edit_new_name(message: Message, state: FSMContext, user):
	data = await state.get_data()
	async with async_session_maker() as session:
		dao = DAO(session)
		category = await dao.get_category_by_id(data["edit_id"])
		if category and category.restaurant_id == user.restaurant_id:
			category.name = message.text
			await session.commit()
			await session.refresh(category)
			await message.answer(f"Категория обновлена: {category.name}")
		else:
			await message.answer("Ошибка: категория не найдена или нет доступа.")
	await state.clear()
# --------------------- СОЗДАНИЕ И РЕДАКТИРОВАНИЕ БЛЮДА ---------------------------------------------------------------------------


# --- СОЗДАНИЕ БЛЮДА ---

# --- РЕДАКТИРОВАНИЕ БЛЮДА ---
@admin_router.message(F.text.lower() == "🍽️ блюдо")
async def dish_edit_start(message: Message, state: FSMContext, user):
	if not user or user.role != "admin":
		await message.answer("Только админ может редактировать блюда.")
		return
	async with async_session_maker() as session:
		dao = DAO(session)
		dishes = await dao.get_dishes_by_restaurant(user.restaurant_id)
	if not dishes:
		await message.answer("Нет блюд для редактирования.")
		return
	kb = InlineKeyboardMarkup(
		inline_keyboard=[[InlineKeyboardButton(text=f"🍽️ {d.name}", callback_data=f"editdish_{d.id}")] for d in dishes]
	)
	await message.answer("Выберите блюдо для редактирования:", reply_markup=kb)
	await state.set_state(DishEditStates.waiting_for_id)

@admin_router.callback_query(F.data.startswith("editdish_"), DishEditStates.waiting_for_id)
async def dish_edit_choose(call: CallbackQuery, state: FSMContext, *, user):
	dish_id = int(call.data.split("_")[1])
	await state.update_data(edit_id=dish_id)
	async with async_session_maker() as session:
		dao = DAO(session)
		dish = await dao.get_dish_by_id(dish_id)
	if not dish or dish.restaurant_id != user.restaurant_id:
		await call.message.answer("Блюдо не найдено или нет доступа.")
		await state.clear()
		await call.answer()
		return
	await call.message.answer(f"Текущее название: {dish.name}\nВведите новое название:")
	await state.set_state(DishEditStates.waiting_for_name)
	await call.answer()


@admin_router.message(DishEditStates.waiting_for_name)
async def dish_edit_name(message: Message, state: FSMContext, user):
	data = await state.get_data()
	await state.update_data(name=message.text)
	# Показываем inline-кнопки с категориями
	async with async_session_maker() as session:
		dao = DAO(session)
		categories = await dao.get_categories_by_restaurant(user.restaurant_id)
	if not categories:
		await message.answer("Нет категорий. Сначала создайте категорию!")
		await state.clear()
		return
	kb = InlineKeyboardMarkup(
		inline_keyboard=[
			[InlineKeyboardButton(text=f"📂 {c.name}", callback_data=f"choosecat_{c.id}") for c in categories]
		]
	)
	await message.answer("Выберите категорию для блюда:", reply_markup=kb)
	await state.set_state(DishEditStates.waiting_for_category)



# Выбор категории через inline-кнопку
@admin_router.callback_query(F.data.startswith("choosecat_"), DishEditStates.waiting_for_category)
async def dish_choose_category(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split("_")[1])
    await state.update_data(category_id=cat_id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dish")]
        ]
    )
    await call.message.answer(
        "Введите ингредиенты через запятую (например: 'картофель, мясо, соль, перец'):",
        reply_markup=kb
    )
    await state.set_state(DishEditStates.waiting_for_composition)
    await call.answer()


@admin_router.callback_query(F.data == "cancel_dish", DishEditStates.waiting_for_composition)
async def cancel_dish_creation(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Создание блюда отменено.")
    await call.answer()


@admin_router.message(DishEditStates.waiting_for_composition)
async def dish_edit_composition(message: Message, state: FSMContext):
	await state.update_data(composition=message.text)
	await message.answer("Введите описание блюда:")
	await state.set_state(DishEditStates.waiting_for_description)


@admin_router.message(DishEditStates.waiting_for_description)
async def dish_edit_description(message: Message, state: FSMContext):
	await state.update_data(description=message.text)
	await message.answer("Отправьте фото ингредиентов блюда:")
	await state.set_state(DishEditStates.waiting_for_ingredients_photo)


@admin_router.message(DishEditStates.waiting_for_video)
async def dish_edit_video(message: Message, state: FSMContext, user):
	data = await state.get_data()
	video_url = None
	if message.video:
		video_url = message.video.file_id
	elif message.text and message.text.lower() == "нет":
		video_url = None
	else:
		await message.answer("Пожалуйста, отправьте видео или напишите 'нет'.")
		return
	async with async_session_maker() as session:
		dao = DAO(session)
		if "edit_id" in data:
			dish = await dao.get_dish_by_id(data["edit_id"])
			if dish and dish.restaurant_id == user.restaurant_id:
				dish.name = data["name"]
				dish.category_id = data["category_id"]
				dish.composition = data["composition"]
				dish.description = data["description"]
				dish.video_url = video_url
				await session.commit()
				await message.answer(f"Блюдо обновлено: {dish.name}")
			else:
				await message.answer("Ошибка: блюдо не найдено или нет доступа.")
		else:
			await dao.create_dish(
				name=data["name"],
				category_id=data["category_id"],
				restaurant_id=user.restaurant_id,
				composition=data["composition"],
				description=data["description"],
				video_url=video_url
			)
			await message.answer(f"Блюдо '{data['name']}' успешно создано!")
	await state.clear()

	# ----------- Хендлеры для генерации видео из фото и аудио, отправки в тех. группу и сохранения file_id -----------


@admin_router.message(DishEditStates.waiting_for_ingredients_photo)
async def dish_edit_ingredients_photo(message: Message, state: FSMContext):
	if not message.photo:
		await message.answer("Пожалуйста, отправьте фото ингредиентов блюда.")
		return
	photo = message.photo[-1]
	file_id = photo.file_id
	bot = message.bot
	file = await bot.get_file(file_id)
	with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
		await bot.download(file, f)
		await state.update_data(ingredients_photo_path=f.name)
	await message.answer("Фото ингредиентов получено. Теперь отправьте фото готового блюда:")
	await state.set_state(DishEditStates.waiting_for_ready_photo)

@admin_router.message(DishEditStates.waiting_for_ready_photo)
async def dish_edit_ready_photo(message: Message, state: FSMContext):
	if not message.photo:
		await message.answer("Пожалуйста, отправьте фото готового блюда.")
		return
	photo = message.photo[-1]
	file_id = photo.file_id
	bot = message.bot
	file = await bot.get_file(file_id)
	with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
		await bot.download(file, f)
		await state.update_data(ready_photo_path=f.name)
	await message.answer("Фото готового блюда получено. Теперь отправьте аудиофайл (mp3):")
	await state.set_state(DishEditStates.waiting_for_audio)

@admin_router.message(DishEditStates.waiting_for_audio)
async def dish_edit_audio(message: Message, state: FSMContext, user):
	audio = message.audio or message.document
	if not audio:
		await message.answer("Пожалуйста, отправьте аудиофайл (mp3).")
		return
	file_id = audio.file_id
	bot = message.bot
	file = await bot.get_file(file_id)
	with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
		await bot.download(file, f)
		await state.update_data(audio_path=f.name)
	await message.answer("Аудио получено. Генерирую видео...")
	data = await state.get_data()
	# Генерация видео из фото ингредиентов
	with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as vf:
		make_video_from_image_and_audio(data["ingredients_photo_path"], data["audio_path"], vf.name)
		video_path = vf.name
	# Формируем карточку блюда (фото готового блюда)
	dish_card = {
		"name": data.get("name", "Блюдо"),
		"description": data.get("description", ""),
		"ingredients": data.get("composition", ""),
		"photo_path": data.get("ready_photo_path"),
		"video_path": video_path
	}
	# Сохраняем блюдо в базу
	async with async_session_maker() as session:
		dao = DAO(session)
		await dao.create_dish(
			name=data.get("name", "Блюдо"),
			category_id=data.get("category_id"),
			restaurant_id=user.restaurant_id,
			composition=data.get("composition", ""),
			description=data.get("description", ""),
			video_url=video_path,
			ingredients_photo_url=data.get("ingredients_photo_path"),
			ready_photo_url=data.get("ready_photo_path")
		)
	from bot.utils import send_dish_card_to_tech_group
	await send_dish_card_to_tech_group(message.bot, dish_card)
	await message.answer("Карточка блюда успешно создана, фото и видео сохранены!")
	await state.clear()


# --- Добавление категории через inline ---
@admin_router.callback_query(F.data == "add_category")
async def add_category_inline(call: CallbackQuery, state: FSMContext, *, user):
	await call.message.answer("Введите название новой категории:")
	await state.set_state(CategoryCreateStates.waiting_for_name)
	await call.answer()

# --- Добавление блюда через inline ---
@admin_router.callback_query(F.data == "add_dish")
async def add_dish_inline(call: CallbackQuery, state: FSMContext, *, user):
	await call.message.answer("Введите название нового блюда:")
	await state.set_state(DishEditStates.waiting_for_name)
	await call.answer()

@admin_router.message(F.text.lower() == "🤝 сделать приглашение")
async def invite_waiter_button(message: Message, user):
	if not user or user.role != "admin":
		await message.answer("Только админ может приглашать официантов.")
		return
	token = secrets.token_urlsafe(16)
	await invite_service.create_token(token, user.restaurant_id, ttl=900)
	bot_username = (await message.bot.me()).username
	invite_link = f"https://t.me/{bot_username}?start={token}"
	print(f"Сгенерирована ссылка приглашения: {invite_link}")
	kb = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="Пригласить официанта", url=invite_link)]
	])
	await message.answer(
		"Ссылка для приглашения официанта (действует 15 минут):",
		reply_markup=kb
	)

@admin_router.message(F.text.lower() == "🧑‍🤝‍🧑 штат")
async def show_waiters(message: Message, user):
    if not user or user.role != "admin":
        await message.answer("Только админ может просматривать официантов.")
        return
    async with async_session_maker() as session:
        dao = DAO(session)
        waiters = await dao.get_users_by_role("waiter")
        waiters = [w for w in waiters if w.restaurant_id == user.restaurant_id]
    if not waiters:
        await message.answer("В вашем ресторане нет официантов.")
        return
    for w in waiters:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delwaiter_{w.id}")]
        ])
        await message.answer(f"{w.first_name} {w.last_name} (@{w.tg_username or '-'}), id: {w.id}", reply_markup=kb)
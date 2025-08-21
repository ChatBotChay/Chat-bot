import secrets
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards.reply import get_keyboard
from database.dao import DAO
from database.engine import async_session_maker
from database.invite_token_service import InviteTokenService

super_admin_router = Router()

super_admin_kb = get_keyboard(
	"Создать ресторан",
	"Сделать администратора",
	sizes=(1, 1)
)

class CreateRestaurantStates(StatesGroup):
	waiting_for_name = State()


@super_admin_router.message(CommandStart())
async def superadmin_start(message: Message, state: FSMContext, user):
	if not user or user.role != "superadmin":
		await message.answer("У вас нет доступа к этому разделу.")
		return
	await message.answer("Вы вошли как супер-админ.", reply_markup=super_admin_kb)


@super_admin_router.message(F.text.lower() == "создать ресторан")
async def create_restaurant_start(message: Message, state: FSMContext, user):
	if not user or user.role != "superadmin":
		await message.answer("Только супер-админ может создавать рестораны.")
		return
	await message.answer("Введите название нового ресторана:")
	await state.set_state(CreateRestaurantStates.waiting_for_name)


@super_admin_router.message(CreateRestaurantStates.waiting_for_name)
async def create_restaurant_name(message: Message, state: FSMContext, user):
	async with async_session_maker() as session:
		dao = DAO(session)
		restaurant = await dao.create_restaurant(message.text)
	await message.answer(f"Ресторан '{restaurant.name}' создан! Теперь вы можете пригласить администратора.", reply_markup=super_admin_kb)
	await state.clear()


# Приглашение администратора ресторана по ссылке
@super_admin_router.message(F.text.lower() == "сделать администратора")
async def invite_admin(message: Message, user):
	if not user or user.role != "superadmin":
		await message.answer("Только супер-админ может приглашать админов.")
		return
	await message.answer("Введите ID ресторана, для которого нужен админ:")


@super_admin_router.message(lambda m: m.text and m.text.isdigit() and len(m.text) < 10)
async def invite_admin_token(message: Message, user):
	if not user or user.role != "superadmin":
		return
	restaurant_id = int(message.text)
	token = secrets.token_urlsafe(16)
	invite_service = InviteTokenService()
	await invite_service.create_token(token, restaurant_id, ttl=900)
	bot_username = (await message.bot.me()).username
	invite_link = f"https://t.me/{bot_username}?start={token}"
	kb = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="Стать администратором ресторана", url=invite_link)]
	])
	await message.answer(
		f"Ссылка для приглашения администратора ресторана (ID {restaurant_id}, действует 15 минут):",
		reply_markup=kb
	)


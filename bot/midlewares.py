from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Dict, Any
from database.dao import DAO
from database.engine import async_session_maker

class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        # Для Message и CallbackQuery
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        if user_id:
            async with async_session_maker() as session:
                dao = DAO(session)
                user = await dao.get_user_by_tg_id(str(user_id))
                data["user"] = user
        return await handler(event, data)

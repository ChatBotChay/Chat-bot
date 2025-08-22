import asyncio
from database.engine import async_session_maker
from database.models import Restaurant, User

async def main():
    async with async_session_maker() as session:
        # --- Задайте свои значения ниже ---
        restaurant = Restaurant(name="Мой ресторан")
        session.add(restaurant)
        await session.flush()  # Получить restaurant.id

        admin = User(
            first_name="Анатолий",
            last_name="Козьмин",
            tg_username="anatolykozmin",
            tg_id="8291139087",
            role="admin",
            restaurant_id=restaurant.id
        )
        session.add(admin)
    await session.commit()
    rest_id = restaurant.id
    admin_id = admin.id
    print(f"Ресторан и админ добавлены: {rest_id}, {admin_id}")

if __name__ == "__main__":
    asyncio.run(main())

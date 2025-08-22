import asyncio
from database.engine import async_session_maker
from database.models import Restaurant, User

async def main():
    async with async_session_maker() as session:

        restaurant = Restaurant(name="Первый")
        session.add(restaurant)
        await session.flush() 


        admin = User(
            first_name="Анатолий",
            last_name="К",
            tg_username="yanejettt",
            tg_id="922109605",
            role="admin",
            restaurant_id=restaurant.id
        )
        session.add(admin)
        await session.commit()
        print(f"Ресторан и админ добавлены: {restaurant.id}, {admin.id}")

if __name__ == "__main__":
    asyncio.run(main())
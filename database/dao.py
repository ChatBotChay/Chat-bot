from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Restaurant, Category, Dish, TestResult

class DAO:
    async def get_user_by_id(self, user_id):
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def delete_user(self, user_id):
        user = await self.get_user_by_id(user_id)
        if user:
            await self.session.delete(user)
            await self.session.commit()
    def __init__(self, session: AsyncSession):
        self.session = session

    # User methods
    async def create_user(self, first_name, last_name, tg_username, tg_id, role, restaurant_id=None):
        f"""

        Args:
            first_name (_type_): 
            last_name (_type_): 
            tg_username (_type_): 
            tg_id (_type_):
            role (_type_): 
            restaurant_id (_type_, optional): 

        Returns:
            _type_: 
        """        

        user = User(
            first_name=first_name,
            last_name=last_name,
            tg_username=tg_username,
            tg_id=tg_id,
            role=role,
            restaurant_id=restaurant_id
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_by_tg_id(self, tg_id):

        f"""

        Returns:
            _type_: _description_
        """        
        result = await self.session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()

    async def get_users_by_role(self, role):
        f"""

        Args:
            role (_type_): _description_

        Returns:
            _type_: _description_
        """        
        result = await self.session.execute(select(User).where(User.role == role))
        return result.scalars().all()

    # Restaurant methods
    async def create_restaurant(self, name):
        f"""

        Args:
            name (_type_): _description_

        Returns:
            _type_: _description_
        """        
        restaurant = Restaurant(name=name)
        self.session.add(restaurant)
        await self.session.commit()
        await self.session.refresh(restaurant)
        return restaurant

    async def get_restaurant(self, restaurant_id):
        f"""

        Args:
            restaurant_id (_type_): _description_

        Returns:
            _type_: _description_
        """        
        result = await self.session.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
        return result.scalar_one_or_none()

    async def get_all_restaurants(self):
        f"""

        Returns:
            _type_: _description_
        """        
        result = await self.session.execute(select(Restaurant))
        return result.scalars().all()


# ----------------Category methods. --------------------------------------------------------------------------------->
    async def get_category_by_id(self, category_id):
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()
    async def create_category(self, name, restaurant_id):
        f"""

        Args:
            name (_type_): _description_
            restaurant_id (_type_): _description_

        Returns:
            _type_: _description_
        """        
        category = Category(name=name, restaurant_id=restaurant_id)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category


    async def get_categories_by_restaurant(self, restaurant_id):
        f"""

        Args:
            restaurant_id (_type_): _description_

        Returns:
            _type_: _description_
        """        

        result = await self.session.execute(select(Category).where(Category.restaurant_id == restaurant_id))
        return result.scalars().all()


# ------------------- Dish methods --------------------------------------------------------------------------------->
    async def get_dish_by_id(self, dish_id):
        result = await self.session.execute(select(Dish).where(Dish.id == dish_id))
        return result.scalar_one_or_none()
    async def create_dish(self, name, category_id, restaurant_id, composition=None, cook_time=None, video_url=None, description=None, ingredients_photo_url=None, ready_photo_url=None):
        f"""

        Args:
            name (_type_): _description_
            category_id (_type_): _description_
            restaurant_id (_type_): _description_
            composition (_type_, optional): _description_. Defaults to None.
            cook_time (_type_, optional): _description_. Defaults to None.
            video_url (_type_, optional): _description_. Defaults to None.
            description (_type_, optional): _description_. Defaults to None.
            ingredients_photo_url (_type_, optional): _description_. Defaults to None.
            ready_photo_url (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """       

        dish = Dish(
            name=name,
            category_id=category_id,
            restaurant_id=restaurant_id,
            composition=composition,
            cook_time=cook_time,
            video_url=video_url,
            description=description,
            ingredients_photo_url=ingredients_photo_url,
            ready_photo_url=ready_photo_url
        )
        self.session.add(dish)
        await self.session.commit()
        await self.session.refresh(dish)
        return dish


    async def get_dishes_by_category(self, category_id):
        f"""

        Args:
            category_id (_type_): _description_

        Returns:
            _type_: _description_
        """     

        result = await self.session.execute(select(Dish).where(Dish.category_id == category_id))
        return result.scalars().all()


    async def get_dishes_by_restaurant(self, restaurant_id):
        f"""

        Args:
            restaurant_id (_type_): _description_

        Returns:
            _type_: _description_
        """        
        result = await self.session.execute(select(Dish).where(Dish.restaurant_id == restaurant_id))
        return result.scalars().all()


# ------------------- TestResult methods. --------------------------------------------------------------------------------->
    async def add_test_result(self, user_id, score, passed_at=None):
        f"""

        Args:
            user_id (_type_): _description_
            score (_type_): _description_
            passed_at (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """        
        test_result = TestResult(user_id=user_id, score=score, passed_at=passed_at)
        self.session.add(test_result)
        await self.session.commit()
        await self.session.refresh(test_result)
        return test_result

    async def get_test_results_by_user(self, user_id):
        f"""

        Args:
            user_id (_type_): _description_

        Returns:
            _type_: _description_
        """        
        result = await self.session.execute(select(TestResult).where(TestResult.user_id == user_id))
        return result.scalars().all()
    
    async def set_dish_video_file_id(self, dish_id: int, video_file_id: str):
        dish = await self.get_dish_by_id(dish_id)
        if dish:
            dish.video_file_id = video_file_id
            await self.session.commit()
            return True
        return False

    async def get_dish_video_file_id(self, dish_id: int) -> str | None:
        dish = await self.get_dish_by_id(dish_id)
        if dish:
            return dish.video_file_id
        return None

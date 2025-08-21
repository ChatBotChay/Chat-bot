from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float
from sqlalchemy.orm import relationship, declarative_base

from database.engine import Base


class Restaurant(Base):
	__tablename__ = "restaurants"
	id = Column(Integer, primary_key=True)
	name = Column(String, nullable=False)
	admins = relationship("User", back_populates="restaurant", cascade="all, delete-orphan")
	categories = relationship("Category", back_populates="restaurant", cascade="all, delete-orphan")
	dishes = relationship("Dish", back_populates="restaurant", cascade="all, delete-orphan")


class User(Base):
	__tablename__ = "users"
	id = Column(Integer, primary_key=True)
	first_name = Column(String, nullable=False)
	last_name = Column(String, nullable=False)
	tg_username = Column(String, nullable=True)
	tg_id = Column(String, nullable=True)
	role = Column(String, nullable=False)  # waiter, admin, superadmin
	restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
	restaurant = relationship("Restaurant", back_populates="admins")
	test_results = relationship("TestResult", back_populates="user", cascade="all, delete-orphan")


class Category(Base):
	__tablename__ = "categories"
	id = Column(Integer, primary_key=True)
	name = Column(String, nullable=False)
	restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
	restaurant = relationship("Restaurant", back_populates="categories")
	dishes = relationship("Dish", back_populates="category", cascade="all, delete-orphan")


class Dish(Base):
	__tablename__ = "dishes"
	id = Column(Integer, primary_key=True)
	name = Column(String, nullable=False)
	category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
	restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
	composition = Column(Text, nullable=True)
	description = Column(Text, nullable=True)  # Описание блюда для озвучки
	cook_time = Column(Float, nullable=True)
	video_url = Column(String, nullable=True)
	ingredients_photo_url = Column(String, nullable=True)  # Фото ингредиентов
	ready_photo_url = Column(String, nullable=True)        # Фото готового блюда
	category = relationship("Category", back_populates="dishes")
	restaurant = relationship("Restaurant", back_populates="dishes")


class TestResult(Base):
	__tablename__ = "test_results"
	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	score = Column(Integer, nullable=False)
	passed_at = Column(String, nullable=True) 
	user = relationship("User", back_populates="test_results")

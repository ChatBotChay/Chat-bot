import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

from typing import Optional

class Settings(BaseSettings):
    BOT_TOKEN: Optional[str] = os.getenv('BOT_TOKEN')
    DB_URL: Optional[str] = os.getenv('DATABASE_URL') or os.getenv('DOCKER_DB_URL')
    TECH_GROUP: Optional[str] = os.getenv('TECH_GROUP')

settings = Settings()

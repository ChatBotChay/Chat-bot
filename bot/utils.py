async def send_dish_card_to_tech_group(bot, dish: dict):
    """
    Отправляет карточку блюда в тех. группу.
    dish: dict с ключами name, description, ingredients, photo_path, video_path (опционально)
    """
    tech_group_id = settings.TECH_GROUP
    if not tech_group_id:
        raise ValueError("TECH_GROUP не задан в .env")
    text = f"🍽 <b>{dish['name']}</b>\n\n"
    if dish.get('description'):
        text += f"<i>{dish['description']}</i>\n\n"
    if dish.get('ingredients'):
        text += f"Ингредиенты: {dish['ingredients']}\n\n"
    from aiogram.types.input_file import FSInputFile
    if dish.get('video_path'):
        media = FSInputFile(dish['video_path'])
        msg = await bot.send_video(chat_id=int(tech_group_id), video=media, caption=text, parse_mode="HTML")
    elif dish.get('photo_path'):
        media = FSInputFile(dish['photo_path'])
        msg = await bot.send_photo(chat_id=int(tech_group_id), photo=media, caption=text, parse_mode="HTML")
    else:
        msg = await bot.send_message(chat_id=int(tech_group_id), text=text, parse_mode="HTML")
    return msg.message_id
# async def send_dish_card_to_tech_group(bot, dish: dict):
    """
    Отправляет карточку блюда в тех. группу.
    dish: dict с ключами name, description, ingredients, photo_path, video_path (опционально)
    """
    tech_group_id = settings.TECH_GROUP
    if not tech_group_id:
        raise ValueError("TECH_GROUP не задан в .env")
    text = f"🍽 <b>{dish['name']}</b>\n\n"
    if dish.get('description'):
        text += f"<i>{dish['description']}</i>\n\n"
    if dish.get('ingredients'):
        text += f"Ингредиенты: {dish['ingredients']}\n\n"
    from aiogram.types.input_file import FSInputFile
    if dish.get('video_path'):
        media = FSInputFile(dish['video_path'])
        msg = await bot.send_video(chat_id=int(tech_group_id), video=media, caption=text, parse_mode="HTML")
    elif dish.get('photo_path'):
        media = FSInputFile(dish['photo_path'])
        msg = await bot.send_photo(chat_id=int(tech_group_id), photo=media, caption=text, parse_mode="HTML")
    else:
        msg = await bot.send_message(chat_id=int(tech_group_id), text=text, parse_mode="HTML")
    return msg.message_id
import os
from moviepy.video.VideoClip import ImageClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from config import settings

def make_video_from_image_and_audio(image_path: str, audio_path: str, output_path: str, duration: int = None):
    """
    Создаёт видео из картинки и аудио.
    image_path: путь к картинке
    audio_path: путь к аудиофайлу
    output_path: путь для сохранения mp4
    duration: длительность видео (если None — берётся длительность аудио)
    """
    audio = AudioFileClip(audio_path)
    img = ImageClip(image_path)
    if duration is None:
        duration = audio.duration
    img = img.with_duration(duration)
    img = img.with_audio(audio)
    img = img.with_fps(24)
    img.write_videofile(output_path, codec="libx264", audio_codec="aac")
    return output_path

async def send_video_to_tech_group(bot, video_path: str):
    """
    Отправляет видео в техническую группу.
    bot: экземпляр aiogram.Bot
    video_path: путь к mp4
    """
    tech_group_id = settings.TECH_GROUP
    if not tech_group_id:
        raise ValueError("TECH_GROUP не задан в .env")
    from aiogram.types.input_file import FSInputFile
    input_file = FSInputFile(video_path)
    msg = await bot.send_video(chat_id=int(tech_group_id), video=input_file)
    return msg.video.file_id

# Пример использования:
# video_id = await send_video_to_tech_group(bot, output_path)
# Сохрани video_id в базу данных блюда для быстрого доступа пользователям

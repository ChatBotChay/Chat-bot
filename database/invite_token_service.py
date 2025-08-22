import os
from database.redis_queue import RedisQueue

class InviteTokenService:
    def __init__(self):
        self.queue = RedisQueue("waiter_invites")

    async def create_token(self, token: str, restaurant_id: int, ttl: int = 900):
        await self.queue.connect()
        await self.queue.redis.setex(f"invite:{token}", ttl, str(restaurant_id))
        await self.queue.close()

    async def get_restaurant_id(self, token: str):
        await self.queue.connect()
        restaurant_id = await self.queue.redis.get(f"invite:{token}")
        print(f"Проверка токена: invite:{token} -> {restaurant_id}")
        await self.queue.close()
        return restaurant_id

    async def delete_token(self, token: str):
        await self.queue.connect()
        await self.queue.redis.delete(f"invite:{token}")
        await self.queue.close()

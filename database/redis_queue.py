import redis.asyncio as aioredis
import os
import json

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class RedisQueue:
    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.redis = None

    async def connect(self):
        self.redis = aioredis.from_url(REDIS_URL, decode_responses=True)

        async def enqueue(self, data: dict):
            await self.redis.rpush(self.queue_name, json.dumps(data))

        async def dequeue(self):
            task = await self.redis.blpop(self.queue_name, timeout=5)
            if task:
                _, data = task
                return json.loads(data)
            return None

    async def close(self):
        if self.redis:
            await self.redis.close()

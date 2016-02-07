import os
import pymongo

from motor.motor_asyncio import AsyncIOMotorClient


client = AsyncIOMotorClient(host=os.environ.get("MONGO_HOST"))
db = client.music


def text_search(query):
    return db.tracks.find(
        { '$text': { '$search': query } },
        { 'score': { '$meta': 'textScore' } }
    ).sort([('score', {'$meta': 'textScore'})])


async def prepare_index():
    await db.tracks.create_index([
        ("title", pymongo.TEXT),
        ("performer", pymongo.TEXT)
    ])
    await db.tracks.create_index([
        ("file_id", pymongo.ASCENDING)
    ])
    await db.users.create_index("id")

import os
import logging
import pymongo
import asyncio
import json
import math

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import timedelta
from aiotg import TgBot

greeting = """
    ✋ Welcome to Telegram Music Catalog! 🎧
We are a community of music fans who are eager to share what we love.
Just send your favourite tracks as audio files and they'll be available for everyone, on any device.
To search through the catalog, just type artist name or track title. Nothing found? Feel free to fix it!
"""

help = """
To search through the catalog, just type artist name or track title.
Inside a group chat you can use /music command, for example:
/music Summer of Haze

By default, the search is fuzzy but you can use double quotes to filter results:
"summer of haze"
"sad family"

To make an even stricter search, just quote both terms:
"aes dana" "haze"
"""

not_found = """
We don't have anything matching your search yet :/
But you can fix it by sending us the tracks you love as audio files!
"""

with open("config.json") as cfg:
    config = json.load(cfg)


bot = TgBot(**config)
logger = logging.getLogger("musicbot")
client = AsyncIOMotorClient(host=os.environ.get("MONGO_HOST"))
db = client.music


@bot.handle("audio")
async def add_track(chat, audio):
    if (await db.tracks.find_one({ "file_id": audio["file_id"] })):
        return

    if "title" not in audio:
        await chat.send_text("Sorry, but your track is missing title")
        return

    doc = audio.copy()
    doc["sender"] = chat.sender["id"]
    await db.tracks.insert(doc)

    logger.info("%s added %s %s",
        chat.sender, doc.get("performer"), doc.get("title"))


@bot.command(r'@%s (.+)' % bot.name)
@bot.command(r'/music@%s (.+)' % bot.name)
@bot.command(r'/music (.+)')
def music(chat, match):
    return search_tracks(chat, match.group(1))


@bot.command(r'\((\d+)/\d+\) show more for "(.+)"')
def more(chat, match):
    page = int(match.group(1)) + 1
    return search_tracks(chat, match.group(2), page)


@bot.default
def default(chat, message):
    return search_tracks(chat, message["text"])


@bot.command(r'/music(@%s)?$' % bot.name)
def usage(chat, match):
    return chat.send_text(greeting)


@bot.command(r'/start')
def start(chat, match):
    tuid = chat.sender["id"]
    if not db.users.find_one({ "id": tuid }):
        logger.info("new user %s", chat.sender)
        db.users.insert_one(chat.sender.copy())

    return chat.send_text(greeting)


@bot.command(r'/stop')
def stop(chat, match):
    tuid = chat.sender["id"]
    db.users.delete_one({ "id": tuid })
    logger.info("%s quit", chat.sender)
    return chat.send_text("Goodbye! We will miss you 😢")


@bot.command(r'/?help')
def usage(chat, match):
    return chat.send_text(help)


@bot.command(r'/stats')
async def stats(chat, match):
    count = await db.tracks.count()
    group = {
        "$group": {
            "_id": None,
            "size": {"$sum": "$file_size"}
        }
    }
    cursor = db.tracks.aggregate([group])
    aggr = await cursor.to_list(1)

    if len(aggr) == 0:
        return (await chat.send_text("Stats are not yet available"))

    size = human_size(aggr[0]["size"])
    text = '%d tracks, %s' % (count, size)

    return (await chat.send_text(text))


def human_size(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    rank = int((math.log10(nbytes)) / 3)
    rank = min(rank, len(suffixes) - 1)
    human = nbytes / (1024.0 ** rank)
    f = ('%.2f' % human).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[rank])


def send_track(chat, keyboard, track):
    return chat.send_audio(
        audio=track["file_id"],
        title=track.get("title"),
        performer=track.get("performer"),
        duration=track.get("duration"),
        reply_markup=json.dumps(keyboard)
    )


def search_db(query):
    return db.tracks.find(
        { '$text': { '$search': query } },
        { 'score': { '$meta': 'textScore' } }
    ).sort([('score', {'$meta': 'textScore'})])


async def search_tracks(chat, query, page=1):
    logger.info("%s searching for %s", chat.sender, query)

    limit = 3
    offset = (page - 1) * limit

    cursor = search_db(query).skip(offset).limit(limit)
    results = await cursor.to_list(limit)

    if len(results) == 0:
        await chat.send_text(not_found)
        return

    # Return single result if we have exact match for title and performer
    if results[0]['score'] >= 2:
        limit = 1
        results = results[:1]

    newoff = offset + limit
    show_more = len(results) > newoff

    if show_more:
        pages = math.ceil(len(results) / limit)
        kb = [['(%d/%d) Show more for "%s"' % (page, pages, query)]]
        keyboard = {
            "keyboard": kb,
            "resize_keyboard": True
        }
    else:
        keyboard = { "hide_keyboard": True }

    for track in results:
        await send_track(chat, keyboard, track)


async def prepare_index():
    await db.tracks.create_index([
        ("title", pymongo.TEXT),
        ("performer", pymongo.TEXT)
    ])
    await db.tracks.create_index([
        ("file_id", pymongo.ASCENDING)
    ])
    await db.users.create_index("id")


async def main():
    await prepare_index()
    await bot.loop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

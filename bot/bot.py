import os
import logging
import json
import math

from aiotg import Bot
from database import db, text_search

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


bot = Bot(
    api_token=os.environ.get("API_TOKEN"),
    name=os.environ.get("BOT_NAME"),
    botan_token=os.environ.get("BOTAN_TOKEN")
)
logger = logging.getLogger("musicbot")


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


@bot.inline
async def inline(iq):
    logger.info("%s searching for %s", iq.sender, iq.query)
    cursor = text_search(iq.query)
    results = [inline_result(t) for t in await cursor.to_list(10)]
    await iq.answer(results)


@bot.command(r'/music(@%s)?$' % bot.name)
def usage(chat, match):
    return chat.send_text(greeting)


@bot.command(r'/start')
async def start(chat, match):
    tuid = chat.sender["id"]
    if not (await db.users.find_one({ "id": tuid })):
        logger.info("new user %s", chat.sender)
        await db.users.insert(chat.sender.copy())

    await chat.send_text(greeting)


@bot.command(r'/stop')
async def stop(chat, match):
    tuid = chat.sender["id"]
    await db.users.remove({ "id": tuid })

    logger.info("%s quit", chat.sender)
    await chat.send_text("Goodbye! We will miss you 😢")


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


async def search_tracks(chat, query, page=1):
    logger.info("%s searching for %s", chat.sender, query)

    limit = 3
    offset = (page - 1) * limit

    cursor = text_search(query).skip(offset).limit(limit)
    count = await cursor.count()
    results = await cursor.to_list(limit)

    if count == 0:
        await chat.send_text(not_found)
        return

    # Return single result if we have exact match for title and performer
    if results[0]['score'] > 2:
        limit = 1
        results = results[:1]

    newoff = offset + limit
    show_more = count > newoff

    if show_more:
        pages = math.ceil(count / limit)
        kb = [['(%d/%d) Show more for "%s"' % (page, pages, query)]]
        keyboard = {
            "keyboard": kb,
            "resize_keyboard": True
        }
    else:
        keyboard = { "hide_keyboard": True }

    for track in results:
        await send_track(chat, keyboard, track)


def inline_result(track):
    return {
        "type": "audio",
        "id": track["file_id"],
        "audio_file_id": track["file_id"],
        "title": "{} - {}".format(
            track.get("performer", "Unknown Artist"),
            track.get("title", "Untitled")
        )
    }

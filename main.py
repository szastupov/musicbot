import logging
import asyncio

from bot import bot
from rest import RestBridge
from database import prepare_index

rest = RestBridge(bot)

async def start():
    await prepare_index()
    await rest.start()
    await bot.loop()


async def stop():
    await rest.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(stop())

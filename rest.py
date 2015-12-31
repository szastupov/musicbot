import asyncio
import aiohttp
import logging

from aiohttp import web
from database import db, text_search


logger = logging.getLogger("rest")
chunk_size = 8192


class RestBridge:
    def __init__(self, bot):
        self.bot = bot

        app = aiohttp.web.Application()
        app.router.add_route('GET', '/tracks', self.search)
        app.router.add_route('GET', '/files/{file_id}', self.download_file)

        self.app = app
        self.handler = app.make_handler()

    async def search(self, request):
        text = request.GET.get("text")
        offset = request.GET.get("offset", 0)
        limit = request.GET.get("limit", 10)

        cursor = text_search(text) if text else db.tracks.find({})

        cursor = cursor.skip(offset).limit(limit)
        results = await cursor.to_list(limit)
        for r in results:
            del r["_id"]
        return web.json_response(results)

    async def download_file(self, request):
        file_id = request.match_info['file_id']

        record = await db.tracks.find_one({ "file_id": file_id })
        if not record:
            return web.HTTPNotFound()

        file = await self.bot.get_file(file_id)
        file_path = file["file_path"]

        resp = web.StreamResponse()
        resp.content_length = file["file_size"]
        resp.content_type = record["mime_type"]
        await resp.prepare(request)

        async with self.bot.download_file(file_path) as r:
            while True:
                chunk = await r.content.read(chunk_size)
                if not chunk:
                    break
                resp.write(chunk)

        return resp

    async def start(self):
        loop = asyncio.get_event_loop()
        srv = await loop.create_server(self.handler, '0.0.0.0', 8080)
        logger.info('serving REST on %s', srv.sockets[0].getsockname())
        self.srv = srv

    async def stop(self):
        await self.handler.finish_connections(1.0)
        self.srv.close()
        await self.srv.wait_closed()
        await self.app.finish()

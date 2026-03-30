import asyncio
from mpc import MpcClient
from mqtt import MqqtClient, ToggleEvent

from aiohttp import web
import aiohttp_cors
import db
from sqlalchemy import select
from sqlalchemy.orm import Session
import json
from adapter import PlayerAdapter, EndEvent, ProgressEvent, ChangeStatusEvent, Status, StartEvent

def buildPlayHandler(player: "Player"):
    async def play(requst: web.Request):
        q = requst.query.getall("q", None)
        p = int(requst.query.get("p", None))
        if q is None or p is None:
            return web.Response(status=400)
        await player.play(q, p)
        return web.Response(status=200)

    return play

def buildAddToQueueHandler(player: "Player"):
    async def play(requst: web.Request):
        q = requst.query.getall("q", None)
        if q is None:
            return web.Response(status=400)
        await player.add(q)
        return web.Response(status=200)

    return play

async def search(requst: web.Request):
    q = requst.query.get("q", "")
    with Session(db.engine) as session:
        tracks = session.scalars(select(db.Track))
        tracks_json = json.dumps([{
            "id": t.id,
            "title": t.title,
            "authors": [a.name for a in t.authors],
            "cover": f'http://27.0.0.1:8076/cover/{t.id}',
            "downloaded": t.isDownloaded,
        } for t in tracks])
        return web.Response(body=tracks_json.encode(), content_type="application/json")

async def cover(request: web.Request):
    trackId = request.match_info.get("track_id", "")
    if trackId == "":
        return web.Response(status=400)
    try:
        cover = open(f'cache/covers/{trackId}.png', "rb")
        resp = web.Response(body=cover.read(), content_type="image/png",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})
        cover.close()
        return resp
    except Exception as e:
        return web.Response(status=403)

async def info(request: web.Request):
    trackId = request.match_info.get("track_id", "")
    if trackId == "":
        return web.Response(status=400)
    with Session(db.engine) as session:
        track = session.scalar(select(db.Track).where(db.Track.id==trackId))
        if track is None:
            return web.Response(status=403)
        return web.Response(body=json.dumps({
            "id": trackId,
            "title": track.title,
            "authors": list(map(lambda artist: artist.name, track.authors)),
            "cover": f'http://127.0.0.1:8076/cover/{track.id}',
            "downloaded": track.isDownloaded,
            "total": (track.duration).__trunc__(),
        }), status=200)

class Player():
    client: PlayerAdapter | None = None
    queue: list[str] = ["128765032", "606570"]
    queuePos: int = 0
    mqttClient: MqqtClient | None = None

    def __init__(self, mpc: PlayerAdapter, mqttClient: MqqtClient):
        self.mqttClient = mqttClient
        self.mqttClient.onToggle.sub(self.toggle)
        self.mqttClient.onNext.sub(self.next)
        self.mqttClient.onPrev.sub(self.prev)
        self.client = mpc
        self.client.onEnd.sub(self.onEnd)
        self.client.onProgress.sub(self.onProgress)
        self.client.onChangeStatus.sub(self.onChangeStatus)

    async def onEnd(self, e: EndEvent):
        await self.next(ToggleEvent())

    async def onProgress(self, e: ProgressEvent):
        self.mqttClient.sendCurrent(e)

    async def onChangeStatus(self, e: ChangeStatusEvent):
        self.mqttClient.sendStatus(e.status.value)
        pass

    async def toggle(self, e: ToggleEvent):
        if self.client.getStatus() == Status.playing:
            await self.client.pause()
        elif self.client.getStatus() == Status.stopped:
            await self.client.cont()

    async def next(self, e: ToggleEvent):
        await self.play(self.queue, (self.queuePos + 1) % len(self.queue))

    async def prev(self, e: ToggleEvent):
        p = self.queuePos - 1
        if p < 0:
            p = len(self.queue) - 1
        await self.play(self.queue, p)


    async def play(self, q: list[str], p: int):
        if self.queue[self.queuePos] != q[p]:
            await self.client.play(q[p])
        self.queue = q
        self.queuePos = p
        self.mqttClient.sendQueue(q, p)

    async def add(self, q: list[str]):
        self.queue.extend(q)
        self.mqttClient.sendQueue(self.queue, self.queuePos)

async def main():
    mpc = MpcClient()
    m = MqqtClient()
    player = Player(mpc, m)
    app = web.Application()
    app.add_routes([web.get('/cover/{track_id}', cover)])
    app.add_routes([web.get('/info/{track_id}', info)])
    app.add_routes([web.get('/search', search)])
    app.add_routes([web.get('/play', buildPlayHandler(player))])
    app.add_routes([web.get("/add", buildAddToQueueHandler(player))])
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["POST", "GET", "OPTIONS"]
        )
    })

    for route in list(app.router.routes()):
        cors.add(route)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8076)
    await site.start()
    await mpc.loop()
    await runner.cleanup()

asyncio.run(main())

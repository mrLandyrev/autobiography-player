
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from yandex_music import Client
from sqlalchemy import select
from sqlalchemy.orm import Session
import contextlib
import asyncio
import pydantic
import db
import uuid
import time
import mpc

a = mpc.Client()

class FeedManager():
    def get_next(self) -> str:
        with Session(db.engine) as session:
            lastTrack = session.scalar(select(db.Listen).order_by(db.Listen.started_at.desc()).limit(1))
            if lastTrack is None:
                return "128765032"
            result = client.rotorStationTracks(f'track:{lastTrack.track_id}')
            if result is None:
                return "128765032"
            return result.sequence[1].track.id

class Player():
    def __init__(self):
        self.status: str = "empty"
        self.current: int = 0
        self.queue: list[str] = []
        self.queue_position: int = -1
        self.is_feed = True
    
    async def __update_status__(self):
        s = await a.get_status()
        if s is None:
            self.status = "empty"
            self.current = 0
            return
        self.status = s.status
        self.current = s.current
    
    def pause(self):
        if self.status != "empty":
            self.status = "paused"

    def cont(self):
        if self.status != "empty":
            self.status = "playing"

    async def play_playlist(self, queueId: str = "feed", position: int = -1, track: str = ""):
        if queueId == "feed":
            if position == -1:
                # play track
                if track == "":
                    return
                if self.is_feed:
                    self.queue = self.queue[0:self.queue_position+1]
                    self.queue.append(track)
                    self.queue_position = self.queue_position+1
                else:
                    self.queue = [track]
                    self.queue_position = 0
                self.is_feed = True
                await self.__play__(track)
                return
            self.queue_position = position
            await self.__play__(self.queue[self.queue_position])
            print("here")
            return
        with Session(db.engine) as session:
            queue = session.scalar(select(db.Playlist).where(db.Playlist==queueId))
            if queue is None or len(queue.tracks) == 0:
                return
            if position == -1:
                position = queue.position
            if position >= len(queue.tracks):
                position = 0
            self.queue = queue.tracks
            self.queue_position = position
            self.is_feed = False
            await self.__clear__()

    async def __play__(self, id: str):
        await self.__clear__()
        await a.play(id)
        with Session(db.engine) as session:
            l = db.Listen()
            l.id = str(uuid.uuid4())
            l.started_at = int(time.time())
            l.track_id = id
            session.add(l)
            session.commit()

    async def __clear__(self):
        await a.clear()
        # print(await vlc.send_command("stop"))
        # print(await vlc.send_command("clear"))

    def __check_track__ready__(self, id: str) -> bool:
        with Session(db.engine) as session:
            track = session.scalar(select(db.Track).where(db.Track.id==id))
            return track is not None and track.isDownloaded
        
    def next(self):
        if self.queue_position >= len(self.queue) - 1:
            if self.is_feed:
                next_track = feed_manager.get_next()
                asyncio.create_task(self.cacheTrackMetadata(next_track))
                self.queue.append(next_track)
                self.queue_position += 1
            else:
                self.queue_position = 0
        else:
            self.queue_position += 1


    async def loop(self):
        controlTask = asyncio.create_task(self.controlTracksLoop())
        updateTask = asyncio.create_task(self.updateStatusLoop())
        await asyncio.wait([controlTask, updateTask])

    async def controlTracksLoop(self):
        while True:
            if self.status == "empty":
                self.next()
                track_id = self.queue[self.queue_position]
                if not self.__check_track__ready__(track_id):
                    asyncio.create_task(self.cacheTrack(track_id))
                    for _ in range(30):
                        if self.__check_track__ready__(track_id):
                            break
                        await asyncio.sleep(1)
                if not self.__check_track__ready__(track_id):
                    continue
                await self.__play__(track_id)
            await asyncio.sleep(1)

    async def updateStatusLoop(self):
        while True:
            await asyncio.sleep(1)
            await self.__update_status__()

    
    async def cacheTrackMetadata(self, track_id: str):
        with Session(db.engine) as session:
            storedTrack = session.scalar(select(db.Track).where(db.Track.id == track_id))
            if storedTrack is not None:
                return

            tracks = client.tracks([track_id])
            if len(tracks) == 0:
                return
            track = tracks[0]
            storedTrack = db.Track()
            storedTrack.id = track.id
            storedTrack.title = track.title
            storedTrack.isDownloaded = False
            storedTrack.isDownloading = False
            storedTrack.duration = track.duration_ms/1000
            session.add(storedTrack)
            for artist in track.artists:
                storedAuthor = session.scalar(
                    select(db.Author).where(db.Author.id == artist.id))
                if storedAuthor is not None:
                    storedAuthor.tracks.append(storedTrack)
                    continue
                storedAuthor = db.Author()
                storedAuthor.id = artist.id
                storedAuthor.name = artist.name
                storedTrack.authors.append(storedAuthor)
                session.add(storedAuthor)
            session.commit()

    async def cacheTrack(self, track_id: str):
        with Session(db.engine) as session:
            storedTrack = session.scalar(select(db.Track).where(db.Track.id == track_id))
            if storedTrack is None or storedTrack.isDownloaded or storedTrack.isDownloading:
                return
            storedTrack.isDownloading = True
            session.flush()
            tracks = client.tracks([track_id])
            if len(tracks) == 0:
                return
            track = tracks[0]
            track.download(f'cache/tracks/{track.id}.mp3')
            track.download_cover(f'cache/covers/{track.id}.png')
            storedTrack.isDownloading = False
            storedTrack.isDownloaded = True
            session.commit()
                    

     
client = Client("token",
                report_unknown_fields=False).init()                   
feed_manager = FeedManager()
player = Player()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print("start")
    task = asyncio.create_task(player.loop())

    yield

    print("stop")
    task.cancel()
    await task

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/search")
def search(query: str):
    if query == "":
        with Session(db.engine) as session:
            tracks = session.scalars(select(db.Track))
            res = []
            for track in tracks:
                try:
                    with open(f'cache/covers/{track.id}.png', "rb") as cover:
                        res.append({
                            "id": track.id,
                            "title": track.title,
                            "authors": list(map(lambda author: author.name, track.authors)),
                            "cover": f'http://192.168.2.105:8077/cover/{track.id}',
                            "downloaded": True,
                        })
                except Exception as e:
                    print(e)
                    print(f'cache/covers/{track.id}.png')
                    continue
        return res
    s = client.search(query)
    if s.tracks is None:
        return []
    res = []
    ids = []
    with Session(db.engine) as session:
        t = session.scalars(select(db.Track).join(db.Author, db.Track.authors).where(
            db.Track.title.contains(query) | db.Author.name.contains(query)).group_by(db.Track.id))
        for tt in t:
            print(tt.id)
        ids = session.scalars(select(db.Track.id).where(db.Track.id.in_(
            list(map(lambda track: f'{track.id}', s.tracks.results))))).all()
    for track in s.tracks.results:
        res.append({
            "id": f'{track.id}',
            "title": track.title,
            "authors": list(map(lambda artist: artist.name, track.artists)),
            "cover": f'http://192.168.2.105:8077/cover/{track.id}',
            "downloaded": f'{track.id}' in ids,
        })
    return res

@app.get("/cover/{track_id}")
def cover(track_id: str):
    try:
        cover = open(f'cache/covers/{track_id}.png', "rb")
        resp = Response(content=cover.read(), media_type="image/png",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})
        cover.close()
        return resp
    except Exception:
        track = client.tracks(track_id)[0]
        return Response(content=track.download_cover_bytes(), media_type="image/png", headers={"Cache-Control": "public, max-age=31536000, immutable"})

@app.get("/info/{track_id}")
def info(track_id: str):
    with Session(db.engine) as session:
        track = session.scalar(select(db.Track).where(db.Track.id==track_id))
        if track is None:
            return Response("Track not found", status.HTTP_404_NOT_FOUND)
        return {
            "title": track.title,
            "authors": list(map(lambda artist: artist.name, track.authors)),
            "cover": f'http://192.168.2.105:8077/cover/{track.id}',
            "downloaded": track.isDownloaded,
            "total": (track.duration).__trunc__(),
        }

class PlayPlaylistRequest(pydantic.BaseModel):
    queue_id: str
    position: int
    track: str


@app.post("/playPlaylist")
async def play_queue(request: PlayPlaylistRequest):
    await player.play_playlist(request.queue_id, request.position, request.track)

@app.get("/status")
def status1():
    return {
        "status": player.status,
        "current": player.current,
        "queue": player.queue,
        "queue_position": player.queue_position,
    }

@app.get("/cache/{track_id}")
def cache(track_id: str, response: Response):
    with Session(db.engine) as session:
        storedTrack = session.scalar(select(db.Track).where(db.Track.id == track_id))
        if storedTrack is not None:
            response.status_code = status.HTTP_200_OK
            return "ok"

        tracks = client.tracks([track_id])
        if len(tracks) == 0:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f'Track with id={track_id} not found')
        track = tracks[0]
        storedTrack = db.Track()
        storedTrack.id = track.id
        storedTrack.title = track.title
        storedTrack.isDownloaded = True
        storedTrack.isDownloading = False
        storedTrack.duration = track.duration_ms/1000
        session.add(storedTrack)
        for artist in track.artists:
            storedAuthor = session.scalar(
                select(db.Author).where(db.Author.id == artist.id))
            if storedAuthor is not None:
                storedAuthor.tracks.append(storedTrack)
                continue
            storedAuthor = db.Author()
            storedAuthor.id = artist.id
            storedAuthor.name = artist.name
            storedTrack.authors.append(storedAuthor)
            session.add(storedAuthor)
        track.download(f'cache/tracks/{track.id}.mp3')
        track.download_cover(f'cache/covers/{track.id}.png')
        session.commit()
        response.status_code = status.HTTP_201_CREATED
        return ""


@app.get("/")
def lis():
    with Session(db.engine) as session:
        tracks = session.scalars(select(db.Track))
        res = []
        for track in tracks:
            res.append({
                "id": track.id,
                "title": track.title,
                "authors": list(map(lambda author: author.name, track.authors)),
            })
    return res

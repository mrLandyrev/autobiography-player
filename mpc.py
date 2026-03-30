import subprocess
import re
import asyncio
from adapter import PlayerAdapter, StartEvent, EndEvent, ProgressEvent, ChangeStatusEvent, Status

class MpcClient(PlayerAdapter):
    __id: str | None = None

    def __init__(self):
        super().__init__()

    async def play(self, id: str) -> None:
        await self.setStatus(Status.pending)
        self.__id = id
        subprocess.run(["mpc", "clear"], env={"MPD_HOST": "/home/mrlandyrev/mpd/socket"})
        subprocess.run(["mpc", "add", self.__prepare_path__(id)], env={"MPD_HOST": "/home/mrlandyrev/mpd/socket"})
        subprocess.run(["mpc", "play"], env={"MPD_HOST": "/home/mrlandyrev/mpd/socket"})

    async def pause(self) -> None:
        await self.setStatus(Status.stopped)
        subprocess.run(["mpc", "pause"], env={"MPD_HOST": "/home/mrlandyrev/mpd/socket"})

    async def cont(self) -> None:
        await self.setStatus(Status.playing)
        subprocess.run(["mpc", "play"], env={"MPD_HOST": "/home/mrlandyrev/mpd/socket"})

    async def loop(self):
        while True:
            await asyncio.sleep(1)
            res = subprocess.run(["mpc", "status"], env={"MPD_HOST": "/home/mrlandyrev/mpd/socket"}, capture_output=True).stdout.decode()
            m = re.match(r".*\n\[(.*)\].*((\d+):(\d\d))\/((\d+):(\d\d))", res)
            if m is None:
                if self.getStatus() == Status.playing:
                    e = EndEvent()
                    e.id = self.__id
                    await self.onEnd.notify(e)
                    await self.setStatus(Status.empty)
                continue
            status = m[1]
            if status == "playing":
                current = int(m[3]) * 60 + int(m[4])
                total = int(m[6]) * 60 + int(m[7])
                e = ProgressEvent()
                e.id = self.__id
                e.current = current
                e.total = total
                await self.onProgress.notify(e)
                if self.getStatus() == Status.pending:
                    e = StartEvent()
                    e.id = self.__id
                    await self.onStart.notify(e)
                    await self.setStatus(Status.playing)

    def __prepare_path__(self, id: str) -> str:
        path = f"home\\mrlandyrev\\kalina\\autobiography-player\\cache\\tracks\\{id}.mp3".replace("\\", "/")
        return f'file:///{path}'
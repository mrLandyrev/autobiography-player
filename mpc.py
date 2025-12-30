import os
import asyncio
import subprocess
import re

class Status:
    status: str
    current: int
    total: int

class Client:
    def __prepare_path__(self, track_id: str) -> str:
        path = os.path.abspath(f"cache\\tracks\\{track_id}.mp3").replace("\\", "/")
        return f'file:///{path}'

    async def play(self, track_id: str):
        print("play")
        print(f"mpc add {self.__prepare_path__(track_id)}")
        subprocess.run(["mpc", "add", self.__prepare_path__(track_id)])
        subprocess.run(["mpc", "play"])
        print("after play")

    async def clear(self):
        print("clear")
        subprocess.run(["mpc", "clear"])

    async def get_status(self) -> Status | None:
        res = subprocess.run(["mpc", "status"], capture_output=True).stdout.decode()
        m = re.match(r".*\n\[(.*)\].*((\d+):(\d\d))\/((\d+):(\d\d))", res)
        if m is None:
            return None
        s = Status()
        s.status = m[1]
        s.current = int(m[3]) * 60 + int(m[4])
        s.total = int(m[6]) * 60 + int(m[7])
        return s

import asyncio
import os
import socket

class Client:
    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
        self.host = host
        self.port = port

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(host=self.host, port=self.port, family=socket.AF_INET)
        print(f"✅ Подключено к VLC на {self.host}:{self.port}")

    def __prepare_path__(self, track_id: str) -> str:
        path = os.path.abspath(f"cache\\tracks\\{track_id}.mp3").replace("\\", "/")
        return f'file:///{path}'
    
    def __prepare_cmd__(self, cmd: str) -> bytes:
        return f"{cmd}\n".encode("utf-8")
    
    async def __send__(self, cmd: str):
        self.writer.write(self.__prepare_cmd__(cmd))
        await self.writer.drain()

    async def play(self, track_id: str):
        print("play")
        path = self.__prepare_path__(track_id)
        await self.__send__(f'add "{path}"')
        await asyncio.sleep(1)
        await self.__send__("play")
        print("after play")

    async def clean(self):
        await self.__send__("clear")

    async def get_time(self):
        await self.__send__("get_time")
        print(await self.reader.readuntil())
        

    def disconnect(self):
        self.writer.close()

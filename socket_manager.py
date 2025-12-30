import fastapi

class ConnectionManager():
    def __init__(self):
        self.connections: list[fastapi.WebSocket] = []

    async def connect(self, websocket: fastapi.WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: fastapi.WebSocket):
        self.connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)
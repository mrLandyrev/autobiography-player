from abc import ABC, abstractmethod
from topic import Topic
import enum

class StartEvent():
    id: str

class EndEvent():
    id: str

class ProgressEvent():
    id: str
    current: int
    total: int

class Status(enum.Enum):
    empty = "empty"
    pending = "pending"
    playing = "playing"
    stopped = "stopped"

class ChangeStatusEvent():
    status: Status

class PlayerAdapter(ABC):
    onStart = Topic[StartEvent]()
    onEnd = Topic[EndEvent]()
    onProgress = Topic[ProgressEvent]()
    onChangeStatus = Topic[ChangeStatusEvent]()

    def __init__(self):
        super().__init__()
        self.__state = Status.empty

    async def setStatus(self, status: Status) -> None:
        self.__state = status
        e = ChangeStatusEvent()
        e.status = status
        await self.onChangeStatus.notify(e)

    def getStatus(self) -> Status:
        return self.__state

    @abstractmethod
    async def play(self, id: str) -> None:
        pass

    @abstractmethod
    async def pause(self) -> None:
        pass

    @abstractmethod
    async def cont(self) -> None:
        pass

    @abstractmethod
    async def loop(self) -> None:
        pass
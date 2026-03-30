from typing import Callable, Awaitable
import inspect
import asyncio

class Topic[T]():
    type Callback = Callable[[T], None | Awaitable[None]]
    
    subscribers: list[Callback]

    def __init__(self):
        self.subscribers = []

    def sub(self, callback: Callback) -> None:
        self.subscribers.append(callback)

    async def notify(self, value: T) -> None:
        for sub in self.subscribers:
            result = sub(value)
            if inspect.iscoroutine(result):
                await result
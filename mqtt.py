import paho.mqtt.client as mqtt
import json
import topic
from adapter import ProgressEvent, Status
import asyncio

class ToggleEvent():
    pass

class MqqtClient():
    onToggle = topic.Topic[ToggleEvent]()
    onNext = topic.Topic[ToggleEvent]()
    onPrev = topic.Topic[ToggleEvent]()

    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_message = self.onMessage
        self.client.connect("127.0.0.1", 1883, 60)
        self.client.subscribe("/music/toggle")
        self.client.subscribe("/music/next")
        self.client.subscribe("/music/prev")
        self.client.loop_start()

    def onMessage(self, client: mqtt.Client, userData, message: mqtt.MQTTMessage):
        async def call():
            if message.topic == "/music/toggle":
                await self.onToggle.notify(ToggleEvent())
            if message.topic == "/music/next":
                await self.onNext.notify(ToggleEvent())
            if message.topic == "/music/prev":
                await self.onPrev.notify(ToggleEvent())
        asyncio.run(call())

    def sendCurrent(self, msg: ProgressEvent):
        self.client.publish("/music/current", json.dumps(msg.__dict__), 2, True)

    def sendStatus(self, msg: Status):
        self.client.publish("/music/status", json.dumps(msg), 2, True)

    def sendQueue(self, q: list[str], p: int):
        self.client.publish("/music/queue", json.dumps({
            'q': q,
            'p': p,
        }), 2, True)

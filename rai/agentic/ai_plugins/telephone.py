import asyncio
import time
from collections import deque
from collections.abc import Callable
from typing import List, Any, AsyncGenerator, Generator
import cv2
import numpy as np
import websockets

# from rai.agentic.ai_modules.threads import ToolThread
from rai.internal.clients.ioredis_client import RedisIO

CHANNEL_REGISTRY = {}


class OperatorTool:
    def __init__(self):
        self.listener_task = None
        self.is_setup = False
        self.pub = RedisIO()
        self.pubsub = None
        self.streaming = False
        self.current_channel_name = 'operator'
        self.messages_in = deque()
        self.messages_out = deque()
        self.running = False
        self.waiting_for_response = False

    def setup_channel(self, channel_name: str, streaming: bool = True):
        self.current_channel_name = channel_name
        self.register_channel(channel_name)
        self.streaming = streaming

    def set_current_channel(self, channel_name: str):
        self.current_channel_name = channel_name

    def register_channel(self, channel: str):
        CHANNEL_REGISTRY[channel] = []

    def subscribe_to_channel(self, channel: str, callback: Callable):
        CHANNEL_REGISTRY[channel].append(callback)

    @property
    def channel_in(self) -> str:
        return f"{self.current_channel_name}-in"

    @property
    def channel_out(self) -> str:
        return f"{self.current_channel_name}-out"

    @property
    def channel_stream(self) -> str:
        return f"{self.current_channel_name}-stream"

    @property
    def channel_live(self) -> str:
        return f"{self.current_channel_name}-live"

    async def ensure_connected(self):
        if self.is_setup:
            return
        await self.pub.connect()
        self.pubsub = self.pub.redis_client.pubsub()
        self.is_setup = True

    async def stream_out(self, message: str):
        if self.streaming:
            await self.pub.redis_client.publish(self.channel_stream, message)

    async def speak_out(self, message: str):
        self.messages_out.append(message)
        await self.pub.redis_client.publish(self.channel_out, message)

    async def speak_in(self, message: str):
        self.messages_in.append(message)
        self.waiting_for_response = True
        await self.pub.redis_client.publish(self.channel_in, message)

    async def _listen_in(self):
        await self.ensure_connected()
        await self.pubsub.subscribe(
            self.channel_in
        )
        print(f"Subscribed to Channel IN")
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                decoded_message = message["data"].decode('utf-8')
                self.messages_in.append(decoded_message)
                self.waiting_for_response = False
                for callback in CHANNEL_REGISTRY.get(self.current_channel_name, []):
                    callback(decoded_message)
    async def _listen_out(self):
        await self.ensure_connected()
        await self.pubsub.subscribe(
            self.channel_out
        )
        print(f"Subscribed to Channel OUT")
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                decoded_message = message["data"].decode('utf-8')
                print("Response:", decoded_message)
                self.messages_out.append(decoded_message)
                self.waiting_for_response = False
                for callback in CHANNEL_REGISTRY.get(self.current_channel_name, []):
                    callback(decoded_message)

    async def watch_live(self):
        await self.ensure_connected()
        await self.pubsub.subscribe(self.channel_live)
        print(f"Subscribed to Live Channel")
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                screenshot_bytes = message['data']
                np_img = np.frombuffer(screenshot_bytes, dtype=np.uint8)
                img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
                if img is not None:
                    cv2.imshow("Live Stream", img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        cv2.destroyAllWindows()

    async def speak_to(self, channel: str, message: str):
        self.messages_out.append(message)
        await self.pub.redis_client.publish(channel, message)

    async def listen_to(self, channel: str) -> AsyncGenerator[str, Any]:
        await self.ensure_connected()
        local_pubsub = self.pub.redis_client.pubsub()
        await local_pubsub.subscribe(channel)
        print(f"Listening to channel: {channel}")
        async for message in local_pubsub.listen():
            if message["type"] == "message":
                yield message["data"].decode('utf-8')

    def start_in(self, channel: str):
        self.current_channel_name = channel
        self.running = True
        self.listener_task = asyncio.create_task(self._listen_in())
        print("Listener started.")
    def start_out(self, channel: str):
        self.current_channel_name = channel
        self.running = True
        self.listener_task = asyncio.create_task(self._listen_out())
        print("Listener started.")
    async def stop(self):
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        await self.pub.disconnect()
        self.running = False
        print("OperatorTool stopped.")

    async def cli(self, channel: str):
        self.start_out(channel)
        print(f"CLI started on channel '{channel}'.")
        time.sleep(3)
        loop = asyncio.get_event_loop()
        try:
            while True:
                message = await loop.run_in_executor(None, input, "Send Message: ")
                if message.lower() in {'exit', 'quit'}:
                    break
                await self.speak_in(message)
                while self.waiting_for_response:
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop()
            print("CLI stopped.")


if __name__ == "__main__":

    loop = asyncio.new_event_loop()
    loop.run_until_complete(OperatorTool().cli('inner-dialog'))
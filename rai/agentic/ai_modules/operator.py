import asyncio
from collections import deque
from typing import List
import cv2
import numpy as np
import websockets

from rai.agentic.ai_modules.threads import ToolThread
from rai.internal.clients.ioredis_client import IORedis

class ToolOperator(ToolThread):
    listener_task = None

    pub = IORedis

    is_client: bool = False
    streaming: bool = False
    channel_name = 'operator'
    messages_in: deque = deque([])
    running: bool = False
    waiting_for_response: bool = False

    def set_channel_name(self, channel_name): self.channel_name = channel_name
    def client_mode_on(self):
        print('Client mode on')
        self.is_client = True
    def client_mode_off(self):
        print('Client mode off')
        self.is_client = False
    @property
    def channel_in(self) -> str:
        if self.is_client: return f"{self.channel_name}-two"
        return f"{self.channel_name}-one"
    @property
    def channel_out(self) -> str:
        if self.is_client: return f"{self.channel_name}-one"
        return f"{self.channel_name}-two"
    @property
    def channel_stream(self) -> str: return f"{self.channel_name}-stream"

    def message_handler(self, message: str):
        print(f"Agent says: {message}")
        self.waiting_for_response = False

    async def stream_out(self, message: str):
        try:
            if not self.streaming: return
            await self.pub.redis_client.publish(self.channel_stream, message)
        except Exception as e:
            print(f"Failed to publish message: {e}")
    async def stream_in(self):
        try:
            pubsub = self.pub.redis_client.pubsub()
            await pubsub.subscribe(self.channel_stream)
            print(f"Subscribed to channel: {self.channel_stream}")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    decoded_message = message["data"].decode('utf-8')
                    self.messages_in.append(decoded_message)
                    self.message_handler(decoded_message)
        except asyncio.CancelledError:
            print("Listening task cancelled.")
        except Exception as e:
            print(f"Error in listener: {e}")

    async def speak(self, message: str):
        try:
            await self.pub.redis_client.publish(self.channel_in, message)
        except Exception as e:
            print(f"Failed to publish message: {e}")
    async def speak_and_wait(self, message: str):
        try:
            await self.speak(message)
            self.waiting_for_response = True
            while self.waiting_for_response:
                await asyncio.sleep(2)
        except Exception as e:
            print(f"Failed to publish message: {e}")
    async def listen(self):
        try:
            pubsub = self.pub.redis_client.pubsub()
            await pubsub.subscribe(self.channel_out)
            print(f"Subscribed to channel: {self.channel_out}")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    decoded_message = message["data"].decode('utf-8')
                    self.messages_in.append(decoded_message)
                    self.message_handler(decoded_message)
                    self.waiting_for_response = False
        except asyncio.CancelledError:
            print("Listening task cancelled.")
        except Exception as e:
            print(f"Error in listener: {e}")

    async def start(self):
        await self.pub.connect()
        self.running = True
        self.listener_task = asyncio.create_task(self.listen())
        print("ToolOperator listener started in the background.")
    async def stop(self):
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                print("Listener task cancelled.")
        await self.pub.disconnect()
        print("ToolOperator disconnected gracefully.")
    def start_in_background(self):
        self.main.main_loop.run_until_complete(self.start())
    def run_cli(self):
        async def cli_loop():
            while True:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(None, input, "Tell your agent: ")
                    await self.speak_and_wait(user_input)
                except asyncio.CancelledError:
                    print("CLI loop cancelled.")
                    break

        asyncio.run(self.start_and_cli(cli_loop))
    async def start_and_cli(self, cli_loop):
        await self.pub.connect()
        listener_task = asyncio.create_task(self.listen())
        cli_task = asyncio.create_task(cli_loop())
        done, pending = await asyncio.wait([listener_task, cli_task], return_when=asyncio.FIRST_COMPLETED )
        for task in pending: task.cancel()
        await self.pub.disconnect()
    async def display_screenshots(self):
        await self.pub.connect()
        pubsub = self.pub.redis_client.pubsub()
        await pubsub.subscribe("agent")
        print(f"Subscribed to Redis channel: agent")
        async for message in pubsub.listen():
            if message['type'] == 'message':
                screenshot_bytes = message['data']
                np_img = np.frombuffer(screenshot_bytes, dtype=np.uint8)
                img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

                if img is not None:
                    cv2.imshow("Browser Screenshot Stream", img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        cv2.destroyAllWindows()



async def receive_and_show_images(ws_url="ws://192.168.1.43:5182/ws/agent"):
    async with websockets.connect(ws_url) as websocket:
        print(f"Connected to {ws_url}")

        try:
            while True:
                image_bytes = await websocket.recv()
                np_img = np.frombuffer(image_bytes, dtype=np.uint8)
                img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

                if img is not None:
                    cv2.imshow("WebSocket Screenshot Stream", img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        except websockets.exceptions.ConnectionClosed as ec:
            print(f"Connection closed [ {ec} ] ")
        finally:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    # loop = asyncio.new_event_loop()
    # loop.run_until_complete(display_screenshots())
    # loop.run_until_complete()
    ops = ToolOperator()
    ops.client_mode_on()
    ops.run_cli()
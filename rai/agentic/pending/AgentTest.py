import asyncio
import cv2
import numpy as np
import websockets
from rai.internal.clients.ioredis_client import RedisIO

redis = RedisIO()


async def display_screenshots():
    await redis.connect()
    pubsub = redis.redis_client.pubsub()
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
    loop = asyncio.new_event_loop()
    # loop.run_until_complete(display_screenshots())
    loop.run_until_complete(receive_and_show_images())
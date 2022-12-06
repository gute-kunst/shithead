import asyncio
import random

import websockets


async def hello():
    uri = f"ws://localhost:8000/ws/{random.randint(0,10000)}"
    async with websockets.connect(uri) as websocket:
        name = input("What's your name? ")

        await websocket.send(name)
        print(f">>> {name}")

        response = await websocket.recv()
        print(f"<<< {response}")

        response = await websocket.recv()
        print(f"<<< {response}")

        response = await websocket.recv()
        print(f"<<< {response}")

        response = await websocket.recv()
        print(f"<<< {response}")


if __name__ == "__main__":
    asyncio.run(hello())

import asyncio
import json

import websockets


async def hello():
    join_game_id = "1"
    uri = f"ws://localhost:8000/join/{join_game_id}"
    async with websockets.connect(uri) as websocket:
        response = await websocket.recv()
        print(f"<<< {response}")
        dict = json.loads(response)

        print(f"<<< WAITING FOR GAME TO BEGIN")
        response = await websocket.recv()

        print(f"<<< game began")


if __name__ == "__main__":
    asyncio.run(hello())

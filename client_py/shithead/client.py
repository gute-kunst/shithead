import asyncio
import json

import websockets


async def main():
    join_game_id = 1
    uri = f"ws://localhost:8000/game/{join_game_id}"
    async with websockets.connect(uri) as websocket:
        response = await websocket.recv()
        print(f"<<< {response}")
        print("server request ...")

        response = await websocket.recv()
        print(f"<<< {response}")
        await websocket.send(json.dumps({"type": "start_game"}))
        response = await websocket.recv()
        print(f"<<< {response}")
        response = await websocket.recv()
        print(f"<<< {response}")
        response = await websocket.recv()
        print(f"<<< {response}")


if __name__ == "__main__":
    asyncio.run(main())

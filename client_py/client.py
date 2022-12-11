import asyncio
import json

import websockets


async def hello():
    join_game_id = "1"
    uri = f"ws://localhost:8000/game/{join_game_id}"
    async with websockets.connect(uri) as websocket:
        response = await websocket.recv()
        print(f"<<< {response}")
        print("server request ...")
        await websocket.send(json.dumps({"type": "START"}))

        print(f"<<< WAITING FOR GAME TO BEGIN")
        response = await websocket.recv()
        dict = json.loads(response)
        if dict["type"] == "start":
            print("client kicks off first move")

        print(f"<<< {response}")
        response = await websocket.recv()


if __name__ == "__main__":
    asyncio.run(hello())

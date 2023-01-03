from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket, WebSocketDisconnect

app = FastAPI()

USERS: list[WebSocket] = list()


@app.websocket_route("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    USERS.append(websocket)
    await websocket.send_json({"msg": "private client send"})
    for user in USERS:
        await user.send_json({"msg": f"broadcast #c: {len(USERS)}"})
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"msg-echo": data["msg"]})
            print("end")
    except WebSocketDisconnect:
        await websocket.close()


def test_websocket():
    client = TestClient(app)
    with client.websocket_connect("/ws") as a:
        with client.websocket_connect("/ws") as b:
            data_a1 = a.receive_json()
            assert data_a1 == {"msg": "private client send"}
            data_a2 = a.receive_json()
            assert data_a2 == {"msg": "broadcast #c: 1"}
            data_a3 = a.receive_json()
            assert data_a3 == {"msg": "broadcast #c: 2"}

            data_b1 = b.receive_json()
            assert data_b1 == {"msg": "private client send"}
            data_b2 = b.receive_json()
            assert data_b2 == {"msg": "broadcast #c: 2"}
            a.send_json({"msg": "send_json"})
            data_a4 = a.receive_json()
            assert data_a4 == {"msg-echo": "send_json"}

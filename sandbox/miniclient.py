# WS client example

import asyncio, websockets, time

async def hello():
    async with websockets.connect("ws://localhost:8765") as websocket:

        counter = 1
        await websocket.send(str(counter))

        while True:

            counter = await websocket.recv()
            await asyncio.sleep(3)

            counter = int(counter) + 1
            await websocket.send(str(counter))
            print(f"got {counter-1} -> sent {counter}")
            


asyncio.get_event_loop().run_until_complete(hello())

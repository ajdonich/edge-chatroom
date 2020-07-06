# WS server example

import asyncio, websockets

async def hello(websocket, path):

    while True:
        counter = await websocket.recv()
        await asyncio.sleep(3)

        counter = int(counter) + 1
        await websocket.send(str(counter))
        print(f"got {counter-1} -> sent {counter}")




start_server = websockets.serve(hello, "localhost", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
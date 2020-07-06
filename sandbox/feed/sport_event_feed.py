import random
import time
import asyncio

from nats.aio.client import Client
import lorem

from gen import event_pb2

EVENT_TOPIC_NAME = "sport_event"



def _generate_new_event():
    event = event_pb2.event()
    sport_index = random.randint(1,7)
    data_event = lorem.paragraph()
    title = lorem.sentence()
    event.sport = sport_index
    event.match_title = title
    event.data_event = data_event
    return event


async def main(event_loop):
    nats_client = Client()
    print("Connecting to NATS Queue")
    await nats_client.connect("localhost:4222", loop=event_loop)
    print("Connected to NATS Queue")

    while True:
        event = _generate_new_event()
        await nats_client.publish(EVENT_TOPIC_NAME, event.SerializeToString())
        await nats_client.flush(timeout=1)
        print("Published: ", event)
        time.sleep(.001)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
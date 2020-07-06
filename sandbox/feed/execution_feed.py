import random
import time
import asyncio

from nats.aio.client import Client

from gen import execution_pb2


SYMBOL_MARKET_MAP = {"DAL-PHL:Line": "FOOTBALL",
                     "DAL-PHL:spread--5": "FOOTBALL",
                    "DAL-PHL:points--40": "FOOTBALL",
                 "MASTERS:winner--Tiger Woods": "GOLF",
                     "MASTERS:winner--Rory McLlroy": "GOLF",
                 "WIMBELDON:winner--Roger Federer": "TENNIS",
                     "WIMBELDON:winner--Novak Djokovic": "TENNIS",
                 "DAYTONA:winner--Bubba Wallace": "NASCAR",
                     "DAYTONA:winner--Kyle Busch": "NASCAR",
                 "OLYMPIC 100m:winner--Usain Bolt": "TRACK&FIELD",
                     "OLYMPIC 100m:winner--Tyson Gay": "TRACK&FIELD",
                 "PRESIDENT:winner--Donald Trump": "POLITICS",
                     "PRESIDENT:winner--Joe Biden": "POLITICS",
                     "PRESIDENT:winner--Vermin Supreme": "POLITICS"}

EXECUTION_TOPIC_NAME = "execution"



def _generate_new_execution():
    execution = execution_pb2.execution()
    symbol, market = random.choice(list(SYMBOL_MARKET_MAP.items()))
    price = random.uniform(0, 100)
    quantity = random.uniform(0, 1000)
    execution.symbol = symbol
    execution.market = market
    execution.price = price
    execution.quantity = quantity
    execution.stateSymbol = "PA"
    execution.executionEpoch = int(time.time())
    return execution


async def main(event_loop):
    nats_client = Client()
    print("Connecting to NATS Queue")
    await nats_client.connect("host.docker.internal:4222", loop=event_loop)
    print("Connected to NATS Queue")

    while True:
        execution = _generate_new_execution()
        await nats_client.publish(EXECUTION_TOPIC_NAME, execution.SerializeToString())
        await nats_client.flush(timeout=1)
        print("Published: ", execution)
        time.sleep(.200)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
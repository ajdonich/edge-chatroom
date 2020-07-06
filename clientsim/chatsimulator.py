# WS chatroom client 

from collections import deque
import argparse, random, lorem, time, asyncio, websockets
from proto import event_pb2, execution_pb2
import proto.chatmessage_pb2 as cmpb2

SPORT_FILTERS = [
    "match_title LIKE '%%sed%%'",
    "SAME",
    "sport = 3",
    "NONE",
    "sport = 4 AND match_title NOT LIKE 'Est%%'",
    "SAME",
    "sport NOT IN (1,2,3,6,7)",
    "ALL",
    "sport = 7 OR sport = 1"]

EXECUTION_FILTERS = [
    "ALL",
    "symbol LIKE '%%DAYTONA%%'",
    "symbol LIKE '%%Joe Biden%%' OR market = 'GOLF'",
    "NONE",
    "market >= 'POLITICS'",
    "SAME",
    "stateSymbol = 'PA'",
    "stateSymbol = 'NY'",
    "stateSymbol = 'PA' OR stateSymbol = 'NV'",
    "market = 'TRACK&FIELD'"]

BAD_SPORT_FILTERS = [
    "sport = 'FOOTBALL'",
    "sport  AND sport = 1",
    "match_title LIKE '%aliquam%'"]

BAD_EXECUTION_FILTERS = [
    "stateSymbol == 'PA'",
    "sport = 3"]

FILTER_TEST = [
    SPORT_FILTERS,
    EXECUTION_FILTERS,
    BAD_SPORT_FILTERS,
    BAD_EXECUTION_FILTERS]

CREATE_USER = 1
USER_NONACTION = 2
USER_COMMENT = 3
USER_FILT_REQ = 4
USER_DISCONNECT = 5

class FeedSets:
#{
    def __init__(self):
        self.event_sport = set()
        self.event_match = set() 
        self.event_data = set()

        self.exec_symbol = set()
        self.exec_market = set() 
        self.exec_price = set()
        self.exec_quantity = set()
        self.exec_epoch = set() 
        self.exec_state = set()

    def add(self, chatmessage):
        if chatmessage.mtype == cmpb2.msgtype.EVENT:
            self.event_sport.add(chatmessage.eventmsg.sport)
            self.event_match.add(chatmessage.eventmsg.match_title)
            self.event_data.add(chatmessage.eventmsg.data_event)

        elif chatmessage.mtype == cmpb2.msgtype.EXECUTION:
            self.exec_symbol.add(chatmessage.execmsg.symbol)
            self.exec_market.add(chatmessage.execmsg.market) 
            self.exec_price.add(chatmessage.execmsg.price)
            self.exec_quantity.add(chatmessage.execmsg.quantity)
            self.exec_epoch.add(chatmessage.execmsg.executionEpoch) 
            self.exec_state.add(chatmessage.execmsg.stateSymbol)
#}

class ChatUser:
#{
    msgtypestr = ['SLOT_0', 'ROOM_STATUS', 'JOIN_REQ', 'COMMENT', 'FILTER', 'EVENT', 'EXECUTION']
    sportstr = ['SLOT_0', 'BASEBALL', 'BASKETBALL', 'FOOTBALL', 'BOXING', 'GOLF', 'NASCAR', 'TENNIS']

    def __init__(self, name, roomid=None, filtertest=None, loopdelay=3):
        self.name = name
        self.roomid = roomid
        self.connstatus = None
        self.productionq = deque()
        self.feedsets = FeedSets()
        self.loopdelay = loopdelay
        self.filtertest = filtertest

    async def connect(self, uri="ws://localhost:4242"):
        print("Entering connect")
        async with websockets.connect(uri) as websocket:
            self.connstatus = "INITALIZE"
            readtask = asyncio.create_task(self.readsocket(websocket))
            prodtask = asyncio.create_task(self.prodcontent(websocket))
            await asyncio.gather(readtask, prodtask)
        
        print("Exiting connect")

    async def readsocket(self, websocket):
        while self.connstatus != "DISCONNECT":
            async for bmessage in websocket:
                await self.handle_message(bmessage, websocket)

    async def prodcontent(self, websocket):
    #{
        initial = time.time()
        filtgtor = self.run_filter_test()

        while self.connstatus != "DISCONNECT":
            if self.connstatus == "CONNECTED" and self.productionq: 
                prodtype = self.productionq.popleft()
                if prodtype == USER_NONACTION: pass #print("Chillin...")
                if prodtype == USER_COMMENT:
                    await websocket.send(await self.create_chatmsg(lorem.sentence()))

                elif (prodtype == USER_FILT_REQ and self.filtertest and
                      time.time()-initial >= self.loopdelay*5):
                    # filtmsg = await self.create_filtmsg()

                    try:
                        filtmsg = next(filtgtor)
                        print(f"FILTER_REQ:")
                        print(f"  sport: {filtmsg.sport_filter}")
                        print(f"  execution: {filtmsg.execution_filter}")
                        await websocket.send(filtmsg.SerializeToString())
                        initial = time.time()

                    except StopIteration:
                        self.filtertest = False
                        self.productionq.append(USER_DISCONNECT)

                elif prodtype == USER_DISCONNECT:
                    print("Disconnecting...")
                    self.connstatus = "DISCONNECT"
                    await websocket.close()

            else:
                # Random action simulation
                percent = random.randint(1,100)
                if percent <= 30: self.productionq.append(USER_NONACTION)
                elif percent > 30 and percent <= 75: self.productionq.append(USER_COMMENT)
                elif percent > 75 and percent <= 99: self.productionq.append(USER_FILT_REQ)
                elif percent == 100 and not self.filtertest: self.productionq.append(USER_DISCONNECT)
                await asyncio.sleep(self.loopdelay)
    #}

    def run_filter_test(self):
    #{
        for i in range(len(FILTER_TEST)):
            for j in range(len(FILTER_TEST[i])):
                filtmsg = cmpb2.chatmessage()
                filtmsg.mtype = cmpb2.msgtype.FILTER
                filtmsg.user = self.name
                filtmsg.roomid = self.roomid

                if i%2 == 0: 
                    filtmsg.sport_filter = FILTER_TEST[i][j]
                    filtmsg.execution_filter = "ALL"
                else:
                    filtmsg.sport_filter = "ALL"
                    filtmsg.execution_filter = FILTER_TEST[i][j] 

                yield filtmsg
    #}

    async def handle_message(self, bmessage, websocket):
    #{        
        chatmessage = cmpb2.chatmessage()
        chatmessage.ParseFromString(bmessage)
        #print(chatmessage)

        if chatmessage.mtype == cmpb2.msgtype.ROOM_STATUS:
            # PENDING/DENIED/REJECTED sent only to me
            if chatmessage.userstatus == "PENDING": 
                await websocket.send(await self.create_joinmsg(chatmessage))
            
            elif chatmessage.userstatus in ["DENIED_BADROOMID", "DENIED_NAMETAKEN", "DENIED_ROOMFULL"]:
                print(f"JOIN_REQ: {chatmessage.userstatus}, disconnecting...")
                self.connstatus = "DISCONNECT"
                await websocket.close()

            elif chatmessage.userstatus == "REJECTED_BADFILTER":
                print(f"FILTER: {chatmessage.userstatus}:")
                print(f"  sport: {chatmessage.sport_filter}")
                print(f"  execution: {chatmessage.execution_filter}")

            # USERJOINED/USEREXITED sent to all room users
            elif chatmessage.userstatus == "USERJOINED": 
                print(f'{chatmessage.userstatus}: {chatmessage.user}')
                if chatmessage.user == self.name: self.connstatus = "CONNECTED"

            elif chatmessage.userstatus == "USEREXITED": 
                print(f'{chatmessage.userstatus}: {chatmessage.user}')
                assert chatmessage.user != self.name, "ERROR: server exited me!"
            
            elif chatmessage.userstatus == "FILTERAPPLIED":
                print(f"FILTER: {chatmessage.userstatus}")
                print(f"  sport: {chatmessage.sport_filter}")
                print(f"  execution: {chatmessage.execution_filter}")

            else: print(f"ERROR: unrecognized userstatus: {chatmessage.userstatus}")

        elif chatmessage.mtype == cmpb2.msgtype.COMMENT:
            if chatmessage.roomid == self.roomid:
                print(f'{chatmessage.user}: {chatmessage.comment}')

        elif chatmessage.mtype == cmpb2.msgtype.EVENT:
            self.feedsets.add(chatmessage)
            print((f"{ChatUser.msgtypestr[chatmessage.mtype]}: "
                   f"({ChatUser.sportstr[chatmessage.eventmsg.sport]}, "
                   f"{chatmessage.eventmsg.match_title})"))

        elif chatmessage.mtype == cmpb2.msgtype.EXECUTION:
            self.feedsets.add(chatmessage)
            print((f"{ChatUser.msgtypestr[chatmessage.mtype]}: "
                   f"({chatmessage.execmsg.symbol}, {chatmessage.execmsg.market}, " 
                   f"{chatmessage.execmsg.executionEpoch}, {chatmessage.execmsg.stateSymbol})"))

        else: print(f"ERROR: bad inbound msgtype: {chatmessage.mtype}")
    #}

    async def create_joinmsg(self, rstatusmsg):
        
        # If needed, randomly select a room from open rooms
        if self.roomid is None: self.roomid = random.choice(
            [room.roomid for room in rstatusmsg.rooms 
             if room.numusers < room.maxusers])

        joinmsg = cmpb2.chatmessage()
        joinmsg.mtype = cmpb2.msgtype.JOIN_REQ
        joinmsg.user = self.name
        joinmsg.roomid = self.roomid
        return joinmsg.SerializeToString()        

    async def create_chatmsg(self, comment):
        chatmsg = cmpb2.chatmessage()
        chatmsg.mtype = cmpb2.msgtype.COMMENT
        chatmsg.user = self.name
        chatmsg.roomid = self.roomid
        chatmsg.comment = comment
        return chatmsg.SerializeToString()

    async def create_filtmsg(self):
        filtmsg = cmpb2.chatmessage()
        filtmsg.mtype = cmpb2.msgtype.FILTER
        filtmsg.user = self.name
        filtmsg.roomid = self.roomid

        # Note: protobuf defaults filters to "SAME" 
        ftype = random.randint(1,10)
        if ftype == 5: filtmsg.sport_filter = "NONE"
        if ftype == 6: filtmsg.execution_filter = "NONE"
        elif ftype <= 4: filtmsg.sport_filter = await self._boolean_filter(1)
        elif ftype >= 7: filtmsg.execution_filter  = await self._boolean_filter(2)
        return filtmsg

    async def _rand_boolean_filter(self, ftype):
    #{
        clause = ""
        if ftype == 1: # Event filter
            if random.randint(1, 2) == 1:
                kv = min(len(self.feedsets.event_sport), random.randint(1, 3))
                values = random.sample(list(self.feedsets.event_sport), k=kv)
                for i, val in enumerate(map(str, values)):
                    clause += f" sport = {val}" if i == 0 else f" OR sport = {val}"
            else: 
                kv = min(len(self.feedsets.event_match), random.randint(1, 3))
                values = random.sample(list(self.feedsets.event_match), k=kv)
                for i, val in enumerate(map(str, values)):
                    clause += f" match_title = '{val}'" if i == 0 else f" OR match_title = '{val}'"

        else: # Execution filter
            fvalue = random.randint(1, 3)
            if fvalue == 1:
                kv = min(len(self.feedsets.exec_symbol), random.randint(1, 3))
                values = random.sample(list(self.feedsets.exec_symbol), k=kv)
                for i, val in enumerate(map(str, values)):
                    clause += f" symbol = '{val}'" if i == 0 else f" OR symbol = '{val}'"
            elif fvalue == 2:
                kv = min(len(self.feedsets.exec_market), random.randint(1, 3))
                values = random.sample(list(self.feedsets.exec_market), k=kv)
                for i, val in enumerate(map(str, values)):
                    clause += f" market = '{val}'" if i == 0 else f" OR market = '{val}'"
            else:
                kv = min(len(self.feedsets.exec_state), random.randint(1, 3))
                values = random.sample(list(self.feedsets.exec_state), k=kv)
                for i, val in enumerate(map(str, values)):
                    clause += f" stateSymbol = '{val}'" if i == 0 else f" OR stateSymbol = '{val}'"
        
        print("Created filter:", clause)
        return "SAME" if clause == "" else clause
    #}
#}

if __name__ == "__main__":
#{
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument('--roomid')
    parser.add_argument('--filter')
    args = parser.parse_args()
    print(args.filter)

    print(f"Starting client '{args.username}' in room: {args.roomid}")
    client = ChatUser(args.username, int(args.roomid), args.filter, loopdelay=3)
    asyncio.run(client.connect())
#}

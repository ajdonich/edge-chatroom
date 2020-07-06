# WS chatroom server

import os, signal, time, asyncio, websockets
from proto import event_pb2, execution_pb2
import proto.chatmessage_pb2 as cmpb2
import edgechat.postgresdb as pgdb
from nats.aio.client import Client

class Chatroom:
#{
    __roomid_index = 0
    def __init__(self, maxusers):
        self.roomid = Chatroom.__roomid_index
        Chatroom.__roomid_index += 1

        self.activeusers = set()
        self.maxusers = maxusers
        self.filters = ["NONE", "NONE"]

    def add(self, user): self.activeusers.add(user)
    def remove(self, user): self.activeusers.remove(user)
    def finduser(self, user): return(user in self.activeusers)

    def roomisfull(self):
        print(f"users: {len(self.activeusers)}/{self.maxusers}")
        assert len(self.activeusers) <= self.maxusers,\
            "ERROR: len(activeusers) somehow exceeds maxusuers"
        return len(self.activeusers) == self.maxusers
#}

class ChatService:
#{
    def __init__(self, nrooms=5, maxusers=[25]):
    #{
        assert len(maxusers) == nrooms or len(maxusers) == 1, \
            f"Invalid len max users specification: {len(maxusers)}"
        
        self.keeprunning = False
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        if len(maxusers) == 1: maxusers = maxusers * nrooms
        self.rooms = [Chatroom(n) for n in maxusers]
        self.usersockets = {}
    #}

    def shutdown(self, signum, frame): 
        self.keeprunning = False

    def name_taken(self, user): 
        for room in self.rooms: 
            if room.finduser(user):
                return True
        return False

    async def initialize(self, host="localhost", port=4242):
    #{
        self.keeprunning = True
        wbserver = websockets.serve(self.readsocket, host, port)    
        natstask = asyncio.create_task(self.readnats())
        await asyncio.gather(wbserver, natstask)
        print(f"Listening on {host}:{port}")

        # Loop until SIGINT or SIGTERM
        while self.keeprunning: await asyncio.sleep(1)
        closetasks = [sock.close() for sock in self.usersockets.keys()] 
        if closetasks: await asyncio.wait(closetasks)
        for task in asyncio.all_tasks(): task.cancel()
    #}

    async def notify_users(self, roomidset, bmessage):
        sendtasks = [wbsock.send(bmessage) for wbsock, (user, rid, status) in 
        self.usersockets.items() if rid in roomidset and status == "CONNECTED"]
        if sendtasks: await asyncio.wait(sendtasks)

    #####################################################
    ## Frontend message handling branch starts here:

    async def readsocket(self, websocket, path):
    #{
        try:
            # Provide initial rooms status to new user
            self.usersockets[websocket] = ("unknown", -1, "INITIALIZE")
            rstatusmsg = await self.create_rstatusmsg("PENDING")
            await self.persist_chatmsg(rstatusmsg)
            await websocket.send(rstatusmsg.SerializeToString())

            # Handle messages
            while websocket.open and self.keeprunning:
                async for bmessage in websocket:
                    await self.handle_chatmsg(bmessage, websocket)
        finally:
            # Connection closed, update status
            user, roomid, status = self.usersockets[websocket]         
            print(f"Socket broken for user {user}, room: {roomid}, status: {status}")
            del self.usersockets[websocket]
            await websocket.close()

            # Update status and notify other users
            if status == "CONNECTED" and self.keeprunning:
                self.rooms[roomid].remove(user)
                rstatusmsg = await self.create_rstatusmsg("USEREXITED", user, roomid)
                await self.persist_chatmsg(rstatusmsg)
                await self.notify_users({roomid}, rstatusmsg.SerializeToString())
    #}

    async def handle_chatmsg(self, bmessage, websocket):
    #{
        chatmsg = cmpb2.chatmessage()
        chatmsg.ParseFromString(bmessage)
        await self.persist_chatmsg(chatmsg)
        user, roomid, status = self.usersockets[websocket]

        if chatmsg.mtype == cmpb2.msgtype.JOIN_REQ:
        #{
            if chatmsg.roomid < 0 or chatmsg.roomid >= len(self.rooms):
                print(chatmsg, "DENIED_BADROOMID")
                rstatusmsg = await self.create_rstatusmsg(
                    "DENIED_BADROOMID", chatmsg.user, chatmsg.roomid)
                await self.persist_chatmsg(rstatusmsg)
                await websocket.send(rstatusmsg.SerializeToString())

            elif self.name_taken(chatmsg.user):
                print(chatmsg, "DENIED_NAMETAKEN")
                rstatusmsg = await self.create_rstatusmsg(
                    "DENIED_NAMETAKEN", chatmsg.user, chatmsg.roomid)
                await self.persist_chatmsg(rstatusmsg)
                await websocket.send(rstatusmsg.SerializeToString())

            elif self.rooms[chatmsg.roomid].roomisfull():
                print(chatmsg, "DENIED_ROOMFULL")
                rstatusmsg = await self.create_rstatusmsg(
                    "DENIED_ROOMFULL", chatmsg.user, chatmsg.roomid)
                await self.persist_chatmsg(rstatusmsg)
                await websocket.send(rstatusmsg.SerializeToString())

            else:
                print(chatmsg, "USERJOINED")
                self.rooms[chatmsg.roomid].add(chatmsg.user)
                self.usersockets[websocket] = (chatmsg.user, chatmsg.roomid, "CONNECTED")

                rstatusmsg = await self.create_rstatusmsg(
                    "USERJOINED", chatmsg.user, chatmsg.roomid)
                await self.persist_chatmsg(rstatusmsg)
                await self.notify_users({chatmsg.roomid}, rstatusmsg.SerializeToString())
        #}
        elif chatmsg.mtype == cmpb2.msgtype.FILTER and status == "CONNECTED":
        #{
            spfvalid = await self.isvalidfilter(pgdb.SportEventTuple, chatmsg.sport_filter)
            exfvalid = await self.isvalidfilter(pgdb.ExecutionTuple, chatmsg.execution_filter)

            if not spfvalid or not exfvalid:
                if not spfvalid: print(f"REJECTED_BADFILTER: {chatmsg.sport_filter}")                    
                if not exfvalid: print(f"REJECTED_BADFILTER: {chatmsg.execution_filter}")

                rstatusmsg = await self.create_rstatusmsg(
                    "REJECTED_BADFILTER", chatmsg.user, chatmsg.roomid)
                await self.persist_chatmsg(rstatusmsg)
                await websocket.send(rstatusmsg.SerializeToString()) 
            
            else:
                rfilt = self.rooms[roomid].filters
                if chatmsg.sport_filter != "SAME": rfilt[0] = chatmsg.sport_filter
                if chatmsg.execution_filter != "SAME": rfilt[1] = chatmsg.execution_filter
                
                print(f"FILTERAPPLIED: {rfilt[0]}")
                print(f"FILTERAPPLIED: {rfilt[1]}")

                rstatusmsg = await self.create_rstatusmsg(
                    "FILTERAPPLIED", chatmsg.user, chatmsg.roomid)
                await self.persist_chatmsg(rstatusmsg)
                await self.notify_users({roomid}, rstatusmsg.SerializeToString())
        #}
        elif chatmsg.mtype == cmpb2.msgtype.COMMENT and status == "CONNECTED":
            await self.notify_users({roomid}, bmessage)

        else: print(f"ERROR: bad inbound msgtype: {chatmsg.mtype}")
    #}
    
    async def create_rstatusmsg(self, userstatus, user='unknown', roomid=-1):
    #{
        rstatusmsg = cmpb2.chatmessage()
        rstatusmsg.mtype = cmpb2.msgtype.ROOM_STATUS
        rstatusmsg.userstatus = userstatus 
        rstatusmsg.numrooms = len(self.rooms)

        for room in self.rooms:
            rstatus = cmpb2.roomstatus()
            rstatus.roomid = room.roomid
            rstatus.maxusers = room.maxusers 
            for ruser in room.activeusers:
                rstatus.currusers.append(ruser)
            
            rstatusmsg.rooms.append(rstatus)
            if room.roomid == roomid:
                rstatusmsg.sport_filter = room.filters[0]
                rstatusmsg.execution_filter = room.filters[1]
    
        rstatusmsg.user = user
        rstatusmsg.roomid = roomid
        return rstatusmsg
    #}

    async def persist_chatmsg(self, chatmsg):
    #{
        with pgdb.PostgreSqlHandle() as db_handle:
            if db_handle is not None:
                chateventtup = pgdb.ChatEventTuple(
                    timetag=int(time.time()), msgtype=chatmsg.mtype, 
                    userstatus=chatmsg.userstatus, username=chatmsg.user, 
                    roomid=chatmsg.roomid, commentxt=chatmsg.comment, 
                    sportfilter=chatmsg.sport_filter, 
                    execfilter=chatmsg.execution_filter)
                db_handle.sqlquery(pgdb.ChatEventTuple.insertproto, 
                    chateventtup.insertdata())

            else: print("WARNING: DATABASE connect fail, not persisting msg:\n", chatmsg)
    #}

    #####################################################
    ## NATS message handling branch starts here:

    async def readnats(self): 
    #{
        nats_client = Client()
        uri = f"{os.environ['NATS_HOST']}:{os.environ['NATS_PORT']}"
        await nats_client.connect(uri, loop=asyncio.get_event_loop())
        await nats_client.subscribe(os.environ['EXECUTION_TOPIC'], cb=self.handle_execmsg)
        await nats_client.subscribe(os.environ['EVENT_TOPIC'], cb=self.handle_eventmsg)

        # Loop until SIGINT or SIGTERM
        while self.keeprunning: await asyncio.sleep(1)
        await nats_client.close()
    #}

    async def isvalidfilter(self, classref, where):
    #{
        if where == "NONE" or where == "ALL" or where == "SAME": return True
        else: 
            with pgdb.PostgreSqlHandle() as db_handle:
                if db_handle: return db_handle.sqlquery(classref.filterproto(
                    where), [1], fetch='one', quiet=True) is not None
                else:
                    print(("WARNING: DATABASE connect fail, "
                    f"cannot validate/accept filter: {where}"))
                    return False
    #}

    async def apply_filters(self, classref, primarykey, filtidx):
    #{
        with pgdb.PostgreSqlHandle() as db_handle:
            if db_handle:
                    # Return set of roomids that are to recieve record at primarykey
                    return {rid for rid, where in [(room.roomid, room.filters[filtidx]) 
                    for room in self.rooms if room.activeusers] if where != "ALL" 
                    and db_handle.sqlquery(classref.filterproto(where), [primarykey], 
                    fetch='one')[0]}
            else:
                print("WARNING: DATABASE connect fail, NO filters applied.")
                return set(range(len(self.rooms)))            
    #}

    async def handle_eventmsg(self, natsmessage):
    #{
        natseventmsg = event_pb2.event()
        natseventmsg.ParseFromString(natsmessage.data)
        pkey = await self.persist_eventmsg(natseventmsg)
        ridset = await self.apply_filters(pgdb.SportEventTuple, pkey, 0)

        if ridset:
            wrappermsg = cmpb2.chatmessage()
            wrappermsg.mtype = cmpb2.msgtype.EVENT
            wrappermsg.eventmsg.CopyFrom(natseventmsg)
            bmessage = wrappermsg.SerializeToString()
            await self.notify_users(ridset, bmessage)
    #}

    async def handle_execmsg(self, natsmessage):
    #{
        natsexecmsg = execution_pb2.execution()
        natsexecmsg.ParseFromString(natsmessage.data)
        pkey = await self.persist_execmsg(natsexecmsg)
        ridset = await self.apply_filters(pgdb.ExecutionTuple, pkey, 1)

        if ridset:
            wrappermsg = cmpb2.chatmessage()
            wrappermsg.mtype = cmpb2.msgtype.EXECUTION
            wrappermsg.execmsg.CopyFrom(natsexecmsg)
            bmessage = wrappermsg.SerializeToString()
            await self.notify_users(ridset, bmessage)
    #}

    # Returns record primary_key or None
    async def persist_eventmsg(self, eventmsg):
    #{
        with pgdb.PostgreSqlHandle() as db_handle:
            if db_handle:
                eventtup = pgdb.SportEventTuple(timetag=int(time.time()), sport=eventmsg.sport, 
                    match_title=eventmsg.match_title, data_event=eventmsg.data_event)
                return db_handle.sqlquery(pgdb.SportEventTuple.insertproto, 
                    eventtup.insertdata(), fetch='one')[0]
            
            else: print("WARNING: DATABASE connect fail, not persisting msg:\n", eventmsg)
        
        return None
    #}

    # Returns record primary_key or None
    async def persist_execmsg(self, execmsg):
    #{
        with pgdb.PostgreSqlHandle() as db_handle:
            if db_handle:
                exectup = pgdb.ExecutionTuple(
                    timetag=int(time.time()), symbol=execmsg.symbol, 
                    market=execmsg.market, price=execmsg.price, quantity=execmsg.quantity, 
                    execution_epoch=execmsg.executionEpoch, state_symbol=execmsg.stateSymbol)
                return db_handle.sqlquery(pgdb.ExecutionTuple.insertproto,
                    exectup.insertdata(), fetch='one')[0]
            
            else: print("WARNING: DATABASE connect fail, not persisting msg:\n", execmsg)
        
        return None
    #}
#}

if __name__ == "__main__":
#{
    nrooms = int(os.environ['NUM_CHATROOMS'])
    port = int(os.environ['CONTAINER_PORT'])
    host = os.environ.get('CONTAINER_HOST', 'localhost')
    maxusers = list(map(int, os.environ['MAX_NUMUSERS'].\
        replace(' ', '')[1:-1].split(',')))

    service = ChatService(nrooms, maxusers)
    asyncio.get_event_loop().run_until_complete(
        service.initialize(host, port))
    asyncio.get_event_loop().close()
#}

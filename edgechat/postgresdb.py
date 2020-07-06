import os, psycopg2

class ChatEventTuple:
#{
    insertproto = ("INSERT INTO chat_event VALUES(DEFAULT, "
                   "%s, %s, %s, %s, %s, %s, %s, %s)")

    def __init__(self, chat_event_id=None, timetag=None, msgtype=None, 
                 userstatus=None, username=None, roomid=None, commentxt=None, 
                 sportfilter=None, execfilter=None):
        self.chat_event_id = chat_event_id
        self.timetag = timetag
        self.msgtype = msgtype
        self.userstatus = userstatus
        self.username = username
        self.roomid = roomid
        self.commentxt = commentxt
        self.sportfilter = sportfilter
        self.execfilter = execfilter

    def __repr__(self):
        return (f"ChatEventTuple: {self.chat_event_id}, {self.timetag}, "
                f"{self.msgtype}, {self.userstatus}, {self.username}, {self.roomid}, "
                f"{self.commentxt}, {self.sportfilter}, {self.execfilter}")

    def insertdata(self): 
        return [self.timetag, self.msgtype, self.userstatus, self.username, 
                self.roomid, self.commentxt, self.sportfilter, self.execfilter]
#}

class SportEventTuple:
#{
    _filterproto = "SELECT COUNT(*) FROM sport_event {} sport_event_id = %s"
    insertproto = ("INSERT INTO sport_event VALUES(DEFAULT, %s, %s, %s, %s) "
                   "RETURNING sport_event_id")

    @classmethod
    def filterproto(cls, wherefilter):
        return cls._filterproto.format("WHERE" if wherefilter == "NONE" 
            else f"WHERE ({wherefilter}) AND ")

    def __init__(self, sport_event_id=None, timetag=None, 
                 sport=None, match_title=None, data_event=None):
        self.sport_event_id = sport_event_id
        self.timetag = timetag
        self.sport = sport
        self.match_title = match_title
        self.data_event = data_event

    def __repr__(self): 
        return (f"SportEventTuple: {self.sport_event_id}, {self.timetag}, "
                f"{self.sport}, {self.match_title}, {self.data_event}")

    def insertdata(self):
        return [self.timetag, self.sport, self.match_title, self.data_event]
#}

class ExecutionTuple:
#{
    _filterproto = "SELECT COUNT(*) FROM execution {} execution_id = %s"
    insertproto = ("INSERT INTO execution VALUES(DEFAULT, %s, %s, %s, %s, %s, %s, %s) "
                   "RETURNING execution_id")

    @classmethod
    def filterproto(cls, wherefilter):
        wherefilter = wherefilter.replace('executionEpoch', 'execution_epoch')
        wherefilter = wherefilter.replace('stateSymbol', 'state_symbol')
        return cls._filterproto.format("WHERE" if wherefilter == "NONE" 
            else f"WHERE ({wherefilter}) AND ")

    def __init__(self, execution_id=None, timetag=None, symbol=None, market=None, 
                 price=None, quantity=None, execution_epoch=None, state_symbol=None):
        self.execution_id = execution_id
        self.timetag = timetag
        self.symbol = symbol
        self.market = market
        self.price = price
        self.quantity = quantity
        self.execution_epoch = execution_epoch
        self.state_symbol = state_symbol

    def __repr__(self): 
        return (f"ExecutionTuple: {self.execution_id}, {self.timetag}, "
                f"{self.symbol}, {self.market}, {self.price}, {self.quantity}, "
                f"{self.execution_epoch}, {self.state_symbol}")

    def insertdata(self):
        return [self.timetag, self.symbol, self.market, self.price, 
                self.quantity, self.execution_epoch, self.state_symbol]
#}

class PostgreSqlHandle: 
#{
    def __init__(self, verbose=False): 
        self._cursor = None
        self.dbconnection = None
        self.verbose = verbose
    
    def __enter__(self):
    #{
        self.dbconnection = None
        try:
        #{
            if self.verbose: print('Connecting to the PostgreSQL database...')
            self.dbconnection = psycopg2.connect(database=os.environ['DATABASE'],
                host=os.environ['POSTGRES_HOST'], port=os.environ['POSTGRES_PORT'],
                user=os.environ['DBUSER'], password=os.environ['DBPASSWORD'], )
            
            # Validate connection
            self.cursor = self.dbconnection.cursor()
            self.cursor.execute('SELECT version()')
            version = self.cursor.fetchone()
            if self.verbose: print(f"PostgreSQL version:\n  {version}")
        #}
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"PostgreSqlHandle::__enter__, ERROR: {error}")
            return None

        return self
    #}
    
    def __exit__(self, exception_type, exception_value, traceback):
    #{
        if self.cursor is not None:
            self.cursor.close(); self.cursor = None
        
        if self.dbconnection is not None:
            self.dbconnection.close(); self.dbconnection = None
    #}

    @property
    def cursor(self):
        if self._cursor is None and self.dbconnection is not None:
            self.cursor = self.dbconnection.cursor()
        return self._cursor

    @cursor.setter
    def cursor(self, value): 
        self._cursor = value 

    def sqlquery(self, sqlproto, paramdata=None, fetch=None, quiet=False):
    #{
        result = None
        try:
            # if sqlproto.startswith("SELECT"): print(sqlproto, paramdata)

            self.cursor.execute(sqlproto, paramdata)
            if fetch == 'all': result = self.cursor.fetchall()
            elif fetch == 'one': result = self.cursor.fetchone()
            elif fetch is not None: result = self.cursor.fetchmany(fetch)
            self.dbconnection.commit()

        except (Exception, psycopg2.DatabaseError) as error:
            if not quiet: 
                print("PostgreSqlHandle::sqlquery, ERROR:", error)
                print(sqlproto, paramdata)
        finally: return result
    #}
#}

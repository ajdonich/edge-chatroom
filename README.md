## Project: edge-chatroom 

This project implements a basic chatroom service with message persistence. It consists of five containerized services: two "external" message feed simulators (borrowed from container images at: [hub.docker/wsumfest](https://hub.docker.com/u/wsumfest)), a NATS message broker, a PostgreSql database and the chatroom service itself. It was developed and tested using Docker Desktop on MacOS and the containers are Alpine Linux based configurations. The repo also contains a chatroom-client simulator, many instances of which can be run simultaneously to drive the chatroom service over websockets. Instructions on running these simulators are provided below.

### Client-Service Interface:

System environment configuration is defined in [docker-compose.yml](https://github.com/ajdonich/edge-chatroom/blob/master/docker-compose.yml) and [postgres/dbconfig.env](https://github.com/ajdonich/edge-chatroom/blob/master/postgres/dbconfig.env) (for database config). My container images have been tagged and published at: ([hub.docker/ajdonich](https://hub.docker.com/u/ajdonich)) and are referenced by this default configuration. All messages in the system are serialized with protobuf. The specs can be found in the repo's proto directory, in particular: [proto/chatmessage.proto](https://github.com/ajdonich/edge-chatroom/blob/master/proto/chatmessage.proto) defines the frontend-to-chatroom interface. 

This single specification defines all exchanged websockets messages; message content is differentiated by the **required msgtype mtype** field. Other fields are generally optional and msgtype dependant. A **ROOM_STATUS** message is sent to the client to convey relevant state information, along with the **string userstatus** field of the form, **VALIDATIONS:** "PENDING", "USERJOINED, "USEREXITED", and "FILTERAPPLIED", and **ERRORS:** "DENIED_BADROOMID", "DENIED_NAMETAKEN", "DENIED_ROOMFULL", and "REJECTED_BADFILTER". The expected exchange protocols can be illustrated as follows:

**Join Room:**
| Client | <=> | Messages/Actions       | <=> | Service  | 
| ------ | --- | ---------------------- | --- | -------- |
|  user  |  :  | listen(host, port)     | <-  | chatroom |
|  user  |  -> | connect(host, port)    |  -> | chatroom |
|  user  | <-  | ROOM_STATUS(PENDING)   | <-  | chatroom |
|  user  | ->  | JOIN_REQ(name, room)   | ->  | chatroom |
|  user  | <=  | ROOM_STATUS(JOINED)    | <=  | chatroom |
|  user  | <-  | or ROOM_STATUS(DENIED) | <-  | chatroom |  


**Filter Feed Messages:**
| Client | <=> | Messages/Actions         | <=> | Service  | 
| ------ | --- | ------------------------ | --- | -------- |
|  user  |  -> | FILTER(bool_sql_where)   | ->  | chatroom |
|  user  | <=  | ROOM_STATUS(APPLIED)     | <=  | chatroom |
|  user  | <-  | or ROOM_STATUS(REJECTED) | <-  | chatroom |

**Comment Broadcast:**
| Client | <=> | Messages/Actions       | <=> | Service  | 
| ------ | --- | ---------------------- | --- | -------- |
|  user  | ->  | COMMENT(name, room)    | ->  | chatroom |
|  user  | <=  | COMMENT(name, room)    | <=  | chatroom |

**Feed Data Broadcast:**
| Client | <=> | Messages/Actions       | <=> | Service  | 
| ------ | --- | ---------------------- | --- | -------- |
|  feed  | ->  | NATS-message(data)     | ->  | chatroom |
|  user  | <=  | EVENT/EXECUTION(data)  | <=  | chatroom |

**User Disconnect Broadcast:**
| Client | <=> | Messages/Actions       | <=> | Service  | 
| ------ | --- | ---------------------- | --- | -------- |
|  user  |  :  | websocket disconnect   |  -> | chatroom |
|  user  | <=  | ROOM_STATUS(USEREXIT)  | <=  | chatroom |

___


### Data Persistence and Filtering:

All data persistence is accomplished with a PostgreSql v.12 relational database service. Three tables are used: **sport_event** and **execution** for feed data, and **chat_event** for persistence of all comments and other message events. If you prefer, the default configurations mentioned above expose an external DB port (5444) and DB login params to enable a pgAdmin tool to easily connect to examine the database state. **Note:** the default [docker-compose.yml](https://github.com/ajdonich/edge-chatroom/blob/master/docker-compose.yml) configuration does **not** currently create a container volume/mount to permanently store data between container cycling.

Feed data filters are implemented using SQL WHERE \<clause\> syntax, "NONE" to filter nothing out, "ALL" to filter everything out, or "SAME" to leave an existing filter unchanged. Feed messages are first persisted, then queried against room filters using the database query engine. This enables flexible boolean filter operations, but puts the onus on the client to formulate SQL syntax. Filter requests with invalid filter syntax will be rejected by the chatroom service. For a tested example collection of both valid and invalid filters, please examine the first 40 lines of the client simulator at [clientsim/chatsimulator.py](https://github.com/ajdonich/edge-chatroom/blob/master/clientsim/chatsimulator.py).

___


### Installation and Execution:

To run the client simulators or extend this repository, either miniconda or straight pip can be used for installation; it includes both a conda [edge-chatroom.yml](https://github.com/ajdonich/edge-chatroom/blob/master/edge-chatroom.yml) env file and a [requirements.txt](https://github.com/ajdonich/edge-chatroom/blob/master/requirements.txt) file. For miniconda, it can be downloaded and installed here: [Miniconda Installation Instructions](https://docs.conda.io/en/latest/miniconda.html), then from a terminal execute:

```
$ git clone https://github.com/ajdonich/edge-chatroom.git
$ cd edge-chatroom
$ conda env create -f edge-chatroom.yml
```

Docker Desktop or a comparable container management system is necessary to run this service. To install Docker see: [Docker Download and Installation](https://www.docker.com/products/docker-desktop). Start Docker Desktop then execute:

```
$ docker-compose up -d
```

This will launch the collection of five containers, which you can examine using Docker Desktop. To run a client simulator test sequence, I suggest opening five terminal windows, one to run the filter test and four others to participate peripherally. In each terminal execute:

```
$ cd edge-chatroom
$ conda activate edge-chatroom
```

Then copy and execute one of these five lines in each of the five respective terminals:

```
$ python -m clientsim.chatsimulator adam --roomid 3 --filter True
$ python -m clientsim.chatsimulator bobby --roomid 3
$ python -m clientsim.chatsimulator carol --roomid 2
$ python -m clientsim.chatsimulator daniel --roomid 2
$ python -m clientsim.chatsimulator erik --roomid 1
```

All users will receive feed messages and randomly send comments to the service. The peripheral participants bobby, carol, daniel and erik will also randomly disconnect 1% of the time. You can restart them as you prefer, trying different rooms or usernames, etc. User adam will also send a sequence of filter requests that isolate the sport_event feed and the execution feed respectively, allowing an examination of the effect, and all taking about 5-10 minutes to complete.

___



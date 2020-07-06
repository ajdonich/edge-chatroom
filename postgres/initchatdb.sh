#!/bin/bash
set -e

export PGPASSFILE=~/.pgpass
if [ ! -f "$PGPASSFILE" ]; then
    echo ${POSTGRES_HOST}:${POSTGRES_PORT}:${POSTGRES_DB}:${POSTGRES_USER}:${POSTGRES_PASSWORD} | tee -a ${PGPASSFILE} >/dev/null
    echo ${POSTGRES_HOST}:${POSTGRES_PORT}:${DATABASE}:${DBUSER}:${DBPASSWORD} | tee -a ${PGPASSFILE} >/dev/null
    chmod 600 ${PGPASSFILE}
fi

psql -v ON_ERROR_STOP=1 -U ${POSTGRES_USER} -d ${POSTGRES_DB} -p ${POSTGRES_PORT} <<-EOSQL
    CREATE DATABASE ${DATABASE};
    CREATE USER ${DBUSER} with ENCRYPTED PASSWORD '${DBPASSWORD}';
    GRANT ALL PRIVILEGES ON DATABASE ${DATABASE} TO ${DBUSER};
EOSQL

psql -v ON_ERROR_STOP=1 -U ${DBUSER} -d ${DATABASE} -p ${POSTGRES_PORT} <<-EOSQL
    CREATE TABLE chat_event (
        chat_event_id SERIAL PRIMARY KEY,
        timetag BIGINT NOT NULL,
        msgtype INTEGER,
        userstatus VARCHAR(32),
        username VARCHAR(64),
        roomid INTEGER,
        commentxt VARCHAR,
        sportfilter VARCHAR(256),
        execfilter VARCHAR(256));
    CREATE INDEX ON chat_event (chat_event_id, username, roomid);

    CREATE TABLE sport_event (
        sport_event_id SERIAL PRIMARY KEY,
        timetag BIGINT NOT NULL,
        sport INTEGER NOT NULL,
        match_title VARCHAR NOT NULL,
        data_event VARCHAR NOT NULL);
    CREATE INDEX ON sport_event (sport_event_id, sport, match_title);

    CREATE TABLE execution (
        execution_id SERIAL PRIMARY KEY,
        timetag BIGINT NOT NULL,
        symbol VARCHAR(128) NOT NULL,
        market VARCHAR(32) NOT NULL,
        price NUMERIC NOT NULL,
        quantity NUMERIC NOT NULL,
        execution_epoch BIGINT NOT NULL,
        state_symbol VARCHAR(2) NOT NULL);
    CREATE INDEX ON execution (execution_id, symbol, market, execution_epoch, state_symbol);
EOSQL
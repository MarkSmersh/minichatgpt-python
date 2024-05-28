from typing import Optional, Any

import psycopg
from dotenv import load_dotenv
from os import getenv

from psycopg import AsyncConnection
from psycopg.abc import Query, Params

load_dotenv()


class Database:
    conn: AsyncConnection[tuple[Any, ...]]

    async def start(self):
        await self.init_tables()

        print("Database has started")

    async def init_tables(self):
        # await self.execute("DROP TABLE IF EXISTS users")
        # await self.execute("DROP TABLE IF EXISTS transactions")

        try:
            await self.execute('''CREATE TABLE IF NOT EXISTS transactions (
                            id SERIAL primary key,
                            chatId BIGINT NOT NULL,
                            tokens int NOT NULL,
                            model VARCHAR(255) NOT NULL
                        );''')

            await self.execute('''CREATE TABLE IF NOT EXISTS users (
                            id SERIAL primary key,
                            chatId BIGINT unique NOT NULL,
                            firstname varchar(255),
                            lastname varchar(255),
                            tokens int DEFAULT 0,
                            balance float DEFAULT 0,
                            state varchar(255) NOT NULL,
                            access int default 0 /*0 - no access, 1 - user, 2 - admin */
                        );''')
        except:
            pass

    async def connect(self):
        return await psycopg.AsyncConnection.connect(getenv("DB_STRING"), autocommit=True)

    async def cursor(self):
        return (await self.connect()).cursor()

    async def execute(self, query: Query, params: Optional[Params] = None):
        return await (await self.cursor()).execute(query, params)

    async def fetchone(self, query: Query, params: Optional[Params] = None):
        return await (await self.execute(query, params)).fetchone()

    async def fetchmany(self, query: Query, params: Optional[Params] = None):
        return await (await self.execute(query, params)).fetchall()


db = Database()

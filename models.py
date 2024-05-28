from typing import TypedDict

from db import db


Transaction = TypedDict('Transaction', {"id": int, "chat_id": int, "tokens": int, "model": str})
User = TypedDict("User", {"id": int, "chat_id": int, "firstname": str, "lastname": str, "tokens": int, "balance": float, "state": str, "access": int})


class Transactions:
    def __init__(self):
        pass
    async def findmany(self, chat_id: int) -> list[Transaction] | None:
        rows = await db.fetchmany("SELECT * FROM transactions WHERE chatId = %s", (chat_id,))
        transactions_list: list[Transaction] = []
        if rows:
            for row in rows:
                transactions_list.append(self.format(row))
            return transactions_list

    async def findone(self, transaction_id: int) -> Transaction | None:
        row = await db.fetchmany("SELECT * FROM transactions WHERE id = %s", (transaction_id,))
        if row:
            return row

    async def create(self, chat_id: int, tokens: int, model: str) -> Transaction | None:
        try:
            await db.execute("INSERT INTO transactions (chatId, tokens, model) VALUES (%s, %s, %s)", (chat_id, tokens, model))
            row = await self.findone(chat_id)
            return row
        except:
            return

    def format(self, row: list):
        return {"id": row[0], "chat_id": row[1], "tokens": row[2], "model": row[3]}


class Users:
    def __init__(self):
        pass

    async def findone(self, chat_id: int) -> User | None:
        row = await db.fetchone("SELECT * FROM users WHERE chatId = %s", (chat_id,))
        if row:
            return self.format(row)

    async def findmany(self, access: int) -> list[User] | None:
        rows = await db.fetchmany("SELECT * FROM users WHERE access = %s", (access,))
        users_list: list[User] = []
        if rows:
            for row in rows:
                users_list.append(self.format(row))
            return users_list

    async def create(self, chat_id: int, firstname: str, lastname: str, state: str) -> User | None:
        try:
            await db.execute("INSERT INTO users (chatId, firstname, lastname, state) VALUES (%s, %s, %s, %s)", (chat_id, firstname, lastname, state))
            row = await self.findone(chat_id)
            return row
        except Exception as e:
            print(e)
            pass

    def format(self, row: list) -> User:
        return {"id": row[0], "chat_id": row[1], "firstname": row[2], "lastname": row[3], "tokens": row[4], "balance": row[5], "state": row[6], "access": row[7]}


transactions = Transactions()
users = Users()

import json
import time
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

####################
# Chat DB Schema
####################

class ChatModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    chat_id: str
    request: str
    response: str
    rai_model: str
    ai_model: str
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    share_id: Optional[str] = None
    archived: bool = False

class ChatForm(BaseModel):
    chat_id: str
    request: str
    response: str
    rai_model: str
    ai_model: str

class ChatTitleForm(BaseModel):
    title: str

class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: str
    chat_id: str
    request: str
    response: str
    rai_model: str
    ai_model: str
    updated_at: int
    created_at: int
    share_id: Optional[str] = None
    archived: bool

class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int

CHAT_COLUMNS = [
    "id",
    "user_id",
    "title",
    "chat_id",
    "request",
    "response",
    "rai_model",
    "ai_model",
    "created_at",
    "updated_at",
    "share_id",
    "archived",
]

def row_to_chatmodel(row: tuple) -> Optional[ChatModel]:
    if not row:
        return None
    data = dict(zip(CHAT_COLUMNS, row))
    return ChatModel(**data)

class ChatArchiveTable:
    def __init__(self, client):
        self.client = client

    def create_chat_table(self):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS "chat" (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            chat_id TEXT,
            request TEXT,
            response TEXT,
            rai_model TEXT,
            ai_model TEXT,
            created_at BIGINT,
            updated_at BIGINT,
            share_id TEXT UNIQUE,
            archived BOOLEAN DEFAULT FALSE
        )
        """
        try:
            self.client.cursor.execute(create_table_query)
            self.client.connection.commit()
            print("Chat table created or already exists.")
        except Exception as e:
            print(f"Error creating chat table: {e}")
            self.client.connection.rollback()

    def insert_new_chat(self, user_id: str, chat_id: str, request: str, response: str, rai_model: str, ai_model: str) -> Optional[ChatModel]:
        try:
            return self.insert_new_chat_by_form(user_id, ChatForm(
                chat_id=chat_id,
                request=request,
                response=response,
                rai_model=rai_model,
                ai_model=ai_model,
            ))
        except Exception as e:
            print(f"Error creating chat archive: {e}")

    def insert_new_chat_by_form(self, user_id: str, form_data: ChatForm) -> Optional[ChatModel]:
        new_id = str(uuid.uuid4())
        title = "Single Chat Message"
        # chat_json = json.dumps(form_data.chat)
        now = int(time.time())

        query = """
        INSERT INTO "chat" (id, user_id, title, chat_id, request, response, rai_model, ai_model, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """
        try:
            self.client.cursor.execute(query, (new_id, user_id, title, form_data.chat_id, form_data.request, form_data.response, form_data.rai_model, form_data.ai_model, now, now))
            row = self.client.cursor.fetchone()
            self.client.connection.commit()
            return row_to_chatmodel(row)
        except Exception as e:
            print(f"Error inserting new chat: {e}")
            self.client.connection.rollback()
            return None

    def get_chat_list_by_user_id(self, user_id: str, include_archived: bool = False, skip: int = 0, limit: int = 50) -> List[ChatModel]:
        if include_archived:
            query = 'SELECT * FROM "chat" WHERE user_id = %s ORDER BY updated_at DESC'
            params = (user_id,)
        else:
            query = 'SELECT * FROM "chat" WHERE user_id = %s AND archived = FALSE ORDER BY updated_at DESC'
            params = (user_id,)
        try:
            self.client.cursor.execute(query, params)
            rows = self.client.cursor.fetchall()
            return [cm for cm in (row_to_chatmodel(r) for r in rows) if cm]
        except Exception:
            return []

    def get_chat_title_id_list_by_user_id(self, user_id: str, include_archived: bool = False, skip: Optional[int] = None, limit: Optional[int] = None) -> List[ChatTitleIdResponse]:
        if include_archived:
            base_query = 'SELECT id, title, updated_at, created_at FROM "chat" WHERE user_id = %s ORDER BY updated_at DESC'
        else:
            base_query = 'SELECT id, title, updated_at, created_at FROM "chat" WHERE user_id = %s AND archived = FALSE ORDER BY updated_at DESC'

        try:
            query = base_query
            params = [user_id]
            if limit:
                query += f" LIMIT {limit}"
            if skip:
                query += f" OFFSET {skip}"

            self.client.cursor.execute(query, tuple(params))
            rows = self.client.cursor.fetchall()
            # rows = [(id, title, updated_at, created_at), ...]
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        "id": r[0],
                        "title": r[1],
                        "updated_at": r[2],
                        "created_at": r[3],
                    }
                )
                for r in rows
            ]
        except Exception:
            return []

    def get_chat_list_by_chat_ids(self, chat_ids: List[str], skip: int = 0, limit: int = 50) -> List[ChatModel]:
        if not chat_ids:
            return []
        query = 'SELECT * FROM "chat" WHERE id = ANY(%s) AND archived = FALSE ORDER BY updated_at DESC'
        try:
            self.client.cursor.execute(query, (chat_ids,))
            rows = self.client.cursor.fetchall()
            return [cm for cm in (row_to_chatmodel(r) for r in rows) if cm]
        except Exception:
            return []

    def get_chat_by_id(self, id: str) -> Optional[ChatModel]:
        query = 'SELECT * FROM "chat" WHERE id = %s'
        try:
            self.client.cursor.execute(query, (id,))
            row = self.client.cursor.fetchone()
            return row_to_chatmodel(row)
        except Exception:
            return None

    def get_chat_by_share_id(self, id: str) -> Optional[ChatModel]:
        # If a chat exists with this share_id, return get_chat_by_id(id)
        query = 'SELECT * FROM "chat" WHERE share_id = %s'
        try:
            self.client.cursor.execute(query, (id,))
            row = self.client.cursor.fetchone()
            if row:
                # id here is the same string we searched by share_id
                return self.get_chat_by_id(id)
            return None
        except Exception:
            return None

    def get_chat_by_id_and_user_id(self, id: str, user_id: str) -> Optional[ChatModel]:
        query = 'SELECT * FROM "chat" WHERE id = %s AND user_id = %s'
        try:
            self.client.cursor.execute(query, (id, user_id))
            row = self.client.cursor.fetchone()
            return row_to_chatmodel(row)
        except Exception:
            return None

    def get_chats(self, skip: int = 0, limit: int = 50) -> List[ChatModel]:
        query = 'SELECT * FROM "chat" ORDER BY updated_at DESC'
        try:
            self.client.cursor.execute(query)
            rows = self.client.cursor.fetchall()
            return [cm for cm in (row_to_chatmodel(r) for r in rows) if cm]
        except Exception:
            return []

    def get_chats_by_user_id(self, user_id: str) -> List[ChatModel]:
        query = 'SELECT * FROM "chat" WHERE user_id = %s ORDER BY updated_at DESC'
        try:
            self.client.cursor.execute(query, (user_id,))
            rows = self.client.cursor.fetchall()
            return [cm for cm in (row_to_chatmodel(r) for r in rows) if cm]
        except Exception:
            return []

    def get_archived_chats_by_user_id(self, user_id: str) -> List[ChatModel]:
        query = 'SELECT * FROM "chat" WHERE user_id = %s AND archived = TRUE ORDER BY updated_at DESC'
        try:
            self.client.cursor.execute(query, (user_id,))
            rows = self.client.cursor.fetchall()
            return [cm for cm in (row_to_chatmodel(r) for r in rows) if cm]
        except Exception:
            return []

    def delete_chat_by_id(self, id: str) -> bool:
        query = 'DELETE FROM "chat" WHERE id = %s'
        try:
            self.client.cursor.execute(query, (id,))
            self.client.connection.commit()
            # also delete shared version
            return True and self.delete_shared_chat_by_chat_id(id)
        except Exception:
            self.client.connection.rollback()
            return False

    def delete_chat_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        query = 'DELETE FROM "chat" WHERE id = %s AND user_id = %s'
        try:
            self.client.cursor.execute(query, (id, user_id))
            self.client.connection.commit()
            # also delete shared version
            return True and self.delete_shared_chat_by_chat_id(id)
        except Exception:
            self.client.connection.rollback()
            return False

    def delete_chats_by_user_id(self, user_id: str) -> bool:
        try:
            # First delete shared chats associated with user's chats
            self.delete_shared_chats_by_user_id(user_id)

            query = 'DELETE FROM "chat" WHERE user_id = %s'
            self.client.cursor.execute(query, (user_id,))
            self.client.connection.commit()
            return True
        except Exception:
            self.client.connection.rollback()
            return False

    def delete_shared_chats_by_user_id(self, user_id: str) -> bool:
        # Get all chat ids for this user
        try:
            select_query = 'SELECT id FROM "chat" WHERE user_id = %s'
            self.client.cursor.execute(select_query, (user_id,))
            rows = self.client.cursor.fetchall()
            chat_ids = [r[0] for r in rows]

            if not chat_ids:
                return True

            # For each chat_id, shared chat user_id is "shared-{chat_id}"
            shared_user_ids = [f"shared-{cid}" for cid in chat_ids]

            # Delete all chats where user_id in shared_user_ids
            delete_query = 'DELETE FROM "chat" WHERE user_id = ANY(%s)'
            self.client.cursor.execute(delete_query, (shared_user_ids,))
            self.client.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleting shared chats by user_id: {e}")
            self.client.connection.rollback()
            return False


# Example usage:
# from your_postgres_client_setup import PostgresClient
# client = PostgresClient()
# Chats = ChatTable(client)
# Chats.create_chat_table()
# form_data = ChatForm(chat={"title": "My First Chat", "messages": []})
# new_chat = Chats.insert_new_chat("user-xyz", form_data)
# print(new_chat)

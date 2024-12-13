import time
from typing import Optional

from pydantic import BaseModel, ConfigDict

####################
# Prompts DB Schema
####################

class PromptModel(BaseModel):
    command: str
    user_id: str
    title: str
    content: str
    timestamp: int  # timestamp in epoch
    model_config = ConfigDict(from_attributes=True)

class PromptForm(BaseModel):
    command: str
    title: str
    content: str

# Column order used when retrieving rows from the database
PROMPT_COLUMNS = ["command", "user_id", "title", "content", "timestamp"]

def row_to_promptmodel(row: tuple) -> Optional[PromptModel]:
    if not row:
        return None
    data = dict(zip(PROMPT_COLUMNS, row))
    return PromptModel(**data)

class PromptsTable:
    def __init__(self, client):
        self.client = client

    def create_prompt_table(self) -> None:
        """
        Create the 'prompt' table if it does not already exist.
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS "prompt" (
            command TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            content TEXT,
            timestamp BIGINT
        )
        """
        try:
            self.client.cursor.execute(create_table_query)
            self.client.connection.commit()
            print("Prompt table created or already exists.")
        except Exception as e:
            print(f"Error creating prompt table: {e}")
            self.client.connection.rollback()

    def insert_new_prompt(
        self, user_id: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        prompt = PromptModel(
            command=form_data.command,
            user_id=user_id,
            title=form_data.title,
            content=form_data.content,
            timestamp=int(time.time())
        )

        record = prompt.model_dump()
        columns = ", ".join(record.keys())
        placeholders = ", ".join([f"%({k})s" for k in record.keys()])
        query = f"INSERT INTO \"prompt\" ({columns}) VALUES ({placeholders}) RETURNING *"

        try:
            self.client.cursor.execute(query, record)
            row = self.client.cursor.fetchone()
            self.client.connection.commit()
            return row_to_promptmodel(row)
        except Exception as e:
            print(f"Error inserting new prompt: {e}")
            self.client.connection.rollback()
            return None

    def get_prompt_by_command(self, command: str) -> Optional[PromptModel]:
        query = 'SELECT * FROM "prompt" WHERE command = %s'
        try:
            self.client.cursor.execute(query, (command,))
            row = self.client.cursor.fetchone()
            return row_to_promptmodel(row)
        except Exception as e:
            print(f"Error getting prompt by command: {e}")
            return None

    def get_prompts(self) -> list[PromptModel]:
        query = 'SELECT * FROM "prompt"'
        try:
            self.client.cursor.execute(query)
            rows = self.client.cursor.fetchall()
            return [pm for pm in (row_to_promptmodel(row) for row in rows) if pm]
        except Exception as e:
            print(f"Error getting prompts: {e}")
            return []

    def update_prompt_by_command(
        self, command: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        now = int(time.time())
        query = """
            UPDATE "prompt" 
            SET title = %s, content = %s, timestamp = %s
            WHERE command = %s
            RETURNING *
        """
        try:
            self.client.cursor.execute(query, (form_data.title, form_data.content, now, command))
            row = self.client.cursor.fetchone()
            self.client.connection.commit()
            return row_to_promptmodel(row)
        except Exception as e:
            print(f"Error updating prompt by command: {e}")
            self.client.connection.rollback()
            return None

    def delete_prompt_by_command(self, command: str) -> bool:
        query = 'DELETE FROM "prompt" WHERE command = %s'
        try:
            self.client.cursor.execute(query, (command,))
            self.client.connection.commit()
            return self.client.cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting prompt by command: {e}")
            self.client.connection.rollback()
            return False


# Example usage:
# from your_postgres_client_setup import PostgresClient
# client = PostgresClient()
# prompts = PromptsTable(client)
# prompts.create_prompt_table()
#
# form_data = PromptForm(command="test_cmd", title="Test Title", content="Test Content")
# user_id = "user-xyz-123"
# new_prompt = prompts.insert_new_prompt(user_id, form_data)
# print(new_prompt)

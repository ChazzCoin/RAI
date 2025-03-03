import logging
import time
from typing import Optional

from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)

####################
# Files DB Schema
####################

class FileModel(BaseModel):
    id: str
    user_id: str
    filename: str
    meta: dict
    created_at: int  # timestamp in epoch
    model_config = ConfigDict(from_attributes=True)

class FileModelResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    meta: dict
    created_at: int  # timestamp in epoch

class FileForm(BaseModel):
    id: str
    filename: str
    meta: dict = {}
    model_config = ConfigDict(extra="forbid")

# Column order used when retrieving rows from the database
FILE_COLUMNS = ["id", "user_id", "filename", "meta", "created_at"]

def row_to_filemodel(row: tuple) -> Optional[FileModel]:
    if not row:
        return None
    data = dict(zip(FILE_COLUMNS, row))
    return FileModel(**data)

class FilesTable:
    def __init__(self, client):
        self.client = client

    def create_file_table(self) -> None:
        """
        Create the 'file' table if it does not already exist.
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS "file" (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            filename TEXT,
            meta JSONB,
            created_at BIGINT
        )
        """
        try:
            self.client.cursor.tool(create_table_query)
            self.client.connection.commit()
            print("File table created or already exists.")
        except Exception as e:
            print(f"Error creating file table: {e}")
            self.client.connection.rollback()

    def insert_new_file(self, user_id: str, form_data: FileForm) -> Optional[FileModel]:
        file = FileModel(
            id=form_data.id,
            user_id=user_id,
            filename=form_data.filename,
            meta=form_data.meta,
            created_at=int(time.time()),
        )

        record = file.model_dump()
        try:
            self.client.add_record("file", record)
            self.client.connection.commit()
            return file
        except Exception as e:
            print(f"Error creating file: {e}")
            self.client.connection.rollback()
            return None

    def get_file_by_id(self, id: str) -> Optional[FileModel]:
        try:
            query = 'SELECT * FROM "file" WHERE id = %s'
            self.client.cursor.tool(query, (id,))
            row = self.client.cursor.fetchone()
            return row_to_filemodel(row)
        except Exception as e:
            print(f"Error getting file by id: {e}")
            return None

    def get_files(self) -> list[FileModel]:
        try:
            query = 'SELECT * FROM "file"'
            self.client.cursor.tool(query)
            rows = self.client.cursor.fetchall()
            return [row_to_filemodel(row) for row in rows if row]
        except Exception as e:
            print(f"Error getting files: {e}")
            return []

    def get_files_by_user_id(self, user_id: str) -> list[FileModel]:
        try:
            query = 'SELECT * FROM "file" WHERE user_id = %s'
            self.client.cursor.tool(query, (user_id,))
            rows = self.client.cursor.fetchall()
            return [row_to_filemodel(row) for row in rows if row]
        except Exception as e:
            print(f"Error getting files by user_id: {e}")
            return []

    def delete_file_by_id(self, id: str) -> bool:
        try:
            query = 'DELETE FROM "file" WHERE id = %s'
            self.client.cursor.tool(query, (id,))
            self.client.connection.commit()
            return self.client.cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting file: {e}")
            self.client.connection.rollback()
            return False

    def delete_all_files(self) -> bool:
        try:
            query = 'DELETE FROM "file"'
            self.client.cursor.tool(query)
            self.client.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleting all files: {e}")
            self.client.connection.rollback()
            return False


# Example usage:
# from your_postgres_client_setup import PostgresClient
# client = PostgresClient()
# files = FilesTable(client)
# files.create_file_table()

# file_form_data = FileForm(
#     id="unique-file-id-123",
#     filename="image.png",
#     meta={"description": "Sample image file", "tags": ["sample", "image"]}
# )
# user_id = "user-abc-123"
# inserted_file = files.insert_new_file(user_id, file_form_data)
# print(inserted_file)

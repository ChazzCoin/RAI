import json
import uuid

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any

class AIModelDetails(BaseModel):
    parent_model: str = ""
    format: str = ""
    family: str = ""
    families: List[str] = []
    parameter_size: str = ""
    quantization_level: str = ""
    model_config = ConfigDict(extra="allow")

class AIModelData(BaseModel):
    id: str
    name: str
    model: str
    zip: str
    address: str
    title: str
    initials: str
    ai_name: str
    ai_flow: str
    org_rep_type: str
    collection: str
    prompt: str
    context_prompt: str
    openai: str
    ollama: str
    org_type: str
    org_specialty: str
    modified_at: str
    size: int
    digest: str
    details: AIModelDetails
    model_config = ConfigDict(from_attributes=True)


def row_to_aimodel(row: tuple) -> Optional[AIModelData]:
    if not row:
        return None
    columns = [
        "id",
        "name",
        "model",
        "zip",
        "address",
        "title",
        "initials",
        "ai_name",
        "ai_flow",
        "org_rep_type",
        "collection",
        "prompt",
        "context_prompt",
        "openai",
        "ollama",
        "org_type",
        "org_specialty",
        "modified_at",
        "size",
        "digest",
        "details",
    ]
    data_dict = dict(zip(columns, row))
    # details is JSON, so we need to parse it back to AIModelDetails
    if data_dict["details"] is not None:
        data_dict["details"] = AIModelDetails(**data_dict["details"])
    return AIModelData(**data_dict)


class ModelsTable:
    def __init__(self, client):
        self.client = client

    def create_ai_model_table(self):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS ai_model (
            id TEXT PRIMARY KEY,
            name TEXT,
            model TEXT,
            zip TEXT,
            address TEXT,
            title TEXT,
            initials TEXT,
            ai_name TEXT,
            ai_flow TEXT,
            org_rep_type TEXT,
            collection TEXT,
            prompt TEXT,
            context_prompt TEXT,
            openai TEXT,
            ollama TEXT,
            org_type TEXT,
            org_specialty TEXT,
            modified_at TEXT,
            size BIGINT,
            digest TEXT,
            details JSONB
        );
        """
        try:
            self.client.cursor.execute(create_table_query)
            self.client.connection.commit()
            print("ai_model table created or already exists.")
        except Exception as e:
            print(f"Error creating ai_model table: {e}")
            self.client.connection.rollback()

    def insert_ai_model_from_json(self, data: dict) -> bool:
        """
        Insert a new AI model record from a raw JSON dictionary.
        Expects the dictionary to match the schema defined by AIModelData.
        """
        try:
            # Parse the dictionary into an AIModelData object
            if not data['id']:
                data['id'] = str(data['name'])
            ai_model_data = AIModelData(**data)
            return self.insert_ai_model(ai_model_data)
        except Exception as e:
            print(f"Error parsing and inserting ai_model from json: {e}")
            return False

    def insert_ai_model(self, data: AIModelData) -> bool:
        # Convert details to JSON
        details_json = json.dumps(data.model_dump())
        # Construct the insert query
        insert_query = f"""
            INSERT INTO ai_model (
                id,
                name,
                model,
                zip,
                address,
                title,
                initials,
                ai_name,
                ai_flow,
                org_rep_type,
                collection,
                prompt,
                context_prompt,
                openai,
                ollama,
                org_type,
                org_specialty,
                modified_at,
                size,
                digest,
                details
            ) VALUES (
                '{data.id}',
                '{data.name}',
                '{data.model}',
                '{data.zip}',
                '{data.address.replace("'", "''")}',
                '{data.title.replace("'", "''")}',
                '{data.initials}',
                '{data.ai_name}',
                '{data.ai_flow}',
                '{data.org_rep_type.replace("'", "''")}',
                '{data.collection}',
                '{data.prompt.replace("'", "''")}',
                '{data.context_prompt.replace("'", "''")}',
                '{data.openai}',
                '{data.ollama}',
                '{data.org_type.replace("'", "''")}',
                '{data.org_specialty.replace("'", "''")}',
                '{data.modified_at}',
                 {data.size},
                '{data.digest}',
                '{details_json.replace("'", "''")}'
            );
        """
        try:
            self.client.cursor.execute(insert_query)
            self.client.connection.commit()
            return True
        except Exception as e:
            print(f"Error inserting ai_model: {e}")
            self.client.connection.rollback()
            return False

    def get_ai_model_by_id(self, id: str) -> Optional[AIModelData]:
        query = f"SELECT * FROM ai_model WHERE id = '{id}';"
        try:
            self.client.cursor.execute(query)
            row = self.client.cursor.fetchone()
            return row_to_aimodel(row)
        except Exception as e:
            print(f"Error getting ai_model by id: {e}")
            return None

    def get_all_ai_models(self) -> List[AIModelData]:
        query = "SELECT * FROM ai_model;"
        try:
            self.client.cursor.execute(query)
            rows = self.client.cursor.fetchall()
            return [m for m in (row_to_aimodel(row) for row in rows) if m is not None]
        except Exception as e:
            print(f"Error getting all ai_models: {e}")
            return []

    def get_ai_model_by_name(self, model_name:str) -> List[AIModelData]:
        query = f"SELECT * FROM ai_model WHERE model = '{model_name}' OR name = '{model_name}';"
        try:
            self.client.cursor.execute(query)
            row = self.client.cursor.fetchone()
            return row_to_aimodel(row)
        except Exception as e:
            print(f"Error getting all ai_models: {e}")
            return []

    def update_ai_model(self, id: str, data: AIModelData) -> Optional[AIModelData]:
        # Convert details to JSON
        details_json = json.dumps(data.details.model_dump())

        # Build the SET clause
        # Escape single quotes to prevent SQL errors if no parameterization is used.
        updates = {
            "name": data.name,
            "model": data.model,
            "zip": data.zip,
            "address": data.address.replace("'", "''"),
            "title": data.title.replace("'", "''"),
            "initials": data.initials,
            "ai_name": data.ai_name,
            "ai_flow": data.ai_flow,
            "org_rep_type": data.org_rep_type.replace("'", "''"),
            "collection": data.collection,
            "prompt": data.prompt.replace("'", "''"),
            "context_prompt": data.context_prompt.replace("'", "''"),
            "openai": data.openai,
            "ollama": data.ollama,
            "org_type": data.org_type.replace("'", "''"),
            "org_specialty": data.org_specialty.replace("'", "''"),
            "modified_at": data.modified_at,
            "size": data.size,
            "digest": data.digest,
            "details": details_json.replace("'", "''")
        }

        set_parts = []
        for key, val in updates.items():
            if isinstance(val, int):
                part = f"{key} = {val}"
            else:
                part = f"{key} = '{val}'"
            set_parts.append(part)

        set_clause = ", ".join(set_parts)
        query = f"UPDATE ai_model SET {set_clause} WHERE id = '{id}' RETURNING *;"

        try:
            self.client.cursor.execute(query)
            updated_row = self.client.cursor.fetchone()
            self.client.connection.commit()
            return row_to_aimodel(updated_row)
        except Exception as e:
            print(f"Error updating ai_model by id: {e}")
            self.client.connection.rollback()
            return None

    def delete_ai_model(self, id: str) -> bool:
        query = f"DELETE FROM ai_model WHERE id = '{id}';"
        try:
            self.client.cursor.execute(query)
            self.client.connection.commit()
            return self.client.cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting ai_model by id: {e}")
            self.client.connection.rollback()
            return False

import time
import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict
from rai.models.chats import ChatArchiveTable


# Assuming UserModel and other classes defined as before
class UserSettings(BaseModel):
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")
    pass

class UserModel(BaseModel):
    name: str
    email: str
    role: str = "pending"
    profile_image_url: str

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    api_key: Optional[str] = None
    settings: Optional[UserSettings] = None
    info: Optional[dict] = None

    oauth_sub: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Columns in the 'user' table and their order:
USER_COLUMNS = [
    "id",
    "name",
    "email",
    "role",
    "profile_image_url",
    "last_active_at",
    "updated_at",
    "created_at",
    "api_key",
    "settings",
    "info",
    "oauth_sub",
]

def row_to_usermodel(row: tuple) -> Optional[UserModel]:
    if not row:
        return None
    data = dict(zip(USER_COLUMNS, row))
    # Convert to UserModel (settings and info JSON fields may be already parsed by psycopg, if not you'd need to parse them)
    return UserModel(**data)

class UsersTable:
    Chats: ChatArchiveTable

    def __init__(self, client):
        self.client = client
        self.Chats = ChatArchiveTable(client)

    def create_user_table(self):
        """
        Create the 'user' table if it does not already exist.
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS "user" (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            role TEXT,
            profile_image_url TEXT,
            last_active_at BIGINT,
            updated_at BIGINT,
            created_at BIGINT,
            api_key TEXT UNIQUE,
            settings JSONB,
            info JSONB,
            oauth_sub TEXT UNIQUE
        )
        """
        try:
            self.client.cursor.execute(create_table_query)
            self.client.connection.commit()
            print("User table created or already exists.")
        except Exception as e:
            print(f"Error creating user table: {e}")
            self.client.connection.rollback()

    def insert_new_user(
            self,
            name: str,
            email: str,
            profile_image_url: str = "/user.png",
            role: str = "pending",
            oauth_sub: Optional[str] = None,
    ) -> Optional[UserModel]:
        now = int(time.time())
        user_id = str(uuid.uuid4())

        # Prepare the values
        oauth_value = "NULL" if oauth_sub is None else f"'{oauth_sub}'"

        # Build the SQL query with all fields from the schema
        insert_query = f"""
            INSERT INTO "user" (
                id, 
                name, 
                email, 
                role, 
                profile_image_url, 
                last_active_at, 
                updated_at, 
                created_at, 
                api_key, 
                settings, 
                info, 
                oauth_sub
            )
            VALUES (
                '{user_id}',
                '{name}',
                '{email}',
                '{role}',
                '{profile_image_url}',
                {now},
                {now},
                {now},
                NULL,
                NULL,
                NULL,
                {oauth_value}
            );
        """

        try:
            self.client.cursor.execute(insert_query)
            self.client.connection.commit()

            # If you need a UserModel, you can construct it or fetch it back from DB.
            # For now, just return None or the newly created user object if implemented.
            return None
        except Exception as e:
            print(f"Error inserting user: {e}")
            self.client.connection.rollback()
            return None

    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        try:
            query = f"SELECT * FROM \"user\" WHERE id = %s"
            self.client.cursor.execute(query, (id,))
            row = self.client.cursor.fetchone()
            return row_to_usermodel(row)
        except Exception as e:
            print(f"Error getting user by id: {e}")
            return None

    def get_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        try:
            query = f"SELECT * FROM \"user\" WHERE api_key = %s"
            self.client.cursor.execute(query, (api_key,))
            row = self.client.cursor.fetchone()
            return row_to_usermodel(row)
        except Exception as e:
            print(f"Error getting user by api_key: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        try:
            query = f"SELECT * FROM \"user\" WHERE email = %s"
            self.client.cursor.execute(query, (email,))
            row = self.client.cursor.fetchone()
            return row_to_usermodel(row)
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None

    def get_user_by_oauth_sub(self, sub: str) -> Optional[UserModel]:
        try:
            query = f"SELECT * FROM \"user\" WHERE oauth_sub = %s"
            self.client.cursor.execute(query, (sub,))
            row = self.client.cursor.fetchone()
            return row_to_usermodel(row)
        except Exception as e:
            print(f"Error getting user by oauth_sub: {e}")
            return None

    def get_users(self, skip: int = 0, limit: int = 50) -> list[UserModel]:
        # For now, skip/limit commented out, but can be easily added to query
        try:
            query = "SELECT * FROM \"user\""
            self.client.cursor.execute(query)
            rows = self.client.cursor.fetchall()
            return [row_to_usermodel(row) for row in rows if row]
        except Exception as e:
            print(f"Error getting users: {e}")
            return []

    def get_num_users(self) -> Optional[int]:
        try:
            query = "SELECT COUNT(*) FROM \"user\""
            self.client.cursor.execute(query)
            (count,) = self.client.cursor.fetchone()
            return count
        except Exception as e:
            print(f"Error getting number of users: {e}")
            return None

    def get_first_user(self) -> Optional[UserModel]:
        try:
            query = "SELECT * FROM \"user\" ORDER BY created_at LIMIT 1"
            self.client.cursor.execute(query)
            row = self.client.cursor.fetchone()
            return row_to_usermodel(row)
        except Exception as e:
            print(f"Error getting first user: {e}")
            return None

    def update_user_role_by_id(self, id: str, role: str) -> Optional[UserModel]:
        try:
            query = "UPDATE \"user\" SET role = %s WHERE id = %s"
            self.client.cursor.execute(query, (role, id))
            self.client.connection.commit()
            return self.get_user_by_id(id)
        except Exception as e:
            print(f"Error updating user role: {e}")
            self.client.connection.rollback()
            return None

    def update_user_profile_image_url_by_id(self, id: str, profile_image_url: str) -> Optional[UserModel]:
        try:
            query = "UPDATE \"user\" SET profile_image_url = %s WHERE id = %s"
            self.client.cursor.execute(query, (profile_image_url, id))
            self.client.connection.commit()
            return self.get_user_by_id(id)
        except Exception as e:
            print(f"Error updating user profile_image_url: {e}")
            self.client.connection.rollback()
            return None

    def update_user_last_active_by_id(self, id: str) -> Optional[UserModel]:
        try:
            now = int(time.time())
            query = "UPDATE \"user\" SET last_active_at = %s WHERE id = %s"
            self.client.cursor.execute(query, (now, id))
            self.client.connection.commit()
            return self.get_user_by_id(id)
        except Exception as e:
            print(f"Error updating user last_active_at: {e}")
            self.client.connection.rollback()
            return None

    def update_user_oauth_sub_by_id(self, id: str, oauth_sub: str) -> Optional[UserModel]:
        try:
            query = "UPDATE \"user\" SET oauth_sub = %s WHERE id = %s"
            self.client.cursor.execute(query, (oauth_sub, id))
            self.client.connection.commit()
            return self.get_user_by_id(id)
        except Exception as e:
            print(f"Error updating user oauth_sub: {e}")
            self.client.connection.rollback()
            return None

    def update_user_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        if not updated:
            return self.get_user_by_id(id)

        # Build the dynamic update query
        set_clause = ", ".join([f"{key} = %s" for key in updated.keys()])
        values = list(updated.values()) + [id]
        query = f"UPDATE \"user\" SET {set_clause} WHERE id = %s"

        try:
            self.client.cursor.execute(query, values)
            self.client.connection.commit()
            return self.get_user_by_id(id)
        except Exception as e:
            print(f"Error updating user: {e}")
            self.client.connection.rollback()
            return None

    def delete_user_by_id(self, id: str) -> bool:
        try:
            # First, delete associated chats
            result = self.Chats.delete_chats_by_user_id(id)
            if result:
                query = "DELETE FROM \"user\" WHERE id = %s"
                self.client.cursor.execute(query, (id,))
                self.client.connection.commit()
                return True
            else:
                return False
        except Exception as e:
            print(f"Error deleting user: {e}")
            self.client.connection.rollback()
            return False

    def update_user_api_key_by_id(self, id: str, api_key: str) -> bool:
        try:
            query = "UPDATE \"user\" SET api_key = %s WHERE id = %s"
            self.client.cursor.execute(query, (api_key, id))
            self.client.connection.commit()
            return self.client.cursor.rowcount == 1
        except Exception as e:
            print(f"Error updating user api_key: {e}")
            self.client.connection.rollback()
            return False

    def get_user_api_key_by_id(self, id: str) -> Optional[str]:
        try:
            query = "SELECT api_key FROM \"user\" WHERE id = %s"
            self.client.cursor.execute(query, (id,))
            row = self.client.cursor.fetchone()
            if row:
                return row[0]
            return None
        except Exception as e:
            print(f"Error getting user api_key: {e}")
            return None

# Example usage:
# client = PostgresClient()
# users = UsersTable(client)
# users.create_user_table()
# new_user = users.insert_new_user(id="123", name="John Doe", email="john@example.com")



# Users = UsersTable()


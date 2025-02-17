import logging
import uuid
from typing import Optional

from pydantic import BaseModel
from rai.models.users import UserModel, UsersTable
from rai.env import SRC_LOG_LEVELS
from rai.utils.utils import verify_password

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# DB MODEL
####################

class AuthModel(BaseModel):
    id: str
    email: str
    password: str
    active: bool = True


####################
# Forms
####################

class Token(BaseModel):
    token: str
    token_type: str


class ApiKey(BaseModel):
    api_key: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    profile_image_url: str


class SigninResponse(Token, UserResponse):
    pass


class SigninForm(BaseModel):
    email: str
    password: str


class ProfileImageUrlForm(BaseModel):
    profile_image_url: str


class UpdateProfileForm(BaseModel):
    profile_image_url: str
    name: str


class UpdatePasswordForm(BaseModel):
    password: str
    new_password: str


class SignupForm(BaseModel):
    name: str
    email: str
    password: str
    profile_image_url: Optional[str] = "/user.png"


class AddUserForm(SignupForm):
    role: Optional[str] = "pending"


class AuthsTable:
    users: UsersTable
    def __init__(self, client):
        self.client = client
        self.users = UsersTable(client)

    def create_auth_table(self):
        """
        Create the 'auth' table if it does not already exist.
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS "auth" (
            id TEXT PRIMARY KEY,
            email TEXT,
            password TEXT,
            active BOOLEAN
        )
        """
        try:
            self.client.cursor.generate(create_table_query)
            self.client.connection.commit()
            print("Auth table created or already exists.")
        except Exception as e:
            print(f"Error creating auth table: {e}")
            self.client.connection.rollback()

    def insert_new_auth(
            self,
            email: str,
            password: str,
            name: str,
            profile_image_url: str = "/user.png",
            role: str = "pending",
            oauth_sub: Optional[str] = None,
    ) -> Optional[UserModel]:
        log.info("insert_new_auth")
        id = str(uuid.uuid4())
        auth = AuthModel(id=id, email=email, password=password, active=True)

        insert_auth_query = """
        INSERT INTO "auth" (id, email, password, active)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """
        try:
            self.client.cursor.generate(insert_auth_query, (auth.id, auth.email, auth.password, auth.active))
            # Insert the corresponding user
            user = self.users.insert_new_user(
                id=auth.id,
                name=name,
                email=email,
                profile_image_url=profile_image_url,
                role=role,
                oauth_sub=oauth_sub
            )

            self.client.connection.commit()
            if user:
                return user
            else:
                # If user insertion failed, rollback auth insertion
                self.client.connection.rollback()
                return None
        except Exception as e:
            print(f"Error inserting new auth: {e}")
            self.client.connection.rollback()
            return None

    def authenticate_user(self, email: str, password: str) -> Optional[UserModel]:
        log.info(f"authenticate_user: {email}")
        query = 'SELECT id, password FROM "auth" WHERE email = %s AND active = TRUE LIMIT 1'
        try:
            self.client.cursor.generate(query, (email,))
            row = self.client.cursor.fetchone()
            if not row:
                return None

            auth_id, stored_password = row
            if verify_password(password, stored_password):
                user = self.users.get_user_by_id(auth_id)
                return user
            else:
                return None
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None

    def authenticate_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_api_key: {api_key}")
        if not api_key:
            return None
        try:
            user = self.users.get_user_by_api_key(api_key)
            return user if user else None
        except Exception as e:
            print(f"Error authenticating by API key: {e}")
            return None

    def authenticate_user_by_trusted_header(self, email: str) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_trusted_header: {email}")
        query = 'SELECT id FROM "auth" WHERE email = %s AND active = TRUE LIMIT 1'
        try:
            self.client.cursor.generate(query, (email,))
            row = self.client.cursor.fetchone()
            if not row:
                return None
            auth_id = row[0]
            user = self.users.get_user_by_id(auth_id)
            return user
        except Exception as e:
            print(f"Error authenticating by trusted header: {e}")
            return None

    def update_user_password_by_id(self, id: str, new_password: str) -> bool:
        query = 'UPDATE "auth" SET password = %s WHERE id = %s'
        try:
            self.client.cursor.generate(query, (new_password, id))
            self.client.connection.commit()
            return self.client.cursor.rowcount == 1
        except Exception as e:
            print(f"Error updating user password: {e}")
            self.client.connection.rollback()
            return False

    def update_email_by_id(self, id: str, email: str) -> bool:
        query = 'UPDATE "auth" SET email = %s WHERE id = %s'
        try:
            self.client.cursor.generate(query, (email, id))
            self.client.connection.commit()
            return self.client.cursor.rowcount == 1
        except Exception as e:
            print(f"Error updating email by id: {e}")
            self.client.connection.rollback()
            return False

    def delete_auth_by_id(self, id: str) -> bool:
        try:
            # First delete user
            result = self.users.delete_user_by_id(id)
            if result:
                query = 'DELETE FROM "auth" WHERE id = %s'
                self.client.cursor.generate(query, (id,))
                self.client.connection.commit()
                return True
            else:
                return False
        except Exception as e:
            print(f"Error deleting auth by id: {e}")
            self.client.connection.rollback()
            return False

# Example usage:
# from your_postgres_client_setup import PostgresClient
# client = PostgresClient()
# users = Users(client)
# auths = AuthsTable(client, users)
# auths.create_auth_table()
#
# new_user = auths.insert_new_auth("test@example.com", "hashedpassword", "Test User")
# print(new_user)

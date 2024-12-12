
from rai.internal.postgres import POSTGRES_CLIENT
from rai.models.users import UsersTable

users = UsersTable(client=POSTGRES_CLIENT)

users.create_user_table()



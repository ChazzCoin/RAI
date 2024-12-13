from rai.app import state
from rai.internal.postgres import POSTGRES_CLIENT
from rai.models.users import UsersTable
from rai.models.auths import AuthsTable
from rai.models.files import FilesTable
from rai.models.models import ModelsTable
from rai.models.prompts import PromptsTable
from rai.models.chats import ChatArchiveTable


class PostgresTables:
    @staticmethod
    def Users(): return UsersTable(POSTGRES_CLIENT)
    @staticmethod
    def Auths(): return AuthsTable(POSTGRES_CLIENT)
    @staticmethod
    def Files(): return FilesTable(POSTGRES_CLIENT)
    @staticmethod
    def AI_Models(): return ModelsTable(POSTGRES_CLIENT)
    @staticmethod
    def Prompts(): return PromptsTable(POSTGRES_CLIENT)
    @staticmethod
    def ChatArchive(): return ChatArchiveTable(POSTGRES_CLIENT)


# table = PostgresTables.ChatArchive()
# table.create_chat_table()
# #
# models = ai_models.get_all_ai_models()
# print(models)
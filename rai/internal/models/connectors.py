from rai.internal.postgres import POSTGRES_CLIENT
from rai.internal.models.users import UsersTable
from rai.internal.models.auths import AuthsTable
from rai.internal.models.files import FilesTable
from rai.internal.models.models import ModelsTable
from rai.internal.models.prompts import PromptsTable
from rai.internal.models.chats import ChatArchiveTable


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
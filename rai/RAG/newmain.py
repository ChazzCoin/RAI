# import logging
# from rai.data.extraction.RaiFileExtraction import VECTOR_DB_CLIENT
# # from rai.RAG.Q import query_chroma_form
# from rai.env import SRC_LOG_LEVELS
#
# log = logging.getLogger(__name__)
# log.setLevel(SRC_LOG_LEVELS["RAG"])
# from F.LOG import Log
# Log = Log("Rai Data Loader")
#
# # Helper functions
# def collection_route(prefix, parent, child, baby):
#     return f"{prefix}.{parent}.{child}.{baby}"
#
# def collection_route_file(prefix, parent, child, baby, file):
#     return f"{prefix}.{parent}.{child}.{baby}-{file}"
#
# def collection_file(prefix, route, file):
#     return f"{prefix}.{route}-{file}"
#
# # Validation
# VALID_USER_ROLES = {'admin', 'coach', 'player', 'parent', 'guest'}
#
# def validate_user_role(user_role):
#     if user_role not in VALID_USER_ROLES:
#         raise ValueError(f"Invalid user role: {user_role}")
#
# def get_all_collections(prefix=None, subfix:str=None):
#     try:
#         # Assuming you have a ChromaDB client instance named 'chromadb_client'
#         collections = VECTOR_DB_CLIENT.client.list_collections()
#         collection_names = [collection.name for collection in collections]
#         if prefix:
#             filtered_by_prefix = []
#             valid = False
#             for collection_name in collection_names:
#                 c_split = collection_name.split('.')
#                 if collection_name.startswith(prefix) and subfix:
#                     for c in c_split:
#                         if c == subfix:
#                             valid = True
#                 elif collection_name.startswith(prefix):
#                     valid = True
#                 if valid:
#                     filtered_by_prefix.append(collection_name)
#                     valid = False
#             collection_names = filtered_by_prefix
#         return collection_names
#     except Exception as e:
#         Log.e("Error retrieving collections from ChromaDB", e)
#         return []
#
# def get_all_collections_old(prefix=None):
#     try:
#         # Assuming you have a ChromaDB client instance named 'chromadb_client'
#         collections = VECTOR_DB_CLIENT.client.list_collections()
#         collection_names = [collection.name for collection in collections]
#         if prefix:
#             filtered_by_prefix = []
#             for collection_name in collection_names:
#                 if collection_name.startswith(prefix):
#                     filtered_by_prefix.append(collection_name)
#             collection_names = filtered_by_prefix
#         return collection_names
#     except Exception as e:
#         Log.e("Error retrieving collections from ChromaDB", e)
#         return []
#
#
#
#
# """
# model_prefix.internal/external.context
#
# BASE: prefix.external.general
# """
#
# # def query_chroma(*collections:str, query:str, k:int=10, hybrid=False):
# #     return query_chroma_form(
# #         form_data=QueryCollectionsForm(
# #             collection_names=collections,
# #             query=query, k=k
# #         ), hybrid=hybrid
# #     )
#
# # if __name__ == "__main__":
#     # print(get_all_collections(prefix='pcsc2024'))
#     # user_role = 'parent'
#     # query = 'Upcoming soccer events'
#     # results = query_chroma_by_user_auth(user_role, query)
#     # if results:
#     #     print("Query Results:", results)
#     # else:
#     #     print("No results returned.")
#
# #     results = query_chroma_by_user_auth(user_auth="ADMIN", collection_prefix="parkcitysc", query="Who coaches the 2015 girls teams?")
# #     print(results)
#

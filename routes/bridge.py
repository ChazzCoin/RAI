
import time

from flask import Blueprint, request
routeBridge_blueprint = Blueprint('routeBridge', __name__)





@routeBridge_blueprint.post("/v1/chat/completions")
@routeBridge_blueprint.post("/chat/completions")
async def generate_openai_chat_completion(form_data: dict):
    return {}

# @routeBridge_blueprint.get('/v1/models')
# async def get_models():
#     """
#        Returns the available pipelines
#        """
#     return {
#         "data": [
#             {
#                 "id": pipeline["id"],
#                 "name": pipeline["name"],
#                 "object": "model",
#                 "created": int(time.time()),
#                 "owned_by": "openai",
#                 "pipeline": {
#                     "type": pipeline["type"],
#                     **(
#                         {
#                             "pipelines": (
#                                 pipeline["valves"].pipelines
#                                 if pipeline.get("valves", None)
#                                 else []
#                             ),
#                             "priority": pipeline.get("priority", 0),
#                         }
#                         if pipeline.get("type", "pipe") == "filter"
#                         else {}
#                     ),
#                     "valves": pipeline["valves"] != None,
#                 },
#             }
#             for pipeline in app.state.PIPELINES.values()
#         ],
#         "object": "list",
#         "pipelines": True,
#     }

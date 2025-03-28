#!/bin/bash
import asyncio
import json
import os.path
from concurrent.futures import ThreadPoolExecutor
from quart import Quart, request, jsonify, websocket
from quart_cors import cors
from F.LOG import Log
from rai.agentic.ai_assistants.knowledge import rKnowledgeAssistant
from rai.agentic.ai_flows.rag_flow import rRagFlow
from rai.agentic.agent_assistants.knowledge_assist import RaiQueryAgentResults
from rai.assistant.connectors import rAI
from rai.internal.clients.ioredis_client import RedisIO
from rai.internal.connectors import REDIS_DB_CLIENT_0, REDIS_DB_CLIENT_1, PostgresTables
from rai.internal.models.models import AIModelData
from typing import Optional


""" DATABASES """
collection_name = "documents"
RAI_CACHE = REDIS_DB_CLIENT_0
RAI_CACHE_SYSTEM = REDIS_DB_CLIENT_1
RAI_MODELS = PostgresTables.AI_Models()
CHAT_ARCHIVE = PostgresTables.ChatArchive()
RAI_AI = rAI()
RAI_ENGINE = RAI_AI.get_engine("openai")
STORED_RAI_MODELS: [AIModelData] = RAI_MODELS.get_all_ai_models()
print("Stored Raiko Models", STORED_RAI_MODELS)
IMAGE_FOLDER = f"{os.path.dirname(__file__)}/files/images"
RAI_VERSION = "0.8.0:raiko"
image_path = '/Users/chazzromeo/Desktop/chat_image.jpg'

Log = Log("RAI API Bruno Canary")
app = Quart(__name__)
app = cors(app, allow_origin="*")

looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=4)


ioredis = RedisIO()

@app.websocket('/ws/<subscription_name>')
async def websocket_proxy(subscription_name):
    await ioredis.connect()
    pubsub = ioredis.redis_client.pubsub()
    await pubsub.subscribe(subscription_name)

    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await websocket.send(message['data'])
    finally:
        await pubsub.unsubscribe(subscription_name)


@app.route('/v1/knowledge', methods=['POST', 'OPTIONS'])
async def knowledge_base():
    data = await request.get_data(as_text=False)
    jbody: dict = json.loads(data.decode('utf-8'))
    model: str = jbody.get('model')
    parent_model = None
    for item in RODELS:
        if item.get('model') == model:
            parent_model = item
    query: str = jbody.get('query')
    knowledge_results = rKnowledgeAssistant("pcsc2025.4").request(
        user_request=query
    )
    dump = knowledge_results.model_dump()
    return jsonify({ "status": 200, "data": dump })


@app.route('/v1/query', methods=['POST', 'OPTIONS'])
async def query():
    data = await request.get_data(as_text=False)
    jbody: dict = json.loads(data.decode('utf-8'))
    model: str = jbody.get('model')
    parent_model = None
    for item in RODELS:
        if item.get('model') == model:
            parent_model = item
    query: str = jbody.get('query')
    # agent_results: RaiQueryAgentResults = RaiQueryAgent.execute("base", "rai2025.1", query)
    query_results: RaiQueryAgentResults = rRagFlow.flow(
        name='base',
        prefix=parent_model.get('collection', "pcsc2025.4"),
        user_prompt=query
    )
    return jsonify({ "status": 200, "data": query_results.model_dump() })

RODELS = [
    {
        'id': 'RAI-2025-1',
        'name': 'RAI:2025-1',
        'model': 'RAI:2025-1',
        'zip': '84098',
        'address': '',
        'title': 'Rai Testing Model 2025-1',
        'initials': 'rai',
        'ai_name': 'Raiko',
        'ai_flow': 'QA',
        'org_rep_type': 'Personal Customer Representative',
        'collection': 'rai2025.5',
        'prompt': "GENERAL_PROMPT_TEMPLATE",
        'context_prompt': "context.SOCCER_CLUB_CONTEXT_EXPANDER",
        'primary_functions': "ysc_primary",
        'secondary_functions': "ysc_secondary",
        'openai': 'gpt-4o',
        'ollama': 'llama3:latest',
        'org_type': "Youth Soccer Club",
        'org_specialty': "",
        'imageSupport': False,
        'provider': ""
    },
    {
        'id': 'park-city-soccer-club-2025-4',
        'name': 'ParkCitySC:2025-4',
        'model': 'ParkCitySC:2025-4',
        'zip':'84098',
        'address': '',
        'title': 'Park City Soccer Club',
        'initials': 'PCSC',
        'ai_name': 'Bruno',
        'ai_flow': 'QA',
        'org_rep_type': 'Personal Customer Representative',
        'collection': 'pcsc2025.4',
        'prompt': "GENERAL_PROMPT_TEMPLATE",
        'context_prompt': "context.SOCCER_CLUB_CONTEXT_EXPANDER",
        'primary_functions': "ysc_primary",
        'secondary_functions': "ysc_secondary",
        'openai': 'gpt-4o',
        'ollama': 'llama3:latest',
        'org_type': "Youth Soccer Club",
        'org_specialty': "",
        'imageSupport': False,
        'provider': ""
     },
    {
        'id': 'park-city-soccer-club-2025-3',
        'name': 'ParkCitySC:2025-3',
        'model': 'ParkCitySC:2025-3',
        'zip':'84098',
        'address': '',
        'title': 'Park City Soccer Club',
        'initials': 'PCSC',
        'ai_name': 'Bruno',
        'ai_flow': 'QA',
        'org_rep_type': 'Personal Customer Representative',
        'collection': 'pcsc2025.3',
        'prompt': "GENERAL_PROMPT_TEMPLATE",
        'context_prompt': "context.SOCCER_CLUB_CONTEXT_EXPANDER",
        'primary_functions': "ysc_primary",
        'secondary_functions': "ysc_secondary",
        'openai': 'gpt-4o',
        'ollama': 'llama3:latest',
        'org_type': "Youth Soccer Club",
        'org_specialty': "",
        'imageSupport': False,
        'provider': ""
     }
]
@app.route('/v1/models', methods=['GET'])
def models():
    return jsonify({"status": 200, "data": RODELS })

@app.route('/v1/agents', methods=['GET', 'OPTIONS'])
async def agents(idx:Optional[int]=None):
    print("Calling Agents")
    agent1 = {
        "name": "Query",
        "type": "base",
        "details": "Similarity Search Agent.",
        "imageSupport": False,
    }

    return jsonify({ "status": 200, "data": [agent1] })

if __name__ == '__main__':
    port = 5182
    debug = False
    host = "0.0.0.0"
    print(f"Starting Bruno Server. Host={host}, Port={port}, Debug={debug}")
    app.run(host=host, port=port, debug=debug, loop=looper)
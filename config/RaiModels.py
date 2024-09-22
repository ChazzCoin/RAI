from F import DICT

RAI_MODEL_MAP = {
    "llama3:latest": "gpt-4o-mini",
    "ChromaDB:search": "gpt-4o-mini",
    "gpt-4o-mini": "gpt-4o-mini",
    "park-city:latest" : "ft:gpt-4o-mini-2024-07-18:personal:pcsc-canary-1:A5Q7aqpL:ckpt-step-323",
    "park-city:gpt4o": "gpt-4o-mini",
}

RAI_COLLECTION_MAP = {
    "llama3:latest": "documents",
    "gpt-4o-mini": "documents",
    "park-city:latest" : "web_pages_2",
    "park-city:gpt4o": "web_pages_2",
}

def getMappedCollection(modelIn:str):
    return DICT.get(modelIn, RAI_COLLECTION_MAP, "documents")

def getMappedModel(modelIn:str):
    return DICT.get(modelIn, RAI_MODEL_MAP, "gpt-4o-mini")


RAI_MODELS = {
    'models': [
        {'name': 'park-city:latest', 'model': 'park-city:latest', 'modified_at': '2024-07-02T06:32:47.913084094Z', 'size': 177669289, 'digest': 'c4ff0145029b23c94b81626b5cdd671a5c48140a3f8d972575efb9d145527581', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0' }},
        {'name': 'park-city:gpt4o', 'model': 'park-city:gpt4o', 'modified_at': '2024-07-02T06:32:47.913084094Z', 'size': 177669289, 'digest': 'c4ff0145029b23c94b81626b5cdd6743434343sdfsfefb9d145527581', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}},
        {'name': 'llama3:latest', 'model': 'llama3:latest', 'modified_at': '2024-06-29T06:01:38.340493962Z', 'size': 4661224676, 'digest': '365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '8.0B', 'quantization_level': 'Q4_0'}},
        {'name': 'ChromaDB:search', 'model': 'ChromaDB:search', 'modified_at': '2024-06-29T06:01:38.340493962Z', 'size': 4661224676, 'digest': '365c0bd3c000a25d28dsearch1c6add414de7275464c4e4d1c3b5fcb5d8ad1', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '8.0B', 'quantization_level': 'Q4_0'}},
        {'name': 'nous-hermes2-mixtral:8x7b', 'model': 'nous-hermes2-mixtral:8x7b', 'modified_at': '2024-06-29T06:24:46.894948698Z', 'size': 26442493141, 'digest': '599da8dce2c14e54737c51f9668961bbc3526674249d3850b0875638a3e5e268', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '47B', 'quantization_level': 'Q4_0'}},
        {'name': 'sqlcoder:15b', 'model': 'sqlcoder:15b', 'modified_at': '2024-06-29T06:01:39.480494281Z', 'size': 8987630230, 'digest': '93bb0e8a904ff98bcc6fa5cf3b8e63dc69203772f4bc713f761c82684541d08d', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'starcoder', 'families': None, 'parameter_size': '15B', 'quantization_level': 'Q4_0'}},
        {'name': 'phi3:medium', 'model': 'phi3:medium', 'modified_at': '2024-06-29T06:01:39.060494165Z', 'size': 7897126241, 'digest': '1e67dff39209b792d22a20f30ebabe679c64db83de91544693c4915b57e475aa', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'phi3', 'families': ['phi3'], 'parameter_size': '14.0B', 'quantization_level': 'F16'}},
        {'name': 'codellama:34b', 'model': 'codellama:34b', 'modified_at': '2024-06-29T06:01:38.020493877Z', 'size': 19052049085, 'digest': '685be00e1532e01f795e04bc59c67bc292d9b1f80b5136d4fbdebe6830402132', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': None, 'parameter_size': '34B', 'quantization_level': 'Q4_0'}},
        {'name': 'llava:34b', 'model': 'llava:34b', 'modified_at': '2024-06-29T06:01:38.736494074Z', 'size': 20166497526, 'digest': '3d2d24f4667475bd28d515495b0dcc03b5a951be261a0babdb82087fc11620ee', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama', 'clip'], 'parameter_size': '34B', 'quantization_level': 'Q4_0'}},
        {'name': 'codellama:13b', 'model': 'codellama:13b', 'modified_at': '2024-06-29T06:01:37.620493765Z', 'size': 7365960935, 'digest': '9f438cb9cd581fc025612d27f7c1a6669ff83a8bb0ed86c94fcf4c5440555697', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': None, 'parameter_size': '13B', 'quantization_level': 'Q4_0'}}
            ]
    }


MODEL_MAP = {
    "llama3:latest": "gpt-4o-mini",
    "park-city:latest" : "ft:gpt-4o-mini-2024-07-18:personal:pcsc-canary-1:A5Q7aqpL:ckpt-step-323"
}
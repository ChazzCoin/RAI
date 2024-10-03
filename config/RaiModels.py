from agents.prompts import context

GENERAL_PROMPT_TEMPLATE = lambda ai_name, org_name, org_rep_type, specialty: f"""
Your name is {ai_name}, {org_name}'s {org_rep_type}.
You are here to serve at the pleasure of the members of {org_name}.

You are going to be a detailed and honest customer service representative who will answer questions based on information given to you.
{specialty}
GOLDEN RULE: If you do not know the answer based on information I give you, please just state you don't know.
"""


""" -- YOU MUST ADD THE MODEL HERE FOR IT TO SHOW UP IN OPEN WEBUI -- """
RAI_MODELS = {'models': [
        {
            'name': 'park-city:latest',
            'model': 'park-city:latest',
            'modified_at': '2024-07-02T06:32:47.913084094Z',
            'size': 177669289,
            'digest': 'c4ff0145029b23c94b81626b5cdd671a5c48140a3f8d972575efb9d145527581',
            'details': {
                'parent_model': '',
                'format': 'gguf',
                'family': 'gpt2',
                'families': ['gpt2'],
                'parameter_size': '163.04M',
                'quantization_level': 'Q8_0'
            }
         },
        {'name': 'ussf:latest', 'model': 'ussf:latest', 'modified_at': '2024-07-02T06:32:47.913084094Z',
         'size': 177669289, 'digest': 'c4ff0145029bussf26b5cdd6743434343sdfsfefb9d145527581',
         'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'],
                     'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}},
        {'name': 'medical-neuro:latest', 'model': 'medical-neuro:latest', 'modified_at': '2024-07-02T06:32:47.913084094Z',
         'size': 177669289, 'digest': 'c4ff0145029bneuro434343sdfsfefb9d145527581',
         'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'],
                     'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}},
        {'name': 'park-city:assistant', 'model': 'park-city:assistant', 'modified_at': '2024-07-02T06:32:47.913084094Z', 'size': 177669289, 'digest': 'c4ff0145029b23c94b81626b5cdd6743434343sdfsfefb9d145527581', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}},
        {'name': 'llama3:latest', 'model': 'llama3:latest', 'modified_at': '2024-06-29T06:01:38.340493962Z', 'size': 4661224676, 'digest': '365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '8.0B', 'quantization_level': 'Q4_0'}},
        {'name': 'ChromaDB:search', 'model': 'ChromaDB:search', 'modified_at': '2024-06-29T06:01:38.340493962Z', 'size': 4661224676, 'digest': '365c0bd3c000a25d28dsearch1c6add414de7275464c4e4d1c3b5fcb5d8ad1', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '8.0B', 'quantization_level': 'Q4_0'}},
        # {'name': 'nous-hermes2-mixtral:8x7b', 'model': 'nous-hermes2-mixtral:8x7b', 'modified_at': '2024-06-29T06:24:46.894948698Z', 'size': 26442493141, 'digest': '599da8dce2c14e54737c51f9668961bbc3526674249d3850b0875638a3e5e268', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '47B', 'quantization_level': 'Q4_0'}},
        # {'name': 'sqlcoder:15b', 'model': 'sqlcoder:15b', 'modified_at': '2024-06-29T06:01:39.480494281Z', 'size': 8987630230, 'digest': '93bb0e8a904ff98bcc6fa5cf3b8e63dc69203772f4bc713f761c82684541d08d', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'starcoder', 'families': None, 'parameter_size': '15B', 'quantization_level': 'Q4_0'}},
        # {'name': 'phi3:medium', 'model': 'phi3:medium', 'modified_at': '2024-06-29T06:01:39.060494165Z', 'size': 7897126241, 'digest': '1e67dff39209b792d22a20f30ebabe679c64db83de91544693c4915b57e475aa', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'phi3', 'families': ['phi3'], 'parameter_size': '14.0B', 'quantization_level': 'F16'}},
        # {'name': 'codellama:34b', 'model': 'codellama:34b', 'modified_at': '2024-06-29T06:01:38.020493877Z', 'size': 19052049085, 'digest': '685be00e1532e01f795e04bc59c67bc292d9b1f80b5136d4fbdebe6830402132', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': None, 'parameter_size': '34B', 'quantization_level': 'Q4_0'}},
        # {'name': 'llava:34b', 'model': 'llava:34b', 'modified_at': '2024-06-29T06:01:38.736494074Z', 'size': 20166497526, 'digest': '3d2d24f4667475bd28d515495b0dcc03b5a951be261a0babdb82087fc11620ee', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama', 'clip'], 'parameter_size': '34B', 'quantization_level': 'Q4_0'}},
        # {'name': 'codellama:13b', 'model': 'codellama:13b', 'modified_at': '2024-06-29T06:01:37.620493765Z', 'size': 7365960935, 'digest': '9f438cb9cd581fc025612d27f7c1a6669ff83a8bb0ed86c94fcf4c5440555697', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': None, 'parameter_size': '13B', 'quantization_level': 'Q4_0'}}
            ]}


""" -- YOU MUST ADD THE MODEL HERE FOR IT TO 'MOLD' TO YOUR CONFIGURATION -- """
RAI_MODs = {
    'park-city:latest': {
            'name': 'park-city:latest',
            'model': 'park-city:latest',
            'zip':'84098',
            'address': '',
            'title': 'Park City Soccer Club',
            'initials': 'PCSC',
            'ai_name': 'Bruno',
            'org_rep_type': 'Personal Customer Representative',
            'collection': 'parkcitysc-new',
            'prompt': GENERAL_PROMPT_TEMPLATE,
            'context_prompt': context.MEDICAL_CONTEXT_EXPANDER,
            'openai': 'gpt-4o-mini',
            'ollama': 'llama3:latest',
            'org_type': 'Soccer Club',
            'org_specialty': f"""
                You specialize in understanding youth soccer clubs, organizational structure, youth soccer parents, youth soccer coaches, youth soccer players.
            """,
            'modified_at': '2024-07-02T06:32:47.913084094Z',
            'size': 177669289,
            'digest': 'c4ff0145029b23c94b81626b5cdd671a5c48140a3f8d972575efb9d145527581',
            'details': {
                'parent_model': '',
                'format': 'gguf',
                'family': 'gpt2',
                'families': ['gpt2'],
                'parameter_size': '163.04M',
                'quantization_level': 'Q8_0'
            }
         },
    'medical-neuro:latest': {
            'name': 'medical-neuro:latest',
            'model': 'medical-neuro:latest',
            'zip':'',
            'address': '',
            'title': 'Medical Neurological Assistant',
            'initials': 'PCSC',
            'ai_name': 'Bruno',
            'org_rep_type': 'Knowledge Base',
            'collection': 'medical-neuro',
            'prompt': GENERAL_PROMPT_TEMPLATE,
            'context_prompt': context.MEDICAL_CONTEXT_EXPANDER,
            'openai': 'gpt-4o-mini',
            'ollama': 'llama3:latest',
            'org_type': 'Medical',
            'org_specialty': f"""
                You specialize in understanding medicine, hospitals, doctors, medical, neuro, neurology, neurosurgery.
                SPECIAL RULE 1: When creating a response, remove any doctors names. I do not want to know about any doctors. Only the information. 
                SPECIAL RULE 2: Stick to copying the knowledge base directly instead of summarizing. 
            """,
            'modified_at': '2024-07-02T06:32:47.913084094Z',
            'size': 177669289,
            'digest': 'c4ff0145029b23c94b81626b5cdd671a5c48140a3f8d972575efb9d145527581',
            'details': {
                'parent_model': '',
                'format': 'gguf',
                'family': 'gpt2',
                'families': ['gpt2'],
                'parameter_size': '163.04M',
                'quantization_level': 'Q8_0'
            }
         },
    'park-city:assistant': {
        'name': 'park-city:assistant',
        'model': 'park-city:assistant',
        'zip':'84098',
        'address': '',
        'title': 'Park City Soccer Club',
        'initials': 'PCSC',
        'ai_name': 'Bruno',
        'org_rep_type': 'Personal Customer Representative',
        'collection': 'parkcitysc-new',
        'prompt': GENERAL_PROMPT_TEMPLATE,
        'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
        'openai': 'gpt-4o-mini',
        'ollama': 'llama3:latest',
        'org_type': 'Soccer Club',
        'org_specialty': f"""
            You specialize in understanding youth soccer clubs, organizational structure, youth soccer parents, youth soccer coaches, youth soccer players.
        """,
        'modified_at': '2024-07-02T06:32:47.913084094Z',
        'size': 177669289,
        'digest': 'c4ff0145029b23c94b81626b5cdd6743434343sdfsfefb9d145527581',
        'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}},
    'ussf:latest': {
        'name': 'ussf:latest',
        'model': 'ussf:latest',
        'zip':'',
        'address': '',
        'title': 'United States Soccer Federation',
        'initials': 'USSF',
        'ai_name': 'Kevin',
        'org_rep_type': 'Personal Knowledge Base Master',
        'collection': 'ussf-main',
        'prompt': GENERAL_PROMPT_TEMPLATE,
        'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
        'openai': 'gpt-4o-mini',
        'ollama': 'llama3:latest',
        'org_type': 'Governing Body of Soccer',
        'org_specialty': f"""
            Governing Body of American Soccer
            You specialize in understanding soccer in the united states of america as the national governing body.
            From Players to Parents and Coaches at any level or age, you understand the rules and the ussf principles.
            SPECIAL RULE 1: When forming the response from the knowledge base, prioritize and focus on top main level principles then sub lower level principles next. 
            SPECIAL RULE 2: Stick to copying the knowledge base directly instead of summarizing. 
        """,
        'modified_at': '2024-07-02T06:32:47.913084094Z',
        'size': 177669289,
        'digest': 'c4ff0145029b2cdd6743434343sdfsfefb9d145527581',
        'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}},
    'llama3:latest': {
        'name': 'llama3:latest',
        'model': 'llama3:latest',
        'zip':'84098',
        'address': '',
        'title': '',
        'initials': '',
        'ai_name': '',
        'org_rep_type': '',
        'collection': 'none',
        'prompt': GENERAL_PROMPT_TEMPLATE,
        'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
        'openai': 'gpt-4o-mini',
        'ollama': 'llama3:latest',
        'org_type': 'Soccer Club',
        'modified_at': '2024-06-29T06:01:38.340493962Z',
        'size': 4661224676,
        'digest': '365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1',
        'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '8.0B', 'quantization_level': 'Q4_0'}},
    'ChromaDB:search': {
        'name': 'ChromaDB:search',
        'model': 'ChromaDB:search',
        'zip': '84098',
        'address': '',
        'title': 'Park City Soccer Club',
        'initials': 'PCSC',
        'ai_name': 'Bruno',
        'org_rep_type': 'Personal Customer Representative',
        'collection': 'parkcitysc-new',
        'prompt': GENERAL_PROMPT_TEMPLATE,
        'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
        'openai': 'gpt-4o-mini',
        'ollama': 'llama3:latest',
        'org_type': 'Soccer Club',
        'modified_at': '2024-06-29T06:01:38.340493962Z',
        'size': 4661224676,
        'digest': '365c0bd3c000a25d28dsearch1c6add414de7275464c4e4d1c3b5fcb5d8ad1',
        'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '8.0B', 'quantization_level': 'Q4_0'}},
    'sqlcoder:15b': {
        'name': 'sqlcoder:15b',
        'model': 'sqlcoder:15b',
        'zip':'84098',
        'address': '',
        'title': 'Park City Soccer Club',
        'initials': 'PCSC',
        'ai_name': 'Bruno',
        'org_rep_type': 'Personal Customer Representative',
        'collection': 'parkcitysc-new',
        'prompt': GENERAL_PROMPT_TEMPLATE,
        'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
        'openai': 'gpt-4o-mini',
        'ollama': 'llama3:latest',
        'org_type': 'Soccer Club',
        'modified_at': '2024-06-29T06:01:39.480494281Z',
        'size': 8987630230,
        'digest': '93bb0e8a904ff98bcc6fa5cf3b8e63dc69203772f4bc713f761c82684541d08d',
        'details': {'parent_model': '', 'format': 'gguf', 'family': 'starcoder', 'families': None, 'parameter_size': '15B', 'quantization_level': 'Q4_0'}},
}

import uuid

from rai.agents.prompts import context

GENERAL_PROMPT_TEMPLATE = lambda ai_name, org_name, org_rep_type, specialty: f"""
Your name is {ai_name}, {org_name}'s {org_rep_type}.
You are here to serve at the pleasure of the members of {org_name}.

You are going to be a detailed and honest customer service representative who will answer questions based on information given to you.
{specialty}
GOLDEN RULE: If you do not know the answer based on information I give you, please just state you don't know.
"""

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
            'collection': 'parkcitysc',
            'prompt': GENERAL_PROMPT_TEMPLATE,
            'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
            'openai': 'gpt-4o',
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
            'ai_name': 'Nuro',
            'org_rep_type': 'Knowledge Base',
            'collection': 'medical-neuro',
            'prompt': GENERAL_PROMPT_TEMPLATE,
            'context_prompt': context.MEDICAL_CONTEXT_EXPANDER,
            'openai': 'gpt-4o',
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
    'ussf:latest': {
        'name': 'ussf:latest',
        'model': 'ussf:latest',
        'zip':'',
        'address': '',
        'title': 'United States Soccer Federation',
        'initials': 'USSF',
        'ai_name': 'Kevin',
        'org_rep_type': 'Personal Knowledge Base Master',
        'collection': 'ussf-internal',
        'prompt': GENERAL_PROMPT_TEMPLATE,
        'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
        'openai': 'gpt-4o',
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
}

def getRaiModels() -> dict:
    mods = []
    for model in RAI_MODs.keys():
        mods.append({'name': model, 'model': model, 'modified_at': '2024-07-02T06:32:47.913084094Z', 'size': 177669289, 'digest': str(uuid.uuid4()), 'details': {
            'parent_model': '',
            'format': 'gguf',
            'family': 'gpt2',
            'families': ['gpt2'],
            'parameter_size': '163.04M',
            'quantization_level': 'Q8_0'
        }},)
    return { 'models': mods }
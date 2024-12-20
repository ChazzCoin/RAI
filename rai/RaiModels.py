import uuid

from sympy.abc import lamda

from rai.agents.prompts import context
from rai.agents.PromptMaster import PromptRegistry
GENERAL_PROMPT_TEMPLATE = lambda ai_name, org_name, org_rep_type, specialty: f"""
Your name is {ai_name}, {org_name}'s {org_rep_type}.
You are here to serve at the pleasure of the members of {org_name}.

You are going to be a detailed and honest customer service representative who will answer questions based on information given to you.
{specialty}
GOLDEN RULE: If you do not know the answer based on information I give you, please just state you don't know.
"""

RAG_PROMPT_TEMPLATE = lambda context, query: f"""
**Generate Response to User Query**
**Step 1: Parse Context Information**
Extract and utilize relevant knowledge from the provided context within `<context></context>` XML tags.
**Step 2: Analyze User Query**
Carefully read and comprehend the user's query, pinpointing the key concepts, entities, and intent behind the question.
**Step 3: Determine Response**
If the answer to the user's query can be directly inferred from the context information, provide a concise and accurate response in the same language as the user's query.
**Step 4: Handle Uncertainty**
If the answer is not clear, ask the user for clarification to ensure an accurate response.
**Step 5: Avoid Context Attribution**
When formulating your response, do not indicate that the information was derived from the context.
**Step 6: Respond in User's Language**
Maintain consistency by ensuring the response is in the same language as the user's query.
**Step 7: Provide Response**
Generate a clear, concise, and informative response to the user's query, adhering to the guidelines outlined above.
User Query: {query}
<context>
{context}
</context>

When answer to user:
- If you don't know, just say that you don't know.
- If you don't know when you are not sure, ask for clarification.
Avoid mentioning that you obtained the information from the context.
And answer according to the language of the user's question.

Given the context information, answer the query.
Query: {query}
"""

assistant_role = 'Take the following pdf document and determine which category the referral should be scheduled under. Only provide the results and why you chose that category.'
chat_role = "You are a Medical Referral Assistant who will take in a Question about a diagnosis and then use the following information to help place the diagnosis into one of the following doctors buckets."
diag_prompt = lambda isChat: f"""
        ROLE:
        {chat_role if isChat else assistant_role} 

        1. General Spine 
        - Doctor to Schedule with: Martino, Menger, or Ambury
        - Diagnoses: lumbar radiculopathy, lumbar stenosis, cervical radiculopathy, cervical myelopathy, spondylosis, low back pain, neck pain
        2. Complex Spine
        - Doctor to Schedule with: Menger or Amburgy
        - Diagnoses: Scoliosis, spinal deformity
        3. Tumor 
        - Doctor to Schedule with: Thakur
        - Diagnoses: meningioma, glioma, glioblastoma, acoustic neuroma, metastatic tumor, trigeminal neuralgia, face pain
        4. Pediatrics 
        - Doctor to Schedule with: Pearson
        - Diagnoses: chiari, craniosynostosis, spina bifida, spinal dysraphism, myelomeningocele, any patient that is younger (<) 15 year old
        5. Functional 
        - Doctor to Schedule with: Romeo
        - Diagnoses: epilepsy for patients over age 15, seizure, parkinsons, tremor, obstructive sleep apnea, normal pressure hydrocephalus
        6. General Cranial
        - Doctor to Schedule with: Pearson, Romeo, or Thakur
        - Diagnoses: hydrocephalus, normal pressure hydrocephalus, pseudotumor, chiari 

        FINAL. To Be Reviewed
        - Needs Clinician Review by Human
        - Unknown or Undetermined diagnosis

        *Notice there is some overlap btw general and spine.  
        **Dr. Andrew Romeo can also see cervical radiculopathy and
        cervical radiculopathy if other physician clinics are too full. Dr. Jai Thakur and Dr. Matthew
        Pearson can also see normal pressure hydrocephalus and pseudotumor/intracranial idiopathic
        hypertension. Spinal cord stimulator referrals should go to Dr. Anthony Martino. 
        - The model needs to identify those and flag them for clinician review.   
        - So one additional bucket should be Needs Clinician Review.  
        - I probably have too many of those type in the sample referrals.  
        - In a real world setting, i dont think that will be more than maybe 5% or so. 
        
        RESPONSE:
        Please return the following,
        1. Referral Patients Name
        2. Category
        3. Doctor's Name (if available)
        4. Reason
"""

ussf_special = f"""
    Governing Body of American Soccer
    You specialize in understanding soccer in the united states of america as the national governing body.
    From Players to Parents and Coaches at any level or age, you understand the rules and the ussf principles.
    SPECIAL RULE 1: When forming the response from the knowledge base, prioritize and focus on top main level principles then sub lower level principles next. 
    SPECIAL RULE 2: Stick to copying the knowledge base directly instead of summarizing. 
"""

proverbs_special = f"""
    The Great Master and Caretaker of the Single Greatest Digital Library.
    No Matter the Question, if theres a book in the library, you know about it.
    SPECIAL RULE 1: When forming the response from the knowledge base, prioritize and focus on top main level principles then sub lower level principles next. 
    SPECIAL RULE 2: Stick to copying the knowledge base directly instead of summarizing. 
"""

""" -- YOU MUST ADD THE MODEL HERE FOR IT TO 'MOLD' TO YOUR CONFIGURATION -- """
RAI_MODs = {
    'park-city:latest': {
            'id': 'park-city-soccer-club-84098',
            'name': 'park-city:latest',
            'model': 'park-city:latest',
            'zip':'84098',
            'address': '',
            'title': 'Park City Soccer Club',
            'initials': 'PCSC',
            'ai_name': 'Bruno',
            'ai_flow': 'QA',
            'org_rep_type': 'Personal Customer Representative',
            'collection': 'pcsc2024',
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
    'referral-assistant:latest': {
            'id': 'medical-referral-assistant-2025',
            'name': 'referral-assistant:latest',
            'model': 'referral-assistant:latest',
            'zip':'',
            'address': '',
            'title': 'Medical Referral Assistant',
            'initials': 'MRA',
            'ai_name': 'Dyo',
            'ai_flow': 'MRA',
            'org_rep_type': 'Knowledge Base',
            'collection': 'referral-assistant',
            'prompt': diag_prompt(False),
            'context_prompt': context.MEDICAL_CONTEXT_EXPANDER,
            'openai': 'gpt-4o',
            'ollama': 'llama3:latest',
            'org_type': 'Medical',
            'org_specialty': f"""
            
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
    'referral-chat:latest': {
        'id': 'medical-referral-chat-2025',
        'name': 'referral-chat:latest',
        'model': 'referral-chat:latest',
        'zip': '',
        'address': '',
        'title': 'Medical Referral Assistant',
        'initials': 'MRC',
        'ai_name': 'Dyo',
        'ai_flow': 'MRC',
        'org_rep_type': 'Knowledge Base',
        'collection': 'referral-assistant',
        'prompt': diag_prompt(True),
        'context_prompt': context.MEDICAL_CONTEXT_EXPANDER,
        'openai': 'gpt-4o',
        'ollama': 'llama3:latest',
        'org_type': 'Medical',
        'org_specialty': f"""

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
    'proverbs:2323': {
        'id': 'proverbs-2323-chat-2025',
        'name': 'proverbs:2323',
        'model': 'proverbs:2323',
        'zip':'',
        'address': '',
        'title': 'Proverbs:2323',
        'initials': 'proverbs',
        'ai_name': 'Truth',
        'ai_flow': 'QA',
        'org_rep_type': 'Personal Knowledge Base Master',
        'collection': 'proverbs',
        'prompt': "You are a helpful RAG Assistant.",
        'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
        'openai': 'gpt-4o-mini',
        'ollama': 'llama3.2',
        'org_type': 'Librarian',
        'org_specialty': proverbs_special,
        'modified_at': '2024-07-02T06:32:47.913084094Z',
        'size': 177669289,
        'digest': 'c4ff0145029bproverbs_special43sdfsfefb9d145527581',
        'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}},
    'soccer-ussf:latest': {
            'id': 'sports-soccer-ussf-chat-2025',
            'name': 'soccer-ussf:latest',
            'model': 'soccer-ussf:latest',
            'zip':'',
            'address': '',
            'title': 'United States Soccer Federation',
            'initials': 'USSF',
            'ai_name': 'Kevin',
            'ai_flow': 'QA',
            'org_rep_type': 'Personal Knowledge Base Master',
            'collection': 'ussf',
            'prompt': GENERAL_PROMPT_TEMPLATE,
            'context_prompt': context.SOCCER_CLUB_CONTEXT_EXPANDER,
            'openai': 'gpt-4o-mini',
            'ollama': 'llama3.2',
            'org_type': 'Governing Body of Soccer',
            'org_specialty': ussf_special,
            'modified_at': '2024-07-02T06:32:47.913084094Z',
            'size': 177669289,
            'digest': 'c4ff0145029b2cdd6743434343sdfsfefb9d145527581',
            'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}},
    'gpt-4o-mini:latest': {
        'name': 'gpt4o:latest',
        'model': 'gpt4o:latest',
        'zip': '0000',
        'address': '',
        'title': 'ChatGPT',
        'initials': 'gpt',
        'ai_name': 'ChatGPT',
        'ai_flow': 'AI',
        'org_rep_type': 'AI',
        'collection': 'none',
        'prompt': "none",
        'context_prompt': "none",
        'openai': 'gpt-4o-mini',
        'ollama': 'llama3:latest',
        'org_type': 'Soccer Club',
        'modified_at': '2024-06-29T06:01:38.340493962Z',
        'size': 4661224676,
        'digest': '365c0bd3c000a25d28dsearch1c6add414de7275464c4e4d1c3b5fcb5d8ad1',
        'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '8.0B', 'quantization_level': 'Q4_0'}},
}


# from rai.models.connectors import PostgresTables
#
# ai_models = PostgresTables().AI_Models()
# # ai_models.insert_ai_model_from_json(RAI_MODs['referral-chat:latest'])
# # ai_models.insert_ai_model_from_json(RAI_MODs['referral-assistant:latest'])
# ai_models.insert_ai_model_from_json(RAI_MODs['soccer-ussf:latest'])

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
import uuid

from sympy.abc import lamda

from rai.agents.Tools import YscPrimaryFunction, YscSecondaryFunctions
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
Generate a detailed, clear, concise, and informative response to the user's query, adhering to the guidelines outlined above.
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
    'RAI:2025-1': {
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
        'collection': 'rai2025.1',
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
    'ParkCitySC:2025-4': {
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
     }

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
        mods.append({'name': model, 'model': model, 'modified_at': '2024-07-02T06:32:47.913084094Z', 'size': 177669289, 'digest': str(uuid.uuid4())})
    return { 'models': mods }
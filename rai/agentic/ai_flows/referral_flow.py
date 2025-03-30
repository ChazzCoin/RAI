import base64
import imghdr
import os
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

from rai.ingest.miners.Pdf import FPDF
from rai.agentic.agent_assistants.knowledge_assist import KnowledgeTool
from rai.assistant.connectors import rAI
from rai.ingest.utilities.TextUtils import TextProcessor

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

REFERRAL_AGENT_REGISTRY = {}
def register_referral_agent(name: str):
    def decorator(cls):
        REFERRAL_AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator

class rReferralFlow(ABC, rAI, TextProcessor):
    name = None
    first = []
    second = []
    third = []

    prefix = 'referral2025.3'

    @classmethod
    def flow(cls, name: str, user_prompt: str):
        agent_classes = REFERRAL_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(user_prompt=user_prompt)

    @classmethod
    async def flow_async(cls, name: str, user_prompt: str):
        agent_classes = REFERRAL_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return await agent_instance.run_async(user_prompt=user_prompt)
    @abstractmethod
    def run(self, user_prompt:str): pass
    @abstractmethod
    async def run_async(self, user_prompt:str): pass
    def system(self): return diag_prompt(isChat=True if str(self.name).endswith("chat") else False)
    def user(self, user_prompt:str):
        return self.decode_base64_to_file(user_prompt) if str(self.name).endswith("format") else user_prompt

    def decode_base64_to_file(self, file_input: str):
        # Determine the input type and obtain the file data in bytes
        if isinstance(file_input, str):
            if os.path.exists(file_input) and os.path.isfile(file_input):
                # The input is a file path; read the file's bytes
                with open(file_input, 'rb') as f:
                    file_bytes = f.read()
                # Convert file bytes to a base64 string
                base64_string = base64.b64encode(file_bytes).decode('utf-8')
            else:
                # Assume the string is already a base64 encoded value
                base64_string = file_input
            try:
                file_data = base64.b64decode(base64_string)
            except Exception as e:
                raise ValueError("Provided string is not valid base64 data.") from e
        elif isinstance(file_input, bytes):
            # Input is already bytes; use them directly
            file_data = file_input
        else:
            raise ValueError("Unsupported input type. Expected a file path, base64 string, or bytes.")

        # Process the decoded file data
        if file_data.startswith(b'%PDF'):
            # For PDFs, extract and return the text
            return FPDF.extract_text_from_pdf(file_data=file_data)
        else:
            # Check if the file is a supported image (jpeg or png)
            file_extension = imghdr.what(None, file_data)
            if file_extension not in ['jpeg', 'png']:
                raise ValueError(
                    "Unsupported file type: the provided input does not represent a JPEG, PNG, or PDF file."
                )
        return file_data

class ReferralResponse(BaseModel):
    patients_name: str
    category: str
    doctor_name: str
    reason: str

@register_referral_agent("medical-format")
class ReferralAgentFormatRunner(rReferralFlow):
    def run(self, user_prompt: str):
        try:
            _user = self.user(user_prompt)
            _system = self.system()
            return self.engine.generate_format(_user, _system, ReferralResponse)
        except Exception as e:
            print(f"Error: {e}")
            return None
    async def run_async(self, user_prompt: str):
        try:
            return self.generate_format("", "", ReferralResponse)
        except Exception as e:
            print(f"Error: {e}")
            return None

@register_referral_agent("medical-chat")
class ReferralAgentChatRunner(rReferralFlow):
    def run(self, user_prompt: str) -> Optional['RaiQueryAgentResults']:
        try:
            results = KnowledgeTool.get_pages(self.prefix)
            str_results = []
            for result in results:
                str_results.append(result.document)
            str_prompt = "\n".join(str_results)
            # response = rRagFlow.flow(name="base", prefix=self.prefix, user_prompt=user_prompt)
            _user = self.user(f"{user_prompt}\n{str_prompt}")
            _system = self.system()
            return self.generate(_user, _system)
        except Exception as e:
            print(f"Error: {e}")
            return None


    async def run_async(self, user_prompt: str) -> Optional['RaiQueryAgentResults']:
        try:
            return self.generate_format("", "", ReferralResponse)
        except Exception as e:
            print(f"Error: {e}")
            return None



def mains(name:str, user_prompt):
    # from rai.pipeline.utilities.text_data import schedule_text
    import json, pprint
    results = rReferralFlow.flow(
            name=name,
            user_prompt=user_prompt
        )
    if type(results) in [ReferralResponse]:
        print(f"""
            Patient Name: {results.patients_name}
            Category: {results.category}
            Doctors Name: {results.doctor_name}
            Reason: {results.reason}
        """)
    elif type(results) in [list, tuple]:
        print(pprint.pprint(results))
    elif type(results) in [dict]:
        print(json.dumps(results, indent=4))
    else:
        print(results)

if __name__ == "__main__":
    user_prompt = "/Users/chazzromeo/Desktop/portal/docs/referral1.pdf"
    query = "What is the diagnosis?"
    mains("medical-chat", user_prompt=query)

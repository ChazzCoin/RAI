from assistant import api
from dataset.PDF import FPDF
# Folders to Modify/Migrate
"""
Repository: relayhealthcare-webapp-newest
Branch: stabilize/ai
-> relayhealthcare-webapp-newest/model_functions (all)
-> /controllers (all)
-> /utils/providers (all)
-> /middleware
-> /routes
-> /helpers
"""

BASE = "/Users/chazzromeo/OneCall/relayhealthcare-webapp-newest"
FILES = [
    "/Users/chazzromeo/ChazzCoin/MedRefs/dataset/refers/Alan_Reed_Referral.pdf",
    "/Users/chazzromeo/ChazzCoin/MedRefs/dataset/refers/Brenda_King_Referral.pdf",
    "/Users/chazzromeo/ChazzCoin/MedRefs/dataset/refers/Emily_Carter_Referral.pdf",
    "/Users/chazzromeo/ChazzCoin/MedRefs/dataset/refers/Henry_Clark_Referral.pdf",
    "/Users/chazzromeo/ChazzCoin/MedRefs/dataset/refers/Joseph_Martin_Referral.pdf",
    "/Users/chazzromeo/ChazzCoin/MedRefs/dataset/refers/Karen_Thompson_Referral-2.pdf"
]
SUCCESSFUL_FILES = []
FAILED_FILES = []


prompt = f"""

Take the following pdf document and determine which category the referral should be scheduled under.
Only provide the results and why you chose that category.

1. Spine 
- Doctor to Schedule with: Okor
- Diagnoses: lumbar radiculopathy, scoliosis, lumbar stenosis, cervical radiculopathy, cervical myelopathy, (anything with the word spine or spinal in front of it)
2. Tumor 
- Doctor to Schedule with: Markert
- Diagnoses: meningioma, glioma, glioblastoma, acoustic neuroma, metastatic tumor, trigeminal neuralgia, face pain
3. Pediatrics 
- Doctor to Schedule with: Oakes
- Diagnoses: chiari, craniosynostosis, any patient that is younger (<) 15 year old
4. Functional 
- Doctor to Schedule with: Guthrie
- Diagnoses: epilepsy, seizure, parkinsons, tremor, obstructive sleep apnea, normal pressure hydrocephalus
5. General
- Doctor to Schedule with: Manley, Smith
- Diagnoses: lumbar stenosis, lumbar radiculopathy, cervical radiculopathy, cervical myelopathy, low back pain, neck pain

*Notice there is some overlap btw general and spine.  
**Also note all referrals will not correctly align diagnosis and surgeon (ex. referral may say brain tumor for Dr. Okor).  
The model needs to identify those and flag them for clinician review.   
So one additional bucket should be Needs Clinician Review.  
I probably have too many of those type in the sample referrals.  
In a real world setting, i dont think that will be more than maybe 5% or so. 

"""
def run_manual_files():
    # Select the proper folder
    for file in FILES:
        try:
            content = FPDF(file_path=file).extract_text_from_pdf(file)
            results = api.chatgpt_request(prompt, content, model="gpt-4o")
            SUCCESSFUL_FILES.append(file)
            print("-------")
            print(results)
            print("-------")
        except Exception as e:
            FAILED_FILES.append(file)
            print(f"Error processing file: {file} with error", e)


if __name__ == "__main__":
    run_manual_files()
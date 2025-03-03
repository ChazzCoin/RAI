"""
1. Medical Diagnosis
2. Doctor to Schedule with
3. Diagnoses Description Model
--
4. Validator for Diagnosis Model %
"""


DIAGNOSTIC_SYSTEM_PROMPT = f"""

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
6. To Be Reviewed
- Needs Clinician Review by Human
- Unknown or Undetermined diagnosis

*Notice there is some overlap btw general and spine.  
**Also note all referrals will not correctly align diagnosis and surgeon (ex. referral may say brain tumor for Dr. Okor).  
The model needs to identify those and flag them for clinician review.   
So one additional bucket should be Needs Clinician Review.  
I probably have too many of those type in the sample referrals.  
In a real world setting, i dont think that will be more than maybe 5% or so. 

"""
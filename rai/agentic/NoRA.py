

from rai.agentic.ai_plugins.QCache import VectorCache
from rai.agentic.ai_plugins.QStore import VectorStore
from rai.agentic.ai_plugins.redis_state import PluginState
from rai.assistant.connectors import rAI
from rai.ingest.utilities.TextUtils import TextProcessor


from abc import ABC
# Assuming rAI, TextProcessor, PluginState, VectorStore, and VectorCache
# are provided by the system.

class NoRAgent(ABC, rAI, TextProcessor):
    name = None

    # Our current state object; using a PluginState for internal state management.
    state = PluginState('nora')
    store = VectorStore()
    cache = VectorCache()

    def __init__(self):
        super().__init__()
        self.session_data = {}

    def set_state(self, new_state: str):
        """Transition to a new state."""
        self.state.value = new_state
        # Optionally log or process state changes here.

    # -----------------------------
    # Preoperative States
    # -----------------------------

    def pre_timeout(self, surgeon: str, patient: str, procedure: str, side: str, medications: list):
        """
        Preoperative Timeout:
            - Confirm Surgeon, Patient, Procedure, Side of Surgery, and preoperative medications given.
        """
        self.session_data['pre:timeout'] = {
            'surgeon': surgeon,
            'patient': patient,
            'procedure': procedure,
            'side': side,
            'medications': medications
        }
        confirmation = (
            f"Preoperative timeout confirmed:\n"
            f"  Surgeon: {surgeon}\n"
            f"  Patient: {patient}\n"
            f"  Procedure: {procedure}\n"
            f"  Side: {side}\n"
            f"  Preoperative Medications: {', '.join(medications)}"
        )
        return confirmation

    def pre_signout(self, procedure_performed: str, pathology_specimen_present: bool):
        """
        Postoperative Sign Out:
            - Confirm Procedure performed and presence of pathology specimen.
        """
        self.session_data['pre:signout'] = {
            'procedure_performed': procedure_performed,
            'pathology_specimen_present': pathology_specimen_present
        }
        confirmation = (
            f"Postoperative sign out confirmed:\n"
            f"  Procedure Performed: {procedure_performed}\n"
            f"  Pathology Specimen Present: {pathology_specimen_present}"
        )
        return confirmation

    # -----------------------------
    # Live Procedure States
    # -----------------------------

    def live_craniotomy_epilepsy(self, pathology_specimen_present: bool, neuropace_rep_present: bool):
        """
        Craniotomy for Epilepsy:
            • Usually has pathology specimen.
            • Neuropace placement requires a representative present.
        """
        self.session_data['live:Craniotomy for Epilepsy'] = {
            'pathology_specimen_present': pathology_specimen_present,
            'neuropace_rep_present': neuropace_rep_present
        }
        confirmation = (
            f"Live procedure: Craniotomy for Epilepsy confirmed:\n"
            f"  Pathology Specimen: {'present' if pathology_specimen_present else 'absent'}\n"
            f"  Neuropace Representative: {'present' if neuropace_rep_present else 'absent'}"
        )
        return confirmation

    def live_dbs_lead_placement(self, side: str, company: str, target: str, targeting_system: str, nexframe_array: bool):
        """
        Deep Brain Stimulation Lead Placement:
            • Required: Confirm Side, Company, Target, Targeting System, Nexframe Array.
        """
        self.session_data['live:Deep Brain Stimulation Lead Placement'] = {
            'side': side,
            'company': company,
            'target': target,
            'targeting_system': targeting_system,
            'nexframe_array': nexframe_array
        }
        confirmation = (
            f"Live procedure: Deep Brain Stimulation Lead Placement confirmed:\n"
            f"  Side: {side}\n"
            f"  Company: {company}\n"
            f"  Target: {target}\n"
            f"  Targeting System: {targeting_system}\n"
            f"  Nexframe Array: {'present' if nexframe_array else 'absent'}"
        )
        return confirmation

    def live_dbs_battery_initial(self, side: str, battery_type: str):
        """
        Deep Brain Stimulation Battery Initial Placement:
            • Required: Confirm Side and Battery Type.
        """
        self.session_data['live:Deep Brain Stimulation Battery Initial Placement'] = {
            'side': side,
            'battery_type': battery_type
        }
        confirmation = (
            f"Live procedure: Deep Brain Stimulation Battery Initial Placement confirmed:\n"
            f"  Side: {side}\n"
            f"  Battery Type: {battery_type}"
        )
        return confirmation

    def live_dbs_battery_replacement(self, side: str, battery_type: str):
        """
        Deep Brain Stimulator Battery Replacement:
            • Required: Confirm Side and Battery Type.
        """
        self.session_data['live:Deep Brain Stimulator Battery Replacement'] = {
            'side': side,
            'battery_type': battery_type
        }
        confirmation = (
            f"Live procedure: Deep Brain Stimulator Battery Replacement confirmed:\n"
            f"  Side: {side}\n"
            f"  Battery Type: {battery_type}"
        )
        return confirmation

    def live_stereotactic_depth_electrode_placement(self, side: str, electrode_rep_present: bool, globus_rep_present: bool):
        """
        Stereotactic Depth Electrode Placement:
            • Required: Confirm Side.
            • Action: Ensure Electrode rep and Globus rep are present.
        """
        self.session_data['live:Stereotactic Depth Electrode Placement'] = {
            'side': side,
            'electrode_rep_present': electrode_rep_present,
            'globus_rep_present': globus_rep_present
        }
        confirmation = (
            f"Live procedure: Stereotactic Depth Electrode Placement confirmed:\n"
            f"  Side: {side}\n"
            f"  Electrode Representative: {'present' if electrode_rep_present else 'absent'}\n"
            f"  Globus Representative: {'present' if globus_rep_present else 'absent'}"
        )
        return confirmation

    def live_hypoglossal_nerve_stimulator_placement(self, motor_monitoring_performed: bool, paralytic_used: bool):
        """
        Hypoglossal Nerve Stimulator Placement:
            • Action: No paralytic is used and motor monitoring is performed.
        """
        self.session_data['live:Hypoglossal Nerve Stimulator Placement'] = {
            'motor_monitoring_performed': motor_monitoring_performed,
            'paralytic_used': paralytic_used
        }
        confirmation = (
            f"Live procedure: Hypoglossal Nerve Stimulator Placement confirmed:\n"
            f"  Motor Monitoring Performed: {motor_monitoring_performed}\n"
            f"  Paralytic Used: {paralytic_used} (should be False)"
        )
        return confirmation

    def live_craniotomy_tumor_resection(self, surgeon: str, frozen_specimen: bool, permanent_specimen: bool,
                                         sonopet_available: bool, microscope_available: bool):
        """
        1. Craniotomy for Tumor resection:
            • Both frozen and permanent pathology specimens are expected.
            • Required Data: Need sonopet and microscope.
            • Additional: If surgeon is Dr. Jai Thakur, confirm availability of number 2 kerrison.
        """
        # Determine if the number 2 kerrison is required.
        required_kerrison = surgeon == "Dr. Jai Thakur"
        self.session_data['live:Craniotomy for Tumor resection'] = {
            'surgeon': surgeon,
            'frozen_specimen': frozen_specimen,
            'permanent_specimen': permanent_specimen,
            'sonopet_available': sonopet_available,
            'microscope_available': microscope_available,
            'required_kerrison': required_kerrison
        }
        confirmation = (
            f"Live procedure: Craniotomy for Tumor resection confirmed:\n"
            f"  Frozen Specimen: {'present' if frozen_specimen else 'absent'}\n"
            f"  Permanent Specimen: {'present' if permanent_specimen else 'absent'}\n"
            f"  Sonopet: {'available' if sonopet_available else 'not available'}\n"
            f"  Microscope: {'available' if microscope_available else 'not available'}"
        )
        if required_kerrison:
            confirmation += "\n  Note: Number 2 kerrison is required due to Dr. Jai Thakur's involvement."
        return confirmation

    def live_endoscopic_endonasal_tumor_resection(self, frozen_specimen: bool, permanent_specimen: bool):
        """
        2. Endoscopic Endonasal Tumor resection:
            • Both frozen and permanent pathology specimens are expected.
        """
        self.session_data['live:Endoscopic Endonasal Tumor resection'] = {
            'frozen_specimen': frozen_specimen,
            'permanent_specimen': permanent_specimen
        }
        confirmation = (
            f"Live procedure: Endoscopic Endonasal Tumor resection confirmed:\n"
            f"  Frozen Specimen: {'present' if frozen_specimen else 'absent'}\n"
            f"  Permanent Specimen: {'present' if permanent_specimen else 'absent'}"
        )
        return confirmation

    def live_vp_shunt_placement(self, valve_type: str, valve_setting: str, antibiotic_catheters_available: bool):
        """
        3. Ventriculoperitoneal shunt placement:
            • Requires general surgery for laparoscopic assistance.
            • Required Data: Confirm valve type and setting; confirm availability of antibiotic impregnated catheters.
        """
        self.session_data['live:Ventriculoperitoneal shunt placement'] = {
            'valve_type': valve_type,
            'valve_setting': valve_setting,
            'antibiotic_catheters_available': antibiotic_catheters_available
        }
        confirmation = (
            f"Live procedure: Ventriculoperitoneal shunt placement confirmed:\n"
            f"  Valve Type: {valve_type}\n"
            f"  Valve Setting: {valve_setting}\n"
            f"  Antibiotic Impregnated Catheters: {'available' if antibiotic_catheters_available else 'not available'}"
        )
        return confirmation

    # -----------------------------
    # Centralized Processing Method
    # -----------------------------

    def process(self, state: str, **kwargs) -> str:
        """
        Routes the incoming data to the appropriate state method based on the state string
        and procedure type (if applicable).
        """
        if state == 'pre:timeout':
            return self.pre_timeout(**kwargs)
        elif state == 'pre:signout':
            return self.pre_signout(**kwargs)
        elif state.startswith('live:'):
            # Expect a key 'procedure' in kwargs to indicate the specific live procedure.
            procedure = kwargs.pop('procedure', None)
            if procedure == 'Craniotomy for Epilepsy':
                return self.live_craniotomy_epilepsy(**kwargs)
            elif procedure == 'Deep Brain Stimulation Lead Placement':
                return self.live_dbs_lead_placement(**kwargs)
            elif procedure == 'Deep Brain Stimulation Battery Initial Placement':
                return self.live_dbs_battery_initial(**kwargs)
            elif procedure == 'Deep Brain Stimulator Battery Replacement':
                return self.live_dbs_battery_replacement(**kwargs)
            elif procedure == 'Stereotactic Depth Electrode Placement':
                return self.live_stereotactic_depth_electrode_placement(**kwargs)
            elif procedure == 'Hypoglossal Nerve Stimulator Placement':
                return self.live_hypoglossal_nerve_stimulator_placement(**kwargs)
            elif procedure == 'Craniotomy for Tumor resection':
                return self.live_craniotomy_tumor_resection(**kwargs)
            elif procedure == 'Endoscopic Endonasal Tumor resection':
                return self.live_endoscopic_endonasal_tumor_resection(**kwargs)
            elif procedure == 'Ventriculoperitoneal shunt placement':
                return self.live_vp_shunt_placement(**kwargs)
            else:
                return "Unknown live procedure state. Please check the procedure type."
        else:
            return "Unknown state provided."

# Example usage:
# agent = NoRAgent("Nora", my_vector_store)
# print(agent.process('pre:timeout', surgeon="Dr. Andrew Romeo", patient="John Doe", procedure="Deep Brain Stimulation Lead Placement", side="Left", medications=["Midazolam", "Fentanyl"]))

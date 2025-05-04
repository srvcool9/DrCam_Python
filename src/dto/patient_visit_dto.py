class PatientVisitDTO:
    def __init__(self, patient_id=None, appointment_id="", patient_name="", last_visited=""):
        self.patient_id = patient_id
        self.appointment_id = appointment_id
        self.patient_name = patient_name
        self.last_visited = last_visited

    @staticmethod
    def from_map(data: dict):
        return PatientVisitDTO(
            patient_id=data.get("patientId"),
            appointment_id=data.get("appointmentId", ""),
            patient_name=data.get("patientName", ""),
            last_visited=data.get("lastVisited", "")
        )

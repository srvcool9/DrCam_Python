class PatientVisitDTO:
    def __init__(self, patient_id=None, appointment_id="", patient_name="", last_visited=""):
        self.patient_id = patient_id
        self.appointment_id = appointment_id
        self.patient_name = patient_name
        self.last_visited = last_visited

    @staticmethod
    def from_map(data):
        if isinstance(data, PatientVisitDTO):
            return data  # already a DTO, return as-is

        if not isinstance(data, dict):
            raise ValueError("Expected a dict for from_map(), got: {}".format(type(data)))

        return PatientVisitDTO(
            patient_id=data.get("patientId"),
            appointment_id=data.get("appointmentId", ""),
            patient_name=data.get("patientName", ""),
            last_visited=data.get("lastVisited", "")
        )

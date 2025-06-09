class PatientVisitDTO:
    def __init__(self, patient_id=None, appointment_id="", patient_name="", last_visited="", visit_dates=None):
        self.patient_id = patient_id
        self.appointment_id = appointment_id
        self.patient_name = patient_name
        self.last_visited = last_visited
        self.visit_dates = visit_dates or []

    @staticmethod
    def from_map(data):
        if isinstance(data, PatientVisitDTO):
            return data

        if not isinstance(data, dict):
            raise ValueError("Expected a dict for from_map(), got: {}".format(type(data)))

        # Parse visitDates (comma-separated string) into list
        visit_dates_str = data.get("visitDates", "")
        visit_dates = visit_dates_str.split(",") if visit_dates_str else []

        return PatientVisitDTO(
            patient_id=data.get("patientId"),
            appointment_id=data.get("appointmentId", ""),
            patient_name=data.get("patientName", ""),
            last_visited=data.get("lastVisited", ""),
            visit_dates=visit_dates
        )

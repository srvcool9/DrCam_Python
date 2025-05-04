

class PatientHistoryModel:
    def __init__(self, id=None, appointment_id="", patient_id=None, appointment_date="", created_on=""):
        self.id = id
        self.appointment_id = appointment_id
        self.patient_id = patient_id
        self.appointment_date = appointment_date
        self.created_on = created_on

    def to_map(self):
        return {
            "id": self.id,
            "appointmentId": self.appointment_id,
            "patientId": self.patient_id,
            "appointmentDate": self.appointment_date,
            "createdOn": self.created_on
        }

    @staticmethod
    def from_map(data: dict):
        return PatientHistoryModel(
            id=data.get("id"),
            appointment_id=data.get("appointmentId", ""),
            patient_id=data.get("patientId"),
            appointment_date=data.get("appointmentDate", ""),
            created_on=data.get("createdOn", "")
        )

    @staticmethod
    def get_table_name():
        return "patient_history"

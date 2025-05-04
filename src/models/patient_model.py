
class PatientsModel:
    def __init__(self, patient_id=None, appointment_id="", patient_name="", gender="", date_of_birth="", phone="", address=""):
        self.patient_id = patient_id
        self.appointment_id = appointment_id
        self.patient_name = patient_name
        self.gender = gender
        self.date_of_birth = date_of_birth
        self.phone = phone
        self.address = address

    def to_map(self):
        return {
            "patientId": self.patient_id,
            "appointmentId": self.appointment_id,
            "patientName": self.patient_name,
            "gender": self.gender,
            "dateOfBirth": self.date_of_birth,
            "phone": self.phone,
            "address": self.address
        }

    @staticmethod
    def from_map(data: dict):
        return PatientsModel(
            patient_id=data.get("patientId"),
            appointment_id=data.get("appointmentId", ""),
            patient_name=data.get("patientName", ""),
            gender=data.get("gender", ""),
            date_of_birth=data.get("dateOfBirth", ""),
            phone=data.get("phone", ""),
            address=data.get("address", "")
        )

    @staticmethod
    def get_table_name():
        return "patients"

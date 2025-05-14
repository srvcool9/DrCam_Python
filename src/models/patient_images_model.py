class PatientImagesModel:
    def __init__(self, image_id=None, patient_id=None, history_id=None, image_base64="", created_on=""):
        self.image_id = image_id
        self.patient_id = patient_id
        self.history_id = history_id
        self.image_base64 = image_base64
        self.created_on = created_on

    def to_map(self):
        return {
            "id": self.image_id,
            "patientId": self.patient_id,
            "historyId": self.history_id,
            "imageBase64": self.image_base64,
            "createdOn": self.created_on
        }

    @staticmethod
    def from_map(data: dict):
        return PatientImagesModel(
            image_id=data.get("id"),
            patient_id=data.get("patientId"),
            history_id=data.get("historyId"),
            image_base64=data.get("imageBase64", ""),
            created_on=data.get("createdOn", "")
        )

    @staticmethod
    def get_table_name():
        return "patient_images"

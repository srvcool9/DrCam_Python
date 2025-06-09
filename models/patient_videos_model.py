class PatientVideosModel:
    def __init__(self, id=None, patient_id=None, history_id=None, video_path="", created_on=""):
        self.id = id
        self.patient_id = patient_id
        self.history_id = history_id
        self.video_path = video_path
        self.created_on = created_on

    def to_map(self):
        return {
            "id": self.id,
            "patientId": self.patient_id,
            "historyId": self.history_id,
            "videoPath": self.video_path,
            "createdOn": self.created_on
        }

    @staticmethod
    def from_map(data: dict):
        return PatientVideosModel(
            id=data.get("id"),
            patient_id=data.get("patientId"),
            history_id=data.get("historyId"),
            video_path=data.get("videoPath", ""),
            created_on=data.get("createdOn", "")
        )

    @staticmethod
    def get_table_name():
        return "patient_videos"

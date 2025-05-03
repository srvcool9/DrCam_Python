
class ProfileModel:
    def __init__(self, id=None, agency_name="", contact_number="", email="", password="", mex_email="", mex_contact=""):
        self.id = id
        self.agency_name = agency_name
        self.contact_number = contact_number
        self.email = email
        self.password = password


    def to_map(self):
        return {
            "id": self.id,
            "agency_name": self.agency_name,
            "contact_number": self.contact_number,
            "email": self.email,
            "password": self.password
        }

    @staticmethod
    def from_map(data: dict):
        return ProfileModel(
            id=data.get("id"),
            agency_name=data.get("agency_name", ""),
            contact_number=data.get("contact_number", ""),
            email=data.get("email", ""),
            password=data.get("password", "")

        )

    @staticmethod
    def get_table_name():
        return "doctor_profile"

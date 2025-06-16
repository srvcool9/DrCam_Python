class CameraSettingsModel:
    def __init__(self, id=1, zoom=1.0, brightness=0, contrast=0, exposure=0.0, white_balance=0.0, frame_rate=20.0):
        self.id = id
        self.zoom = zoom
        self.brightness = brightness
        self.contrast = contrast
        self.exposure = exposure
        self.white_balance = white_balance
        self.frame_rate = frame_rate

    def to_map(self):
        return {
            "id": self.id,
            "zoom": self.zoom,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "exposure": self.exposure,
            "white_balance": self.white_balance,
            "frame_rate": self.frame_rate
        }

    @staticmethod
    def from_map(data: dict):
        return CameraSettingsModel(
            id=data.get("id", 1),
            zoom=data.get("zoom", 1.0),
            brightness=data.get("brightness", 0),
            contrast=data.get("contrast", 0),
            exposure=data.get("exposure", 0.0),
            white_balance=data.get("white_balance", 0.0),
            frame_rate=data.get("frame_rate", 20.0)
        )

    @staticmethod
    def get_table_name():
        return "camera_settings"

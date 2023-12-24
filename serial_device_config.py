import tomlkit


class SerialDeviceConfig:
    def __init__(self, default_port, baud_rate: int, active: bool):
        self.default_port = default_port
        self.baud_rate = baud_rate
        self.active = active

    @classmethod
    def read_from_file(cls, path, name: str):
        with open(path, "r") as f:
            doc = tomlkit.load(f)
            table = doc[name]

            default_port = table["com_port"]
            baud_rate = table["baud_rate"]
            active = table["active"]

            return SerialDeviceConfig(default_port, baud_rate, active)

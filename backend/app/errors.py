class VoltWiseError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class DeviceNotFoundError(VoltWiseError):
    def __init__(self, device_id: str) -> None:
        super().__init__(
            "DEVICE_NOT_FOUND", f"Unknown device: {device_id}", status_code=404
        )

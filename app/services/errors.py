class ServiceError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    pass


class InvalidRequest(ServiceError):
    pass


class ConflictError(ServiceError):
    pass

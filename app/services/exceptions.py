class ServiceError(Exception):
    pass


class DuplicateStudentCodeError(ServiceError):
    pass


class DuplicateCardIdError(ServiceError):
    pass


class StudentNotFoundError(ServiceError):
    pass


class UnknownCardError(ServiceError):
    pass


class InactiveStudentError(ServiceError):
    pass


class TouchTokenNotFoundError(ServiceError):
    pass


class TouchTokenExpiredError(ServiceError):
    pass


class InvalidActionError(ServiceError):
    pass

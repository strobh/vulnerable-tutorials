class VulntutsError(Exception):
    pass


class InvalidArgumentError(VulntutsError):
    pass


class SearchError(VulntutsError):
    pass


class ApiError(VulntutsError):
    pass


class InvalidInspectionError(VulntutsError):
    pass


class InspectionTypeChangedError(VulntutsError):
    pass

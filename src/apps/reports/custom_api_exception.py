from rest_framework.exceptions import APIException

class CustomAPIException(APIException):
    status_code = 400
    default_detail = 'An error occurred'
    default_code = 'error'

    def __init__(self, detail=None):
        self.detail = detail or self.default_detail
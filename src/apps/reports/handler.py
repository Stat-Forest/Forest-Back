from rest_framework.response import Response
from rest_framework.views import exception_handler
from .custom_api_exception import CustomAPIException


def custom_exception_handler(exc, context):
    if isinstance(exc, CustomAPIException):
        response_data = {
            'code': exc.default_code,
            'status_code': exc.status_code,
        }

        if isinstance(exc.detail, dict):
            response_data['errors'] = exc.detail
        else:
            response_data['detail'] = exc.detail

        return Response(response_data, status=exc.status_code)

    return exception_handler(exc, context)







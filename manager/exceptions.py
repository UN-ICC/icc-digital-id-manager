from rest_framework.exceptions import APIException


class ConnectionNotReady(APIException):
    status_code = 403
    default_detail = "Connection not ready."
    default_code = "connection_not_ready"

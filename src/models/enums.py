from enum import StrEnum


class IntegrationType(StrEnum):
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "Azure"


class HttpStatus(StrEnum):
    OK = "200"
    CREATED = "201"
    NO_CONTENT = "204"
    BAD_REQUEST = "400"
    UNAUTHORIZED = "401"
    NOT_FOUND = "404"
    CONFLICT = "409"
    INTERNAL_SERVER_ERROR = "500"


EXPECTED_STATUS = {
    "create_integration": 200,
    "get_integration": 200,
    "list_integrations": 200,
    "update_integration": 200,
    "delete_integration": 200,
    "create_asset": 200,
    "get_asset": 200,
    "list_assets": 200,
    "update_asset": 200,
    "delete_asset": 204,
}

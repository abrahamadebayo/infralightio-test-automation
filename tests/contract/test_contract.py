"""OpenAPI contract validation tests."""

import pytest

from src.client import APIClient
from src.models import EXPECTED_STATUS, IntegrationType
from src.models import Asset, Integration
from tests.helpers import unique_name


def _spec_response_codes(spec: dict, path: str, method: str) -> list[str]:
    """Extract defined response status codes from the swagger spec."""
    return list(
        spec.get("paths", {}).get(path, {}).get(method, {}).get("responses", {}).keys()
    )


def _spec_definition_fields(spec: dict, model_name: str) -> set[str]:
    """Extract field names from a swagger spec definition."""
    for key in spec.get("definitions", {}):
        if model_name.lower() in key.lower():
            return set(spec["definitions"][key].get("properties", {}).keys())
    return set()


@pytest.mark.contract
class TestIntegrationResponseSchema:

    def test_create_response_matches_model(
        self,
        user1_client: APIClient,
        integration_factory,
    ):
        name = unique_name("schema")
        data = integration_factory(user1_client, name, IntegrationType.AWS)
        integration = Integration.model_validate(data)
        assert integration.id
        assert integration.name == name
        assert integration.type == IntegrationType.AWS
        assert integration.tenant_id

    def test_list_response_is_array_of_integrations(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        resp = user1_client.list_integrations()
        data = resp.json()
        assert isinstance(data, list), (
            f"BUG: List integrations returns {type(data).__name__}, spec requires array"
        )
        for item in data:
            Integration.model_validate(item)

    def test_get_response_matches_model(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        resp = user1_client.get_integration(user1_base_integration["id"])
        Integration.model_validate(resp.json())


@pytest.mark.contract
class TestAssetResponseSchema:

    def test_create_response_matches_model(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
        asset_factory,
    ):
        data = asset_factory(user1_client, user1_base_integration["id"])
        Asset.model_validate(data)

    def test_list_response_is_array_of_assets(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
        user1_base_asset: dict,
    ):
        resp = user1_client.list_assets(user1_base_integration["id"])
        data = resp.json()
        assert isinstance(data, list)
        for item in data:
            Asset.model_validate(item)

    def test_get_response_matches_model(
        self,
        user1_client: APIClient,
        user1_base_asset: dict,
    ):
        resp = user1_client.get_asset(user1_base_asset["id"])
        Asset.model_validate(resp.json())


@pytest.mark.contract
class TestErrorResponseSchema:

    def test_404_error_matches_spec_schema(self, user1_client: APIClient):
        resp = user1_client.get_integration("nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert "code" in data and "message" in data, (
            f"BUG: Error response is {data}, "
            f"spec requires {{code: int, message: str}}"
        )

    def test_400_error_matches_spec_schema(self, user1_client: APIClient):
        resp = user1_client.raw_request("GET", "/assets")
        assert resp.status_code == 400
        data = resp.json()
        assert "code" in data and "message" in data, (
            f"BUG: Error response is {data}, "
            f"spec requires {{code: int, message: str}}"
        )

    def test_401_error_matches_spec_schema(self, bad_creds_client: APIClient):
        resp = bad_creds_client.list_integrations()
        assert resp.status_code == 401


@pytest.mark.contract
class TestStatusCodes:

    def test_create_integration_status_code(self, user1_client: APIClient):
        resp = user1_client.create_integration(unique_name(), IntegrationType.AWS)
        assert resp.status_code == EXPECTED_STATUS["create_integration"], (
            f"BUG: POST /integrations returns {resp.status_code}, "
            f"spec says {EXPECTED_STATUS['create_integration']}"
        )

    def test_create_asset_status_code(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        resp = user1_client.create_asset(unique_name(), "desc", user1_base_integration["id"])
        assert resp.status_code == EXPECTED_STATUS["create_asset"], (
            f"BUG: POST /assets returns {resp.status_code}, "
            f"spec says {EXPECTED_STATUS['create_asset']}"
        )

    def test_delete_asset_status_code(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        resp = user1_client.create_asset(unique_name("delsc"), "desc", user1_base_integration["id"])
        asset_id = resp.json()["id"]
        del_resp = user1_client.delete_asset(asset_id)
        assert del_resp.status_code == EXPECTED_STATUS["delete_asset"], (
            f"BUG: DELETE /assets/{{id}} returns {del_resp.status_code}, "
            f"spec says {EXPECTED_STATUS['delete_asset']}"
        )


@pytest.mark.contract
class TestContentNegotiation:

    def test_response_content_type_is_json(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        resp = user1_client.list_integrations()
        assert "application/json" in resp.headers.get("Content-Type", ""), (
            f"Response Content-Type is {resp.headers.get('Content-Type')}, "
            f"expected application/json"
        )

    def test_invalid_content_type_rejected(self, user1_client: APIClient):
        resp = user1_client.raw_request(
            "POST",
            "/integrations",
            headers={"Content-Type": "text/plain"},
            data='{"name":"test","type":"AWS"}',
        )
        assert resp.status_code in (400, 415), (
            f"BUG: API accepts text/plain Content-Type (status {resp.status_code})"
        )


@pytest.mark.contract
class TestNullVsEmptyArray:

    def test_empty_integration_list_not_null(self, user1_client: APIClient):
        resp = user1_client.list_integrations()
        body = resp.text.strip()
        assert body != "null", (
            "BUG: Empty integration list returns null instead of []"
        )

    def test_empty_asset_list_not_null(self, user1_client: APIClient):
        resp = user1_client.list_assets("nonexistent-integration-id")
        body = resp.text.strip()
        assert body != "null", (
            "BUG: Empty asset list returns null instead of []"
        )


@pytest.mark.contract
class TestSwaggerSpecCompliance:
    """Validate API behavior against the live swagger specification."""

    def test_spec_defines_integration_endpoints(self, swagger_spec: dict):
        paths = swagger_spec.get("paths", {})
        integration_paths = [p for p in paths if "integration" in p.lower()]
        assert integration_paths, (
            f"Swagger spec has no integration endpoints. Paths: {list(paths.keys())}"
        )

    def test_spec_defines_asset_endpoints(self, swagger_spec: dict):
        paths = swagger_spec.get("paths", {})
        asset_paths = [p for p in paths if "asset" in p.lower()]
        assert asset_paths, (
            f"Swagger spec has no asset endpoints. Paths: {list(paths.keys())}"
        )

    def test_create_integration_status_matches_spec(
        self,
        swagger_spec: dict,
        user1_client: APIClient,
    ):
        spec_codes = _spec_response_codes(swagger_spec, "/integrations", "post")
        resp = user1_client.create_integration(unique_name("spec"), IntegrationType.AWS)
        assert str(resp.status_code) in spec_codes, (
            f"BUG: POST /integrations returns {resp.status_code}, "
            f"spec defines responses for: {spec_codes}"
        )

    def test_create_asset_status_matches_spec(
        self,
        swagger_spec: dict,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        spec_codes = _spec_response_codes(swagger_spec, "/assets", "post")
        resp = user1_client.create_asset(
            unique_name("spec"), "desc", user1_base_integration["id"],
        )
        assert str(resp.status_code) in spec_codes, (
            f"BUG: POST /assets returns {resp.status_code}, "
            f"spec defines responses for: {spec_codes}"
        )

    def test_list_integrations_status_matches_spec(
        self,
        swagger_spec: dict,
        user1_client: APIClient,
    ):
        spec_codes = _spec_response_codes(swagger_spec, "/integrations", "get")
        resp = user1_client.list_integrations()
        assert str(resp.status_code) in spec_codes, (
            f"BUG: GET /integrations returns {resp.status_code}, "
            f"spec defines responses for: {spec_codes}"
        )

    def test_delete_integration_status_matches_spec(
        self,
        swagger_spec: dict,
        user1_client: APIClient,
    ):
        resp = user1_client.create_integration(unique_name("specdelint"), IntegrationType.AWS)
        integration_id = resp.json()["id"]
        spec_codes = _spec_response_codes(
            swagger_spec, "/integrations/{id}", "delete",
        )
        del_resp = user1_client.delete_integration(integration_id)
        assert str(del_resp.status_code) in spec_codes, (
            f"BUG: DELETE /integrations/{{id}} returns {del_resp.status_code}, "
            f"spec defines responses for: {spec_codes}"
        )

    def test_response_fields_match_spec_definition(
        self,
        swagger_spec: dict,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        spec_fields = _spec_definition_fields(swagger_spec, "Integration")
        if not spec_fields:
            pytest.skip("Integration definition not found in swagger spec")
        resp = user1_client.get_integration(user1_base_integration["id"])
        actual_fields = set(resp.json().keys())
        missing = spec_fields - actual_fields
        assert not missing, (
            f"BUG: Response missing fields defined in spec: {missing}"
        )

    def test_error_response_matches_spec_definition(
        self,
        swagger_spec: dict,
        user1_client: APIClient,
    ):
        spec_fields = _spec_definition_fields(swagger_spec, "Error")
        if not spec_fields:
            pytest.skip("Error definition not found in swagger spec")
        resp = user1_client.get_integration("nonexistent")
        actual_fields = set(resp.json().keys())
        missing = spec_fields - actual_fields
        assert not missing, (
            f"BUG: Error response missing fields defined in spec: {missing}. "
            f"Got {actual_fields}, spec requires {spec_fields}"
        )

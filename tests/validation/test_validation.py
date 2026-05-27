"""Input validation and edge-case tests."""

import pytest

from src.client import APIClient
from src.models import IntegrationType


@pytest.mark.validation
class TestIntegrationValidation:

    def test_create_empty_body_returns_400(self, user1_client: APIClient):
        resp = user1_client.raw_request(
            "POST", "/integrations", json={},
        )
        assert resp.status_code == 400, (
            f"BUG: Empty body returns {resp.status_code}, expected 400"
        )

    def test_create_missing_name_returns_400(self, user1_client: APIClient):
        resp = user1_client.raw_request(
            "POST", "/integrations", json={"type": "AWS"},
        )
        assert resp.status_code == 400, (
            f"BUG: Missing 'name' returns {resp.status_code}, expected 400"
        )

    def test_create_missing_type_returns_400(self, user1_client: APIClient):
        resp = user1_client.raw_request(
            "POST", "/integrations", json={"name": "test"},
        )
        assert resp.status_code == 400, (
            f"BUG: Missing 'type' returns {resp.status_code}, expected 400"
        )

    def test_create_no_body_returns_400(self, user1_client: APIClient):
        resp = user1_client.raw_request("POST", "/integrations")
        assert resp.status_code == 400


@pytest.mark.validation
class TestAssetValidation:

    def test_create_empty_body_returns_400(self, user1_client: APIClient):
        resp = user1_client.raw_request("POST", "/assets", json={})
        assert resp.status_code == 400, (
            f"BUG: Empty asset body returns {resp.status_code}, expected 400"
        )

    def test_create_missing_integration_id_returns_400(self, user1_client: APIClient):
        resp = user1_client.raw_request(
            "POST", "/assets", json={"name": "test", "description": "desc"},
        )
        assert resp.status_code == 400, (
            f"BUG: Missing integration_id returns {resp.status_code}, expected 400"
        )

    def test_list_without_integration_id_returns_400(self, user1_client: APIClient):
        resp = user1_client.raw_request("GET", "/assets")
        assert resp.status_code == 400

    def test_create_asset_nonexistent_integration_rejected(
        self,
        user1_client: APIClient,
    ):
        resp = user1_client.create_asset("orphan", "desc", "no-such-integration")
        assert resp.status_code in (400, 404), (
            f"BUG: Asset created with nonexistent integration_id "
            f"(status {resp.status_code})"
        )

    def test_update_asset_empty_id_returns_400(self, user1_client: APIClient):
        resp = user1_client.update_asset("", "name", "desc")
        assert resp.status_code in (400, 404)

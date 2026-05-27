"""CRUD tests for the /integrations endpoints."""

import pytest

from src.client import APIClient
from src.models import EXPECTED_STATUS, IntegrationType
from src.models import Integration
from tests.helpers import unique_name


@pytest.mark.crud
class TestCreateIntegration:

    @pytest.mark.smoke
    def test_create_returns_expected_status(self, user1_client: APIClient):
        resp = user1_client.create_integration(unique_name(), IntegrationType.GCP)
        assert resp.status_code == EXPECTED_STATUS["create_integration"], (
            f"BUG: Create integration returns {resp.status_code}, "
            f"spec says {EXPECTED_STATUS['create_integration']}"
        )

    @pytest.mark.smoke
    def test_create_integration_success(self, user1_client: APIClient, integration_factory):
        name = unique_name("my-int")
        data = integration_factory(user1_client, name, IntegrationType.AWS)
        assert "id" in data
        assert data["name"] == name
        assert data["type"] == IntegrationType.AWS
        assert data["tenant_id"] == user1_client.auth[0]

    def test_create_sets_tenant_to_authenticated_user(
        self,
        user2_client: APIClient,
        integration_factory,
    ):
        data = integration_factory(user2_client, unique_name(), IntegrationType.GCP)
        assert data["tenant_id"] == user2_client.auth[0]

    def test_create_duplicate_name_returns_conflict(
        self,
        user1_client: APIClient,
        integration_factory,
    ):
        name = unique_name("dup")
        integration_factory(user1_client, name, IntegrationType.AWS)
        resp = user1_client.create_integration(name, IntegrationType.AWS)
        assert resp.status_code == 409

    def test_create_same_name_different_tenants_allowed(
        self,
        user1_client: APIClient,
        user2_client: APIClient,
        integration_factory,
    ):
        name = unique_name("shared")
        integration_factory(user1_client, name, IntegrationType.AWS)
        resp = user2_client.create_integration(name, IntegrationType.GCP)
        assert resp.status_code in (200, 201), (
            f"BUG: Different tenants cannot use the same integration name "
            f"(status {resp.status_code}): {resp.text}"
        )


@pytest.mark.crud
class TestGetIntegration:

    @pytest.mark.smoke
    def test_get_own_integration(self, user1_client: APIClient, user1_base_integration: dict):
        resp = user1_client.get_integration(user1_base_integration["id"])
        assert resp.status_code == 200
        Integration.model_validate(resp.json())
        assert resp.json()["id"] == user1_base_integration["id"]

    def test_get_nonexistent_returns_404(self, user1_client: APIClient):
        resp = user1_client.get_integration("nonexistent-id")
        assert resp.status_code == 404


@pytest.mark.crud
class TestListIntegrations:

    @pytest.mark.smoke
    def test_list_returns_array(self, user1_client: APIClient, user1_base_integration: dict):
        resp = user1_client.list_integrations()
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_returns_only_own_tenant_integrations(
        self,
        user1_client: APIClient,
        user2_client: APIClient,
        user1_base_integration: dict,
        user2_base_integration: dict,
    ):
        resp = user1_client.list_integrations()
        data = resp.json()
        tenant_ids = {item["tenant_id"] for item in data}
        assert tenant_ids == {user1_client.auth[0]}, (
            f"BUG: Tenant isolation violated — user1 sees tenant_ids: {tenant_ids}"
        )


@pytest.mark.crud
class TestUpdateIntegration:

    def test_update_own_integration(
        self, user1_client: APIClient, integration_factory,
    ):
        target = integration_factory(user1_client, unique_name("upd"))
        resp = user1_client.update_integration(target["id"], unique_name("updated"))
        assert resp.status_code == 200, (
            f"BUG: Update integration returns {resp.status_code} — "
            f"PUT /integrations endpoint appears broken"
        )

    def test_update_nonexistent_returns_404(self, user1_client: APIClient):
        resp = user1_client.update_integration("nonexistent", "name")
        assert resp.status_code == 404


@pytest.mark.crud
class TestDeleteIntegration:

    @pytest.mark.smoke
    def test_delete_own_integration(self, user1_client: APIClient):
        resp = user1_client.create_integration(unique_name("del"), IntegrationType.AWS)
        integration_id = resp.json()["id"]
        del_resp = user1_client.delete_integration(integration_id)
        assert del_resp.status_code == 200

        get_resp = user1_client.get_integration(integration_id)
        assert get_resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, user1_client: APIClient):
        resp = user1_client.delete_integration("nonexistent-id")
        assert resp.status_code == 404, (
            f"BUG: Deleting nonexistent integration returns {resp.status_code}, expected 404"
        )

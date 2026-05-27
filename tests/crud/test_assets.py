"""CRUD tests for the /assets endpoints."""

import pytest

from src.client import APIClient
from src.models import EXPECTED_STATUS
from src.models import Asset
from tests.helpers import unique_name


@pytest.mark.crud
class TestCreateAsset:

    @pytest.mark.smoke
    def test_create_returns_expected_status(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        resp = user1_client.create_asset(unique_name(), "desc", user1_base_integration["id"])
        assert resp.status_code == EXPECTED_STATUS["create_asset"], (
            f"BUG: Create asset returns {resp.status_code}, "
            f"spec says {EXPECTED_STATUS['create_asset']}"
        )

    @pytest.mark.smoke
    def test_create_asset_success(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
        asset_factory,
    ):
        name = unique_name("new")
        data = asset_factory(user1_client, user1_base_integration["id"], name, "a description")
        assert "id" in data
        assert data["name"] == name
        assert data["description"] == "a description"
        assert data["integration_id"] == user1_base_integration["id"]
        assert data["tenant_id"] == user1_client.auth[0]

    def test_create_sets_tenant_from_auth(
        self,
        user2_client: APIClient,
        user2_base_integration: dict,
        asset_factory,
    ):
        data = asset_factory(user2_client, user2_base_integration["id"], unique_name("t2"), "desc")
        assert data["tenant_id"] == user2_client.auth[0]

    def test_create_asset_with_nonexistent_integration(
        self,
        user1_client: APIClient,
    ):
        resp = user1_client.create_asset(unique_name(), "desc", "nonexistent-integration-id")
        assert resp.status_code in (400, 404), (
            f"BUG: Creating asset with nonexistent integration_id returns "
            f"{resp.status_code} — should validate foreign key"
        )


@pytest.mark.crud
class TestGetAsset:

    @pytest.mark.smoke
    def test_get_own_asset(self, user1_client: APIClient, user1_base_asset: dict):
        resp = user1_client.get_asset(user1_base_asset["id"])
        assert resp.status_code == 200
        Asset.model_validate(resp.json())
        assert resp.json()["id"] == user1_base_asset["id"]

    def test_get_nonexistent_returns_404(self, user1_client: APIClient):
        resp = user1_client.get_asset("nonexistent")
        assert resp.status_code == 404


@pytest.mark.crud
class TestListAssets:

    @pytest.mark.smoke
    def test_list_returns_array(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
        user1_base_asset: dict,
    ):
        resp = user1_client.list_assets(user1_base_integration["id"])
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_requires_integration_id(self, user1_client: APIClient):
        resp = user1_client.raw_request("GET", "/assets")
        assert resp.status_code == 400

    def test_list_empty_integration_returns_empty_array(self, user1_client: APIClient):
        resp = user1_client.list_assets("nonexistent-integration")
        data = resp.json()
        assert isinstance(data, list), (
            f"BUG: Empty asset list returns {type(data).__name__}, expected list"
        )
        assert data == []


@pytest.mark.crud
class TestUpdateAsset:

    def test_update_own_asset(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
        asset_factory,
    ):
        target = asset_factory(user1_client, user1_base_integration["id"], unique_name("upd"))
        resp = user1_client.update_asset(target["id"], unique_name("updated"), "updated-desc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "updated-desc"

    def test_update_nonexistent_returns_404(self, user1_client: APIClient):
        resp = user1_client.update_asset("nonexistent", "name", "desc")
        assert resp.status_code == 404, (
            f"BUG: Updating nonexistent asset returns {resp.status_code}, expected 404"
        )


@pytest.mark.crud
class TestDeleteAsset:

    @pytest.mark.smoke
    def test_delete_own_asset(
        self,
        user1_client: APIClient,
        user1_base_integration: dict,
    ):
        create_resp = user1_client.create_asset(unique_name("del"), "desc", user1_base_integration["id"])
        data = create_resp.json()
        assert data and "id" in data, f"Create failed: status {create_resp.status_code}"
        asset_id = data["id"]

        del_resp = user1_client.delete_asset(asset_id)
        assert del_resp.status_code == EXPECTED_STATUS["delete_asset"]

        get_resp = user1_client.get_asset(asset_id)
        assert get_resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, user1_client: APIClient):
        resp = user1_client.delete_asset("nonexistent")
        assert resp.status_code == 404, (
            f"BUG: Deleting nonexistent asset returns {resp.status_code}, expected 404"
        )

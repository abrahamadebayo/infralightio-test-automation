"""Tenant isolation / segregation tests.

These tests verify that a multi-tenant API properly isolates data between
tenants.  Each test uses session-scoped base resources and then attempts
cross-tenant access.
"""

import pytest

from src.client import APIClient
from tests.helpers import unique_name


@pytest.mark.tenant
class TestIntegrationTenantIsolation:

    def test_list_integrations_only_shows_own_tenant(
        self,
        user1_client: APIClient,
        user2_client: APIClient,
        user1_base_integration: dict,
        user2_base_integration: dict,
    ):
        for client in (user1_client, user2_client):
            tenant = client.auth[0]
            data = client.list_integrations().json()
            foreign = [i for i in data if i["tenant_id"] != tenant]
            assert foreign == [], (
                f"BUG: {tenant} can see integrations from other tenants: "
                f"{[i['tenant_id'] for i in foreign]}"
            )

    def test_get_integration_cross_tenant_blocked(
        self,
        user2_client: APIClient,
        user1_base_integration: dict,
    ):
        resp = user2_client.get_integration(user1_base_integration["id"])
        assert resp.status_code in (403, 404), (
            f"BUG: user2 can read user1's integration (status {resp.status_code})"
        )

    def test_delete_integration_cross_tenant_blocked(
        self,
        user1_client: APIClient,
        user2_client: APIClient,
        integration_factory,
    ):
        target = integration_factory(user1_client, unique_name("del-target"))
        resp = user2_client.delete_integration(target["id"])
        assert resp.status_code in (403, 404), (
            f"BUG: user2 can delete user1's integration (status {resp.status_code})"
        )
        verify = user1_client.get_integration(target["id"])
        assert verify.status_code == 200, (
            "BUG: Integration was actually deleted by another tenant"
        )

    def test_update_integration_cross_tenant_blocked(
        self,
        user2_client: APIClient,
        user1_base_integration: dict,
    ):
        resp = user2_client.update_integration(user1_base_integration["id"], "hacked")
        assert resp.status_code in (403, 404), (
            f"BUG: user2 can update user1's integration (status {resp.status_code})"
        )


@pytest.mark.tenant
class TestAssetTenantIsolation:

    def test_get_asset_cross_tenant_blocked(
        self,
        user2_client: APIClient,
        user1_base_asset: dict,
    ):
        resp = user2_client.get_asset(user1_base_asset["id"])
        assert resp.status_code in (403, 404), (
            f"BUG: user2 can read user1's asset (status {resp.status_code})"
        )

    def test_list_assets_cross_tenant_returns_empty(
        self,
        user2_client: APIClient,
        user1_base_integration: dict,
        user1_base_asset: dict,
    ):
        resp = user2_client.list_assets(user1_base_integration["id"])
        data = resp.json()
        if isinstance(data, list):
            tenant = user2_client.auth[0]
            foreign = [a for a in data if a["tenant_id"] != tenant]
            assert foreign == [], (
                f"BUG: user2 can see user1's assets via list"
            )

    def test_delete_asset_cross_tenant_blocked(
        self,
        user1_client: APIClient,
        user2_client: APIClient,
        user1_base_integration: dict,
        asset_factory,
    ):
        target = asset_factory(user1_client, user1_base_integration["id"], unique_name("xdel"))
        resp = user2_client.delete_asset(target["id"])
        assert resp.status_code in (403, 404), (
            f"BUG: user2 can delete user1's asset (status {resp.status_code})"
        )
        verify = user1_client.get_asset(target["id"])
        assert verify.status_code == 200, (
            "BUG: Asset was actually deleted by another tenant"
        )

    def test_update_asset_cross_tenant_blocked(
        self,
        user2_client: APIClient,
        user1_base_asset: dict,
    ):
        resp = user2_client.update_asset(user1_base_asset["id"], "hacked", "by user2")
        assert resp.status_code in (403, 404), (
            f"BUG: user2 can update user1's asset (status {resp.status_code})"
        )

    def test_create_asset_on_other_tenants_integration_blocked(
        self,
        user1_client: APIClient,
        user2_base_integration: dict,
    ):
        resp = user1_client.create_asset("injected", "desc", user2_base_integration["id"])
        assert resp.status_code in (400, 403, 404), (
            f"BUG: user1 can create assets on user2's integration "
            f"(status {resp.status_code})"
        )

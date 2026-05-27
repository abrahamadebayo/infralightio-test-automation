"""Pagination tests for list endpoints."""

import pytest

from src.client import APIClient
from src.models import IntegrationType
from tests.helpers import unique_name


@pytest.mark.pagination
class TestIntegrationPagination:

    @pytest.fixture()
    def pagination_integrations(self, user1_client: APIClient):
        items = []
        for i in range(3):
            resp = user1_client.create_integration(unique_name(f"pgint{i}"), IntegrationType.AWS)
            items.append(resp.json())
        return items

    def test_limit_restricts_result_count(
        self,
        user1_client: APIClient,
        pagination_integrations: list,
    ):
        resp = user1_client.list_integrations(page=1, limit=2)
        data = resp.json()
        assert len(data) <= 2, (
            f"BUG: Requested limit=2 but got {len(data)} results"
        )

    def test_pages_return_different_results(
        self,
        user1_client: APIClient,
        pagination_integrations: list,
    ):
        page1 = user1_client.list_integrations(page=1, limit=2).json() or []
        page2 = user1_client.list_integrations(page=2, limit=2).json() or []
        assert page2, "BUG: Page 2 returns null/empty — pagination not working"
        page1_ids = {item["id"] for item in page1}
        page2_ids = {item["id"] for item in page2}
        assert page1_ids.isdisjoint(page2_ids), (
            f"BUG: Page 1 and page 2 overlap — IDs in common: {page1_ids & page2_ids}"
        )

    def test_all_items_reachable_through_pagination(
        self,
        user1_client: APIClient,
        pagination_integrations: list,
    ):
        all_ids = set()
        for page in range(1, 20):
            data = user1_client.list_integrations(page=page, limit=2).json() or []
            if not data:
                break
            all_ids.update(item["id"] for item in data)
        created_ids = {item["id"] for item in pagination_integrations}
        missing = created_ids - all_ids
        assert not missing, (
            f"BUG: {len(missing)} integrations not reachable through pagination"
        )


@pytest.mark.pagination
class TestAssetPagination:

    @pytest.fixture()
    def pagination_assets(self, user1_client: APIClient):
        int_resp = user1_client.create_integration(unique_name("pgassetint"), IntegrationType.AWS)
        integration_id = int_resp.json()["id"]
        items = []
        for i in range(3):
            resp = user1_client.create_asset(unique_name(f"pgasset{i}"), f"desc-{i}", integration_id)
            items.append(resp.json())
        return {"integration_id": integration_id, "items": items}

    def test_limit_restricts_result_count(
        self,
        user1_client: APIClient,
        pagination_assets: dict,
    ):
        resp = user1_client.list_assets(pagination_assets["integration_id"], page=1, limit=2)
        data = resp.json()
        assert len(data) <= 2

    def test_pages_return_different_results(
        self,
        user1_client: APIClient,
        pagination_assets: dict,
    ):
        iid = pagination_assets["integration_id"]
        page1 = user1_client.list_assets(iid, page=1, limit=2).json()
        page2 = user1_client.list_assets(iid, page=2, limit=2).json()
        page1_ids = {item["id"] for item in page1}
        page2_ids = {item["id"] for item in page2}
        assert page1_ids.isdisjoint(page2_ids), (
            f"BUG: Asset pages overlap — IDs in common: {page1_ids & page2_ids}"
        )

    def test_all_items_reachable_through_pagination(
        self,
        user1_client: APIClient,
        pagination_assets: dict,
    ):
        iid = pagination_assets["integration_id"]
        all_ids = set()
        for page in range(1, 20):
            data = user1_client.list_assets(iid, page=page, limit=2).json() or []
            if not data:
                break
            all_ids.update(item["id"] for item in data)
        created_ids = {item["id"] for item in pagination_assets["items"]}
        missing = created_ids - all_ids
        assert not missing, (
            f"BUG: {len(missing)} assets not reachable through pagination"
        )

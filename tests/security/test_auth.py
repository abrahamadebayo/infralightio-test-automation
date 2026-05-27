"""Authentication and authorization tests."""

import pytest

from src.client import APIClient, UnauthenticatedClient, _curl


@pytest.mark.auth
class TestAuthentication:
    """Verify that Basic Auth is enforced on all endpoints."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/integrations"),
        ("POST", "/integrations"),
        ("PUT", "/integrations"),
        ("GET", "/integrations/fake-id"),
        ("DELETE", "/integrations/fake-id"),
        ("GET", "/assets?integrationId=fake"),
        ("POST", "/assets"),
        ("PATCH", "/assets"),
        ("GET", "/assets/fake-id"),
        ("DELETE", "/assets/fake-id"),
    ]

    @pytest.mark.smoke
    def test_valid_credentials_accepted(self, user1_client: APIClient):
        resp = user1_client.list_integrations()
        assert resp.status_code != 401

    @pytest.mark.smoke
    def test_no_credentials_rejected(self, unauth_client: UnauthenticatedClient):
        resp = unauth_client.get("/integrations")
        assert resp.status_code == 401

    def test_invalid_credentials_rejected(self, bad_creds_client: APIClient):
        resp = bad_creds_client.list_integrations()
        assert resp.status_code == 401

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS, ids=[
        f"{m} {p}" for m, p in PROTECTED_ENDPOINTS
    ])
    def test_unauthenticated_access_blocked(
        self,
        unauth_client: UnauthenticatedClient,
        method: str,
        path: str,
    ):
        resp = _curl(method, f"{unauth_client.base_url}{path}")
        assert resp.status_code == 401, (
            f"{method} {path} should require auth, got {resp.status_code}"
        )

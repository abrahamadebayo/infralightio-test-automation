from __future__ import annotations

import subprocess
import time

import pytest

from src.client import APIClient, UnauthenticatedClient, _curl, _reset_call_count
from src.config import UserCredentials, settings
from src.models import IntegrationType
from tests.helpers import unique_name


class LiveResource(dict):
    """Mutable dict wrapper so session fixtures survive API restarts."""

    def refresh(self, new_data: dict) -> None:
        self.clear()
        self.update(new_data)


_u1_int = LiveResource()
_u2_int = LiveResource()
_u1_asset = LiveResource()
_u2_asset = LiveResource()


def _create_base_resources() -> None:
    u1 = APIClient(settings.user1)
    u2 = APIClient(settings.user2)
    _u1_int.refresh(u1.create_integration(unique_name("u1-base"), IntegrationType.AWS).json())
    _u2_int.refresh(u2.create_integration(unique_name("u2-base"), IntegrationType.GCP).json())
    _u1_asset.refresh(
        u1.create_asset(unique_name("u1-base-asset"), "base asset user1", _u1_int["id"]).json()
    )
    _u2_asset.refresh(
        u2.create_asset(unique_name("u2-base-asset"), "base asset user2", _u2_int["id"]).json()
    )


# ── Clients ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def user1_client() -> APIClient:
    return APIClient(settings.user1)


@pytest.fixture(scope="session")
def user2_client() -> APIClient:
    return APIClient(settings.user2)


@pytest.fixture(scope="session")
def unauth_client() -> UnauthenticatedClient:
    return UnauthenticatedClient()


@pytest.fixture(scope="session")
def bad_creds_client() -> APIClient:
    return APIClient(UserCredentials(username="invalid", password="wrong"))


# ── Factories ────────────────────────────────────────────────────────

@pytest.fixture()
def integration_factory():
    def _create(
        client: APIClient,
        name: str | None = None,
        type_: str = IntegrationType.AWS,
    ) -> dict:
        name = name or unique_name("integration")
        resp = client.create_integration(name, type_)
        return resp.json()

    return _create


@pytest.fixture()
def asset_factory():
    def _create(
        client: APIClient,
        integration_id: str,
        name: str | None = None,
        description: str = "test description",
    ) -> dict:
        name = name or unique_name("asset")
        resp = client.create_asset(name, description, integration_id)
        return resp.json()

    return _create


# ── Session-scoped base resources (mutable, survive restarts) ────────

@pytest.fixture(scope="session")
def user1_base_integration() -> LiveResource:
    return _u1_int


@pytest.fixture(scope="session")
def user2_base_integration() -> LiveResource:
    return _u2_int


@pytest.fixture(scope="session")
def user1_base_asset() -> LiveResource:
    return _u1_asset


@pytest.fixture(scope="session")
def user2_base_asset() -> LiveResource:
    return _u2_asset


# ── API health and auto-restart ──────────────────────────────────────

def _wait_for_api() -> None:
    """Poll swagger endpoint without incrementing the call counter."""
    for _ in range(30):
        time.sleep(1)
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "--max-time", "2", f"{settings.base_url}/swagger/doc.json"],
                capture_output=True, text=True, timeout=5,
            )
            if result.stdout.strip() == "200":
                return
        except subprocess.TimeoutExpired:
            pass


def _restart_api() -> None:
    subprocess.run(
        ["docker", "compose", "up", "-d", "--force-recreate", "api"],
        capture_output=True, timeout=60,
    )
    _reset_call_count()
    _wait_for_api()
    time.sleep(1)
    _create_base_resources()


_CALL_LIMIT = 15


@pytest.fixture(scope="session", autouse=True)
def _bootstrap():
    """Verify API is reachable and create initial base resources."""
    resp = _curl("GET", f"{settings.base_url}/swagger/doc.json", timeout=5)
    if resp.status_code == 0:
        pytest.exit("API is not reachable. Start it with: docker compose up -d")
    _create_base_resources()


def _api_is_alive() -> bool:
    """Write-path liveness probe — detects the partial crash where GETs work but writes hang."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "3",
             "-u", f"{settings.user1.username}:{settings.user1.password}",
             "-X", "DELETE",
             f"{settings.api_url}/integrations/_probe"],
            capture_output=True, text=True, timeout=6,
        )
        return result.stdout.strip() != "000"
    except subprocess.TimeoutExpired:
        return False


@pytest.fixture(autouse=True)
def _ensure_api_healthy():
    """Restart the API if it's unresponsive or approaching the resource-leak limit."""
    import src.client.http as _mod
    if _mod._call_count >= _CALL_LIMIT or not _api_is_alive():
        _restart_api()


@pytest.fixture(scope="session")
def swagger_spec() -> dict:
    resp = _curl("GET", f"{settings.base_url}/swagger/doc.json", timeout=5)
    return resp.json()

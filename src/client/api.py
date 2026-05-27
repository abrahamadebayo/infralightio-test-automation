from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from src.client.http import REQUEST_TIMEOUT, CurlResponse, _curl
from src.config import Settings, UserCredentials, settings


class APIClient:
    def __init__(
        self,
        credentials: UserCredentials,
        cfg: Settings = settings,
    ) -> None:
        self.base_url = cfg.api_url
        self.auth = credentials.auth_tuple

    def _request(self, method: str, url: str, **kwargs: Any) -> CurlResponse:
        auth = kwargs.pop("auth", self.auth)
        headers = kwargs.pop("headers", {})
        json_payload = kwargs.pop("json", None)
        data = kwargs.pop("data", None)
        params = kwargs.pop("params", None)
        timeout = kwargs.pop("timeout", REQUEST_TIMEOUT)

        if params:
            url = f"{url}?{urlencode(params)}"

        return _curl(
            method,
            url,
            headers=headers,
            auth=auth,
            json_payload=json_payload,
            data=data,
            timeout=timeout,
        )

    # -- Integrations --

    def create_integration(
        self,
        name: str,
        type_: str,
        **kwargs: Any,
    ) -> CurlResponse:
        payload = {"name": name, "type": type_}
        payload.update(kwargs)
        return self._request("POST", f"{self.base_url}/integrations", json=payload)

    def list_integrations(
        self,
        page: int | None = None,
        limit: int | None = None,
    ) -> CurlResponse:
        params: dict[str, int] = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        return self._request("GET", f"{self.base_url}/integrations", params=params)

    def get_integration(self, integration_id: str) -> CurlResponse:
        return self._request("GET", f"{self.base_url}/integrations/{integration_id}")

    def update_integration(
        self,
        integration_id: str,
        name: str,
    ) -> CurlResponse:
        payload = {"id": integration_id, "name": name}
        return self._request("PUT", f"{self.base_url}/integrations", json=payload)

    def delete_integration(self, integration_id: str) -> CurlResponse:
        return self._request("DELETE", f"{self.base_url}/integrations/{integration_id}")

    # -- Assets --

    def create_asset(
        self,
        name: str,
        description: str,
        integration_id: str,
        **kwargs: Any,
    ) -> CurlResponse:
        payload = {
            "name": name,
            "description": description,
            "integration_id": integration_id,
        }
        payload.update(kwargs)
        return self._request("POST", f"{self.base_url}/assets", json=payload)

    def list_assets(
        self,
        integration_id: str,
        page: int | None = None,
        limit: int | None = None,
    ) -> CurlResponse:
        params: dict[str, Any] = {"integrationId": integration_id}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        return self._request("GET", f"{self.base_url}/assets", params=params)

    def get_asset(self, asset_id: str) -> CurlResponse:
        return self._request("GET", f"{self.base_url}/assets/{asset_id}")

    def update_asset(
        self,
        asset_id: str,
        name: str,
        description: str,
    ) -> CurlResponse:
        payload = {"id": asset_id, "name": name, "description": description}
        return self._request("PATCH", f"{self.base_url}/assets", json=payload)

    def delete_asset(self, asset_id: str) -> CurlResponse:
        return self._request("DELETE", f"{self.base_url}/assets/{asset_id}")

    # -- Raw request for contract / edge-case tests --

    def raw_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> CurlResponse:
        return self._request(method, f"{self.base_url}{path}", **kwargs)


class UnauthenticatedClient:
    def __init__(self, cfg: Settings = settings) -> None:
        self.base_url = cfg.api_url

    def get(self, path: str) -> CurlResponse:
        return _curl("GET", f"{self.base_url}{path}")

    def post(self, path: str, **kwargs: Any) -> CurlResponse:
        return _curl("POST", f"{self.base_url}{path}", **kwargs)

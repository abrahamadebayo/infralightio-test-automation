from __future__ import annotations

from pydantic import BaseModel


class Integration(BaseModel):
    id: str
    name: str
    type: str
    tenant_id: str


class CreateIntegrationRequest(BaseModel):
    name: str
    type: str


class UpdateIntegrationRequest(BaseModel):
    id: str
    name: str


class Asset(BaseModel):
    id: str
    name: str
    description: str
    tenant_id: str
    integration_id: str


class CreateAssetRequest(BaseModel):
    name: str
    description: str
    integration_id: str


class UpdateAssetRequest(BaseModel):
    id: str
    name: str
    description: str


class APIError(BaseModel):
    code: int
    message: str

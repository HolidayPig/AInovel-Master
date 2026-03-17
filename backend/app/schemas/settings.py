from datetime import datetime
from pydantic import BaseModel


class SettingsCreate(BaseModel):
    provider: str
    api_key_encrypted: str = ""
    model_name: str = ""
    proxy_url: str | None = None
    web_search_enabled: bool = False
    extra_config_json: str = "{}"


class SettingsUpdate(BaseModel):
    provider: str | None = None
    api_key_encrypted: str | None = None
    model_name: str | None = None
    proxy_url: str | None = None
    web_search_enabled: bool | None = None
    extra_config_json: str | None = None


class SettingsResponse(BaseModel):
    id: int
    provider: str
    model_name: str
    proxy_url: str | None
    web_search_enabled: bool
    extra_config_json: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Settings
from ..schemas import SettingsCreate, SettingsUpdate, SettingsResponse

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingsResponse])
async def list_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings))
    items = result.scalars().all()
    return [SettingsResponse(
        id=s.id,
        provider=s.provider,
        model_name=s.model_name,
        proxy_url=s.proxy_url,
        web_search_enabled=s.web_search_enabled,
        extra_config_json=s.extra_config_json,
        created_at=s.created_at,
        updated_at=s.updated_at,
    ) for s in items]


@router.post("", response_model=SettingsResponse)
async def create_settings(data: SettingsCreate, db: AsyncSession = Depends(get_db)):
    settings = Settings(
        provider=data.provider,
        api_key_encrypted=data.api_key_encrypted,
        model_name=data.model_name,
        proxy_url=data.proxy_url,
        web_search_enabled=data.web_search_enabled,
        extra_config_json=data.extra_config_json,
    )
    db.add(settings)
    await db.flush()
    await db.refresh(settings)
    return SettingsResponse(
        id=settings.id,
        provider=settings.provider,
        model_name=settings.model_name,
        proxy_url=settings.proxy_url,
        web_search_enabled=settings.web_search_enabled,
        extra_config_json=settings.extra_config_json,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.get("/{settings_id}", response_model=SettingsResponse)
async def get_settings(settings_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.id == settings_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Settings not found")
    return SettingsResponse(
        id=s.id,
        provider=s.provider,
        model_name=s.model_name,
        proxy_url=s.proxy_url,
        web_search_enabled=s.web_search_enabled,
        extra_config_json=s.extra_config_json,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.patch("/{settings_id}", response_model=SettingsResponse)
async def update_settings(settings_id: int, data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.id == settings_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Settings not found")
    if data.provider is not None:
        s.provider = data.provider
    if data.api_key_encrypted is not None:
        s.api_key_encrypted = data.api_key_encrypted
    if data.model_name is not None:
        s.model_name = data.model_name
    if data.proxy_url is not None:
        s.proxy_url = data.proxy_url
    if data.web_search_enabled is not None:
        s.web_search_enabled = data.web_search_enabled
    if data.extra_config_json is not None:
        s.extra_config_json = data.extra_config_json
    await db.flush()
    await db.refresh(s)
    return SettingsResponse(
        id=s.id,
        provider=s.provider,
        model_name=s.model_name,
        proxy_url=s.proxy_url,
        web_search_enabled=s.web_search_enabled,
        extra_config_json=s.extra_config_json,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.delete("/{settings_id}", status_code=204)
async def delete_settings(settings_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.id == settings_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Settings not found")
    await db.delete(s)
    return None

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from pydantic import BaseModel

from ..database import get_db
from ..models import Card
from ..schemas import CardCreate, CardUpdate, CardResponse
from ..services import card_engine

router = APIRouter(prefix="/cards", tags=["cards"])


class RefreshAllBody(BaseModel):
    novel_id: int
    settings_id: int


class RefreshOneBody(BaseModel):
    card_id: int
    novel_id: int
    settings_id: int


class SearchOnlineBody(BaseModel):
    card_id: int
    settings_id: int


@router.get("", response_model=list[CardResponse])
async def list_cards(novel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Card).where(Card.novel_id == novel_id))
    return list(result.scalars().all())


@router.post("", response_model=CardResponse)
async def create_card(data: CardCreate, db: AsyncSession = Depends(get_db)):
    card = Card(
        novel_id=data.novel_id,
        card_type=data.card_type,
        name=data.name,
        content_json=data.content_json,
        auto_update=data.auto_update,
    )
    db.add(card)
    await db.flush()
    await db.refresh(card)
    return card


@router.post("/refresh-all")
async def refresh_all_cards(body: RefreshAllBody, db: AsyncSession = Depends(get_db)):
    """One-click refresh: re-extract all cards from latest novel content and apply directly."""
    updated = await card_engine.refresh_all_cards(body.novel_id, body.settings_id, db)
    return {"updated": updated}


@router.post("/refresh-one-suggestion")
async def refresh_one_suggestion(body: RefreshOneBody, db: AsyncSession = Depends(get_db)):
    """Get suggested new text for one card (before/after for user confirm)."""
    out = await card_engine.refresh_one_card_suggestion(
        body.card_id, body.novel_id, body.settings_id, db
    )
    if not out:
        raise HTTPException(status_code=400, detail="Failed to get suggestion or card not found")
    return out


@router.post("/search-online")
async def search_online(body: SearchOnlineBody, db: AsyncSession = Depends(get_db)):
    """Search online by card name/description and return refined card content."""
    try:
        new_text = await card_engine.search_online_and_refine_card(body.card_id, body.settings_id, db)
        if not new_text:
            raise HTTPException(status_code=400, detail="Failed to search (empty result) or missing API Key")
        return {"new_text": new_text}
    except HTTPException:
        raise
    except Exception as e:
        # Surface upstream tool/schema errors (e.g. 422 tools schema) for debugging.
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{card_id}", response_model=CardResponse)
async def get_card(card_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Card).where(Card.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.patch("/{card_id}", response_model=CardResponse)
async def update_card(card_id: int, data: CardUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Card).where(Card.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if data.card_type is not None:
        card.card_type = data.card_type
    if data.name is not None:
        card.name = data.name
    if data.content_json is not None:
        card.content_json = data.content_json
    if data.auto_update is not None:
        card.auto_update = data.auto_update
    await db.flush()
    await db.refresh(card)
    return card


@router.delete("/{card_id}", status_code=204)
async def delete_card(card_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Card).where(Card.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    await db.delete(card)
    return None

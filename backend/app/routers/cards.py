from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Card
from ..schemas import CardCreate, CardUpdate, CardResponse

router = APIRouter(prefix="/cards", tags=["cards"])


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

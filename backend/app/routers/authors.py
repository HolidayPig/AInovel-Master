from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Author
from ..schemas.author import AuthorCreate, AuthorUpdate, AuthorResponse

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=list[AuthorResponse])
async def list_authors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Author).order_by(Author.updated_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=AuthorResponse)
async def create_author(data: AuthorCreate, db: AsyncSession = Depends(get_db)):
    author = Author(
        name=data.name,
        style=data.style,
        format_rules=data.format_rules,
        extra_json=data.extra_json,
    )
    db.add(author)
    await db.flush()
    await db.refresh(author)
    return author


@router.get("/{author_id}", response_model=AuthorResponse)
async def get_author(author_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Author).where(Author.id == author_id))
    author = result.scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author


@router.patch("/{author_id}", response_model=AuthorResponse)
async def update_author(author_id: int, data: AuthorUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Author).where(Author.id == author_id))
    author = result.scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    if data.name is not None:
        author.name = data.name
    if data.style is not None:
        author.style = data.style
    if data.format_rules is not None:
        author.format_rules = data.format_rules
    if data.extra_json is not None:
        author.extra_json = data.extra_json
    await db.flush()
    await db.refresh(author)
    return author


@router.delete("/{author_id}", status_code=204)
async def delete_author(author_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Author).where(Author.id == author_id))
    author = result.scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    await db.delete(author)
    return None

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Chapter
from ..schemas import ChapterCreate, ChapterUpdate, ChapterResponse

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.get("", response_model=list[ChapterResponse])
async def list_chapters(novel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.sort_order, Chapter.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=ChapterResponse)
async def create_chapter(data: ChapterCreate, db: AsyncSession = Depends(get_db)):
    chapter = Chapter(
        novel_id=data.novel_id,
        title=data.title,
        content=data.content,
        sort_order=data.sort_order,
    )
    db.add(chapter)
    await db.flush()
    await db.refresh(chapter)
    return chapter


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.patch("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(chapter_id: int, data: ChapterUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    if data.title is not None:
        chapter.title = data.title
    if data.content is not None:
        chapter.content = data.content
    if data.sort_order is not None:
        chapter.sort_order = data.sort_order
    await db.flush()
    await db.refresh(chapter)
    return chapter


@router.delete("/{chapter_id}", status_code=204)
async def delete_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    await db.delete(chapter)
    return None

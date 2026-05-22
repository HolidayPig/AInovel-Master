from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ConsistencyCheck
from ..schemas import ConsistencyCheckResponse, ConsistencyCheckUpdate

router = APIRouter(prefix="/consistency-checks", tags=["consistency-checks"])


@router.patch("/{check_id}", response_model=ConsistencyCheckResponse)
async def update_consistency_check(
    check_id: int,
    data: ConsistencyCheckUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ConsistencyCheck).where(ConsistencyCheck.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Consistency check not found")
    if data.resolved is not None:
        check.resolved = data.resolved
    await db.flush()
    await db.refresh(check)
    return check

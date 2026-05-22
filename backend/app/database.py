"""Database connection and session configuration."""
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DATA_DIR, 'ainovel.db')}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def _migrate_chapters_columns(conn):
    """Add newer chapter columns if missing."""
    result = await conn.execute(text("PRAGMA table_info(chapters)"))
    rows = result.fetchall()
    if not rows:
        return
    names = {row[1] for row in rows}
    if "summary" not in names:
        await conn.execute(text("ALTER TABLE chapters ADD COLUMN summary TEXT"))
    if "target_words" not in names:
        await conn.execute(text("ALTER TABLE chapters ADD COLUMN target_words INTEGER"))
    if "status" not in names:
        await conn.execute(text("ALTER TABLE chapters ADD COLUMN status VARCHAR(32) DEFAULT 'drafting'"))


async def _migrate_novels_columns(conn):
    """Add newer novel columns if missing."""
    result = await conn.execute(text("PRAGMA table_info(novels)"))
    rows = result.fetchall()
    if not rows:
        return
    names = {row[1] for row in rows}
    if "outline" not in names:
        await conn.execute(text("ALTER TABLE novels ADD COLUMN outline TEXT DEFAULT ''"))


async def _migrate_cards_columns(conn):
    """Add newer card metadata columns if missing."""
    result = await conn.execute(text("PRAGMA table_info(cards)"))
    rows = result.fetchall()
    if not rows:
        return
    names = {row[1] for row in rows}
    if "tags" not in names:
        await conn.execute(text("ALTER TABLE cards ADD COLUMN tags TEXT DEFAULT ''"))
    if "importance" not in names:
        await conn.execute(text("ALTER TABLE cards ADD COLUMN importance INTEGER DEFAULT 2"))
    if "last_referenced_chapter_id" not in names:
        await conn.execute(text("ALTER TABLE cards ADD COLUMN last_referenced_chapter_id INTEGER"))
    if "last_referenced_at" not in names:
        await conn.execute(text("ALTER TABLE cards ADD COLUMN last_referenced_at DATETIME"))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        await _migrate_novels_columns(conn)
        await _migrate_chapters_columns(conn)
        await _migrate_cards_columns(conn)

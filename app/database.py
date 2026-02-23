from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine_kwargs = {"echo": settings.DEBUG}
# SQLite doesn't support pool_size / pool_pre_ping the same way
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(pool_size=20, max_overflow=10, pool_pre_ping=True)

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


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


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in settings.DATABASE_URL:
            for col, typ in [
                ("password_reset_token", "VARCHAR(255)"),
                ("password_reset_expires", "DATETIME"),
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typ}"))
                except Exception:
                    pass

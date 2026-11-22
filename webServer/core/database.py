from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import Settings

settings = Settings()
engine = create_async_engine(settings.POSTGRES_URI, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def connect_db() -> None:
    from model.base import Base
    import model.meeting              # noqa: F401
    import model.prize                # noqa: F401
    import model.manager              # noqa: F401
    import model.employee             # noqa: F401
    import model.nominate             # noqa: F401
    import model.judge                # noqa: F401
    import model.vote                 # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def disconnect_db() -> None:
    await engine.dispose()


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
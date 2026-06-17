from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

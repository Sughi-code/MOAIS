from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Строка подключения
# заменитЬ user/password на акутальные данные
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/library_db"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# асинхронные сессии
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Зависимость для получения сессии БД
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
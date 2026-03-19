from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Book
from schemas import BookCreate, BookUpdate

async def get_book(db: AsyncSession, book_id: int):
    result = await db.get(Book, book_id)
    return result

async def get_books(db: AsyncSession, skip: int = 0, limit: int = 100):
    query = select(Book).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def create_book(db: AsyncSession, book: BookCreate):
    # Преобразуем схему Pydantic в словарь и создаем объект ORM
    db_book = Book(**book.model_dump())
    db.add(db_book)
    await db.commit()
    await db.refresh(db_book)
    return db_book

async def update_book(db: AsyncSession, book_id: int, book: BookUpdate):
    db_book = await get_book(db, book_id)
    if db_book:
        update_data = book.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_book, key, value)
        await db.commit()
        await db.refresh(db_book)
    return db_book

async def delete_book(db: AsyncSession, book_id: int):
    db_book = await get_book(db, book_id)
    if db_book:
        await db.delete(db_book)
        await db.commit()
    return db_book
from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

import models
import schemas
import crud
from database import engine, get_db

# Создаем таблицы в БД при запуске
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

app = FastAPI(title="Library CRUD API Async")

# Инициализация БД при старте приложения
@app.on_event("startup")
async def on_startup():
    await init_db()

# --- Эндпоинты ---

@app.post("/books/", response_model=schemas.BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book_endpoint(book: schemas.BookCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_book(db=db, book=book)

@app.get("/books/", response_model=List[schemas.BookResponse])
async def read_books_endpoint(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    books = await crud.get_books(db, skip=skip, limit=limit)
    return books

@app.get("/books/{book_id}", response_model=schemas.BookResponse)
async def read_book_endpoint(book_id: int, db: AsyncSession = Depends(get_db)):
    db_book = await crud.get_book(db, book_id=book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

@app.put("/books/{book_id}", response_model=schemas.BookResponse)
async def update_book_endpoint(book_id: int, book: schemas.BookUpdate, db: AsyncSession = Depends(get_db)):
    db_book = await crud.update_book(db, book_id=book_id, book=book)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book_endpoint(book_id: int, db: AsyncSession = Depends(get_db)):
    db_book = await crud.delete_book(db, book_id=book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return None
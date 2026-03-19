from pydantic import BaseModel, ConfigDict

# Базовый класс для общих атрибутов
class BookBase(BaseModel):
    title: str
    author: str
    year: int

# Схема для создания (данные от клиента)
class BookCreate(BookBase):
    pass

# Схема для обновления (можно менять частично)
class BookUpdate(BaseModel):
    title: str = None
    author: str = None
    year: int = None

# Схема для ответа (включаем ID)
class BookResponse(BookBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
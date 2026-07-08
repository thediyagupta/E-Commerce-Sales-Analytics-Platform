from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 50

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int
    data: list

from fastapi import Query
from sqlalchemy.orm import Query as SAQuery


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Página atual"),
        page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    ):
        self.page = page
        self.page_size = page_size


def paginate(query: SAQuery, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total

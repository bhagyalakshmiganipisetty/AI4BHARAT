from sqlalchemy import asc, desc
from sqlalchemy.orm import Query

SEARCH_PATTERN = r"^[A-Za-z0-9 _.,@-]*$"
SORT_PATTERN = r"^-?[a-z_]+$"


def apply_sort(query: Query, sort: str | None, allowed: dict[str, object]) -> Query:
    if not sort:
        return query
    direction = desc if sort.startswith("-") else asc
    field = sort.lstrip("-")
    column = allowed.get(field)
    if column is None:
        return query
    return query.order_by(direction(column))


def apply_pagination(query: Query, page: int, limit: int) -> Query:
    page = max(page, 1)
    limit = max(limit, 1)
    offset = (page - 1) * limit
    return query.offset(offset).limit(limit)

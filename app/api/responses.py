from app.schemas.common import ErrorResponse

UNAUTHORIZED = {401: {"model": ErrorResponse, "description": "Unauthorized"}}
FORBIDDEN = {403: {"model": ErrorResponse, "description": "Forbidden"}}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Not found"}}
RATE_LIMITED = {429: {"model": ErrorResponse, "description": "Too many requests"}}

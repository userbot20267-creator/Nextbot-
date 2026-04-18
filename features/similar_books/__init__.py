# features/similar_books/__init__.py
from .services import get_similar_books
from .handlers import register_handlers

__all__ = ["get_similar_books", "register_handlers"]

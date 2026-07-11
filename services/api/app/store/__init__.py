"""Persistence layer. M0 ships an in-memory store; SQLAlchemy/Postgres lands in M1."""

from .memory import InMemoryStore
from .protocol import NotFoundError, StoreProtocol

__all__ = ["InMemoryStore", "StoreProtocol", "NotFoundError"]

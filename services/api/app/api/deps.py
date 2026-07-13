"""FastAPI dependency accessors for app-scoped services."""

from fastapi import Request

from app.config import Settings
from app.store.protocol import StoreProtocol
from app.store.sql import SqlAlchemyStore
from app.workflow.pipeline import WorkflowPipeline


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_store(request: Request) -> StoreProtocol:
    store: StoreProtocol = request.app.state.store
    return store


def get_sql_store(request: Request) -> SqlAlchemyStore:
    store: SqlAlchemyStore = request.app.state.store
    return store


def get_pipeline(request: Request) -> WorkflowPipeline:
    pipeline: WorkflowPipeline = request.app.state.pipeline
    return pipeline

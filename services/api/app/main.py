"""Application factory.

``create_app`` wires settings, the store, providers, and the workflow
pipeline. Demo mode (default) binds simulated providers and needs no
credentials. Live providers are not implemented in M0; constructing the app
with ``demo_mode=False`` raises rather than silently pretending.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import approvals, health, incidents
from app.config import Settings
from app.demo.seed import seed_demo
from app.domain.enums import ProviderMode
from app.providers.simulated import (
    SimulatedCodeAgentGateway,
    SimulatedDeploymentHistoryProvider,
    SimulatedInvestigationProvider,
    SimulatedLocalRepositoryProvider,
    SimulatedRunbookProvider,
    SimulatedTelemetryProvider,
    SimulatedVerificationRunner,
)
from app.store.sql import SqlAlchemyStore
from app.workflow.pipeline import WorkflowPipeline


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    if settings.provider_mode is not ProviderMode.SIMULATED:
        raise NotImplementedError(
            "Live providers arrive in M4-M7; run with DEMO_MODE=true for M0"
        )

    store = SqlAlchemyStore(settings.database_url or "sqlite:///demo.db")
    pipeline = WorkflowPipeline(
        store=store,
        telemetry=SimulatedTelemetryProvider(),
        deployments=SimulatedDeploymentHistoryProvider(),
        repository=SimulatedLocalRepositoryProvider(),
        runbook=SimulatedRunbookProvider(),
        investigation=SimulatedInvestigationProvider(),
        code_agent=SimulatedCodeAgentGateway(),
        verifier=SimulatedVerificationRunner(),
        provider_mode=settings.provider_mode,
    )

    app = FastAPI(
        title="Incident Commander AI API",
        version="0.1.0",
        description="M0 foundation: typed contracts, deterministic demo workflow slice",
    )
    app.state.settings = settings
    app.state.store = store
    app.state.pipeline = pipeline

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Demo-Admin-Key"],
    )

    app.include_router(health.router)
    app.include_router(incidents.router)
    app.include_router(approvals.router)

    seed_demo(store)
    return app


app = create_app()

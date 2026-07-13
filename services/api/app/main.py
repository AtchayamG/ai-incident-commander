"""Application factory.

``create_app`` wires settings, the store, providers, and the workflow
pipeline. Demo mode (default) binds simulated providers and needs no
credentials. Live providers are not implemented in M0; constructing the app
with ``demo_mode=False`` raises rather than silently pretending.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import approvals, health, incidents
from app.config import Settings
from app.demo.seed import seed_demo
from app.domain.enums import ProviderMode
from app.providers.code_agent import build_code_agent_gateway
from app.providers.simulated import (
    SimulatedDeploymentHistoryProvider,
    SimulatedInvestigationProvider,
    SimulatedLocalRepositoryProvider,
    SimulatedRunbookProvider,
    SimulatedTelemetryProvider,
)
from app.providers.simulated_investigation import (
    FixtureChangeCorrelationSpecialist,
    FixtureCodeMappingSpecialist,
    FixtureInvestigationGateway,
    FixtureRunbookSpecialist,
    FixtureTelemetrySpecialist,
)
from app.providers.simulated_remediation import FixtureRemediationPlanner
from app.sandbox.executor import SandboxPatchExecutor
from app.sandbox.verifier import DeterministicVerifier
from app.store.sql import SqlAlchemyStore
from app.workflow.investigation_manager import InvestigationManager
from app.workflow.pipeline import WorkflowPipeline
from app.workflow.remediation_planner import RemediationPlanningManager


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    if settings.provider_mode is not ProviderMode.SIMULATED:
        raise NotImplementedError(
            "Live providers arrive in M4-M7; run with DEMO_MODE=true for M0"
        )

    store = SqlAlchemyStore(settings.database_url or "sqlite:///demo.db")
    # The investigation manager is the single explicit M3 stage. Specialists
    # and the gateway are the demo (fixture) bindings; the gateway's model ID
    # is environment-driven so a live structured-output model can replace it
    # without touching the manager or workflow.
    investigation_manager = InvestigationManager(
        specialists=(
            FixtureTelemetrySpecialist(),
            FixtureChangeCorrelationSpecialist(),
            FixtureCodeMappingSpecialist(),
            FixtureRunbookSpecialist(),
        ),
        gateway=FixtureInvestigationGateway(model_id=settings.investigation_model),
    )
    # The planning manager is the single explicit M4 stage: it grounds planner
    # drafts in the investigation's code mapping and applies the deterministic
    # remediation policy before any plan or approval exists.
    remediation_planner = RemediationPlanningManager(
        planner=FixtureRemediationPlanner(model_id=settings.investigation_model),
    )
    # M5: the sandbox executor owns the isolated-workspace patch lifecycle;
    # the gateway (fixture in demo mode, codex-cli when explicitly configured)
    # only produces the edits inside the workspace.
    patch_executor = SandboxPatchExecutor(
        store=store,
        gateway=build_code_agent_gateway(settings),
    )
    pipeline = WorkflowPipeline(
        store=store,
        telemetry=SimulatedTelemetryProvider(),
        deployments=SimulatedDeploymentHistoryProvider(),
        repository=SimulatedLocalRepositoryProvider(),
        runbook=SimulatedRunbookProvider(),
        investigation=SimulatedInvestigationProvider(),
        investigation_manager=investigation_manager,
        remediation_planner=remediation_planner,
        patch_executor=patch_executor,
        # M6: deterministic subprocess verification of the captured candidate
        # patch. The environment is copied once here so the runner's own
        # allowlist — not the parent process — decides what the check
        # subprocesses can see.
        verifier=DeterministicVerifier(store=store, environ=dict(os.environ)),
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
        allow_headers=["Content-Type", "X-Demo-Admin-Key", "X-Approver-Role"],
    )

    app.include_router(health.router)
    app.include_router(incidents.router)
    app.include_router(approvals.router)

    seed_demo(store)
    return app


app = create_app()

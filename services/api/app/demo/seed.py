"""Golden demo incident seed (blueprint section 17.1 example).

Seeding is idempotent per store reset and never touches external systems.
"""

from datetime import UTC, datetime

from app.domain.contracts import Incident
from app.domain.enums import Environment, ProviderMode, Severity, WorkflowState
from app.store.protocol import StoreProtocol

GOLDEN_INCIDENT_ID = "inc-demo-0001"


def seed_demo(store: StoreProtocol) -> list[str]:
    """Create the golden incident in RECEIVED state. Returns seeded IDs."""
    from app.store.protocol import NotFoundError
    try:
        store.get_incident(GOLDEN_INCIDENT_ID)
        return [GOLDEN_INCIDENT_ID]
    except NotFoundError:
        pass
    now = datetime.now(UTC)
    incident = Incident(
        id=GOLDEN_INCIDENT_ID,
        title="Checkout API elevated 500 errors",
        service="checkout-api",
        environment=Environment.PRODUCTION,
        severity=Severity.SEV2,
        summary="HTTP 500 rate exceeded 12% after deployment.",
        state=WorkflowState.RECEIVED,
        provider_mode=ProviderMode.SIMULATED,
        created_at=now,
        updated_at=now,
    )
    store.add_incident(incident)
    store.append_workflow_event(incident.id, None, WorkflowState.RECEIVED, "demo.seed")
    return [incident.id]

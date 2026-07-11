import os
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict

from api.models import WorkflowRequest, WorkflowResponse

app = FastAPI(title="Incident Commander AI API")

# Demo Mode Configuration
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "demo_mode": str(DEMO_MODE)}

@app.post("/workflow/execute", response_model=WorkflowResponse)
def execute_workflow(request: WorkflowRequest) -> WorkflowResponse:
    if DEMO_MODE:
        # Simulated provider response
        return WorkflowResponse(
            status="simulated",
            message=f"Simulated execution for incident {request.incident_id}, action: {request.action}",
            requires_approval=request.requires_approval
        )
    else:
        # Real provider logic would go here
        raise HTTPException(status_code=501, detail="Real providers not implemented in M0")

@app.post("/provider/simulate")
def simulate_provider_action(action: str) -> Dict[str, str]:
    if not DEMO_MODE:
        raise HTTPException(status_code=400, detail="Only available in demo mode")
    
    return {"status": "success", "simulated_action": action, "mocked": "true"}

from typing import List, Optional
from pydantic import BaseModel, Field

# Security and Redaction Boundary
class LogEntry(BaseModel):
    id: str
    message: str
    is_redacted: bool = False

# Workflow Contracts
class WorkflowRequest(BaseModel):
    incident_id: str = Field(..., description="ID of the incident")
    action: str = Field(..., description="Action to perform")
    requires_approval: bool = True

class WorkflowResponse(BaseModel):
    status: str
    message: str
    requires_approval: bool

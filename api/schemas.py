"""
TripWeaver AI — Enterprise API Schemas
=======================================
Pydantic v2 validation schemas for travel planning requests, human approvals,
system health checks, and operational observability.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TravelRequest(BaseModel):
    """Client request initiating a travel planning pipeline."""
    message: str = Field(..., description="User trip planning query in natural language.")
    thread_id: Optional[str] = Field(default=None, description="Optional thread ID for conversational memory.")


class ApprovalRequest(BaseModel):
    """Client response to a Human-in-the-Loop review request."""
    thread_id: str = Field(..., min_length=1, description="Unique conversation thread identifier.")
    approved: bool = Field(..., description="True to approve draft; False to request revision.")
    feedback: str = Field(default="", description="Revision comments if approved=False.")


class TripConstraints(BaseModel):
    destination: Optional[str] = ""
    origin: Optional[str] = ""
    duration: Optional[str] = ""
    budget: Optional[str] = ""
    travel_style: Optional[str] = ""
    special_preferences: List[str] = Field(default_factory=list)


class TravelResponse(BaseModel):
    """Enterprise travel response payload."""
    success: bool = True
    thread_id: str
    answer: str
    requires_approval: bool = False
    approval_request: str = ""
    flight_results: Optional[str] = ""
    hotel_results: Optional[str] = ""
    weather_results: Optional[str] = ""
    budget_results: Optional[str] = ""
    itinerary: Optional[str] = ""
    selected_agents: List[str] = Field(default_factory=list)
    trip_constraints: Dict[str, Any] = Field(default_factory=dict)
    supervisor_reasoning: Optional[str] = ""
    guardrail_allowed: bool = True
    guardrail_reason: Optional[str] = ""
    approved: Optional[bool] = None
    human_feedback: Optional[str] = ""
    llm_calls: int = 0
    execution_time_seconds: Optional[float] = None


class HealthResponse(BaseModel):
    """Liveness & readiness probe response."""
    status: str = "ok"
    message: str = "TripMate AI API is running"
    version: str = "2.1.0"
    environment: str = "production"
    features: List[str] = Field(default_factory=lambda: [
        "supervisor_agent",
        "input_guardrail",
        "human_in_the_loop",
        "enterprise_resilience",
        "structured_logging",
    ])
    database_connected: Optional[bool] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Any] = None

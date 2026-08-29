import time
import json
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict, field_validator

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"

class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    CONFIRM_NEEDED = "CONFIRM_NEEDED"
    DENY = "DENY"

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class EmptyParams(StrictBaseModel):
    """Schema for actions requiring zero parameters."""
    pass

class OpenApplicationParams(StrictBaseModel):
    """Schema for launching an allowlisted application."""
    app_id: str = Field(..., min_length=1, description="Registered application identifier or alias (e.g. 'vscode', 'chrome')")

class VolumeSetParams(StrictBaseModel):
    """Schema for setting exact volume level (0 to 100)."""
    level: int = Field(50, ge=0, le=100, description="Target volume percentage (0 to 100)")

class VolumeAdjustParams(StrictBaseModel):
    """Schema for adjusting volume by a specific delta step."""
    step: Optional[int] = Field(default=5, ge=1, le=100, description="Volume step delta percentage (1 to 100)")

class MouseMoveParams(StrictBaseModel):
    """Schema for cursor movement."""
    norm_x: float = Field(..., ge=0.0, le=1.0, description="Normalized X coordinate (0.0 to 1.0)")
    norm_y: float = Field(..., ge=0.0, le=1.0, description="Normalized Y coordinate (0.0 to 1.0)")

class ScrollParams(StrictBaseModel):
    """Schema for scroll wheel input."""
    amount: int = Field(..., description="Scroll delta amount")

class AppTargetParams(StrictBaseModel):
    """Schema for application/window targeting actions."""
    target: Optional[str] = Field(default="active", min_length=1, description="Application or window identifier (defaults to 'active')")

class FileTargetParams(StrictBaseModel):
    """Schema for file operation targeting."""
    path: str = Field(..., min_length=1, description="Target file path")

def _validate_depth(data: Any, current: int = 1, max_depth: int = 6) -> None:
    if current > max_depth:
        raise ValueError(f"Payload nesting depth exceeds maximum allowed limit of {max_depth}.")
    if isinstance(data, dict):
        for v in data.values():
            _validate_depth(v, current + 1, max_depth)
    elif isinstance(data, (list, tuple, set)):
        for item in data:
            _validate_depth(item, current + 1, max_depth)

class StructuredActionRequest(BaseModel):
    """
    Contract for all action intents generated across any subsystem (Voice, Gesture, API, AI).
    The Policy Checker treats all requests as untrusted regardless of source.
    Includes defense against payload DoS via maximum size and recursion depth limits.
    """
    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., min_length=1, description="Registered action identifier")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameter payload")
    source: str = Field(..., min_length=1, description="Originating source (gesture, voice, api, ai, etc.)")
    correlation_id: UUID = Field(default_factory=uuid4, description="Unique correlation identifier for tracing and audit")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp of request generation")

    @field_validator("action", "source")
    @classmethod
    def strip_and_validate_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("String field cannot be blank or whitespace.")
        return v

    @field_validator("params")
    @classmethod
    def validate_params_security_bounds(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not v:
            return v
        
        # 1. Enforce max payload size limit (64 KB)
        try:
            serialized = json.dumps(v)
            if len(serialized.encode("utf-8")) > 65536:
                raise ValueError("Payload size exceeds maximum permitted limit (64 KB).")
        except TypeError:
            pass # Non-serializable objects will be caught by schema validation

        # 2. Enforce maximum nesting depth to prevent DoS recursion
        _validate_depth(v, current=1, max_depth=6)
        return v

class PolicyDecisionResult(BaseModel):
    """
    Deterministic authorization decision output produced by the Policy Checker.
    Contains no execution side-effects.
    """
    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecision = Field(..., description="Final authorization decision")
    risk_level: RiskLevel = Field(..., description="Determined risk level for the action")
    reason: str = Field(..., description="Security reason justifying the decision")
    correlation_id: UUID = Field(..., description="Correlation ID matching the evaluated request")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp of decision")

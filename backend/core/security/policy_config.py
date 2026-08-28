import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError
from core.security.models import RiskLevel

class PolicyConfigurationError(Exception):
    """Raised when security policy configuration fails to load or is malformed (Fail-Closed)."""
    pass

class ActionPolicyRule(BaseModel):
    risk: RiskLevel

class PolicyConfig(BaseModel):
    """
    Declarative security policy specification.
    Defines per-action risk levels and explicitly blocked operations.
    """
    version: str = Field(..., min_length=1)
    name: str = Field(default="Nexa Policy")
    actions: Dict[str, ActionPolicyRule] = Field(default_factory=dict)
    blocked_actions: List[str] = Field(default_factory=list)
    require_confirmation_for_high_risk: bool = Field(default=True)

    def is_blocked(self, action: str) -> bool:
        """Returns True if the action is explicitly on the blocked actions list."""
        return action in self.blocked_actions

    def get_action_risk(self, action: str, default: RiskLevel = RiskLevel.LOW) -> RiskLevel:
        """Returns the configured risk level for an action or the provided default."""
        if action in self.actions:
            return self.actions[action].risk
        return default

class PolicyLoader:
    """
    Loads and validates declarative policy configurations.
    Fails closed on any parse error, missing file, or schema invalidity.
    """
    @staticmethod
    def load_from_dict(data: dict) -> PolicyConfig:
        try:
            return PolicyConfig.model_validate(data)
        except ValidationError as e:
            raise PolicyConfigurationError(f"Malformed policy configuration schema: {e}") from e
        except Exception as e:
            raise PolicyConfigurationError(f"Failed to load policy configuration: {e}") from e

    @staticmethod
    def load_from_json_string(json_str: str) -> PolicyConfig:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise PolicyConfigurationError(f"Invalid JSON in policy configuration: {e}") from e
        return PolicyLoader.load_from_dict(data)

    @staticmethod
    def load_from_file(file_path: Optional[str] = None) -> PolicyConfig:
        if file_path is None:
            # Default to default_policy.json co-located in the same directory
            base_dir = Path(__file__).resolve().parent
            file_path = str(base_dir / "default_policy.json")

        path = Path(file_path)
        if not path.exists():
            raise PolicyConfigurationError(f"Policy configuration file not found at: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise PolicyConfigurationError(f"Cannot read policy file at {file_path}: {e}") from e

        return PolicyLoader.load_from_json_string(content)

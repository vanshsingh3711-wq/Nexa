from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

class LaunchStrategyType(str, Enum):
    SYSTEM_PATH = "SYSTEM_PATH"                  # Standard system binary (e.g. notepad.exe)
    DISCOVERABLE_EXECUTABLE = "DISCOVERABLE_EXECUTABLE" # Probes trusted paths in ProgramFiles/AppData/PATH
    SHELL_TARGET = "SHELL_TARGET"                # Windows shell targets (e.g. explorer.exe)

class ApplicationDefinition(BaseModel):
    """
    Strongly validated model representing an allowed application in the Nexa Application Registry.
    
    Security constraints:
    - All executable candidates and launch arguments are static, pre-configured definitions.
    - No user/voice/AI parameters can inject arbitrary executable paths or command strings.
    """
    model_config = ConfigDict(extra="forbid")

    app_id: str = Field(..., min_length=1, description="Unique, lowercase alphanumeric identifier for the application.")
    display_name: str = Field(..., min_length=1, description="Human-readable name of the application.")
    aliases: List[str] = Field(default_factory=list, description="List of recognized spoken/text aliases for lookup.")
    strategy_type: LaunchStrategyType = Field(default=LaunchStrategyType.DISCOVERABLE_EXECUTABLE, description="Launch strategy used.")
    executable_candidates: List[str] = Field(..., min_length=1, description="List of trusted executable names or candidate filepaths.")
    default_args: List[str] = Field(default_factory=list, description="Fixed launch arguments (if any).")
    description: Optional[str] = Field(default="", description="Optional description of the application.")

    @field_validator("app_id")
    @classmethod
    def validate_app_id(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("app_id cannot be blank.")
        if not all(c.isalnum() or c in ("_", "-") for c in cleaned):
            raise ValueError(f"app_id '{cleaned}' must contain only alphanumeric characters, dashes, or underscores.")
        return cleaned

    @field_validator("aliases")
    @classmethod
    def validate_aliases(cls, v: List[str]) -> List[str]:
        cleaned_list = []
        for alias in v:
            c = alias.strip().lower()
            if c and c not in cleaned_list:
                cleaned_list.append(c)
        return cleaned_list

class LaunchResult(BaseModel):
    """
    Structured outcome of an application launch attempt.
    """
    model_config = ConfigDict(extra="forbid")

    success: bool
    app_id: str
    display_name: str
    message: str
    error: Optional[str] = None

"""Common step contracts for modular Layer 3 extraction pipelines."""

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
from abc import ABC, abstractmethod
from app.layer_1.schemas.base_schema import BaseSchema
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector

@dataclass(frozen=True)
class ExtractionContext:
    """
    Immutable context used by extraction steps.

    This is intentionally lightweight for Phase 1. It can be extended with
    domain/schema/platform-specific runtime dependencies over time.
    """

    repo_url: str
    domain: str
    schema: BaseSchema
    platform: Optional[str] = None
    access_token: Optional[str] = None


@dataclass
class ExtractionState:
    """
    Mutable state that flows across extraction steps.

    Attributes:
      metadata: current aggregate being enriched.
      data: step-local scratchpad for intermediate values.
    """
    metadata_collector: MetadataCollector 
    data: dict[str, Any] = field(default_factory=dict)
    errors : dict[str, Exception] = field(default_factory=dict)


class ExtractionStep(ABC):
    """
    Small, composable unit of extraction behavior.

    Naming convention:
    - Extract*Step lives under extract_steps/ and stores normalized values in state.data.
    - Merge*Step lives under merge_steps/ and applies state.data values to state.metadata.
    - Apply*Step may write directly when there is no separate extraction phase.
    - Reusable helper functions live under helpers/, not beside steps.
    - Step files use the snake_case version of the class name with the
      trailing `_step` suffix, e.g. ExtractCitationAuthorsStep lives in
      extract_citation_authors_step.py.

    Extract step names should include the source scope, such as
    "citation.extract_authors". Merge step names should include the target
    domain and property, such as "software.merge_authors".
    """

    
    @property
    @abstractmethod
    def name() -> str:
      ...
    
    @property
    @abstractmethod
    def extracts() -> set["SchemaProperty"]:
      ...
    
    @property
    @abstractmethod
    def platforms() -> set[str]:
      ...

    @abstractmethod
    def extract(self, context: ExtractionContext, state: ExtractionState) -> ExtractionState:
        """Apply this step and return updated state."""
        ...

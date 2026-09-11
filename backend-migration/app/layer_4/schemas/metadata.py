"""
Response schemas for metadata endpoints (Layer 4 – API contracts).
Kept separate from routes so the API layer stays modular.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

class MetadataPlainResponse(BaseModel):
    """Response for GET /metadata: canonical maSMP/CODEMETA JSON-LD only."""

    model_config = ConfigDict(populate_by_name=True)
    status: str
    schema_: str = Field(alias="schema", description="Schema used (maSMP or CODEMETA)")
    code_url: HttpUrl
    message: str
    errors: Optional[Dict[str, str]] = None
    results: Dict[str, Any]


class MetadataEnrichedResponse(BaseModel):
    """Response for GET /metadata/enriched: JSON-LD plus confidence, source, category per property."""

    model_config = ConfigDict(populate_by_name=True)
    status: str
    schema_: str = Field(alias="schema", description="Schema used (maSMP or CODEMETA)")
    code_url: HttpUrl
    message: str
    results: Dict[str, Any]
    enriched_metadata: Dict[str, Any]
    errors: Optional[Dict[str, str]] = None


class FairnessResponse(BaseModel):
    """Response for GET /fairness: JSON-LD plus FAIRness scores."""

    model_config = ConfigDict(populate_by_name=True)
    status: str
    schema_: str = Field(alias="schema", description="Schema used (maSMP or CODEMETA)")
    code_url: HttpUrl
    message: str
    results: Dict[str, Any]
    fairness: Dict[str, Any]

class SinglePropertyItem(BaseModel):
    """Single property value plus enrichment for a specific profile."""

    value: Any
    source: Optional[Any] = None
    confidence: Optional[float] = None


class SinglePropertyResponse(BaseModel):
    """Response for GET /metadata/property: one property across profiles."""

    model_config = ConfigDict(populate_by_name=True)
    status: str
    schema_: str = Field(alias="schema", description="Schema used (maSMP or CODEMETA)")
    code_url: HttpUrl
    message: str
    property: str
    results: List[SinglePropertyItem]
    errors: Optional[Dict[str, str]] = None


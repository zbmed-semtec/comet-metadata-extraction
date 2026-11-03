from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")

@dataclass
class MetadataProperty(Generic[T]):
    source: str
    property_name: str
    property_value: T
    # Ranking weight of this source. Callers that omit it are treated as fully reliable.
    # The LLM evidence score is stored separately in extraction_confidence.
    confidence: float = 1.0
    evidence: Any = None
    extraction_confidence: float | None = None

class MetadataCollector:
    data : dict[str, list[MetadataProperty]]

    def __init__(self):
        self.data = {}
    
    def collect(
        self,
        source: str,
        property_name: str,
        property_value: Any,
        confidence: float = 1.0,
        *,
        evidence: Any = None,
        extraction_confidence: float | None = None,
    ):
        if not property_name in self.data:
            self.data[property_name] = []
        all_records = self.data[property_name]
        all_records.append(
            MetadataProperty(
                source,
                property_name,
                property_value,
                confidence,
                evidence,
                extraction_confidence,
            )
        )
        self.data[property_name] = all_records
    
    def get(self, property_name: str) -> dict[str, Any] | Any:
        all_records = self.data.get(property_name, dict())
        return all_records
    
    def get_most_confident(self, uri: str) -> MetadataProperty[Any]:
        all = self.data.get(uri, [])
        values = sorted(all, key=lambda x : x.confidence, reverse=True)
        try:
            return values[0]
        except:
            return None

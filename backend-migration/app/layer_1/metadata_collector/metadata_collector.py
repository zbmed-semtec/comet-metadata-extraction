from dataclasses import dataclass, asdict
from typing import Any, Generic, TypeVar

T = TypeVar("T")

@dataclass
class MetadataProperty(Generic[T]):
    source: str
    property_name: str
    property_value: T
    source_reliability: float = 1.0
    evidence: Any = None
    extraction_confidence: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

class MetadataCollector:
    data : dict[str, list[MetadataProperty]]

    def __init__(self):
        self.data = {}
    
    def collect(
        self,
        source: str,
        property_name: str,
        property_value: Any,
        source_reliability: float = 1.0,
        evidence: Any = None,
        extraction_confidence: float | None = None,
    ):
        if not property_name in self.data:
            self.data[property_name] = []
        all_records = self.data[property_name]
        all_records.append(
            MetadataProperty(
                source=source,
                property_name=property_name,
                property_value=property_value,
                source_reliability=source_reliability,
                evidence=evidence,
                extraction_confidence=extraction_confidence,
            )
        )
        self.data[property_name] = all_records
    
    def get(self, property_name: str) -> dict[str, Any] | Any:
        all_records = self.data.get(property_name, dict())
        return all_records
    
    def get_most_reliable(self, uri: str) -> MetadataProperty[Any]:
        all = self.data.get(uri, [])
        values = sorted(all, key=lambda x : x.source_reliability, reverse=True)
        try:
            return values[0]
        except:
            return None

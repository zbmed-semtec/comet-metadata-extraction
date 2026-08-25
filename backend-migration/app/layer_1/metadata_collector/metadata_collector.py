from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")

@dataclass
class MetadataProperty(Generic[T]):
    source: str
    property_name: str
    property_value: T
    confidence: float = 1.0

class MetadataCollector:
    data : dict[str, list[MetadataProperty]]

    def __init__(self):
        self.data = {}
    
    def collect(self, source: str, property_name: str, property_value: Any, confidence:float=1.0):
        if not property_name in self.data:
            self.data[property_name] = []
        all_records = self.data[property_name]
        all_records.append(MetadataProperty(source, property_name, property_value, confidence))
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

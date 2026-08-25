from typing import AbstractSet, Any, Dict
from app.layer_1.schemas.base_schema import BaseSchema
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
from pydantic import BaseModel
from app.layer_2.use_cases.extract_metadata import JSONLDBuilderBase

class JSONLDBuilder(JSONLDBuilderBase):
    def build_jsonld(self, metadata: MetadataCollector, schema: BaseSchema) -> Dict[str, Any]:

        context = schema.build_context()
        result = {"@context": context}
        
        for property_name in schema.get_property_list():
            uri = schema.get_uri(property_name)
            record = metadata.get_most_confident(uri)
            if record:
                val = record.property_value
                if isinstance(val, BaseModel):
                    result[property_name] = val.model_dump(mode='json')
                else:
                    result[property_name] = val
            else:
                result[property_name] = None
        return result

__all__ = ["JSONLDBuilder"]

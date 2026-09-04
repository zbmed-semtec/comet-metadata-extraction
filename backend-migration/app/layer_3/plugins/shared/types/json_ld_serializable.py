from abc import ABC
from pydantic import BaseModel

JSONLD_CONTEXT = {
    "@vocab": "https://schema.org/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "account": "foaf:account",
    "OnlineAccount": "foaf:OnlineAccount",
    "accountName": "foaf:accountName",
    "accountServiceHomepage": {"@id": "foaf:accountServiceHomepage", "@type": "@id"},
}

class JsonLdSerializable(BaseModel, ABC):
    def to_jsonld_dict(self, is_root: bool = True) -> dict:
        result = {}
        for key, field_info in self.__class__.model_fields.items():
            alias = field_info.serialization_alias or field_info.alias or key
            value = getattr(self, key)
            serialized = self._serialize_value(value)
            if serialized is None:
                continue
            result[alias] = serialized

        result["@type"] = self.__class__.__name__
        if is_root:
            result["@context"] = JSONLD_CONTEXT
        return result

    def _serialize_value(self, value):
        if value is None:
            return None
        if isinstance(value, JsonLdSerializable):
            return value.to_jsonld_dict(is_root=False)
        if isinstance(value, list):
            serialized = [self._serialize_value(v) for v in value]
            return [v for v in serialized if v is not None] or None
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items() if v is not None} or None
        return value
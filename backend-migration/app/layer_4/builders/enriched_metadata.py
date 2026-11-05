"""
Build enriched_metadata for the API (per-property source reliability, source, category).
Values come from results; this module only shapes annotations for the response.
"""
from typing import Dict, Any

from app.layer_1.schemas.base_schema import BaseSchema
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector, MetadataProperty

def build_enriched_metadata(
    collector: MetadataCollector,
    schema: BaseSchema,
) -> Dict[str, Any]:
    """
    Build enriched_metadata for the API response: per-profile, per-property annotations only.
    No value (get that from results); source_reliability, source, and category, plus
    the LLM pipeline's confidence and evidence when that source supplied the value.
    source_reliability is how reliable the winning source is. It is separate from
    the confidence score returned by the LLM extraction pipeline.
    - For maSMP: per-profile (SoftwareSourceCode / SoftwareApplication), with category.
    - For CODEMETA: flat \"codemeta\" profile without category.
    """
   
    result = {}
    for prop in schema.get_property_list():
        uri = schema.get_uri(prop)
        record = collector.get_most_reliable(uri)
        category = schema.get_categories_of(property_name=prop)
        if isinstance(category, list):
            if len(category) > 0:
                category = category[0]
            else:
                category = "optional"
        if category is None:
            category = "optional"
        if not record:
            continue
        entry = {
            "category": category,
        }
        entry.update(record.as_dict())
        result[prop] = entry
    return result

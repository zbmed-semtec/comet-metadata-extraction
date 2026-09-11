import logging
from pathlib import Path
from linkml_runtime import SchemaView
from app.layer_1.schemas.base_schema_registry import BaseSchemaRegistry
from app.layer_3.schemas.linkml.linkml_schema import LinkMlSchema

logger = logging.getLogger(__name__)

class MissingSchemaError(KeyError):
    """Raised when a requested schema is not found in the registry."""
    pass

class LinkMlSchemaRegistry(BaseSchemaRegistry):
    def __init__(self):
        self.schemas: dict[str, LinkMlSchema] = {}

    def load(self, directory: str | Path) -> list[str]:
        directory = Path(directory)
        if not directory.is_dir():
            raise NotADirectoryError(f"{directory} is not a valid directory")

        loaded = []
        for path in directory.glob("*.yaml"):
            try:
                view = SchemaView(str(path))
                for class_name in view.all_classes():
                    schema_name = view.schema.name
                    name = f"{schema_name.lower()}:{class_name.lower()}"
                    schema = LinkMlSchema(view, class_name)
                    self.schemas[name] = schema
                loaded.append(name)
            except Exception:
                logger.exception("Error loading schema from %s", path)

        return loaded

    def get(self, schema_name: str, class_name: str) -> LinkMlSchema:
        name = f"{schema_name.lower()}:{class_name.lower()}"
        if name not in self.schemas:
            raise MissingSchemaError(f"Schema '{name}' not found in registry")
        return self.schemas[name]

    def list(self) -> list[str]:
        return list(self.schemas.keys())
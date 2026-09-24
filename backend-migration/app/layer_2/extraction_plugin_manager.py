import logging
from app.layer_2.errors import UnknownPropertyError
from app.layer_2.plugin_manager import PluginManager
from app.layer_2.extraction_plugin import ExtractionPlugin
from app.layer_2.contracts import ExtractionContext, ExtractionState

SchemaProperty = str

logger = logging.getLogger(__name__)


class ExtractionPluginManager(PluginManager):

    def __init__(self):
        super().__init__()
        self.metadata_providers : dict[SchemaProperty, set[str]] = {}

    def _on_plugin_registration(self, plugin_class):
        if issubclass(plugin_class, ExtractionPlugin):
            for property in plugin_class.extracts:
                helper = self.metadata_providers.get(property, set())
                helper.add(plugin_class.name)
                self.metadata_providers[property] = helper
                self.object_registry[plugin_class.name] = self._instantiate_plugin(plugin_class)
        logger.info("registered %s", plugin_class)

    def select(self, schema_property: SchemaProperty, context: ExtractionContext) -> set[ExtractionPlugin]:
        result = set()
        try:
            uri = context.schema.get_uri(schema_property)
        except UnknownPropertyError:
            raise
        except Exception as e:
            raise UnknownPropertyError(
                f"Unknown property '{schema_property}' for schema "
                f"'{context.schema.get_schema_name()}:{context.schema.get_class_name()}'."
            ) from e
        if uri not in self.metadata_providers:
            raise UnknownPropertyError(
                f"Unknown property '{schema_property}' (URI '{uri}'): no plugin declares it."
            )
        for pluginName in self.metadata_providers.get(uri, {}):
            instance = self.get(pluginName)
            if instance.applicable(context):
                result.add(instance)
        if len(result) < 1:
            logger.warning("missing applicable plugin to extract '%s'!", uri)
        return result

    def extract(self, schema_property: SchemaProperty, context: ExtractionContext, state: ExtractionState) -> ExtractionState:
        for plugin in self.select(schema_property, context):
            plugin.extract(context, state)
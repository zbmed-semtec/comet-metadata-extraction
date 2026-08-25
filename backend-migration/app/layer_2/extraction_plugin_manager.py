from app.layer_2.plugin_manager import PluginManager
from app.layer_2.extraction_plugin import ExtractionPlugin
from app.layer_2.contracts import ExtractionContext, ExtractionState

SchemaPropery = str

class ExtractionPluginManager(PluginManager):

    def __init__(self):
        super().__init__()
        self.metadata_providers : dict[SchemaPropery, set[str]] = {}

    def _on_plugin_registration(self, plugin_class):
        if issubclass(plugin_class, ExtractionPlugin):
            for property in plugin_class.extracts:
                helper = self.metadata_providers.get(property, set())
                helper.add(plugin_class.name)
                self.metadata_providers[property] = helper
                self.object_registry[plugin_class.name] = self._instantiate_plugin(plugin_class)
        # print("registered", plugin_class)

    def select(self, schema_property: SchemaPropery, context: ExtractionContext) -> set[ExtractionPlugin]:
        result = set()
        uri = context.schema.get_uri(schema_property)
        for pluginName in self.metadata_providers.get(uri, {}):
            instance = self.get(pluginName)
            if instance.applicable(context):
                result.add(instance)
        if len(result) < 1:
            pass
            # raise Warning(f"missing plugin to extract '{uri}'!")
        return result

    def extract(self, schema_property: SchemaPropery, context: ExtractionContext, state: ExtractionState) -> ExtractionState:
        for plugin in self.select(schema_property, context):
            plugin.extract(context, state)
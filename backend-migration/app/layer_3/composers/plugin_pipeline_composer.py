import logging
from app.layer_2.errors import UnknownPropertyError
from app.layer_2.extraction_plugin import ExtractionPlugin
from app.layer_2.contracts import PipelineComposer, ExtractionContext
from app.layer_2.extraction_plugin_manager import ExtractionPluginManager
from app.layer_3.steps.contracts.pipeline import ExtractionPipeline
import app.layer_3.plugins

logger = logging.getLogger(__name__)


class PluginPipelineComposer(PipelineComposer):

    plugin_manager : ExtractionPluginManager = None

    def get_plugin_manager(self):
        if not self.plugin_manager:
            self.plugin_manager = ExtractionPluginManager()
            self.plugin_manager.discover(app.layer_3.plugins)
        return self.plugin_manager

    def compose(self, context : ExtractionContext, single_property: str = None) -> ExtractionPipeline:

        export_keys = context.schema.get_property_list()

        priority_groups : dict[int, set[ExtractionPlugin]] = dict()

        if single_property:
            export_keys = [single_property]

        for key in export_keys:
            try:
                candidate_plugins = self.get_plugin_manager().select(key, context)
            except UnknownPropertyError:
                if single_property:
                    raise
                logger.exception("failed to select plugins for property '%s'", key)
                continue
            except Exception:
                if single_property:
                    # Do not launder runtime errors (network, rate limit, ...)
                    # into "unknown property"; surface the real cause.
                    raise
                logger.exception("failed to select plugins for property '%s'", key)
                continue
            for plugin in candidate_plugins:
                group = priority_groups.get(plugin.priority_level, set())
                group.add(plugin)
                priority_groups[plugin.priority_level] = group

        if single_property and not priority_groups:
            # Property is known (select did not raise) but no applicable plugin.
            raise ValueError(
                f"No applicable plugin to extract property '{single_property}' for schema "
                f"'{context.schema.get_schema_name()}:{context.schema.get_class_name()}'"
            )

        pipeline_steps = []
        for priority_level in sorted(priority_groups.keys(), reverse=True):
            pipeline_steps.extend(sorted(priority_groups[priority_level], key=lambda p: p.name))

        return ExtractionPipeline(steps=pipeline_steps)
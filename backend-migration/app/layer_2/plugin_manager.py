import importlib
import inspect
import logging
import pkgutil
from app.layer_2.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class PluginManager:

    PLUGIN_BASE_CLASS = BasePlugin

    def __init__(self):
        self.object_registry: dict[str, BasePlugin] = {}
        self.class_registry: dict[str, any] = {}
        self.registered_aliases : dict[str, set[str]] = {}

    def discover(self, package):
        """
        Walk every module in the given package,
        import it, then look for self.PLUGIN_BASE_CLASS subclasses
        """
        for finder, module_name, ispkg in pkgutil.walk_packages(
            path=package.__path__,
            prefix=package.__name__ + ".",
        ):
            try:
                module = importlib.import_module(module_name)
                self._load_from_module(module)
            except Exception:
                logger.exception("problem in %s", module_name)

    def _load_from_module(self, module):
        """Inspect a module and register any self.PLUGIN_BASE_CLASS subclasses found"""
        for attr_name in dir(module):
            obj = getattr(module, attr_name)

            if not inspect.isclass(obj):
                continue
            if not issubclass(obj, self.PLUGIN_BASE_CLASS):
                logger.debug("skipping %s, doesn't belong to base class tree", obj)
                continue
            if obj is self.PLUGIN_BASE_CLASS:
                # skip the base class itself
                logger.debug("skipping %s, is plugin base class", obj)
                continue
            if inspect.isabstract(obj):
                # skip partially implemented classes
                logger.debug("skipping %s, is abstract", obj)
                continue

            self._register(obj)

    def _instantiate_plugin(self, plugin_class):
        instance = plugin_class()
        instance.set_plugin_manager(self)
        instance.on_load()
        return instance

    def _on_plugin_registration(self, plugin_class):
        logger.info("Registered plugin: '%s' v%s", plugin_class.name, plugin_class.version)

    def _register(self, plugin_class):
        if plugin_class.name not in self.class_registry:
            self.class_registry[plugin_class.name] = plugin_class
            for alias in plugin_class.aliases:
                self.registered_aliases[alias] = plugin_class.name
            self._on_plugin_registration(plugin_class)

    def get(self, name_or_key: str) -> BasePlugin | None:
        if name_or_key in self.registered_aliases:
            return self.get(self.registered_aliases[name_or_key])
        if name_or_key in self.object_registry:
            return self.object_registry[name_or_key]
        if name_or_key in self.class_registry:
            instance = self._instantiate_plugin(self.class_registry[name_or_key])
            self.object_registry[name_or_key] = instance
            return instance
        return None

    def unload_all(self):
        for plugin in self.object_registry.values():
            plugin.on_unload()
        self.object_registry.clear()
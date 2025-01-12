

_registries = {}

class RaiRegistry:

    class Names:
        data_processors = "data_processors"
        data_loaders = "data_loaders"
        ai_models = "ai_models"
        ai_prompts = "ai_prompts"
        ai_agents = "ai_agents"

    class Registries:
        data_processors = {}
        data_loaders = {}
        ai_models = {}
        ai_prompts = {}
        ai_agents = {}

    def __init__(self):
        self.create_registry(self.Names.data_processors)
        self.create_registry(self.Names.data_loaders)
        self.create_registry(self.Names.ai_models)
        self.create_registry(self.Names.ai_prompts)
        self.create_registry(self.Names.ai_agents)

    def retrieve_item(self, registry_name: str, name: str):
        registry = self.get_registry(registry_name)
        return registry.get(name)

    @staticmethod
    def create_registry(registry_name: str) -> None:
        if registry_name not in _registries:
            _registries[registry_name] = {}

    @staticmethod
    def get_registry(registry_name: str) -> dict:
        if registry_name not in _registries:
            RaiRegistry.create_registry(registry_name)
        return _registries[registry_name]
    @staticmethod
    def register_item(registry_name: str, name: str, item) -> None:
        registry = RaiRegistry.get_registry(registry_name)
        registry[name] = item
    @staticmethod
    def all_registries() -> dict:
        return _registries
    @staticmethod
    def register(registry_name: str, name: str):
        def decorator(func_or_class):
            RaiRegistry.register_item(registry_name, name, func_or_class)
            return func_or_class
        return decorator
    @staticmethod
    def data_processor(name: str):
        def decorator(func_or_class):
            RaiRegistry.register_item(RaiRegistry.Names.data_processors, name, func_or_class)
            return func_or_class
        return decorator
    @staticmethod
    def data_loader(name: str):
        def decorator(func_or_class):
            RaiRegistry.register_item(RaiRegistry.Names.data_loaders, name, func_or_class)
            return func_or_class
        return decorator
    @staticmethod
    def ai_model(name: str):
        def decorator(func_or_class):
            RaiRegistry.register_item(RaiRegistry.Names.ai_models, name, func_or_class)
            return func_or_class
        return decorator
    @staticmethod
    def ai_prompt(name: str):
        def decorator(func_or_class):
            RaiRegistry.register_item(RaiRegistry.Names.ai_models, name, func_or_class)
            return func_or_class
        return decorator
    @staticmethod
    def ai_agent(name: str):
        def decorator(func_or_class):
            RaiRegistry.register_item(RaiRegistry.Names.ai_agents, name, func_or_class)
            return func_or_class
        return decorator

from abc import ABC

from langchain_core.document_loaders import BaseLoader

LOADER_REGISTRY = {}

def register_loader(name: str):
    def decorator(cls):
        """
        1. Registers `cls` under `name` in our registry.
        2. Returns `cls` unchanged.
        """
        LOADER_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator


class RaiBaseLoaders(ABC):
    name = None

    @classmethod
    def get_registry(cls): return LOADER_REGISTRY

    @classmethod
    def pipeline(cls, name: str) -> BaseLoader:
        """
        Main pipeline method. Looks up which agent classes are registered under 'name',
        instantiates the first one, and calls its 'run(...)' method.
        """
        agent_cls = LOADER_REGISTRY.get(name)
        if not agent_cls:
            raise ValueError(f"No agent found with name '{name}'")
        cls.name = name
        return agent_cls[0]


@register_loader('base')
class BLoad(RaiBaseLoaders):

    def __init__(self):
        print("Setting up BLoad")

if __name__ == '__main__':
    print(RaiBaseLoaders.pipeline('base'))
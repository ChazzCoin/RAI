from abc import ABC
from langchain_core.document_loaders import BaseLoader

LOADER_REGISTRY = {}

def register_loader(name: str):
    def decorator(cls):
        LOADER_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator


class RaiBaseLoaders(ABC):
    name = None

    @classmethod
    def get_registry(cls): return LOADER_REGISTRY

    @classmethod
    def pipeline(cls, name: str) -> BaseLoader:
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
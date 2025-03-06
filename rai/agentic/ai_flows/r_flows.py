
# from rai.agentic.ai_flows import knowledge_flow
FLOW_REGISTRY = {}

def register_flow(name: str):
    def decorator(cls):
        FLOW_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator

class rFlows:
    name = None

    def __init_subclass__(cls, flow_name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if flow_name:
            FLOW_REGISTRY.setdefault(flow_name, []).append(cls)

    @classmethod
    def get_registry(cls): return FLOW_REGISTRY
    @classmethod
    def get_flow_names(cls): return list(FLOW_REGISTRY.keys())
    @classmethod
    def flow(cls, name: str, prefix: str, user_prompt: str, engine: str='openai'):
        agent_classes = FLOW_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls
        return agent_instance.exec(name=name, prefix=prefix, user_prompt=user_prompt, engine=engine)


def main(name, prefix, user_prompt):
    # from rai.ingest.utilities.text_data import schedule_text
    results = rFlows.flow(
            name=name,
            prefix=prefix,
            user_prompt=user_prompt
        )
    if type(results) in [list, tuple]:
        for item in results:
            print(item)
    elif type(results) in [dict]:
        for item in results.items():
            print(item)
    else:
        print(results)


if __name__ == "__main__":
    from rai.ingest.utilities.text_data import schedule_text
    user_prompt = "I wanna see the last 10 documents."
    main("knowledge_flow", prefix="rai2025.1", user_prompt=user_prompt)
    # asyncio.run(
    #     main(
    #         name="objective",
    #         user_prompt=user_prompt
    #     )
    # )
    # asyncio.run(
    #     main(
    #         name="subject",
    #         user_prompt=user_prompt
    #     )
    # )
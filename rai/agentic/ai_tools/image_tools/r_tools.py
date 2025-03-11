
import threading
from abc import abstractmethod, ABC

from rai.agentic.ai_tools.image_tools.image_formats import aiImageFormats
from rai.agentic.ai_tools.image_tools.image_functions import aiImageFunctions
from rai.agentic.ai_tools.image_tools.image_prompts import aiImagePrompts
from rai.assistant.connectors import rAI
from rai.ingest.utilities.TextUtils import TextProcessor

IMAGE_AGENT_REGISTRY = {}


def register_image_agent(name: str):
    def decorator(cls):
        IMAGE_AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator


class rImageTools(ABC, rAI, TextProcessor):
    name = None

    def __init__(self):
        super().__init__()

    @classmethod
    def get_registry(cls): return IMAGE_AGENT_REGISTRY

    @classmethod
    def tool(cls, name: str, image=None):
        agent_classes = IMAGE_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(image=image)

    @classmethod
    def tools(cls, *names: str, user_prompt: str, system_prompt: str=None):
        pipe_results = {}

        def thread_runner(user_prompt, name, system_prompt):
            agent_classes = IMAGE_AGENT_REGISTRY.get(name)
            if not agent_classes:
                pipe_results[name] = None
                return
            cls.name = name
            agent_cls = agent_classes[0]
            agent_instance = agent_cls()
            pipe_results[name] = agent_instance.run(user_prompt=user_prompt, system_prompt=system_prompt)

        # Create and start a thread for each collection
        threads = []
        for name in names:
            thread = threading.Thread(target=thread_runner, args=(user_prompt, name, system_prompt))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

        return pipe_results

    @classmethod
    async def generate_async(cls, name: str, image=None):
        agent_classes = IMAGE_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return await agent_instance.run_async(image=image)

    @classmethod
    def generates(cls, *names: str, image=None):
        pipe_results = {}

        def thread_runner(name, image):
            agent_classes = IMAGE_AGENT_REGISTRY.get(name)
            if not agent_classes:
                pipe_results[name] = None
                return
            cls.name = name
            agent_cls = agent_classes[0]
            agent_instance = agent_cls()
            pipe_results[name] = agent_instance.run(image=image)

        # Create and start a thread for each collection
        threads = []
        for name in names:
            thread = threading.Thread(target=thread_runner, args=(name, image))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

        return pipe_results


    @abstractmethod
    def type(self): pass
    @abstractmethod
    def parse(self, result): pass
    def system_prompt(self): return aiImagePrompts.prompt(self.name)
    def user_prompt(self): return ""

    def run(self, image=None):
        try:
            if self.type() == "format":
                return self.parse(self.generate_format(
                    user=self.user_prompt(),
                    system=self.system_prompt(),
                    format=aiImageFormats.format(self.name),
                    image=image
                ))
            elif self.type() == "function":
                return self.parse(self.generate_function(
                    user=self.user_prompt(),
                    system=self.system_prompt(),
                    functions=aiImageFunctions.function(self.name),
                    image=image
                ))
            elif self.type() == "generate":
                return self.parse(self.engine.generate(
                    user=self.user_prompt(),
                    system=self.system_prompt(),
                    image=image
                ))
        except Exception as e:
            print(f"Error: {e}")
            return None

    async def run_async(self, image=None):
        try:
            if self.type() == "format":
                return await self.parse(self.engine.generate_format_async(
                    user=self.user_prompt(),
                    system=self.system_prompt(),
                    format=aiImageFormats.format(self.name),
                    image=image
                ))
            elif self.type() == "function":
                return await self.parse(self.engine.generate_function_async(
                    user=self.user_prompt(),
                    system=self.system_prompt(),
                    functions=aiImageFunctions.function(self.name),
                    image=image
                ))
            elif self.type() == "generate":
                return await self.parse(self.engine.generate_async(
                    user=self.user_prompt(),
                    system=self.system_prompt(),
                    image=image
                ))
        except Exception as e:
            print(f"Error: {e}")
            return None

"""
These seem to be turning into Configurations for agents.
What they do, how they do it...what they need...etc...
- remove term of service issues
- summarize data
- 
"""

@register_image_agent("text_extractor")
class AgentImageTextExtractor(rImageTools):
    def type(self): return "generate"
    def parse(self, result): return result

@register_image_agent("table_extractor")
class AgentImageTableExtractor(rImageTools):
    def type(self): return "format"
    def parse(self, result): return result

@register_image_agent("form_extractor")
class AgentImageFormExtractor(rImageTools):
    def type(self): return "format"
    def parse(self, result): return result

@register_image_agent("image_type")
class AgentImageTypeExtractor(rImageTools):
    def type(self): return "function"
    def parse(self, result): return result

""" To Build Out """
@register_image_agent("qr_extractor")
class AgentQRExtractor(rImageTools):
    def type(self):
        return "extract"
    def parse(self, result):
        # Process result to decode QR/barcode data.
        return result


@register_image_agent("visual_query_generator")
class AgentVisualQueryGenerator(rImageTools):
    def type(self):
        return "generate"  # Focused on generating a text query from visual data.

    def parse(self, result):
        # Convert the generated query result into a format suitable for the retriever.
        return result


@register_image_agent("image_metadata_extractor")
class AgentImageMetadataExtractor(rImageTools):
    def type(self):
        return "analyze"  # For analyzing and extracting metadata.

    def parse(self, result):
        # Process and return the extracted metadata.
        return result


@register_image_agent("visual_sentiment_analyzer")
class AgentVisualSentimentAnalyzer(rImageTools):
    def type(self):
        return "analyze"  # Analyzes the emotional context of the image.

    def parse(self, result):
        # Process sentiment analysis result (e.g., positive, negative, neutral).
        return result


async def main(name, image):
    # from rai.pipeline.utilities.text_data import schedule_text
    results = await rImageTools.generate_async(
            name=name,
            image=image
        )
    if type(results) in [list, tuple]:
        for item in results:
            print(item)
    elif type(results) in [dict]:
        for item in results.items():
            print(item)
    else:
        print(results)

def mains(*names:str, image):
    # from rai.pipeline.utilities.text_data import schedule_text
    results = rImageTools.generates(
            *names,
            image=image
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
    # from rai.pipeline.utilities.text_data import schedule_text
    image = "/Users/chazzromeo/Desktop/pcsc2024/Complex Schedule.png"
    # mains("form_extractor", image=image)
    results = rImageTools.tool(
        "image_type",
        image=image
    )
    print(results)

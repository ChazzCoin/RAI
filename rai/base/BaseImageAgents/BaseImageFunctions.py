from abc import ABC, abstractmethod

IMAGE_BASE_FUNCTIONS = {}

def register_image_functions(name: str):
    def decorator(cls):
        IMAGE_BASE_FUNCTIONS.setdefault(name, []).append(cls)
        return cls
    return decorator


class RaiBaseImageFunctions(ABC):
    name = None

    @classmethod
    def get_registry(cls):
        """Returns the entire registry dict."""
        return IMAGE_BASE_FUNCTIONS

    @classmethod
    def function(cls, name: str, sub=False):
        agent_classes = IMAGE_BASE_FUNCTIONS.get(name)
        if not agent_classes:
            raise ValueError(f"No agent found with name '{name}'")
        cls.name = name
        # You might decide to pick the first, or do additional logic if multiple classes are registered.
        agent_cls = agent_classes[0]
        # Instantiate the agent. If your agent requires, e.g. an engine, pass it here.
        agent_instance = agent_cls()
        if sub: return agent_instance.sub_run()
        return agent_instance.run()

    @staticmethod
    def getFunctionJsonNoArgs(name, description) -> dict:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description
            },
        }
    @abstractmethod
    def type(self) -> str: pass
    @abstractmethod
    def functions(self) -> dict: pass
    @abstractmethod
    def sub_functions(self) -> dict: pass
    def run(self):
        try:
            if self.type() == "no_args":
                return [ self.getFunctionJsonNoArgs(key, value) for key, value in self.functions().items() ]
        except Exception as e:
            print(f"Error: {e}")
            return None
    def sub_run(self):
        try:
            if self.type() == "no_args":
                return [ self.getFunctionJsonNoArgs(key, value) for key, value in self.sub_functions().items() ]
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
@register_image_functions("image_type")
class BaseImageFunctionImageType(RaiBaseImageFunctions):
    def type(self):
        return "no_args"

    def functions(self) -> dict:
        return {
            "plain_text": "The image consists of basic, unstructured text. It may include scanned documents, handwritten notes, or printed text with minimal formatting.",
            "table": "The image contains structured table data, complete with headers and rows. It may include merged cells or multi-level headers and is ideal for structured data extraction.",
            "form": "The image displays a form layout, including field labels, input types, placeholders, default values, and selectable options. Perfect for digital form reconstruction.",
            "photograph": "The image is a photograph or real-world scene, rich in visual details but with minimal or no structured textual data.",
            "graph": "The image presents a graph, chart, or plot that displays data trends or comparisons. It includes elements like axes, legends, and markers.",
            "diagram": "The image contains a diagram or flowchart that illustrates processes, systems, or relationships using nodes, connectors, and labels.",
            "infographic": "The image is an infographic combining text, images, and charts to convey information visually in a compelling and organized manner.",
            "screenshot": "The image is a screenshot capturing a digital interface, which may include various UI elements, notifications, and toolbars.",
            "code": "The image features code snippets or programming content, often including syntax highlighting and formatting, suitable for code extraction.",
            "receipt": "The image is a receipt or invoice, containing structured data such as dates, itemized lists, prices, and totals, often with mixed printed and handwritten text."
        }
    def sub_functions(self) -> dict: return {}





if __name__ == "__main__":
    print(RaiBaseImageFunctions.pipeline("categorize_sports", sub=True))
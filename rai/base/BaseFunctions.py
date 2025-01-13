from abc import ABC, abstractmethod

BASE_FUNCTIONS = {}

def register_functions(name: str):
    def decorator(cls):
        BASE_FUNCTIONS.setdefault(name, []).append(cls)
        return cls
    return decorator


class RaiBaseFunctions(ABC):
    name = None

    @classmethod
    def get_registry(cls):
        """Returns the entire registry dict."""
        return BASE_FUNCTIONS

    @classmethod
    def pipeline(cls, name: str, sub=False):
        agent_classes = BASE_FUNCTIONS.get(name)
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
@register_functions("categorize_sports")
class BaseFunctionCategories(RaiBaseFunctions):
    def type(self): return "no_args"
    def functions(self) -> dict: return {
        "tryout_registration": f"User Prompt Context Involves tryouts, placements, registration or how to signup and get involved in the club.",
        "uniforms_attire": f"User Prompt Context Involves how to order or get their uniforms and other attire.",
        "tournaments": f"User Prompt Context Involves tournament information.",
        "development_curriculum": f"User Prompt Context Involves long term player and parent development models.",
        "policy_procedures": f"User Prompt Context Involves police and the procedures the club adheres to.",
        "finance_payments": f"User Prompt Context Involves payments finance cost.",
        "scholarship_programs": f"User Prompt Context Involves scholarship programs that are available.",
        "facilities_locations": f"User Prompt Context Involves fields, locations, office, facilities, directions.",
        "volunteers": f"User Prompt Context Involves volunteer work, helping or getting involved as a parent.",
        "contact_information": f"User Prompt Context Involves a persons/coach/admin/parent contact information, email, phone number, social tag.",
        "roster_teams": f"User Prompt Context Involves a team, teams, players, roster information.",
        "events_schedules": f"User Prompt Context Involves schedules and events around practices, games, tournaments, meetings, parties.",
    }
    def sub_functions(self) -> dict: return {
        "admin": f"User Prompt Context general information about a team involving staff, coaches, players, events.",
        "summary": f"User Prompt Context general information about a team involving staff, coaches, players, events.",
        "events": f"User Prompt Context Calendar based events like practices, games, festivals, meetings, parties.",
        "practices": f"User Prompt Context Calendar or general information about team practices.",
        "games": f"User Prompt Context Calendar or general information about based team games.",
        "roster": f"User Prompt Context Players, Coaches, Parents, Managers, Staff involving a team or teams.",
        "teams": f"User Prompt Context List of teams or overview of club teams.",
        "staff": f"User Prompt Context List or General Information about Coaches, Admins and Staff.",
        "notifications": f"User Prompt Context Updates or Real-Time updates and information.",
    }


if __name__ == "__main__":
    print(RaiBaseFunctions.pipeline("categorize_sports", sub=True))
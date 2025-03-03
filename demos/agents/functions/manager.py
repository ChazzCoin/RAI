from typing import overload

from F import DICT

from rai.assistant.Tools import find_RaiFunction, getFunctionJsonNoArgs
from rai.assistant.connectors import rAI





class RaiFunctionManager:
    """
    A manager for dynamically creating and storing function definitions
    by categorized lists. Includes placeholders for database integration.
    """
    ai = rAI('openai')
    context = ""
    prefix = "Prompt Context Involves"

    def __init__(self, context:str, prefix=None):
        self.context = context
        if prefix: self.prefix = prefix

        # Each category holds a list of function definitions
        # Key = category name (str), Value = list of function definition dicts
        self.categories = {}

        # Initialize categories
        self.init_function_categories()  # "ysc_categories"
        self.init_website_categories()  # "youth_website_categories"

        # You can also define a separate category for "other" or "misc" if needed.
        # For example: self.categories["misc"] = []

        # Example: a built-in category for any single “global” or “common” functions
        self.categories["global"] = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Call whenever the user is looking or requesting weather information about a particular location.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The Location of the Users Request for Weather."
                            }
                        },
                        "required": ["location"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

    #########################
    # Category Initializers
    #########################
    @overload
    def generate(self, data: str, functions: [dict]):
        return self.ai.generate_function(
            data,
            f"""
            **OVERALL PURPOSE**:
            Your goal is to identify relevant function calls from the provided function definitions ("functions") based on the user's prompt.
            **OVERALL CONTEXT**:
            {self.context}
            **OBJECTIVE**:
            - Treat each function name in the "functions" list as a Topic/Category.
            - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
            - Return the function calls (in a specific format) that match the user's needs.
            """,
            functions
            )

    def generate(self, data: str, category_name: str):
        return self.ai.generate_function(
            data,
            f"""
            **OVERALL PURPOSE**:
            Your goal is to identify relevant function calls from the provided function definitions ("functions") based on the user's prompt.
            **OVERALL CONTEXT**:
            {self.context}
            **OBJECTIVE**:
            - Treat each function name in the "functions" list as a Topic/Category.
            - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
            - Return the function calls (in a specific format) that match the user's needs.
            """,
            self.get_category(category_name)
            )

    @overload
    async def generate_async(self, data: str, functions: [dict]):
        return await self.ai.generate_function_async(
            data,
            f"""
            **OVERALL PURPOSE**:
            Your goal is to identify relevant function calls from the provided function definitions ("functions") based on the user's prompt.
            **OVERALL CONTEXT**:
            {self.context}
            **OBJECTIVE**:
            - Treat each function name in the "functions" list as a Topic/Category.
            - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
            - Return the function calls (in a specific format) that match the user's needs.
            """,
            functions
        )

    async def generate_async(self, data: str, functions: str):
        return await self.ai.generate_function_async(
            data,
            f"""
            **OVERALL PURPOSE**:
            Your goal is to identify relevant function calls from the provided function definitions ("functions") based on the user's prompt.
            **OVERALL CONTEXT**:
            {self.context}
            **OBJECTIVE**:
            - Treat each function name in the "functions" list as a Topic/Category.
            - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
            - Return the function calls (in a specific format) that match the user's needs.
            """,
            self.get_category(functions)
        )

    def init_function_categories(self, category_name="ysc_primary"):
        """
        Build or load the Youth Soccer Club categories and store them
        in self.categories[category_name].
        """
        self.categories[category_name] = self.build_function_list(self.ysc_primary())

    def init_website_categories(self, category_name="ysc_secondary"):
        """
        Build or load the Youth Soccer Website categories and store them
        in self.categories[category_name].
        """
        self.categories[category_name] = self.build_function_list(self.ysc_secondary())

    #########################
    # Public Category Methods
    #########################

    def add_category(self, category_name: str) -> None:
        """
        Create a new empty category if it doesn’t exist.
        """
        if category_name not in self.categories:
            self.categories[category_name] = []

    def remove_category(self, category_name: str) -> bool:
        """
        Remove a category entirely (with all its functions).
        Returns True if found, False otherwise.
        """
        if category_name in self.categories:
            del self.categories[category_name]
            return True
        return False

    def get_category(self, category_name: str):
        """
        Retrieve the list of functions for a given category.
        Returns None if category does not exist.
        """
        return self.categories.get(category_name)

    #########################
    # Managing Functions
    #########################

    def add_function_to_category(
            self, category_name: str, name: str, description: str,
            properties: dict = None, required_fields: list = None
    ) -> None:
        """
        Dynamically add a new function definition to a specific category.
        If the category doesn’t exist, create it.
        """
        if category_name not in self.categories:
            self.categories[category_name] = []

        if properties and required_fields:
            function_def = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required_fields,
                        "additionalProperties": False
                    }
                }
            }
        else:
            # If no properties exist, treat it as a no-arguments function.
            function_def = getFunctionJsonNoArgs(name, description)

        self.categories[category_name].append(function_def)

    def remove_function_from_category(self, category_name: str, function_name: str) -> bool:
        """
        Remove a function by name from a specific category.
        Returns True if the function was found and removed.
        """
        if category_name not in self.categories:
            return False

        cat_list = self.categories[category_name]
        for i, func in enumerate(cat_list):
            existing_name = DICT.get("name", func, None)
            if existing_name == function_name:
                del cat_list[i]
                return True
        return False

    def find_function_in_category(self, category_name: str, function_name: str) -> dict:
        """
        Find a function dictionary by name within a specific category.
        Returns the dictionary if found, else None.
        """
        if category_name not in self.categories:
            return None

        return find_RaiFunction(function_name, self.categories[category_name])

    def list_all_functions(self) -> list:
        """
        Returns a flat list of *all* functions across all categories.
        """
        all_funcs = []
        for _, func_list in self.categories.items():
            all_funcs.extend(func_list)
        return all_funcs

    def build_function_list(self, function_dict:dict) -> list:
        return [ getFunctionJsonNoArgs(key, value) for key, value in function_dict.items() ]

    def ysc_primary(self):
        return {
            "tryout_registration": f"{self.prefix} tryouts, placements, registration or how to signup and get involved in the club. {self.context}",
            "uniforms_attire": f"{self.prefix} how to order or get their uniforms and other attire {self.context}",
            "tournaments": f"{self.prefix} tournament information {self.context}",
            "development_curriculum": f"{self.prefix} long term player and parent development models {self.context}",
            "policy_procedures": f"{self.prefix} police and the procedures the club adheres to {self.context}",
            "finance_payments": f"{self.prefix} payments finance cost {self.context}",
            "scholarship_programs": f"{self.prefix} scholarship programs that are available {self.context}",
            "facilities_locations": f"{self.prefix} fields, locations, office, facilities, directions {self.context}",
            "volunteers": f"{self.prefix} volunteer work, helping or getting involved as a parent {self.context}",
            "contact_information": f"{self.prefix} a persons/coach/admin/parent contact information, email, phone number, social tag. {self.context}",
            "roster_teams": f"{self.prefix} a team, teams, players, roster information. {self.context}",
            "events_schedules": f"{self.prefix} schedules and events around practices, games, tournaments, meetings, parties {self.context}",
        }
    def ysc_secondary(self):
        return {
            "admin": f"{self.prefix} general information about a team involving staff, coaches, players, events {self.context}",
            "summary": f"{self.prefix} general information about a team involving staff, coaches, players, events {self.context}",
            "events": f"{self.prefix} Calendar based events like practices, games, festivals, meetings, parties {self.context}",
            "practices": f"{self.prefix} Calendar or general information about team practices {self.context}",
            "games": f"{self.prefix} Calendar or general information about based team games {self.context}",
            "roster": f"{self.prefix} Players, Coaches, Parents, Managers, Staff involving a team or teams {self.context}",
            "teams": f"{self.prefix} List of teams or overview of club teams {self.context}",
            "staff": f"{self.prefix} List or General Information about Coaches, Admins and Staff. {self.context}",
            "notifications": f"{self.prefix} Updates or Real-Time updates and information. {self.context}",
        }

    #########################
    # Database placeholders
    #########################

    def load_functions_from_db(self, db_connection):
        """
        Placeholder to demonstrate how you'd load data from a DB.
        Adjust logic for your schema and DB driver (PyMySQL, psycopg2, SQLAlchemy, etc.).
        """
        # Example pseudo-code:
        # results = db_connection.query("SELECT category, name, description, properties, required FROM functions_table")
        # for row in results:
        #     self.add_function_to_category(
        #         category_name=row["category"],
        #         name=row["name"],
        #         description=row["description"],
        #         properties=row["properties"],
        #         required_fields=row["required"]
        #     )
        pass

    def save_functions_to_db(self, db_connection):
        """
        Placeholder to demonstrate how you'd save the current function categories to a DB.
        """
        # Example pseudo-code:
        # for category_name, func_list in self.categories.items():
        #     for func_def in func_list:
        #         name = DICT.get("name", func_def, None)
        #         description = DICT.get("description", func_def, None)
        #         parameters = DICT.get("parameters", DICT.get("function", func_def, {}), {})
        #         properties = parameters.get("properties", {})
        #         required_fields = parameters.get("required", [])
        #
        #         # Insert/update logic, including the category_name, name, description, etc.
        pass

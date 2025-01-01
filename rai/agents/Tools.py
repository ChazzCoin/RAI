from F import DICT

PreFix = "Prompt Context Involves"
YSC_Context = "Youth Soccer Club"
def getFuncProperty(type, desc):
    return {
        "type": type,
        "description": desc
    }
FuncPropertyBoolean = {
  "type": "boolean",
  "description": "True/False if the user context is discussing the function description."
}
FuncPropertyString = {
  "type": "string",
  "description": "string value"
}
FuncPropertyInt = {
  "type": "integer",
  "description": "integer value"
}
FuncProperty = lambda property_name, property_type: {
    property_name: property_type
}
def getFunctionJson(name, description, property_name, property_type) -> dict:
    return {
      "type": "function",
      "function": {
          "name": name,
          "description": description,
          "parameters": {
              "type": "object",
              "properties": {
                  property_name: property_type,
              },
              "required": [property_name],
              "additionalProperties": False,
          },
      },
  }
def getFunctionJsonNoArgs(name, description) -> dict:
    return {
      "type": "function",
      "function": {
          "name": name,
          "description": description
      },
  }
def find_RaiFunction(name:str, rai_functions:[]):
    for func in rai_functions:
        func_name = DICT.get("name", func, None)
        if func_name:
            if func_name == name:
                return func
    return None
# Step 1: Define the dictionary dynamically
def build_function_dict(ysc_context, pre_fix=PreFix, ):
    function_dict = {
        "tryout_registration": f"{pre_fix} tryouts, placements, registration or how to signup and get involved in the club. {ysc_context}",
        "uniforms_attire": f"{pre_fix} how to order or get their uniforms and other attire {ysc_context}",
        "tournaments": f"{pre_fix} tournament information {ysc_context}",
        "development_curriculum": f"{pre_fix} long term player and parent development models {ysc_context}",
        "policy_procedures": f"{pre_fix} police and the procedures the club adheres to {ysc_context}",
        "finance_payments": f"{pre_fix} payments finance cost {ysc_context}",
        "scholarship_programs": f"{pre_fix} scholarship programs that are available {ysc_context}",
        "facilities_locations": f"{pre_fix} fields, locations, office, facilities, directions {ysc_context}",
        "volunteers": f"{pre_fix} volunteer work, helping or getting involved as a parent {ysc_context}",
        "contact_information": f"{pre_fix} a persons/coach/admin/parent contact information, email, phone number, social tag. {ysc_context}",
        "roster_teams": f"{pre_fix} a team, teams, players, roster information. {ysc_context}",
        "events_schedules": f"{pre_fix} schedules and events around practices, games, tournaments, meetings, parties {ysc_context}",
    }
    return function_dict

# Step 2: Define a function to dynamically build the list
def build_rai_function_categories(ysc_context, pre_fix=PreFix):
    function_dict = build_function_dict(ysc_context, pre_fix)
    rai_function_categories = [
        getFunctionJsonNoArgs(key, value) for key, value in function_dict.items()
    ]
    return rai_function_categories

RaiFunctionCategories = build_rai_function_categories(YSC_Context)



RaiFunctions = [

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
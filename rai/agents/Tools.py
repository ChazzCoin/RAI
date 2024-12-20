from F import DICT

PreFix = "Whenever a user is asking about"
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

RaiFunctionCategories = [
    getFunctionJsonNoArgs(
        "tryout_registration",
        f"{PreFix} tryouts, placements, registration or how to signup and get involved in the club. {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
    "uniforms_attire",
    f"{PreFix} how to order or get their uniforms and other attire {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "tournaments",
        f"{PreFix} tournament information {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "development_curriculum",
        f"{PreFix} long term player and parent development models {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "policy_procedures",
        f"{PreFix} police and the procedures the club adheres to {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "finance_payments",
        f"{PreFix} payments finance cost {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "scholarship_programs",
        f"{PreFix} scholarship programs that are available {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "facilities_locations",
        f"{PreFix} fields, locations, office, facilities, directions {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "volunteers",
        f"{PreFix} volunteer work, helping or getting involved as a parent {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "contact_information",
        f"{PreFix} a persons/coach/admin/parent contact information, email, phone number, social tag. {YSC_Context}"
    ),
    getFunctionJsonNoArgs(
        "events_schedules",
        f"{PreFix} schedules and events around practices, games, tournaments, meetings, parties {YSC_Context}"
    )
]



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
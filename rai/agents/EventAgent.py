from typing import Optional, Dict
from pydantic import BaseModel

from rai.assistant.connectors import RaiAi
# Initialize OpenAI API key
ai = RaiAi('openai')

class EventFormat(BaseModel):
    name: Optional[str]
    date: Optional[str]
    time: Optional[str]
    details: Optional[str]

class EventExtractor:
    def __init__(self, default_model: str):
        self.default_model = default_model

    def generate_format(self, user: str, system: str):
        try:
            response = ai.get_engine().generate_format(
                user=user,
                system=system,
                format=EventFormat
            )
            return response
        except Exception as e:
            print(e)
            return "Uh oh. Something has gone wrong!"

    def format_markup(self, event: EventFormat) -> str:
        """
        Generate a clean, modern, and professional markup for the extracted event.
        """
        if not event:
            return "<div>No event details found.</div>"

        return f"""
        <div style='font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9;'>
            <h2 style='color: #333;'>Event Details</h2>
            <p><strong>Date:</strong> {event.date or 'N/A'}</p>
            <p><strong>Time:</strong> {event.time or 'N/A'}</p>
            <p><strong>Details:</strong> {event.details or 'N/A'}</p>
        </div>
        """

if __name__ == "__main__":
    # Initialize the extractor with the desired model
    extractor = EventExtractor(default_model="gpt-4o")

    # Example system prompt and user input
    system_prompt = "Extract event details from the user's text and format it as a JSON object with keys `name`, `date`, `time`, and `details`. Return null for missing fields."
    user_input = "Join us for the team meeting on March 3rd, 2024, at 5 PM. We'll meet at the HQ conference room to discuss next quarter's strategy."

    # Generate and format the response
    formatted_event = extractor.generate_format(user_input, system_prompt)
    print(formatted_event)
    if formatted_event:
        markup = extractor.format_markup(formatted_event)
        print(markup)
    else:
        print("<div>No event details found.</div>")

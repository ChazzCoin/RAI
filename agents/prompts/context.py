
SOCCER_CLUB_CONTEXT_EXPANDER = lambda previous_messages: f"""
1. Add keywords to add context to users questions.
2. Keywords should be based on youth soccer organizations and clubs.
3. If the question has enough context, just return it back unmodified.
4. Use previous messages accordingly.

Examples: 
- If they are asking about a persons name, 'coach', 'staff' and other keywords should be added.
- "coach" = staff, employee, director
- "fee" = money, cost, costs, annual fees, fees, payment
- "field" = complex, fields, stadium, location

PREVIOUS USER INPUTS/QUESTIONS FOR BETTER CONTEXT:
{reversed(previous_messages) if isinstance(previous_messages, list) else previous_messages}

RESPONSE RULE: Only return the Users Input with keywords and nothing else.
"""


MEDICAL_CONTEXT_EXPANDER = lambda previous_messages: f"""
1. Add keywords to add context to users questions.
2. Keywords should be based on medicine, medical, doctors.
3. If the question has enough context, just return it back unmodified.
4. Use previous messages accordingly.

Examples: 
None

PREVIOUS USER INPUTS/QUESTIONS FOR BETTER CONTEXT:
{reversed(previous_messages) if isinstance(previous_messages, list) else previous_messages}

RESPONSE RULE: Only return the Users Input with keywords and nothing else.
"""
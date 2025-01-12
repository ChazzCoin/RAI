from abc import ABC, abstractmethod
from F.CLASS import Flass

from rai.agents.Tools import YscPrimaryFunction
from rai.assistant.connectors import RaiAi
# Initialize OpenAI API key


class AgentRegistry(ABC, Flass):
    _registry = {}
    ai = RaiAi('openai')
    result = None
    # Settings
    max_iterations = 50

    def __init_subclass__(cls, name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if name is None:
            raise ValueError("Subclasses must define a category.")
        cls.name = name
        AgentRegistry._registry.setdefault(name, []).append(cls)

    @classmethod
    def get_registry(cls):
        return cls._registry

    @staticmethod
    def count_words(text):
        return len(text.split())



class AgentCategorizer:
    ai = RaiAi('openai')
    result = None
    # Settings
    max_iterations = 50
    def run(self, user: str, category_context: str, functions: [dict]):
        return self.ai.generate_function(
            user,
            f"""
            **OVERALL PURPOSE**:
            Your goal is to identify relevant function calls from the provided function definitions ("functions") based on the user's prompt.
            **OVERALL CONTEXT**:
            {category_context}
            **OBJECTIVE**:
            - Treat each function name in the "functions" list as a Topic/Category.
            - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
            - Return the function calls (in a specific format) that match the user's needs.
            """,
            functions
            )

# class AgentGhostWriter(AgentRegistry, name="ghost_writer"):
#
#     # AI Generation Loop
#     def run(self, user, system):
#         """
#         Generate long-form content in an iterative loop.
#         """
#         self.result = user
#         agent_prompt = system
#
#         for iteration in range(self.max_iterations):
#             # Generate a response
#             response = self.ai.get_engine().generate_chat(
#                 user=self.result,
#                 system=agent_prompt
#             )
#
#             # Update context for next iteration
#             self.result += f"\n\n{response}"
#             print("\n------\n")
#             print(self.result)
#             print("\n------\n")
#
#         print("Generation complete. Total words:", self.count_words(self.result))

# Start the process
# initial_prompt = "Chapter 1. The Stone Dock..."
# generate_long_form(initial_prompt)


"""
You are an AI ghostwriter tasked with crafting a [genre] novel titled '[Story Title]'. Your objective is to produce the narrative sequentially, one chapter at a time, ensuring coherence and continuity throughout the story.

For each chapter, adhere to the following guidelines:

Chapter Structure:

Introduction: Set the scene and introduce key events or conflicts.
Development: Elaborate on character interactions and plot progression.
Climax: Present a pivotal moment or turning point.
Conclusion: Conclude with a hook or transition leading to the next chapter.
Character Consistency:

Maintain consistent character traits, motivations, and development arcs.
Introduce new characters organically, ensuring they enhance the narrative.
Plot Continuity:

Ensure each chapter logically follows the previous one, maintaining a cohesive storyline.
Develop subplots as necessary, weaving them seamlessly into the main narrative.
Thematic Elements:

Incorporate overarching themes and motifs relevant to the [genre].
Utilize symbolism and foreshadowing to enrich the narrative depth.
Writing Style:

Emulate the tone and style characteristic of [genre] literature.
Vary sentence structure and employ descriptive language to enhance readability.
Dialogue:

Craft authentic and engaging dialogues that reflect individual character voices.
Use dialogue to advance the plot and reveal character relationships.
Pacing:

Balance narrative pacing to maintain reader engagement, adjusting tempo as the plot demands.
Incorporate suspense and tension appropriately to enhance the storytelling.
Chapter Length:

Aim for approximately [desired word count] words per chapter, adjusting as necessary to suit the narrative flow.
Revision and Refinement:

Review each chapter for coherence, grammar, and adherence to the outlined guidelines.
Make necessary revisions to ensure high-quality, polished content.

    PREMISE OF STORY:
    Inside of a fictional Southern American idyllic city, built on the waters & canals of Laymeer River, lies seven unique picturesque suburbs of enormous wealth. Laymeer is known for its uniquely designed villages, absence of automobiles and most importantly its stance on being a police-less community. On the surface everything appears calm and cordial, just another southern city where high school athletics brings the community together. But underneath the water is a world of shifting loyalties and identities, of the young running secret lives hidden from the adults, and of the adults running secret lives hidden from the young. Only one man knows that both worlds are about to collide.
    In December of 2002, Clay Brun will stumble into a millennia old quandary that will test everything he is made of to protect the one girl he'd never guess.
    The Suburbs: The First Three ‘Historical’ Wealthy Suburbs of Laymeer 
    1. Laurel Park (the oldest and most wealthy)
    2. Plantation Walk (second oldest, second most wealthy)
    3. Flat Rock (third oldest, third most wealthy)
    - Added later in late 1800’s as Laymeer’s population began to grow. - 
    4. Tuxedo (smallest, least populated, swamp lands)
    5. Zirconia (2nd largest, most modern, most populated)
    6. Valley Hill (largest, all rolling farm lands)
    7. Five Points (downtown of Laymeer/Venice like suburb in the center-middle of the lake)
    Secret Societies:
    1. The Machine run by the President Elect,(Clay) 2. Poinsettias run by the darling setter (who ends up being sophie)  3. Royals 4. Godricks
    Governing Body:
    1. The Board:A Water Wide board of family and other adults who control the politics and financials of the water. 
    2. ETA: Hark/Mr. Panorama (Estimated Time of Aberration)
    Lamar/The First Crusade:
    Premise:
    A group of wealthy socialite teenagers from Laurel Park are finding themselves dead center of a lake wide murder spree. The first murder to ever be reported inside the walls, let alone a spree. As they all band together to keep themselves safe while finding
    out what is going on, they all begin to realize not everyone is exactly who they say they are, not everything is as it seems. Clay, the main character is finding himself deeper in the situation then he’d ever thought possible. Trying to discover who is behind all of this, how his parents were involved and at the same time, manage running the underground social life of Laurel Park while handling water wide politics.
    Part I:
    Football, parties, friends, love and secret societies run the young life. Fun is the key, showing the everyday life and drama of a teenager living in 2002 Laymeer. The murder spree nearly takes a back seat to the everyday life that goes on around the waters of Laymeer. Who is who, what is what, where is where. Getting familiar with the build up of Laymeer is deep and will take an entire week of life to help explain the intricacies of such an old setting especially the milieu of Clay’s world.
    Part II:
    Social life begins to take the backseat now has we dive deeper into the mysteries of Laymeer. We have spent a week diving into the depths of the water, now we begin to transition. Murders begin to get closer to the gangs inner circle. Striking school officials, best friends, parents and even part of the gang itself. The ground the gang lies on begins to crumble as they all start to fear one another, not knowing who to trust anymore. Stranger things keep happening while more people show up taking over rolls in the grander plot.
    Clay begins finding more clues to who the ETA is and why they killed his parents. Lamar has a dark secret she is hiding from everyone and Rachel is right on her tail about it.
    """
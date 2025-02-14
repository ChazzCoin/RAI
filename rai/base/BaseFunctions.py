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
@register_functions("industry")
class BaseFunctionIndustry(RaiBaseFunctions):
    def type(self):
        return "no_args"

    def functions(self) -> dict:
        return {
            "sports": "User Prompt Context Involves Sports-Related Queries",
            "medical": "User Prompt Context Involves Medical or Health-Related Queries",
            "law":    "User Prompt Context Involves Legal or Law-Related Queries"
        }
    def sub_functions(self) -> dict: return {}


@register_functions("sports")
class BaseFunctionSports(RaiBaseFunctions):
    def type(self):
        return "no_args"

    def functions(self) -> dict:
        return {
            "soccer":   "User Prompt Context Involves Soccer",
            "baseball": "User Prompt Context Involves Baseball",
            "football": "User Prompt Context Involves Football"
        }
    def sub_functions(self) -> dict: return {}

@register_functions("medical")
class BaseFunctionMedical(RaiBaseFunctions):
    def type(self):
        return "no_args"

    def functions(self) -> dict:
        return {
            "neuro":      "User Prompt Context Involves Neurology/Brain-Related Topics",
            "cardiology": "User Prompt Context Involves Cardiology/Heart-Related Topics",
            "optometry":  "User Prompt Context Involves Optometry/Eye-Related Topics"
        }
    def sub_functions(self) -> dict: return {}

@register_functions("law")
class BaseFunctionLaw(RaiBaseFunctions):
    def type(self):
        return "no_args"

    def functions(self) -> dict:
        return {
            "criminal":  "User Prompt Context Involves Criminal Law",
            "civil":     "User Prompt Context Involves Civil Law",
            "corporate": "User Prompt Context Involves Corporate Law"
        }
    def sub_functions(self) -> dict: return {}

@register_functions("text_sentiment")
class BaseFunctionSentiment(RaiBaseFunctions):
    def type(self):
        return "no_args"

    def functions(self) -> dict:
        return {
            "extremely_positive": "Exuberant tone with high enthusiasm and optimism.",
            "positive": "Clearly favorable sentiment reflecting optimism and satisfaction.",
            "mildly_positive": "Subtly optimistic with a gentle, positive undertone.",
            "neutral": "Balanced tone without strong emotional cues.",
            "mildly_negative": "Slightly pessimistic sentiment with subtle discontent.",
            "negative": "Clearly unfavorable sentiment with noticeable dissatisfaction.",
            "extremely_negative": "Overwhelmingly negative tone with intense disapproval.",
            "mixed": "Conveys conflicting sentiments, blending both positive and negative elements."
        }

    def sub_functions(self) -> dict: return {}

@register_functions("document_type")
class BaseFunctionDocumentContent(RaiBaseFunctions):
    def sub_functions(self) -> dict:
        pass

    def type(self):
        return "no_args"

    def functions(self) -> dict:
        return {
            "pdf": (
                "User Prompt Context Involves processing PDF documents. "
                "This includes extracting text layers, handling embedded images, "
                "annotations, and metadata. It supports both native PDFs and scanned "
                "documents by integrating OCR to accurately extract text from image-based content."
            ),
            "webpage": (
                "User Prompt Context Involves parsing webpage content. "
                "It extracts main text, metadata (such as title, description, and keywords), "
                "structured data (e.g., schema.org annotations), and embedded media. "
                "The process filters out navigational elements and advertisements to ensure content integrity."
            ),
            "image": (
                "User Prompt Context Involves processing image files for content extraction. "
                "This may include applying OCR to extract any embedded text, analyzing EXIF metadata, "
                "and detecting visual elements (e.g., diagrams, charts) to index images for context-aware retrieval."
            ),
            "scanned_document": (
                "User Prompt Context Involves handling scanned documents. "
                "Advanced OCR techniques are used alongside noise reduction and layout analysis "
                "to reconstruct the text accurately and preserve the original formatting of the document."
            ),
            "word_document": (
                "User Prompt Context Involves processing Microsoft Word documents (.doc/.docx). "
                "This includes extracting rich text content, preserving formatting, handling embedded objects, "
                "and capturing metadata such as authorship and revision history for comprehensive content querying."
            ),
            "spreadsheet": (
                "User Prompt Context Involves processing spreadsheet files (e.g., Excel). "
                "It extracts structured tabular data, including formulas, cell formatting, and multiple sheets, "
                "transforming the data into a query-friendly format while preserving relational context."
            ),
            "presentation": (
                "User Prompt Context Involves processing presentation files (e.g., PowerPoint). "
                "This includes extracting text from slides, speaker notes, embedded media, and slide layouts, "
                "ensuring that the narrative flow is maintained for effective content retrieval."
            ),
            "email": (
                "User Prompt Context Involves processing email communications. "
                "It extracts email headers (sender, recipient, subject), body text, attachments, and conversation threading, "
                "maintaining context for query purposes."
            ),
            "json": (
                "User Prompt Context Involves processing JSON documents. "
                "This function parses nested structures, normalizes key-value pairs, and extracts data "
                "to support flexible and precise querying of semi-structured content."
            ),
            "xml": (
                "User Prompt Context Involves processing XML documents. "
                "It parses hierarchical data, extracts element text and attributes, and converts structured information "
                "into a format that is conducive to effective query operations."
            ),
            "audio_transcript": (
                "User Prompt Context Involves processing transcripts generated from audio sources. "
                "This includes handling time-coded text, speaker segmentation, and contextual markers, "
                "ensuring that the spoken content is accurately represented for retrieval."
            ),
            "video_caption": (
                "User Prompt Context Involves processing video caption files. "
                "It extracts caption text along with timing information and speaker identification, "
                "facilitating precise indexing and context-aware retrieval of video content."
            ),
        }


@register_functions("topic_sports")
class BaseFunctionTopicSports(RaiBaseFunctions):
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

@register_functions("topic_medical")
class BaseFunctionTopicMedical(RaiBaseFunctions):
    def type(self): return "no_args"
    def functions(self) -> dict: return {
        "tryout_registration": f"User Prompt Context Involves tryouts, placements, registration or how to signup and get involved in the club.",
    }
    def sub_functions(self) -> dict: return {
        "admin": f"User Prompt Context general information about a team involving staff, coaches, players, events.",
        "summary": f"User Prompt Context general information about a team involving staff, coaches, players, events.",
        "events": f"User Prompt Context Calendar based events like practices, games, festivals, meetings, parties.",
        "staff": f"User Prompt Context List or General Information about Coaches, Admins and Staff.",
        "notifications": f"User Prompt Context Updates or Real-Time updates and information.",
    }

@register_functions("topic_law")
class BaseFunctionTopicLaw(RaiBaseFunctions):
    def type(self): return "no_args"
    def functions(self) -> dict: return {
        "tryout_registration": f"User Prompt Context Involves tryouts, placements, registration or how to signup and get involved in the club.",
    }
    def sub_functions(self) -> dict: return {
        "admin": f"User Prompt Context general information about a team involving staff, coaches, players, events.",
        "summary": f"User Prompt Context general information about a team involving staff, coaches, players, events.",
        "events": f"User Prompt Context Calendar based events like practices, games, festivals, meetings, parties.",
        "staff": f"User Prompt Context List or General Information about Coaches, Admins and Staff.",
        "notifications": f"User Prompt Context Updates or Real-Time updates and information.",
    }

@register_functions("objective")
class BaseFunctionObjective(RaiBaseFunctions):
    def type(self): return "no_args"
    def functions(self) -> dict: return {
        "how_to_guide": "User Prompt Context Involves asking how to do something, offering a step-by-step guide or detailed breakdown of a process.",
        "find_search": "User Prompt Context Involves seeking out specific information, facts, or resources relevant to a user's query.",
        "summarize": "User Prompt Context Involves condensing a broader topic or source text into a concise and coherent overview.",
        "explain": "User Prompt Context Involves providing an in-depth elucidation or rationale for a particular concept or subject.",
        "clarify": "User Prompt Context Involves resolving ambiguities, simplifying complexities, and adding precision to a user's request.",
        "create": "User Prompt Context Involves generating new content, whether through code, written text, or other creative outputs."
    }
    def sub_functions(self) -> dict: return {
        "step_by_step_tutorial": "User Prompt Sub-Objective Involves providing a methodical, phase-by-phase guide for completing a task.",
        "quick_tips_best_practices": "User Prompt Sub-Objective Involves offering concise lists of essential pointers and tried-and-true methods.",
        "troubleshooting_error_resolution": "User Prompt Sub-Objective Involves identifying pitfalls or mistakes and providing practical fixes or workarounds.",
        "workflow_optimization": "User Prompt Sub-Objective Involves improving efficiency or productivity within existing workflows or processes.",
        "demonstration_with_examples": "User Prompt Sub-Objective Involves illustrating concepts or solutions through practical, real-world examples.",

        "resource_retrieval": "User Prompt Sub-Objective Involves locating and sharing relevant documentation, articles, or libraries.",
        "fact_finding": "User Prompt Sub-Objective Involves seeking specific data, statistics, or factual details.",
        "comparative_search": "User Prompt Sub-Objective Involves comparing information across multiple sources or options.",
        "recommendation": "User Prompt Sub-Objective Involves suggesting tools, products, or services based on certain criteria.",
        "location_reference_lookup": "User Prompt Sub-Objective Involves finding location-based data, references, or materials.",

        "high_level_overview": "User Prompt Sub-Objective Involves condensing a broader topic into a concise abstract or summary.",
        "bullet_point_breakdown": "User Prompt Sub-Objective Involves creating a succinct list of critical takeaways or highlights.",
        "key_insights_highlights": "User Prompt Sub-Objective Involves focusing on the most impactful or defining points in a subject.",
        "executive_summary": "User Prompt Sub-Objective Involves crafting an ultra-condensed overview for quick comprehension at a decision-making level.",
        "comparative_summary": "User Prompt Sub-Objective Involves merging multiple perspectives into one cohesive, concise summary.",

        "conceptual_breakdown": "User Prompt Sub-Objective Involves dissecting a topic into easily digestible, fundamental concepts.",
        "in_depth_analysis": "User Prompt Sub-Objective Involves exploring deeper reasoning, logic, or mechanics behind a concept.",
        "analogy_based_explanation": "User Prompt Sub-Objective Involves simplifying complex ideas through relatable metaphors or comparisons.",
        "contextualized_scenario": "User Prompt Sub-Objective Involves providing real-life examples or situations for clarity.",
        "advanced_vs_beginner_explanation": "User Prompt Sub-Objective Involves toggling between technical and simple explanations.",

        "definition_terminology": "User Prompt Sub-Objective Involves clarifying or refining the meaning of keywords or phrases.",
        "disambiguation": "User Prompt Sub-Objective Involves distinguishing between similar terms or topics to remove confusion.",
        "context_reframing": "User Prompt Sub-Objective Involves reinterpreting the question or data to ensure correct scope.",
        "error_correction": "User Prompt Sub-Objective Involves identifying and fixing inaccurate assumptions in the user’s request.",
        "rephrase_simplify": "User Prompt Sub-Objective Involves converting complex language into more direct, understandable wording.",

        "idea_generation": "User Prompt Sub-Objective Involves brainstorming or outlining fresh concepts, approaches, or creative angles.",
        "content_production": "User Prompt Sub-Objective Involves generating new written or multimedia assets (articles, videos, etc.).",
        "code_snippet_prototype": "User Prompt Sub-Objective Involves creating sample code or minimal working examples for demonstration.",
        "design_layout": "User Prompt Sub-Objective Involves producing visual elements, UI/UX mockups, or overall page layouts.",
        "customized_examples_demos": "User Prompt Sub-Objective Involves tailoring examples or demos specifically to the user’s unique requirements."
    }



if __name__ == "__main__":
    print(RaiBaseFunctions.pipeline("categorize_sports", sub=True))
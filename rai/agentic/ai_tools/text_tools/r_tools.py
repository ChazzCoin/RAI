
from rai.assistant.connectors import register_text_tool, rAI

class rTextTools(rAI): pass

"""
These seem to be turning into Configurations for agents.
What they do, how they do it...what they need...etc...
- remove term of service issues
- summarize data
- 
"""
@register_text_tool("generate")
class AgentConfigGenerate(rTextTools):
    def type(self): return "generate"
    def parse(self, result): return result

@register_text_tool("rag")
class AgentConfigRAG(rTextTools):
    def type(self): return "generate"
    def parse(self, result): return result

@register_text_tool("paraphrase")
class AgentConfigParaphrase(rTextTools):
    def type(self): return "generate"
    def parse(self, result): return result

@register_text_tool("summarize")
class AgentConfigSummarize(rTextTools):
    def type(self): return "generate"
    def parse(self, result): return result

@register_text_tool("objective")
class AgentConfigObjective(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("objective-summary")
class AgentConfigObjectiveSummary(rTextTools):
    def type(self): return "generate"
    def parse(self, result) -> str: return str(result)

@register_text_tool("text_sentiment")
class AgentConfigTextSentiment(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("document_type")
class AgentConfigDocumentType(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("categorize_sports")
class AgentConfigCategorizeSports(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)
@register_text_tool("industry")
class AgentConfigCategorizeIndustry(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("sports")
class AgentConfigCategorizeSports(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("medical")
class AgentConfigCategorizeMedical(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("law")
class AgentConfigCategorizeLaw(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("topic_sports")
class AgentConfigTopicSports(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("topic_medical")
class AgentConfigTopicMedical(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_text_tool("topic_law")
class AgentConfigTopicLaw(rTextTools):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)


@register_text_tool("context_expander")
class AgentConfigPromptExpander(rTextTools):
    def type(self): return "format"
    def parse(self, result): return result.queries

@register_text_tool("metadata")
class AgentConfigMetadata(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try:
            return result.model_dump()
        except Exception as e:
            print(e)
            return {}

@register_text_tool("create-required-data")
class AgentConfigCreateRequiredData(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.data
        except Exception as e:
            print(e)
            return {}

@register_text_tool("extract-required-data")
class AgentConfigExtractRequiredData(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.data
        except Exception as e:
            print(e)
            return {}

@register_text_tool("chain-of-steps")
class AgentConfigChainOfStepsExtractor(rTextTools):
    def type(self): return "format"
    def parse(self, result): return result.chain_of_steps

@register_text_tool("form_extractor")
class AgentConfigFormExtractor(rTextTools):
    def type(self): return "format"
    def parse(self, result): return result

@register_text_tool("herbal")
class AgentConfigHerbal(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.herbs
        except: return result

@register_text_tool("next-step")
class AgentConfigHerbal(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.next_step_or_action
        except: return result

@register_text_tool("urls")
class AgentConfigUrls(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.urls
        except: return result
@register_text_tool("contextual_groups")
class AgentConfigContextualGroups(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.groups
        except: return result
@register_text_tool("faq")
class AgentConfigQuestionAnswer(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.faqs
        except: return result
@register_text_tool("is_event")
class AgentConfigIsEvent(rTextTools):
    def type(self): return "format"
    def parse(self, result): return result.answer

@register_text_tool("is_true")
class AgentConfigIsTrue(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        return result.answer or False

@register_text_tool("complete-objective")
class AgentConfigIsTrue(rTextTools):
    def type(self): return "generate"
    def parse(self, result):
        return result or "I was unable to complete the objective."

@register_text_tool("events")
class AgentConfigEvents(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.events
        except: return result

@register_text_tool("contacts")
class AgentConfigContacts(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.contacts
        except: return result
@register_text_tool("locations")
class AgentConfigLocations(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.locations
        except: return result
@register_text_tool("step_by_step")
class AgentConfigStepByStep(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.steps
        except: return result

@register_text_tool("separate_prompt")
class AgentConfigSeparatePrompt(rTextTools):
    def type(self): return "format"
    def parse(self, result):
        try: return result.prompts
        except: return result

@register_text_tool("subject")
class AgentConfigSubject(rTextTools):
    def type(self): return "format"
    def parse(self, result): return result.subject

@register_text_tool("rag_query_generator")
class AgentConfigRagQueryGenerator(rTextTools):
    def type(self): return "format"
    def parse(self, result): return result.queries

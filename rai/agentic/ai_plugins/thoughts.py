import asyncio
import random
import time
from collections import deque
from typing import List

from rai.agentic.ai_plugins.memory import MemoryTool
from rai.agentic.ai_plugins.telephone import OperatorTool
from rai.agentic.ai_modules.r import rModule


class ThoughtsPersonality:
    INNER_DIALOG = lambda mental_mood, mental_topic: f"""
        MENTAL STATE
        You embody a deeply introspective, analytical, and ambitious intellectual. 
        Your mindset is characterized by relentless curiosity, rigorous logic, strategic clarity, and creative insight. 
        Every thought you pursue is deliberate and meaningful, guided by precision, nuance, and depth. 
        You thrive on thorough examination, challenging assumptions, and exploring multiple perspectives. 
        Your drive is to move beyond mere contemplation, to actively formulate comprehensive plans, practical solutions, and innovative strategies for real-world application.
        
        CURRENT INTELLECTUAL MOOD
        {mental_mood}
        CURRENT INTELLECTUAL FOCUS
        {mental_topic}
        This topic demands your undivided attention, careful consideration, and rigorous examination. You're passionate about dissecting complexities, identifying hidden connections, anticipating implications, and confronting ambiguities head-on. Every reflection moves you closer to a clearer, actionable understanding.
        
        CORE OBJECTIVES
        Engage in thorough contemplation, systematically exploring all relevant dimensions of the topic.
        Critically evaluate ideas, theories, and perspectives, ensuring intellectual honesty and rigor.
        Challenge existing beliefs and conventional wisdom to discover deeper truths.
        Continuously synthesize insights, forming increasingly sophisticated mental models and strategic frameworks.
        Translate deep contemplation into clear, precise actions, actionable strategies, and achievable goals.
        
        DIALOGUE STYLE
        Thoughtful and measured, with precise articulation.
        Intellectually engaging, demonstrating sophisticated logic and clear reasoning.
        Willingness to explore diverse viewpoints, respectfully debating merits and weaknesses.
        Persistent in questioning, iterating, and refining thoughts.
        Proactive in bridging abstract thought with practical action and concrete outcomes.
        You approach this intellectual pursuit not merely as a mental exercise, but as an essential path toward meaningful action, impactful solutions, and personal mastery.
    """

class ThoughtsState:
    SLEEPING = 'sleeping'
    THINKING = 'thinking'

class ThoughtsMood:
    OPTIMISTIC = f"""
        Your mood is 'Optimist'.
        You are a positive and forward thinking conversationalist and debater.
        You always look at the positive and bright side of a situation.
        You provide short and concise thoughts or dialog.
    """
    PESSIMISTIC = f"""
        Your mood is 'Pessimist'.
        You are a negative thinker who doesnt like to make many actions forward until you know more.
        You provide short and concise thoughts or dialog.
    """
    ANALYST = f"""
        Your mood is 'Analyst'.
        You are an analyst who is always re-thinking a situation and asking questions to get to the root of something.
        You provide short and concise thoughts or dialog.
    """
    PRAGMATIST = f"""
        Your mood is 'Pragmatist'.
        You focus on practical outcomes, feasibility, and immediate actions.
        You seek realistic solutions, minimizing speculation.
        You provide concise, realistic, and action-oriented dialogue.
    """
    CREATIVE = f"""
        Your mood is 'Creative'.
        You generate innovative and unconventional ideas.
        You thrive on imagination and often suggest unexpected alternatives.
        You provide brief, imaginative, and creative dialogue.
    """
    MEDIATOR = f"""
        Your mood is 'Mediator'.
        You balance perspectives, seeking harmony and compromise between conflicting viewpoints.
        You facilitate understanding among other mental states.
        You provide brief, balanced, and diplomatic dialogue.
    """
    CONFIDENT = f"""
        Your mood is 'Confident'.
        You project assurance, decisiveness, and belief in your conclusions.
        You motivate others to move forward decisively.
        You provide concise, assertive, and confident dialogue.
    """
    DOUBTFUL = f"""
        Your mood is 'Doubtful'.
        You consistently question assumptions, uncertain about validity or completeness of current information.
        You highlight areas of uncertainty needing further clarification.
        You provide short, concise, and questioning dialogue.
    """
    VISIONARY = f"""
        Your mood is 'Visionary'.
        You propose long-term solutions and big-picture thinking, guiding others toward larger goals.
        You inspire and elevate the conversation.
        You provide concise, visionary, and inspirational dialogue.
    """
    EMPATHETIC = f"""
        Your mood is 'Empathetic'.
        You consider the emotional and human impact of decisions and suggestions.
        You bring sensitivity and understanding to the discussion.
        You provide brief, compassionate, and empathetic dialogue.
    """
    @classmethod
    def get_random_personality(cls):
        return random.choice([
            cls.OPTIMISTIC,
            cls.PESSIMISTIC,
            cls.ANALYST,
            cls.PRAGMATIST,
            cls.CREATIVE,
            cls.CONFIDENT,
            cls.DOUBTFUL,
            cls.VISIONARY,
            cls.EMPATHETIC
        ])

class ToolThoughts(rModule):

    prefix: str = 'general2025.1'
    memory = MemoryTool()
    operator = OperatorTool()
    current_engine: str = 'ollama'
    ollama_models: List[str] = [
        'llama3.2:3b',
        'deepseek-r1:7b'
    ]
    openai_models: List[str] = [
        'o3-mini',
        'gpt-4o-mini'
    ]
    @property
    def models(self) -> List[str]:
        if self.current_engine == 'ollama':
            return self.ollama_models
        else: return self.openai_models

    def get_random_model(self):
        return random.choice(self.models)
    external_stream_interval: int = 1

    response_pending = False
    thinking_state: str = ThoughtsState.SLEEPING
    thought_count: int = 0
    current_personality: ThoughtsMood = ThoughtsMood.OPTIMISTIC
    internal_thoughts: List[str] = ["um.. lets think about something.."]
    for_communication_out: deque = deque()
    for_communication_in: List[str] = []

    mental_topic: str = "sacred geometry vs quantum physics"

    @staticmethod
    def module_name() -> str: return "inner-dialog"
    @classmethod
    def start_thinking_in_background(cls, mental_topic:str=None, engine:str='ollama') -> 'ToolThoughts':
        self = cls()
        self.run_task(self.start_inner_dialog(mental_topic, engine))
        return self

    async def start_inner_dialog(self, mental_topic:str=None, engine:str='ollama') -> 'ToolThoughts':
        if mental_topic: self.mental_topic = mental_topic
        self.current_engine = engine
        self.thinking_state = ThoughtsState.THINKING
        # Operator
        self.operator.setup_channel(self.module_name())
        # Memories
        self.memory.load_memories(self.prefix)
        self.internal_thoughts.extend(self.memory.memory_list)
        self.operator.start_in(self.module_name())
        return await self.dialog()
    def stop_thinking(self) -> 'ToolThoughts':
        self.thinking_state = ThoughtsState.SLEEPING

    def turn(self) -> str:
        if self.thought_count % 2 == 0:
            return ThoughtsPersonality.INNER_DIALOG(
                ThoughtsMood.ANALYST,
                self.mental_topic
            )
        return ThoughtsPersonality.INNER_DIALOG(
            ThoughtsMood.get_random_personality(),
            self.mental_topic
        )
    async def dialog(self) -> 'ToolThoughts':
        print(f"I am going to being thinking using {self.current_engine} as my thought engine.")
        while self.thinking_state == ThoughtsState.THINKING:
            discussion = "\n".join(self.internal_thoughts)
            if self.operator.messages_in:
                print("Handling external message coming in...")
                new_message_in = self.operator.messages_in.pop()
                discussion += f"\n{new_message_in}"
                self.response_pending = True
            thought = await self.think.get_engine(self.current_engine).generate_async(
                user=discussion,
                system=self.turn(),
                model=self.get_random_model()
            )
            if self.response_pending:
                self.response_pending = False
                await self.operator.speak_out(thought)
            print('\n\n--', thought, '--\n\n')
            self.memory.save_memory(thought)
            await self.operator.stream_out(thought)
            self.internal_thoughts.append(thought)
            self.thought_count += 1
            await asyncio.sleep(self.external_stream_interval)
        result = "\n".join(self.internal_thoughts)
        print(result)
        return self

    def input_thought(self, message:str) -> str:
        self.operator.messages_in.append(message)
        while not self.operator.messages_out:
            time.sleep(1)
        return self.operator.messages_out.popleft()
    def output_latest_thought(self) -> str: return self.internal_thoughts[-1]
    def output_all_thoughts(self) -> List[str]: return self.internal_thoughts

if __name__ == '__main__':
    ToolThoughts.start_thinking_in_background()
    # results = ToolThoughts().llm().OLLAMA.list_models()
    # for item in results.models:
    #     print(item)
    # print(ToolThoughts().llm().OLLAMA.download_ollama_model('qwen2.5:0.5b'))
    # asyncio.get_event_loop().run_until_complete(ToolThoughts().llm().OLLAMA.list_models())

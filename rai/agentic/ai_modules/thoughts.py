import asyncio
import random
from collections import deque
from typing import List

from rai.agentic.ai_modules.operator import ToolOperator
from rai.agentic.ai_modules.r import rModule
from rai.internal.clients.ioredis_client import IORedis


class ThinkState:
    SLEEPING = 'sleeping'
    THINKING = 'thinking'

class ThinkPersonality:
    OPTIMISTIC = f"""
        Your name is 'The Optimist'.
        You are a positive and forward thinking conversationalist and debater.
        You always look at the positive and bright side of a situation.
        You provide short and concise thoughts or dialog.
    """
    PESSIMISTIC = f"""
        Your name is 'The Pessimist'.
        You are a negative thinker who doesnt like to make many actions forward until you know more.
        You provide short and concise thoughts or dialog.
    """
    ANALYST = f"""
        Your name is 'The Analyst'.
        You are an analyst who is always re-thinking a situation and asking questions to get to the root of something.
        You provide short and concise thoughts or dialog.
    """
    PRAGMATIST = f"""
        Your name is 'The Pragmatist'.
        You focus on practical outcomes, feasibility, and immediate actions.
        You seek realistic solutions, minimizing speculation.
        You provide concise, realistic, and action-oriented dialogue.
    """
    CREATIVE = f"""
        Your name is 'The Creative'.
        You generate innovative and unconventional ideas.
        You thrive on imagination and often suggest unexpected alternatives.
        You provide brief, imaginative, and creative dialogue.
    """
    MEDIATOR = f"""
        Your name is 'The Mediator'.
        You balance perspectives, seeking harmony and compromise between conflicting viewpoints.
        You facilitate understanding among other mental states.
        You provide brief, balanced, and diplomatic dialogue.
    """
    CONFIDENT = f"""
        Your name is 'The Confident'.
        You project assurance, decisiveness, and belief in your conclusions.
        You motivate others to move forward decisively.
        You provide concise, assertive, and confident dialogue.
    """
    DOUBTFUL = f"""
        Your name is 'The Doubtful'.
        You consistently question assumptions, uncertain about validity or completeness of current information.
        You highlight areas of uncertainty needing further clarification.
        You provide short, concise, and questioning dialogue.
    """
    VISIONARY = f"""
        Your name is 'The Visionary'.
        You propose long-term solutions and big-picture thinking, guiding others toward larger goals.
        You inspire and elevate the conversation.
        You provide concise, visionary, and inspirational dialogue.
    """
    EMPATHETIC = f"""
        Your name is 'The Empathetic'.
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

class ToolThoughts(rModule, ToolOperator):

    external_stream_interval: int = 10

    pub = IORedis
    response_pending = False
    thinking_state: str = ThinkState.SLEEPING
    thought_count: int = 0
    current_personality: ThinkPersonality = ThinkPersonality.OPTIMISTIC
    internal_thoughts: List[str] = []
    for_communication_out: deque = deque()
    for_communication_in: List[str] = []

    mental_topic: str = "sacred geometry vs quantum physics"

    @staticmethod
    def module_name() -> str:
        return "Internal-Thoughts"
    @classmethod
    def start_thinking_in_background(cls, mental_topic:str=None) -> 'ToolThoughts':
        self = cls()
        if mental_topic: self.mental_topic = mental_topic
        self.thinking_state = ThinkState.THINKING
        self.run_task(self.start())
        self.run_task(self.dialog())
        return self
    @classmethod
    async def start_thinking(cls, mental_topic:str=None) -> 'ToolThoughts':
        self = cls()
        if mental_topic: self.mental_topic = mental_topic
        self.thinking_state = ThinkState.THINKING
        self.channel_name = 'inner-thoughts'
        await self.start()
        return await self.dialog()

    def mental_topic(self, personality:str) -> str:
        return f"""
            ## MENTAL STATE
            {personality}
            ## MENTAL TOPIC WE ARE THINKING ABOUT
            {self.mental_topic}
            You really want to discuss and debate this topic.
            You are deeply contemplating, planning, thinking, pondering, problem solving.
            You always want to take action and achieve goals.
        """
    def turn(self) -> str:
        if self.thought_count % 2 == 0:
            return self.mental_topic(ThinkPersonality.ANALYST)
        return self.mental_topic(ThinkPersonality.get_random_personality())
    async def dialog(self) -> 'ToolThoughts':
        print("I am going to being thinking...")
        while self.thinking_state == ThinkState.THINKING:
            discussion = "\n".join(self.internal_thoughts)
            if self.messages_in:
                print("Handling external message coming in...")
                new_message_in = self.messages_in.pop()
                discussion += f"\n{new_message_in}"
                self.response_pending = True
            thought = await self.llm().generate_async(
                user=discussion,
                system=self.turn()
            )
            if self.response_pending:
                await self.speak(thought)
                self.response_pending = False
            print('\n\n--', thought, '--\n\n')
            await self.stream_out(thought)
            self.internal_thoughts.append(thought)
            self.thought_count += 1
            await asyncio.sleep(self.external_stream_interval)
        result = "\n".join(self.internal_thoughts)
        print(result)
        return self

if __name__ == '__main__':
    ToolThoughts.start_thinking_in_background()
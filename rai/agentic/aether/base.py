from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional, Any, Union

from pydantic import BaseModel, Field, model_validator

from rai.agentic.aether.UseBrowser import BrowserUseTool
from rai.agentic.aether.aellm import AeLLM
from rai.agentic.aether.chat_completion import CreateChatCompletion
from rai.agentic.aether.schema import Memory, AgentState, Message, ROLE_TYPE, ToolCall
from rai.agentic.aether.terminate import Terminate
from rai.agentic.aether.tool_collection import ToolCollection
from rai.agentic.ai_modules import mAssistLog
from rai.agentic.ai_modules.data import mData
from rai.agentic.ai_modules.r import rModule

"""
Base Agent Functionality (engine)
"""
class BaseAgent(BaseModel, rModule, mData, mAssistLog,  ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    objective_is_complete: bool = False
    objective: Optional[str] = Field(
        default="You have not established the objective yet.",
        description="The goal or objective the agent is trying to achieve."
    )


    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    user_request_prompt: Optional[str] = Field(
        None,
        description="The users original prompt/request"
    )

    assistant_rules_tagged: Optional[str] = Field(
        default="You will do everything you can to accomplish the users request.",
        description="The agents rules and guidelines."
    )

    initial_request_tagged: Optional[str] = Field(
        None,
        description="Users requested tagged for AI generation."
    )

    int_documentation_tagged: Optional[str] = Field(
        None,
        description="Information about contextually relevant subjects."
    )

    # Dependencies
    ai: AeLLM = Field(
        default_factory=AeLLM,
        description="Language model instance"
    )
    memory: Memory = Field(
        default_factory=Memory,
        description="Agent's memory store"
    )
    state: AgentState = Field(
        default=AgentState.IDLE,
        description="Current agent state"
    )

    class Step(BaseModel):
        step: str
        index: int
        tools: List[ToolCall] = []
        result: Optional[str] = None

    steps_taken: List[Step] = Field(default=[], description="List of steps or actions that have been performed.")
    current_step: Optional[Step] = None
    required_data: Optional[Any] = None

    available_tools: ToolCollection = ToolCollection(
        BrowserUseTool(), Terminate(), CreateChatCompletion()
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step_count: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.ai is None or not isinstance(self.ai, AeLLM):
            self.ai = AeLLM()
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            self.state = previous_state  # Revert to previous state

    def update_memory(self, role: ROLE_TYPE, content: str, **kwargs) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        msg_factory = message_map[role]
        msg = msg_factory(content, **kwargs) if role == "tool" else msg_factory(content)
        self.memory.add_message(msg)

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously.
            Args: request: Optional initial user request to process.
            Returns: A string summarizing the execution results.
            Raises: RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            self.update_memory("user", request)
        self.initial_request_tagged = f"\n<USERS_REQUEST>\n{request}\n</USERS_REQUEST>\n"
        self.setup_assistant(request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (self.current_step_count < self.max_steps and self.state != AgentState.FINISHED):
                if self.current_step_count >= 2:
                    self.ask_if_objective_is_completed()
                    if self.objective_is_complete:
                        self.state = AgentState.FINISHED
                        break

                self.ask_to_generate_the_next_step()
                self.current_step_count += 1
                self.assistant_log(f"Executing step {self.current_step_count}/{self.max_steps}")
                step_result = await self.step()

                # Check for stuck state
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step_count}: {step_result}")

            if self.current_step_count >= self.max_steps:
                self.current_step_count = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        resp = self.ask_to_generate_final_response()
        return resp

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.
        Must be implemented by subclasses to define specific behavior.
        """

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        self.assistant_log(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @staticmethod
    def assistant_rules() -> str:
        return """
          Your name is AEther, you are an objective/goal oriented autonomous agent.
          You receive User Requests and you establish the objective and begin trying to achieve it.
        """

    def decision_prompt(self) -> str:
        return f"""
        Based on the User Prompt below, determine the best Function/Tool to select and call.
            <External Assistant Rules>
            {self.assistant_rules()}
            </External Assistant Rules>
            <ASSISTANT LOG>
            {self.get_assistant_log_str()}
            </ASSISTANT LOG>
        """

    def decide_objective_completion_prompt(self) -> str:
        # has_data = f"FLAG FOR IF WE HAVE DATA READY FOR THE USER: [ {self.has_data()} ]"
        return self.chain_data(self.get_assistant_log_str(), self.get_step_log_str(), self.objective)

    def generate_objective_prompt(self) -> str:
        return self.chain_data(
            self.assistant_rules_tagged,
            self.initial_request_tagged
        )

    def get_step_log_str(self):
        steps = ""
        for s in self.steps_taken:
            steps = self.chain_data(
                f"\n<STEP_TAKEN>\n{s.index}.{s.step}\n</STEP_TAKEN>\n",
                f"\n<STEP_TOOL>\n{s.index}.{s.tools}\n</STEP_TOOL>\n",
                f"\n<STEP_RESULT>\n{s.index}.{s.result}\n</STEP_RESULT>\n"
            )
        return steps
    def get_tools_document(self):
        return f"""
            <TOOLS_TO_PICK>
                {self.available_tools.to_params_str()} 
            </TOOLS_TO_PICK>
        """
    def format_next_step(self) -> str:
        return self.chain_data(
            self.assistant_rules_tagged,
            self.get_tools_document(),
            self.get_step_log_str(),
            self.objective,
            self.initial_request_tagged
        )
    def final_response_prompt(self) -> str:
        return self.chain_data(
            self.assistant_rules_tagged,
            self.get_assistant_log_str(),
            self.get_log_str("DATA"),
            self.objective,
            self.initial_request_tagged,
        )
    @staticmethod
    def _required_data_model_type() -> BaseModel:
        """Return the required data model for the assistant."""
        pass

    def setup_assistant(self, user_request: str):
        # The Assistant Process Log
        self.assistant_log("Setting up AEther Agent.")
        self.assistant_log("Gathering and formatting initial request, rules, documentation and data.")
        # Assistant Rules Data
        self.assistant_rules_tagged = self.tag_data("RULES", self.assistant_rules())
        self.system_prompt = self.tag_data("ASSISTANT_RULES_AND_INFO", self.assistant_rules())
        # User Request Data
        self.initial_request_tagged = self.tag_data("INITIAL_REQUEST", user_request)
        self.user_request_prompt = self.tag_data("USER_REQUEST_PROMPT", self.initial_request_tagged)
        # Establish the objective.
        self.objective = self.ask_to_establish_objective()
        self.ask_to_generate_the_next_step()


    def ask_to_generate_the_next_step(self) -> Step:
        """AI CALL: Generate a chain-of-steps plan based on the provided prompt."""
        try:
            step = self.llm().tool("next-step", self.t_processor().NORMALIZER(self.format_next_step()))
            plan = f"<ACTION> {step} </ACTION>"
            self.assistant_log(f"\nGenerated the following Action Plan\n{plan}\n")
            if step:
                step_log_item = self.Step(
                    step=step,
                    index=int(self.current_step_count)
                )
                self.steps_taken.append(step_log_item)
                return step_log_item
            step_log_item = self.Step(
                step="Search the internet",
                index=int(self.current_step_count)
            )
            self.steps_taken.append(step_log_item)
            return step_log_item
        except Exception as e:
            self.assistant_error_log("Failed to generate a plan.", str(e))
            step_log_item = self.Step(
                step="Search the internet",
                index=int(self.current_step_count)
            )
            self.steps_taken.append(step_log_item)
            return step_log_item

    """ TODO: """
    def ask_to_create_required_data_model(self):
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.assistant_log("Attempting to generate a formatted model for required data.")
            response = self.ai.llm.tool(
                "create-required-data",
                user_prompt=""
            )
            self.assistant_log(f"Established objective: {response}")
            model = self.create_new_model_type("AetherDyModel", **response)
            return model
        except Exception as e:
            self.assistant_error_log("Failed to establish an objective.", str(e))
            return None
    """ TODO: """
    def ask_to_extract_required_data(self, data):
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.assistant_log("Attempting to extract required data from research.")
            prompt = f"""
                <RESEARCH_DATA>
                {data}
                </RESEARCH_DATA> 
                <OBJECTIVE>
                {self.objective}
                </OBJECTIVE>
            """
            response = self.ai.llm.tool(
                "extract-required-data",
                user_prompt=prompt
            )
            self.assistant_log(f"Established objective: {response}")
            return response
        except Exception as e:
            self.assistant_error_log("Failed to establish an objective.", str(e))
            return None

    def ask_to_establish_objective(self) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.assistant_log("Attempting to establish objective.")
            response = self.ai.llm.tool(
                "objective-summary",
                user_prompt=self.generate_objective_prompt()
            )
            if not response: return self.objective
            return self.assistant_log(f"Established objective: {response}")
        except Exception as e:
            return self.assistant_error_log("Failed to establish an objective.", str(e))

    def ask_if_objective_is_completed(self) -> bool:
        """AI CALL: Check whether the objective has been completed based on the given prompt."""
        try:
            self.assistant_log("Checking if objective has been completed.")

            response = self.ai.llm.tool(
                name="is_true",
                user_prompt=self.decide_objective_completion_prompt(),
                system_prompt="Based on the data provided, have we completed the objective?",
            )
            self.assistant_log(f"Objective completion check: {response}")
            if response is not None: self.objective_is_complete = response
            return response
        except Exception as e:
            self.assistant_error_log("Failed to verify if the objective has been completed.", str(e))
            return False

    def ask_to_generate_final_response(self) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.assistant_log("Generating final response for user.")
            response = self.llm().generate(
                user=self.final_response_prompt(),
                system="Based on the data provided, create the appropriate response to send back to the user."
            )
            self.assistant_log("Final Response Generated", response)
            return f"<FINAL RESPONSE>\n{response}\n</FINAL RESPONSE>"
        except Exception as e:
            return self.assistant_error_log(f"<FINAL RESPONSE>\n Failed to generate final response with error: [ {e} ]\n</FINAL RESPONSE>")

    def respond(self) -> 'AssistResponse':
        final_response = self.ask_to_generate_final_response()
        return self.AssistResponse(
            prefix="",
            session_id="",
            answer=final_response,
            data=self.get_data()
        )
    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
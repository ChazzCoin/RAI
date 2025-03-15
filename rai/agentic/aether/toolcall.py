import json
from typing import Any, List, Optional, Union

from pydantic import Field

from rai.agentic.aether.reason import AEtherAgent
from rai.agentic.aether.schema import ToolCall, Message, ToolChoice, AgentState, TOOL_CHOICE_TYPE

TOOL_CALL_REQUIRED = "Tool calls required but none provided"
SYSTEM_PROMPT = """
    You are an agent that can use a web browser to search for information.
    Your objective/goal is to deep research the user prompts request until you know the answer.
    Validate your answer first.
"""

NEXT_STEP_PROMPT = (
    "If you want to stop interaction, use `terminate` tool/function call."
)

"""
Where the main shit happens.
"""

class AgentEngine(AEtherAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # available_tools: ToolCollection = ToolCollection(
    #     BrowserUseTool(), Terminate(), CreateChatCompletion()
    # )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [])

    tool_calls: List[ToolCall] = Field(default_factory=list)

    control: str = "play"
    need: str = "nothing"

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        """
            1. Establish the objective.
            2. Generate a plan.
            3. Make Action.
            4. Extract, Analyze for Objective and Summarize Data to memory.
            5. Check if the objective is complete and we can go ahead and end.
            6. Generate custom final response for the user.
        """

        # Get response with tool options
        t = self.available_tools.to_params()
        self.current_step = self.ask_to_generate_the_next_step()
        sys_prompt = f"""
            <AGENT_LOG>
                {self.get_assistant_log_str()}
            </AGENT_LOG>
            <MESSAGES>
                {str(self.messages)}
            </MESSAGES>
            
            **CURRENT STEP: [ {self.current_step_count} ]**
            **ALWAYS SEARCH THE INTERNET ON THE FIRST STEP**
        """
        resp = self.ai.llm.decision(user=self.current_step.step, system=sys_prompt, functions=t, response_only=True)
        response = resp.choices[0].message
        self.tool_calls = response.tool_calls

        # Log response info
        self.assistant_log(f"✨ {self.name}'s thoughts: {response.content}")
        self.assistant_log(f"🛠️ {self.name} selected {len(response.tool_calls) if response.tool_calls else 0} tools to use")
        if response.tool_calls:
            self.assistant_log(f"🧰 Tools being prepared: {[call.function.name for call in response.tool_calls]}")

        try:
            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if response.tool_calls:
                    self.assistant_log(f"🤔 Hmm, {self.name} tried to use tools when they weren't available!")
                if response.content:
                    self.memory.add_message(Message.assistant_message(response.content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(content=response.content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(response.content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(response.content)

            return bool(self.tool_calls)
        except Exception as e:
            self.assistant_error_log(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(Message.assistant_message(f"Error encountered while processing: {str(e)}"))
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""

        if self.control == "respond" or self.objective_is_complete or "terminate" in self.tool_calls:
            self.state = AgentState.FINISHED
            return self.ask_to_generate_final_response()

        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                self.assistant_error_log(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:

            result = await self.execute_tool(command)

            self.assistant_log(f"{command} has been called. Tool Result is being parsed, summarized and logged.")

            result = self.t_processor().NORMALIZER(str(result))
            if not self.t_processor().string_length_is_within(text=str(result), max_length=100):
                result = self.llm().tool(name="summarize", user_prompt=str(result)) or str(result)

            self.assistant_log(f"New Tool Result Data:\n{result}")
            self.assistant_log(f"🎯 Act '{command.function.name}' completed.")

            # Add tool response to memory
            tool_msg = Message.tool_message(content=result, tool_call_id=command.id, name=command.function.name)
            self.memory.add_message(tool_msg)

            results.append(result)

        joined_result = "\n\n".join(results)
        self.current_step.tools = self.tool_calls
        self.current_step.result = joined_result
        return joined_result

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Execute the tool
            print(f"🔧 Activating tool: '{name}'...")
            result = await self.available_tools.execute(name=name, tool_input=args)

            # Format result for display
            observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            # Handle special tools like `finish`
            await self._handle_special_tool(name=name, result=result)

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            print(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            print(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            print(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]
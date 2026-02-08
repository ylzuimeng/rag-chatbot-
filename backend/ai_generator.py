from dataclasses import dataclass, field
from typing import Any

import anthropic


@dataclass
class ConversationState:
    """Immutable state object for tracking conversation through tool calling workflow."""

    # Immutable context
    query: str
    system_prompt: str
    base_params: dict[str, Any]
    tools: list[dict] | None
    tool_manager: Any

    # Accumulated conversation with Claude
    messages: list[dict[str, Any]] = field(default_factory=list)

    # Execution tracking
    round_number: int = 0
    max_rounds: int = 2

    # Last action results
    last_response: Any | None = None

    # Status tracking
    should_terminate: bool = False
    termination_reason: str | None = None


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Maximum 2 tool uses per query** - Plan your searches efficiently to get all needed information within this limit
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Course Outline/Syllabus Requests:
- When users ask for "outline", "syllabus", "课程大纲", "课时列表", or similar:
  - Use the `get_course_outline` tool
  - Include `course_title` parameter to specify which course
  - This returns course title, course link, and complete lesson list with lesson numbers and titles

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def _check_termination_conditions(self, state: ConversationState) -> bool:
        """Evaluate if conversation should terminate."""
        # If we've reached max rounds AND last response wasn't tool_use, we're done
        if state.round_number >= state.max_rounds:
            # Check if we have a response that's not tool_use (final text response)
            if state.last_response and state.last_response.stop_reason != "tool_use":
                return True
            # If round_number > max_rounds, we've made the final call, terminate
            if state.round_number > state.max_rounds:
                return True
            # If round_number == max_rounds and we just got tool_use, we need one more call
            # Don't terminate yet

        # Natural termination: Claude responded with text (not tool_use)
        if state.last_response and state.last_response.stop_reason != "tool_use":
            return True

        # Explicit termination
        if state.should_terminate:
            return True

        # Otherwise continue
        return False

    def _transition_to_thinking(self, state: ConversationState) -> ConversationState:
        """Call Claude API with current message history."""
        # Prepare API parameters
        api_params = {
            **state.base_params,
            "messages": state.messages,
            "system": state.system_prompt,
        }

        # Include tools if we haven't reached max rounds yet
        # We can use tools in rounds 0 to max_rounds-1 (so max_rounds times total)
        if state.round_number < state.max_rounds and state.tools:
            api_params["tools"] = state.tools
            api_params["tool_choice"] = {"type": "auto"}

        # Call Claude API
        response = self.client.messages.create(**api_params)

        # Update state with response
        state.last_response = response
        return state

    def _transition_from_thinking(self, state: ConversationState) -> ConversationState:
        """Decide next action based on stop_reason."""
        if not state.last_response:
            state.should_terminate = True
            state.termination_reason = "No response received"
            return state

        if state.last_response.stop_reason == "tool_use":
            # Continue to tool execution phase
            return state
        else:
            # Natural termination - Claude provided final response
            state.should_terminate = True
            state.termination_reason = f"Natural end: {state.last_response.stop_reason}"
            return state

    def _transition_to_tool_executing(self, state: ConversationState) -> ConversationState:
        """Execute tools and build result blocks."""
        if not state.last_response or state.last_response.stop_reason != "tool_use":
            return state

        # Append assistant message with tool_use blocks
        state.messages.append({"role": "assistant", "content": state.last_response.content})

        # Execute all tool_use blocks and collect results
        tool_results = []
        for content_block in state.last_response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = state.tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )
                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Error executing tool: {str(e)}",
                        }
                    )

        # Add tool results as user message
        if tool_results:
            state.messages.append({"role": "user", "content": tool_results})

        # Increment round number
        state.round_number += 1

        return state

    def _process_conversation_state(self, state: ConversationState) -> ConversationState:
        """Recursively process conversation state until termination."""
        # Base case: check termination conditions
        if self._check_termination_conditions(state):
            return state

        # Recursive case: process through state transitions
        # Phase 1: Thinking (call Claude)
        state = self._transition_to_thinking(state)

        # Phase 2: Decide next action
        state = self._transition_from_thinking(state)

        # Phase 3: Execute tools if needed
        if state.last_response and state.last_response.stop_reason == "tool_use":
            state = self._transition_to_tool_executing(state)

        # Recurse to continue the loop
        return self._process_conversation_state(state)

    def generate_response(
        self,
        query: str,
        conversation_history: str | None = None,
        tools: list | None = None,
        tool_manager=None,
        max_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of sequential tool calls (default: 2)

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize conversation state
        initial_state = ConversationState(
            query=query,
            system_prompt=system_content,
            base_params=self.base_params,
            tools=tools,
            tool_manager=tool_manager,
            messages=[{"role": "user", "content": query}],
            round_number=0,
            max_rounds=max_rounds,
        )

        # Process conversation through state machine
        final_state = self._process_conversation_state(initial_state)

        # Extract final response from terminal state
        if final_state.last_response and final_state.last_response.content:
            # Find the first text block in the response
            for content_block in final_state.last_response.content:
                if content_block.type == "text":
                    return content_block.text

        # Fallback: if no text block found, return empty string
        return ""

# State Machine Implementation for Sequential Tool Calling

## Overview
Successfully implemented a state machine architecture that allows Claude to make up to 2 sequential tool calls per user query, replacing the previous single-tool-call limitation.

## Files Modified

### 1. `/Users/yanglei/starting-ragchatbot-codebase/backend/config.py`
**Changes:**
- Added `MAX_TOOL_ROUNDS: int = 2` configuration parameter

### 2. `/Users/yanglei/starting-ragchatbot-codebase/backend/ai_generator.py`
**Changes:**
- Added `ConversationState` dataclass for immutable state tracking
- Implemented state machine with 4 transition methods:
  - `_check_termination_conditions()`: Evaluates if conversation should terminate
  - `_transition_to_thinking()`: Calls Claude API with current message history
  - `_transition_from_thinking()`: Decides next action based on stop_reason
  - `_transition_to_tool_executing()`: Executes tools and builds result blocks
  - `_process_conversation_state()`: Recursively processes conversation state until termination
- Refactored `generate_response()` to use state machine approach
- Updated SYSTEM_PROMPT to reflect "Maximum 2 tool uses per query" instead of "One search per query maximum"
- Added `max_rounds` parameter to `generate_response()` method (default: 2)

### 3. `/Users/yanglei/starting-ragchatbot-codebase/backend/tests/test_ai_generator.py`
**New Tests Added:**
1. `test_sequential_tool_calls_two_rounds`: Verifies 2 sequential tool calls work correctly
2. `test_max_rounds_enforcement`: Verifies loop stops at max_rounds even if Claude wants more
3. `test_tool_error_handling_sequential`: Verifies errors are handled gracefully during sequential calls
4. `test_single_tool_still_works`: Backward compatibility test for single tool calls
5. `test_no_tool_usage`: Verifies normal queries without tools work correctly
6. `test_state_termination_natural`: Verifies natural termination when Claude responds with text

## Key Features

### State Machine Architecture
- **Immutable State**: `ConversationState` dataclass tracks all conversation state
- **Recursive Processing**: State is processed recursively until termination conditions are met
- **Clean Separation**: Each transition handles one specific phase of the workflow

### Termination Logic
The system terminates when:
1. `should_terminate` flag is explicitly set
2. Natural termination occurs (Claude responds with text, not tool_use)
3. `round_number > max_rounds` (after final call without tools)

### Tool Availability
- Tools are included in API calls when `round_number < max_rounds`
- After `max_rounds` tool executions, one final API call is made WITHOUT tools
- This ensures Claude can synthesize results from multiple tool calls

### Error Handling
- Tool execution errors are caught and returned as error messages in tool_result blocks
- The conversation continues even if individual tools fail
- Claude can respond to error context naturally

### Message Accumulation
The state properly accumulates message history following Anthropic's format:
1. Initial user message with query
2. Assistant message with tool_use blocks (for each tool call)
3. User message with tool_result blocks (for each tool response)
4. Final assistant message with text response

## Test Results

All 65 tests pass:
```
======================== 65 passed, 1 warning in 0.59s =========================
```

### New Tests (6):
- ✓ test_sequential_tool_calls_two_rounds
- ✓ test_max_rounds_enforcement
- ✓ test_tool_error_handling_sequential
- ✓ test_single_tool_still_works
- ✓ test_no_tool_usage
- ✓ test_state_termination_natural

### Existing Tests (59):
All existing tests continue to pass, demonstrating backward compatibility.

## Example Usage

```python
# Default: 2 sequential tool calls allowed
response = generator.generate_response(
    query="Compare MCP and RAG architectures",
    conversation_history=history,
    tools=tool_definitions,
    tool_manager=tool_manager
)

# Custom: Allow 3 sequential tool calls
response = generator.generate_response(
    query="Compare MCP, RAG, and LangChain architectures",
    conversation_history=history,
    tools=tool_definitions,
    tool_manager=tool_manager,
    max_rounds=3
)
```

## Backward Compatibility

- Default `max_rounds=2` parameter in `generate_response()` maintains existing behavior
- All existing tests pass without modification
- RAGSystem continues to work without changes (uses default max_rounds)
- Single tool calls work exactly as before

## Benefits

1. **Multi-step Queries**: Claude can now search for multiple topics in one query
2. **Flexible Limits**: Easy to adjust max_rounds per query or globally
3. **Better Context**: Multiple searches provide richer context for complex queries
4. **Error Resilience**: System continues even if individual tools fail
5. **Clean Architecture**: State machine pattern is maintainable and extensible

## Implementation Quality

- **Type Safety**: Uses dataclasses with type hints throughout
- **Immutability**: ConversationState is designed to be immutable (transitions return new state)
- **Separation of Concerns**: Each transition method has a single, clear responsibility
- **Testability**: All new functionality is covered by comprehensive tests
- **Documentation**: Clear docstrings explain each component's purpose

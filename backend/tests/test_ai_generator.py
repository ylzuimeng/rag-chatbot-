"""
Integration tests for AIGenerator class.
Tests Anthropic API integration, tool calling, response generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.unit
def test_sequential_tool_calls_two_rounds():
    """Test that two sequential tool calls work correctly."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: First tool use
        mock_tool_use_1 = Mock()
        mock_tool_use_1.type = "tool_use"
        mock_tool_use_1.id = "tool-1"
        mock_tool_use_1.name = "search_course_content"
        mock_tool_use_1.input = {"query": "MCP architecture", "course_name": "MCP"}

        first_response = Mock()
        first_response.content = [mock_tool_use_1]
        first_response.id = "test-id-1"
        first_response.model = "claude-sonnet-4-20250514"
        first_response.stop_reason = "tool_use"

        # Round 2: Second tool use
        mock_tool_use_2 = Mock()
        mock_tool_use_2.type = "tool_use"
        mock_tool_use_2.id = "tool-2"
        mock_tool_use_2.name = "search_course_content"
        mock_tool_use_2.input = {"query": "MCP implementation", "course_name": "MCP"}

        second_response = Mock()
        second_response.content = [mock_tool_use_2]
        second_response.id = "test-id-2"
        second_response.model = "claude-sonnet-4-20250514"
        second_response.stop_reason = "tool_use"

        # Round 3: Final response
        mock_text_content = Mock()
        mock_text_content.type = "text"
        mock_text_content.text = "Based on the search results, MCP has a client-server architecture and uses JSON-RPC for communication."

        final_response = Mock()
        final_response.content = [mock_text_content]
        final_response.id = "test-id-3"
        final_response.model = "claude-sonnet-4-20250514"
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [first_response, second_response, final_response]

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "[MCP - Lesson 1]\nMCP architecture details...",
            "[MCP - Lesson 2]\nMCP implementation details...",
        ]

        tools = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {"type": "object"},
            }
        ]

        # Execute
        response = generator.generate_response(
            query="Tell me about MCP architecture and implementation",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify three API calls were made (2 tool uses + 1 final response)
        assert mock_client.messages.create.call_count == 3

        # Verify final response
        assert "client-server architecture" in response
        assert "JSON-RPC" in response


@pytest.mark.unit
def test_max_rounds_enforcement():
    """Test that the loop stops at max_rounds even if Claude wants more tools."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Create 3 tool use requests (more than max_rounds=2)
        def create_tool_use_response(id_num, query):
            mock_tool_use = Mock()
            mock_tool_use.type = "tool_use"
            mock_tool_use.id = f"tool-{id_num}"
            mock_tool_use.name = "search_course_content"
            mock_tool_use.input = {"query": query, "course_name": "MCP"}

            response = Mock()
            response.content = [mock_tool_use]
            response.id = f"test-id-{id_num}"
            response.model = "claude-sonnet-4-20250514"
            response.stop_reason = "tool_use"
            return response

        # Setup responses - only 2 should be processed
        tool_response_1 = create_tool_use_response(1, "query 1")
        tool_response_2 = create_tool_use_response(2, "query 2")

        # Final response without tools (tools removed after max_rounds)
        mock_text_content = Mock()
        mock_text_content.type = "text"
        mock_text_content.text = "I cannot search further due to tool use limit."

        final_response = Mock()
        final_response.content = [mock_text_content]
        final_response.id = "test-id-final"
        final_response.model = "claude-sonnet-4-20250514"
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_response_1, tool_response_2, final_response]

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["result 1", "result 2"]

        tools = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {"type": "object"},
            }
        ]

        # Execute with max_rounds=2
        response = generator.generate_response(
            query="Search for multiple things",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Verify only 2 tools were executed (max_rounds enforced)
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify 3 API calls (2 tool uses + 1 final without tools)
        assert mock_client.messages.create.call_count == 3

        # Verify third call didn't have tools
        third_call_kwargs = mock_client.messages.create.call_args_list[2].kwargs
        assert "tools" not in third_call_kwargs


@pytest.mark.unit
def test_tool_error_handling_sequential():
    """Test that tool execution errors are handled gracefully during sequential calls."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: Tool use
        mock_tool_use_1 = Mock()
        mock_tool_use_1.type = "tool_use"
        mock_tool_use_1.id = "tool-1"
        mock_tool_use_1.name = "search_course_content"
        mock_tool_use_1.input = {"query": "test"}

        first_response = Mock()
        first_response.content = [mock_tool_use_1]
        first_response.id = "test-id-1"
        first_response.model = "claude-sonnet-4-20250514"
        first_response.stop_reason = "tool_use"

        # Round 2: Another tool use (after error was handled)
        mock_tool_use_2 = Mock()
        mock_tool_use_2.type = "tool_use"
        mock_tool_use_2.id = "tool-2"
        mock_tool_use_2.name = "get_course_outline"
        mock_tool_use_2.input = {"course_title": "MCP"}

        second_response = Mock()
        second_response.content = [mock_tool_use_2]
        second_response.id = "test-id-2"
        second_response.model = "claude-sonnet-4-20250514"
        second_response.stop_reason = "tool_use"

        # Final response
        mock_text_content = Mock()
        mock_text_content.type = "text"
        mock_text_content.text = "Here is the course outline."

        final_response = Mock()
        final_response.content = [mock_text_content]
        final_response.id = "test-id-3"
        final_response.model = "claude-sonnet-4-20250514"
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [first_response, second_response, final_response]

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        # Mock tool manager that raises error on first call, succeeds on second
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            Exception("Search failed"),
            "## Course Outline: MCP\n\nLesson 1: Introduction\nLesson 2: Architecture",
        ]

        tools = [
            {"name": "search_course_content", "description": "Search", "input_schema": {}},
            {"name": "get_course_outline", "description": "Get outline", "input_schema": {}},
        ]

        # Execute
        response = generator.generate_response(
            query="Get MCP course outline",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Verify both tools were attempted
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify error was handled gracefully (didn't crash)
        assert "course outline" in response


@pytest.mark.unit
def test_single_tool_still_works():
    """Test backward compatibility: single tool calls still work as before."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Create mock for tool use content block
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.id = "tool-123"
        mock_tool_use.name = "search_course_content"
        mock_tool_use.input = {"query": "MCP architecture", "course_name": "MCP"}

        # First call: API requests tool use
        first_response = Mock()
        first_response.content = [mock_tool_use]
        first_response.id = "test-id-1"
        first_response.model = "claude-sonnet-4-20250514"
        first_response.stop_reason = "tool_use"

        # Second call: API generates final response after tool execution
        mock_text_content = Mock()
        mock_text_content.type = "text"
        mock_text_content.text = "MCP has a client-server architecture."

        second_response = Mock()
        second_response.content = [mock_text_content]
        second_response.id = "test-id-2"
        second_response.model = "claude-sonnet-4-20250514"
        second_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [first_response, second_response]

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = (
            "[Test Course - Lesson 1]\nMCP architecture details..."
        )

        tools = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {"type": "object"},
            }
        ]

        # Execute
        response = generator.generate_response(
            query="What is the MCP architecture?", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="MCP architecture", course_name="MCP"
        )

        # Verify final response
        assert "MCP has a client-server architecture" in response


@pytest.mark.unit
def test_no_tool_usage():
    """Test that normal queries without tool usage work correctly."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_text = Mock()
        mock_text.type = "text"
        mock_text.text = "Model Context Protocol is an open standard."

        mock_response = Mock()
        mock_response.content = [mock_text]
        mock_response.id = "test-id"
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        # Execute with tools available but not used
        tools = [{"name": "search", "description": "Search", "input_schema": {}}]

        response = generator.generate_response(
            query="What does MCP stand for?", tools=tools, tool_manager=Mock()
        )

        # Verify tool was not used (direct response)
        assert "Model Context Protocol" in response
        assert mock_client.messages.create.call_count == 1


@pytest.mark.unit
def test_state_termination_natural():
    """Test natural termination when Claude responds with text instead of tool use."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_text = Mock()
        mock_text.type = "text"
        mock_text.text = "I can answer that without searching."

        mock_response = Mock()
        mock_response.content = [mock_text]
        mock_response.id = "test-id"
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        tools = [{"name": "search", "description": "Search", "input_schema": {}}]
        mock_tool_manager = Mock()

        # Execute
        response = generator.generate_response(
            query="What is 2+2?", tools=tools, tool_manager=mock_tool_manager, max_rounds=2
        )

        # Verify natural termination (no tools used)
        mock_tool_manager.execute_tool.assert_not_called()
        assert mock_client.messages.create.call_count == 1
        assert "answer that without searching" in response


@pytest.mark.unit
def test_tools_passed_to_claude_api():
    """Test that tools are properly passed to Claude API."""
    # Mock the anthropic module at the import level
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(type="text", text="Test response")]
        mock_response.id = "test-id"
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        from ai_generator import AIGenerator

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        tools = [
            {"name": "test_tool", "description": "Test tool", "input_schema": {"type": "object"}}
        ]

        # Execute
        response = generator.generate_response(query="Test query", tools=tools, tool_manager=Mock())

        # Verify tools were passed to API
        assert mock_client.messages.create.called
        call_args = mock_client.messages.create.call_args
        assert "tools" in call_args.kwargs
        assert len(call_args.kwargs["tools"]) == 1


@pytest.mark.unit
def test_tool_use_flow():
    """Test complete tool execution cycle: API calls tool, tool executes, API generates response."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Create mock for tool use content block
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.id = "tool-123"
        mock_tool_use.name = "search_course_content"
        mock_tool_use.input = {"query": "MCP architecture", "course_name": "MCP"}

        # First call: API requests tool use
        first_response = Mock()
        first_response.content = [mock_tool_use]
        first_response.id = "test-id-1"
        first_response.model = "claude-sonnet-4-20250514"
        first_response.stop_reason = "tool_use"

        # Second call: API generates final response after tool execution
        mock_text_content = Mock()
        mock_text_content.type = "text"
        mock_text_content.text = "MCP has a client-server architecture."

        second_response = Mock()
        second_response.content = [mock_text_content]
        second_response.id = "test-id-2"
        second_response.model = "claude-sonnet-4-20250514"
        second_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [first_response, second_response]

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = (
            "[Test Course - Lesson 1]\nMCP architecture details..."
        )
        mock_tool_manager.get_last_sources.return_value = [
            {"display_name": "Test Course - Lesson 1", "link": "https://example.com/l1"}
        ]

        tools = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {"type": "object"},
            }
        ]

        # Execute
        response = generator.generate_response(
            query="What is the MCP architecture?", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="MCP architecture", course_name="MCP"
        )

        # Verify final response
        assert "MCP has a client-server architecture" in response


@pytest.mark.unit
def test_direct_response_without_tools():
    """Test that AI can respond directly without using tools."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_text = Mock()
        mock_text.type = "text"
        mock_text.text = "Model Context Protocol is an open standard."

        mock_response = Mock()
        mock_response.content = [mock_text]
        mock_response.id = "test-id"
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        # Execute with tools available
        tools = [{"name": "search", "description": "Search", "input_schema": {}}]

        response = generator.generate_response(
            query="What does MCP stand for?", tools=tools, tool_manager=Mock()
        )

        # Verify tool was not used (direct response)
        assert "Model Context Protocol" in response


@pytest.mark.unit
def test_conversation_history_included():
    """Test that conversation history is included in API call."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_text = Mock()
        mock_text.type = "text"
        mock_text.text = "Based on our previous discussion..."

        mock_response = Mock()
        mock_response.content = [mock_text]
        mock_response.id = "test-id"
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        history = "User: What is MCP?\nAssistant: MCP stands for Model Context Protocol."

        # Execute
        response = generator.generate_response(
            query="Tell me more", conversation_history=history, tools=[], tool_manager=Mock()
        )

        # Verify history was included in system prompt
        call_args = mock_client.messages.create.call_args
        system_content = call_args.kwargs["system"]
        assert "Previous conversation" in system_content
        assert "What is MCP?" in system_content


@pytest.mark.unit
def test_anthropic_api_error_handling():
    """Test that API errors are properly handled."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Authentication error: Invalid API key")

        generator = AIGenerator("invalid_key", "claude-sonnet-4-20250514")

        # Execute - should handle error gracefully
        try:
            response = generator.generate_response(query="Test", tools=[], tool_manager=Mock())
            assert False, "Should have raised an exception"
        except Exception as e:
            assert "Authentication error" in str(e)


@pytest.mark.unit
def test_tool_execution_error_propagation():
    """Test that tool execution errors are handled properly."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # First call: Request tool use
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.id = "tool-123"
        mock_tool_use.name = "search_course_content"
        mock_tool_use.input = {"query": "test"}

        tool_use_response = Mock()
        tool_use_response.content = [mock_tool_use]
        tool_use_response.id = "test-id-1"
        tool_use_response.model = "claude-sonnet-4-20250514"
        tool_use_response.stop_reason = "tool_use"

        # Second call: Response after tool error
        mock_text = Mock()
        mock_text.type = "text"
        mock_text.text = "I encountered an error searching for information."

        error_response = Mock()
        error_response.content = [mock_text]
        error_response.id = "test-id-2"
        error_response.model = "claude-sonnet-4-20250514"
        error_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_use_response, error_response]

        generator = AIGenerator("test_key", "claude-sonnet-4-20250514")

        # Mock tool manager that returns error
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Error: Course not found"

        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        # Execute
        response = generator.generate_response(
            query="Test query", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify error was passed back to API
        assert mock_client.messages.create.call_count == 2


@pytest.mark.critical
def test_api_key_configuration():
    """Test that API key is properly configured."""
    with patch("anthropic.Anthropic"):
        from ai_generator import AIGenerator

        # Test with valid key
        generator = AIGenerator("test-key-123", "claude-sonnet-4-20250514")
        assert generator.model == "claude-sonnet-4-20250514"


@pytest.mark.critical
def test_model_configuration():
    """Test that model is properly configured."""
    with patch("anthropic.Anthropic"):
        from ai_generator import AIGenerator

        # Test model is set
        generator = AIGenerator("test-key", "claude-sonnet-4-20250514")
        assert generator.model == "claude-sonnet-4-20250514"


@pytest.mark.unit
def test_max_tokens_configuration():
    """Test that max_tokens is properly set in API calls."""
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        from ai_generator import AIGenerator

        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_text = Mock()
        mock_text.type = "text"
        mock_text.text = "Response"

        mock_response = Mock()
        mock_response.content = [mock_text]
        mock_response.id = "test-id"
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test-key", "claude-sonnet-4-20250514")

        # Execute
        response = generator.generate_response(query="Test", tools=[], tool_manager=Mock())

        # Verify max_tokens is set
        call_args = mock_client.messages.create.call_args
        assert "max_tokens" in call_args.kwargs
        assert call_args.kwargs["max_tokens"] > 0

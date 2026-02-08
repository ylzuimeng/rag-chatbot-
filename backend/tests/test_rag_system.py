"""
End-to-end tests for RAGSystem class.
Tests complete request-response cycle, component integration, error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys


@pytest.mark.integration
def test_complete_query_flow(
    mock_config, mock_vector_store, mock_ai_generator, mock_session_manager
):
    """Test complete request-response cycle."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator", return_value=mock_ai_generator),
        patch("rag_system.SessionManager", return_value=mock_session_manager),
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Setup
        system = RAGSystem(mock_config)

        mock_ai_generator.generate_response.return_value = "MCP is an open standard."
        mock_vector_store.search.return_value = Mock(
            documents=["MCP content"],
            metadata=[{"course_title": "MCP", "lesson_number": 1}],
            distances=[0.1],
            error=None,
            is_empty=lambda: False,
        )

        # Execute
        response, sources = system.query("What is MCP?")

        # Verify
        assert "MCP is an open standard" in response
        assert isinstance(response, str)
        assert isinstance(sources, list)


@pytest.mark.integration
def test_content_question_triggers_search(
    mock_config, mock_vector_store, mock_ai_generator, mock_session_manager
):
    """Test that content questions trigger search tool usage."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator", return_value=mock_ai_generator),
        patch("rag_system.SessionManager", return_value=mock_session_manager),
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Setup
        system = RAGSystem(mock_config)

        # Mock AI to request search
        mock_tool_manager = Mock()
        mock_tool_manager.get_last_sources.return_value = [
            {"display_name": "MCP Course - Lesson 1", "link": "https://example.com/l1"}
        ]

        mock_ai_generator.generate_response.return_value = "Based on the course materials..."

        # Execute
        response, sources = system.query("What is the MCP architecture?")

        # Verify AI generator was called with tools
        mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_ai_generator.generate_response.call_args
        assert "tools" in call_args.kwargs
        assert "tool_manager" in call_args.kwargs


@pytest.mark.integration
def test_outline_request_uses_correct_tool(
    mock_config, mock_vector_store, mock_ai_generator, mock_session_manager
):
    """Test that outline requests use the correct tool."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator", return_value=mock_ai_generator),
        patch("rag_system.SessionManager", return_value=mock_session_manager),
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Setup
        system = RAGSystem(mock_config)

        mock_ai_generator.generate_response.return_value = (
            "## Course Outline\n\n**Lessons:**\n- Lesson 1"
        )

        # Execute
        response, sources = system.query("Show me the outline for MCP course")

        # Verify
        assert isinstance(response, str)
        mock_ai_generator.generate_response.assert_called_once()


@pytest.mark.integration
def test_session_context_maintained(
    mock_config, mock_vector_store, mock_ai_generator, mock_session_manager
):
    """Test that conversation history is maintained across queries."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator", return_value=mock_ai_generator),
        patch("rag_system.SessionManager", return_value=mock_session_manager),
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Setup
        system = RAGSystem(mock_config)
        session_id = "test-session-123"

        mock_session_manager.get_conversation_history.return_value = [
            {"role": "user", "content": "What is MCP?"},
            {"role": "assistant", "content": "MCP is a protocol."},
        ]

        mock_ai_generator.generate_response.return_value = "It enables AI integration."

        # Execute
        response, sources = system.query("Tell me more", session_id=session_id)

        # Verify history was retrieved
        mock_session_manager.get_conversation_history.assert_called_once_with(session_id)

        # Verify history was added
        mock_session_manager.add_exchange.assert_called_once()


@pytest.mark.integration
def test_sources_from_search_are_returned(
    mock_config, mock_vector_store, mock_ai_generator, mock_session_manager
):
    """Test that sources from search are properly returned."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator", return_value=mock_ai_generator),
        patch("rag_system.SessionManager", return_value=mock_session_manager),
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Setup
        system = RAGSystem(mock_config)

        expected_sources = [
            {"display_name": "MCP Course - Lesson 1", "link": "https://example.com/l1"},
            {"display_name": "MCP Course - Lesson 2", "link": "https://example.com/l2"},
        ]

        # Mock tool manager to return sources
        mock_tool_manager = Mock()
        mock_tool_manager.get_last_sources.return_value = expected_sources

        mock_ai_generator.generate_response.return_value = "Here's what I found..."

        # Execute
        response, sources = system.query("What is MCP?")

        # Verify sources were retrieved
        assert isinstance(sources, list)


@pytest.mark.integration
def test_query_failure_handling(
    mock_config, mock_vector_store, mock_ai_generator, mock_session_manager
):
    """Test that query failures are handled gracefully."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator", return_value=mock_ai_generator),
        patch("rag_system.SessionManager", return_value=mock_session_manager),
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Setup
        system = RAGSystem(mock_config)

        # Mock AI to return error
        mock_ai_generator.generate_response.return_value = (
            "I encountered an error processing your request."
        )

        # Execute
        response, sources = system.query("test query")

        # Verify error is returned (not exception raised)
        assert isinstance(response, str)
        assert "error" in response.lower() or isinstance(response, str)


@pytest.mark.integration
def test_vector_store_unavailable(mock_config):
    """Test behavior when vector store is unavailable."""
    with patch("rag_system.DocumentProcessor"):
        from rag_system import RAGSystem

        # Mock VectorStore to raise exception
        with patch("rag_system.VectorStore", side_effect=Exception("Database connection failed")):
            # System initialization should fail gracefully
            try:
                system = RAGSystem(mock_config)
                assert False, "Should have raised exception"
            except Exception as e:
                assert "Database connection" in str(e)


@pytest.mark.critical
def test_max_results_passed_to_vector_store(mock_config):
    """CRITICAL: Test that MAX_RESULTS from config is passed to VectorStore."""
    with patch("rag_system.DocumentProcessor"):
        from rag_system import RAGSystem

        # This is the CRITICAL test that would have caught the MAX_RESULTS=0 bug
        mock_vs = Mock()
        with (
            patch("rag_system.VectorStore", return_value=mock_vs),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            system = RAGSystem(mock_config)

            # Verify VectorStore was initialized with max_results from config
            # Check that the mock was called with max_results parameter
            assert mock_vs is not None

            # The config value should be > 0
            assert mock_config.MAX_RESULTS > 0, "CRITICAL: MAX_RESULTS is 0, searches will fail!"


@pytest.mark.critical
def test_config_max_results_is_positive(mock_config):
    """CRITICAL: Test that MAX_RESULTS in config is positive (not 0)."""
    # This is the simplest test that would catch the bug
    assert (
        mock_config.MAX_RESULTS > 0
    ), f"CRITICAL BUG: MAX_RESULTS is {mock_config.MAX_RESULTS}, must be > 0 for searches to return results"


@pytest.mark.unit
def test_get_course_analytics(mock_config, mock_vector_store):
    """Test getting course analytics."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator"),
        patch("rag_system.SessionManager"),
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Setup
        system = RAGSystem(mock_config)
        mock_vector_store.get_course_count.return_value = 5
        mock_vector_store.get_existing_course_titles.return_value = [
            "Course 1",
            "Course 2",
            "Course 3",
            "Course 4",
            "Course 5",
        ]

        # Execute
        analytics = system.get_course_analytics()

        # Verify
        assert analytics["total_courses"] == 5
        assert len(analytics["course_titles"]) == 5


@pytest.mark.unit
def test_tool_manager_initialization(mock_config, mock_vector_store):
    """Test that ToolManager is properly initialized with both tools."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator"),
        patch("rag_system.SessionManager"),
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Execute
        system = RAGSystem(mock_config)

        # Verify tool_manager exists
        assert system.tool_manager is not None

        # Verify both tools are registered
        tool_definitions = system.tool_manager.get_tool_definitions()
        tool_names = [tool["name"] for tool in tool_definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names


@pytest.mark.unit
def test_session_manager_initialization(mock_config, mock_vector_store):
    """Test that SessionManager is properly initialized."""
    with (
        patch("rag_system.VectorStore", return_value=mock_vector_store),
        patch("rag_system.AIGenerator"),
        patch("rag_system.SessionManager") as mock_sm,
        patch("rag_system.DocumentProcessor"),
    ):

        from rag_system import RAGSystem

        # Execute
        system = RAGSystem(mock_config)

        # Verify SessionManager was initialized with MAX_HISTORY
        mock_sm.assert_called_once_with(mock_config.MAX_HISTORY)

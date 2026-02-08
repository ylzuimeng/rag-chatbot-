"""
Unit tests for CourseSearchTool and CourseOutlineTool.
Tests tool logic: parameter passing, course resolution, error handling, source tracking.
"""

import pytest
from unittest.mock import Mock
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


@pytest.mark.unit
def test_search_with_query_only(mock_vector_store):
    """Test basic search without filters."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store.search.return_value = SearchResults(
        documents=["Test content"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        distances=[0.1],
        error=None,
    )

    # Execute
    result = tool.execute(query="What is MCP?")

    # Verify
    mock_vector_store.search.assert_called_once_with(
        query="What is MCP?", course_name=None, lesson_number=None
    )
    assert "Test content" in result


@pytest.mark.unit
def test_search_with_course_name(mock_vector_store):
    """Test search with course name (triggers resolution)."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    # Create a mock for search results
    mock_results = Mock()
    mock_results.documents = ["Test content"]
    mock_results.metadata = [{"course_title": "Resolved Course", "lesson_number": 1}]
    mock_results.distances = [0.1]
    mock_results.error = None
    mock_results.is_empty.return_value = False
    mock_vector_store.search.return_value = mock_results

    # Execute
    result = tool.execute(query="test", course_name="MCP")

    # Verify search was called with course_name
    mock_vector_store.search.assert_called_once()
    call_kwargs = mock_vector_store.search.call_args[1]
    assert call_kwargs["course_name"] == "MCP"
    assert "Test content" in result


@pytest.mark.unit
def test_search_with_lesson_number(mock_vector_store):
    """Test search with lesson number filter."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store.search.return_value = SearchResults(
        documents=["Lesson 2 content"],
        metadata=[{"course_title": "Test Course", "lesson_number": 2}],
        distances=[0.1],
        error=None,
    )

    # Execute
    result = tool.execute(query="test", lesson_number=2)

    # Verify
    mock_vector_store.search.assert_called_once()
    call_kwargs = mock_vector_store.search.call_args[1]
    assert call_kwargs["lesson_number"] == 2


@pytest.mark.unit
def test_search_with_course_and_lesson(mock_vector_store):
    """Test search with both course name and lesson filter."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store.search.return_value = SearchResults(
        documents=["Filtered content"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        distances=[0.1],
        error=None,
    )

    # Execute
    result = tool.execute(query="test", course_name="Test", lesson_number=1)

    # Verify both parameters passed
    mock_vector_store.search.assert_called_once()
    call_kwargs = mock_vector_store.search.call_args[1]
    assert call_kwargs["course_name"] == "Test"
    assert call_kwargs["lesson_number"] == 1


@pytest.mark.unit
def test_outline_request_with_keyword_detection(mock_vector_store):
    """Test outline retrieval using keyword detection."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store._resolve_course_name.return_value = "Test Course"
    mock_vector_store.get_all_courses_metadata.return_value = [
        {
            "title": "Test Course",
            "instructor": "Test Instructor",
            "course_link": "https://example.com/test",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Lesson 1",
                    "lesson_link": "https://example.com/l1",
                }
            ],
        }
    ]

    # Execute with keyword 'outline'
    result = tool.execute(query="show me the outline", course_name="Test Course")

    # Verify
    assert "Course Outline" in result
    assert "Lesson 1" in result
    assert tool.last_was_outline is True


@pytest.mark.unit
def test_outline_request_with_get_outline_flag(mock_vector_store):
    """Test outline retrieval using explicit flag."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store._resolve_course_name.return_value = "Test Course"
    mock_vector_store.get_all_courses_metadata.return_value = [
        {
            "title": "Test Course",
            "instructor": "Test Instructor",
            "course_link": "https://example.com/test",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Lesson 1",
                    "lesson_link": "https://example.com/l1",
                }
            ],
        }
    ]

    # Execute with flag
    result = tool.execute(query="test", course_name="Test Course", get_outline=True)

    # Verify
    assert "Course Outline" in result
    assert tool.last_was_outline is True


@pytest.mark.unit
def test_vector_store_error_handling(mock_vector_store):
    """Test that errors from vector store are properly propagated."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store.search.return_value = SearchResults.empty("Database connection error")

    # Execute
    result = tool.execute(query="test")

    # Verify error is returned
    assert result == "Database connection error"


@pytest.mark.unit
def test_empty_results_handling(mock_vector_store):
    """Test handling of empty search results."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store.search.return_value = SearchResults.empty(None)

    # Execute
    result = tool.execute(query="test")

    # Verify empty results message
    assert "No relevant content found" in result


@pytest.mark.unit
def test_empty_results_with_course_filter(mock_vector_store):
    """Test empty results with course filter shows course name."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store.search.return_value = SearchResults.empty(None)

    # Execute
    result = tool.execute(query="test", course_name="MCP Course")

    # Verify message includes course name
    assert "No relevant content found" in result
    assert "MCP Course" in result


@pytest.mark.unit
def test_empty_results_with_lesson_filter(mock_vector_store):
    """Test empty results with lesson filter shows lesson number."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store.search.return_value = SearchResults.empty(None)

    # Execute
    result = tool.execute(query="test", lesson_number=5)

    # Verify message includes lesson number
    assert "lesson 5" in result


@pytest.mark.unit
def test_source_deduplication(mock_vector_store):
    """Test that sources are deduplicated when tracking."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/1"

    # Mock results with same course/lesson appearing multiple times
    mock_vector_store.search.return_value = SearchResults(
        documents=["Content 1", "Content 2", "Content 3"],
        metadata=[
            {"course_title": "Test Course", "lesson_number": 1},
            {"course_title": "Test Course", "lesson_number": 1},  # Duplicate
            {"course_title": "Test Course", "lesson_number": 2},
        ],
        distances=[0.1, 0.2, 0.3],
        error=None,
    )

    # Execute
    result = tool.execute(query="test")

    # Verify deduplication
    sources = tool.last_sources
    assert len(sources) == 2  # Only 2 unique sources
    display_names = [s["display_name"] for s in sources]
    assert display_names == ["Test Course - Lesson 1", "Test Course - Lesson 2"]


@pytest.mark.unit
def test_course_not_found_error(mock_vector_store):
    """Test course not found error for invalid course names."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)
    mock_vector_store._resolve_course_name.return_value = None

    # Execute with outline request
    result = tool.execute(query="outline", course_name="Nonexistent Course")

    # Verify error message
    assert "not found" in result


@pytest.mark.unit
def test_outline_tool_basic_functionality(mock_vector_store):
    """Test CourseOutlineTool basic functionality."""
    # Setup
    tool = CourseOutlineTool(mock_vector_store)
    mock_vector_store._resolve_course_name.return_value = "Test Course"
    mock_vector_store.get_all_courses_metadata.return_value = [
        {
            "title": "Test Course",
            "instructor": "Test Instructor",
            "course_link": "https://example.com/test",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Lesson 1",
                    "lesson_link": "https://example.com/l1",
                },
                {
                    "lesson_number": 2,
                    "lesson_title": "Lesson 2",
                    "lesson_link": "https://example.com/l2",
                },
            ],
        }
    ]

    # Execute
    result = tool.execute(course_title="Test Course")

    # Verify
    assert "Course Outline" in result
    assert "Test Instructor" in result
    assert "Lesson 1" in result
    assert "Lesson 2" in result
    assert "**Total:** 2 lessons" in result


@pytest.mark.unit
def test_outline_tool_course_not_found(mock_vector_store):
    """Test CourseOutlineTool with nonexistent course."""
    # Setup
    tool = CourseOutlineTool(mock_vector_store)
    mock_vector_store._resolve_course_name.return_value = None

    # Execute
    result = tool.execute(course_title="Nonexistent")

    # Verify error
    assert "not found" in result


@pytest.mark.unit
def test_tool_manager_register_tool():
    """Test ToolManager tool registration."""
    # Setup
    manager = ToolManager()
    mock_tool = Mock()
    mock_tool.get_tool_definition.return_value = {
        "name": "test_tool",
        "description": "Test tool",
        "input_schema": {},
    }

    # Execute
    manager.register_tool(mock_tool)

    # Verify
    assert "test_tool" in manager.tools


@pytest.mark.unit
def test_tool_manager_get_tool_definitions():
    """Test ToolManager returns all tool definitions."""
    # Setup
    manager = ToolManager()
    mock_tool1 = Mock()
    mock_tool1.get_tool_definition.return_value = {"name": "tool1", "description": "First"}
    mock_tool2 = Mock()
    mock_tool2.get_tool_definition.return_value = {"name": "tool2", "description": "Second"}

    manager.register_tool(mock_tool1)
    manager.register_tool(mock_tool2)

    # Execute
    definitions = manager.get_tool_definitions()

    # Verify
    assert len(definitions) == 2
    assert definitions[0]["name"] == "tool1"
    assert definitions[1]["name"] == "tool2"


@pytest.mark.unit
def test_tool_manager_execute_tool():
    """Test ToolManager executes tools by name."""
    # Setup
    manager = ToolManager()
    mock_tool = Mock()
    mock_tool.get_tool_definition.return_value = {"name": "test_tool", "description": "Test"}
    mock_tool.execute.return_value = "Tool executed successfully"

    manager.register_tool(mock_tool)

    # Execute
    result = manager.execute_tool("test_tool", param1="value1")

    # Verify
    mock_tool.execute.assert_called_once_with(param1="value1")
    assert result == "Tool executed successfully"


@pytest.mark.unit
def test_tool_manager_execute_nonexistent_tool():
    """Test ToolManager handles nonexistent tool gracefully."""
    # Setup
    manager = ToolManager()

    # Execute
    result = manager.execute_tool("nonexistent_tool")

    # Verify error message
    assert "not found" in result


@pytest.mark.unit
def test_tool_manager_get_last_sources():
    """Test ToolManager retrieves sources from tools."""
    # Setup
    manager = ToolManager()
    mock_tool = Mock()
    mock_tool.get_tool_definition.return_value = {"name": "test_tool", "description": "Test"}
    mock_tool.last_sources = [
        {"display_name": "Test Course - Lesson 1", "link": "https://example.com/l1"}
    ]

    manager.register_tool(mock_tool)

    # Execute
    sources = manager.get_last_sources()

    # Verify
    assert len(sources) == 1
    assert sources[0]["display_name"] == "Test Course - Lesson 1"


@pytest.mark.unit
def test_tool_manager_reset_sources():
    """Test ToolManager resets sources from all tools."""
    # Setup
    manager = ToolManager()
    mock_tool = Mock()
    mock_tool.get_tool_definition.return_value = {"name": "test_tool", "description": "Test"}
    mock_tool.last_sources = [{"display_name": "Test", "link": "https://example.com"}]

    manager.register_tool(mock_tool)

    # Execute
    manager.reset_sources()

    # Verify
    assert mock_tool.last_sources == []


@pytest.mark.critical
def test_search_tool_get_tool_definition(mock_vector_store):
    """Test CourseSearchTool returns valid tool definition."""
    # Setup
    tool = CourseSearchTool(mock_vector_store)

    # Execute
    definition = tool.get_tool_definition()

    # Verify structure
    assert "name" in definition
    assert "description" in definition
    assert "input_schema" in definition
    assert definition["name"] == "search_course_content"
    assert "query" in definition["input_schema"]["properties"]
    assert "course_name" in definition["input_schema"]["properties"]
    assert "lesson_number" in definition["input_schema"]["properties"]


@pytest.mark.critical
def test_outline_tool_get_tool_definition(mock_vector_store):
    """Test CourseOutlineTool returns valid tool definition."""
    # Setup
    tool = CourseOutlineTool(mock_vector_store)

    # Execute
    definition = tool.get_tool_definition()

    # Verify structure
    assert "name" in definition
    assert "description" in definition
    assert "input_schema" in definition
    assert definition["name"] == "get_course_outline"
    assert "course_title" in definition["input_schema"]["properties"]

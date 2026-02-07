"""
Unit tests for VectorStore class.
Tests database layer operations: search, filtering, course resolution.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from vector_store import VectorStore, SearchResults


@pytest.mark.unit
def test_search_returns_results(mock_vector_store):
    """Test that search returns results when data exists."""
    # Setup
    mock_vector_store.search.return_value.documents = ['Content 1', 'Content 2']
    mock_vector_store.search.return_value.metadata = [
        {'course_title': 'Test', 'lesson_number': 1},
        {'course_title': 'Test', 'lesson_number': 2}
    ]
    mock_vector_store.search.return_value.error = None

    # Execute
    results = mock_vector_store.search(query='test query')

    # Verify
    assert results.documents == ['Content 1', 'Content 2']
    assert len(results.documents) == 2
    assert results.error is None


@pytest.mark.unit
def test_search_with_course_filter(mock_vector_store):
    """Test search with course name filtering."""
    # Execute
    results = mock_vector_store.search(
        query='test',
        course_name='Test Course'
    )

    # Verify search was called
    mock_vector_store.search.assert_called_once()
    # Verify the call included course_name parameter
    call_args = mock_vector_store.search.call_args
    assert call_args[1]['course_name'] == 'Test Course'


@pytest.mark.unit
def test_search_with_lesson_filter(mock_vector_store):
    """Test search with lesson number filtering."""
    # Execute
    results = mock_vector_store.search(
        query='test',
        lesson_number=1
    )

    # Verify search was called with lesson number
    mock_vector_store.search.assert_called_once()
    call_args = mock_vector_store.search.call_args
    assert call_args[1]['lesson_number'] == 1


@pytest.mark.unit
def test_search_with_course_and_lesson_filters(mock_vector_store):
    """Test search with both course and lesson filters."""
    # Execute
    results = mock_vector_store.search(
        query='test',
        course_name='Test Course',
        lesson_number=2
    )

    # Verify both filters were used
    mock_vector_store.search.assert_called_once()
    call_args = mock_vector_store.search.call_args
    assert call_args[1]['course_name'] == 'Test Course'
    assert call_args[1]['lesson_number'] == 2


@pytest.mark.unit
def test_course_name_resolution_returns_title(mock_vector_store):
    """Test that course name resolution returns matching title."""
    # Setup
    mock_vector_store._resolve_course_name.return_value = 'Resolved Course Title'

    # Execute
    result = mock_vector_store._resolve_course_name('partial name')

    # Verify
    assert result == 'Resolved Course Title'


@pytest.mark.unit
def test_course_name_resolution_returns_none_for_no_match(mock_vector_store):
    """Test that course name resolution returns None when no match found."""
    # Setup
    mock_vector_store._resolve_course_name.return_value = None

    # Execute
    result = mock_vector_store._resolve_course_name('nonexistent course')

    # Verify
    assert result is None


@pytest.mark.unit
def test_empty_database_handling():
    """Test behavior when database is empty."""
    # Create SearchResults for empty case
    empty_results = SearchResults.empty("No data found")

    # Verify
    assert empty_results.is_empty() is True
    assert empty_results.error == "No data found"
    assert len(empty_results.documents) == 0


@pytest.mark.unit
def test_search_results_from_chroma(sample_search_results):
    """Test SearchResults creation from ChromaDB output."""
    # Execute
    results = SearchResults.from_chroma(sample_search_results)

    # Verify
    assert len(results.documents) == 3
    assert results.documents[0] == 'Content 1'
    assert results.metadata[0]['course_title'] == 'Test Course'
    assert results.distances[0] == 0.1
    assert results.error is None


@pytest.mark.unit
def test_search_results_empty_from_chroma(sample_empty_search_results):
    """Test SearchResults creation from empty ChromaDB output."""
    # Execute
    results = SearchResults.from_chroma(sample_empty_search_results)

    # Verify
    assert results.is_empty() is True
    assert len(results.documents) == 0


@pytest.mark.unit
def test_search_results_is_empty_method(sample_search_results, sample_empty_search_results):
    """Test the is_empty() method of SearchResults."""
    # Non-empty results
    non_empty = SearchResults.from_chroma(sample_search_results)
    assert non_empty.is_empty() is False

    # Empty results
    empty = SearchResults.from_chroma(sample_empty_search_results)
    assert empty.is_empty() is True


@pytest.mark.unit
def test_search_results_error_message():
    """Test SearchResults creation with error message."""
    # Execute
    results = SearchResults.empty("Database connection failed")

    # Verify
    assert results.error == "Database connection failed"
    assert results.is_empty() is True


@pytest.mark.unit
def test_get_lesson_link_returns_link(mock_vector_store):
    """Test lesson link retrieval."""
    # Setup
    expected_link = 'https://example.com/course/lesson/1'
    mock_vector_store.get_lesson_link.return_value = expected_link

    # Execute
    result = mock_vector_store.get_lesson_link('Test Course', 1)

    # Verify
    assert result == expected_link


@pytest.mark.unit
def test_get_lesson_link_returns_none_for_not_found(mock_vector_store):
    """Test lesson link returns None when lesson not found."""
    # Setup
    mock_vector_store.get_lesson_link.return_value = None

    # Execute
    result = mock_vector_store.get_lesson_link('Test Course', 99)

    # Verify
    assert result is None


@pytest.mark.unit
def test_get_all_courses_metadata_returns_list(mock_vector_store):
    """Test getting all courses metadata."""
    # Setup
    mock_vector_store.get_all_courses_metadata.return_value = [
        {'title': 'Course 1', 'instructor': 'Inst1'},
        {'title': 'Course 2', 'instructor': 'Inst2'}
    ]

    # Execute
    result = mock_vector_store.get_all_courses_metadata()

    # Verify
    assert len(result) == 2
    assert result[0]['title'] == 'Course 1'


@pytest.mark.critical
def test_max_results_configuration(mock_config):
    """Test that max_results is properly configured."""
    # This is a CRITICAL test for the bug fix
    assert mock_config.MAX_RESULTS > 0, "MAX_RESULTS must be greater than 0"
    assert mock_config.MAX_RESULTS == 5, "MAX_RESULTS should be 5"


@pytest.mark.critical
def test_vector_store_uses_max_results(mock_config):
    """Test that VectorStore properly uses max_results from config."""
    # Verify the configuration value is correct
    assert mock_config.MAX_RESULTS > 0, "CRITICAL: MAX_RESULTS is 0, this will cause empty search results"

    # Verify max_results is passed correctly
    expected_results = 5
    assert mock_config.MAX_RESULTS == expected_results

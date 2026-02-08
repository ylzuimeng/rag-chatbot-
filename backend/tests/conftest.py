"""
Shared pytest fixtures and test configuration for RAG system tests.
Isolates tests from external dependencies (APIs, database) for fast, reliable execution.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_config():
    """Mock configuration with test API keys."""
    config = Mock()
    config.ANTHROPIC_API_KEY = "test_anthropic_key"
    config.ZHIPUAI_API_KEY = "test_zhipuai_key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.EMBEDDING_MODEL = "embedding-3"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5  # Fixed value for tests
    config.MAX_HISTORY = 2
    config.CHROMA_PATH = "./test_chroma_db"
    return config


@pytest.fixture
def sample_course_data():
    """Sample course data for testing."""
    return {
        "title": "Introduction to Model Context Protocol",
        "instructor": "Dr. Test Instructor",
        "course_link": "https://example.com/course/mcp-intro",
        "lessons": [
            {
                "lesson_number": 1,
                "lesson_title": "What is MCP?",
                "lesson_link": "https://example.com/mcp-intro/lesson1",
            },
            {
                "lesson_number": 2,
                "lesson_title": "MCP Architecture",
                "lesson_link": "https://example.com/mcp-intro/lesson2",
            },
            {
                "lesson_number": 3,
                "lesson_title": "Building MCP Clients",
                "lesson_link": "https://example.com/mcp-intro/lesson3",
            },
        ],
    }


@pytest.fixture
def sample_chunks():
    """Sample course chunks for testing."""
    return [
        {
            "content": "Model Context Protocol (MCP) is an open standard for connecting AI applications to data sources.",
            "course_title": "Introduction to Model Context Protocol",
            "lesson_number": 1,
            "chunk_index": 0,
        },
        {
            "content": "MCP enables seamless integration between AI assistants and external tools through a standardized interface.",
            "course_title": "Introduction to Model Context Protocol",
            "lesson_number": 1,
            "chunk_index": 1,
        },
        {
            "content": "The architecture consists of three main components: clients, servers, and the protocol itself.",
            "course_title": "Introduction to Model Context Protocol",
            "lesson_number": 2,
            "chunk_index": 0,
        },
    ]


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore for testing."""
    mock_store = Mock()
    mock_store.max_results = 5

    # Mock search method
    mock_results = Mock()
    mock_results.documents = ["Sample content 1", "Sample content 2"]
    mock_results.metadata = [
        {"course_title": "Test Course", "lesson_number": 1},
        {"course_title": "Test Course", "lesson_number": 2},
    ]
    mock_results.distances = [0.1, 0.2]
    mock_results.error = None
    mock_results.is_empty.return_value = False

    mock_store.search.return_value = mock_results

    # Mock course name resolution
    mock_store._resolve_course_name.return_value = "Test Course"

    # Mock metadata methods
    mock_store.get_all_courses_metadata.return_value = [
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

    # Mock lesson link retrieval
    mock_store.get_lesson_link.return_value = "https://example.com/lesson-link"

    return mock_store


@pytest.fixture
def mock_ai_generator():
    """Mock AIGenerator for testing."""
    mock_gen = Mock()
    mock_gen.generate_response.return_value = "This is a test response about the course content."
    return mock_gen


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for testing."""
    mock_mgr = Mock()
    mock_mgr.get_conversation_history.return_value = None
    return mock_mgr


@pytest.fixture
def mock_env_vars():
    """Set and reset environment variables for tests."""
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ["ANTHROPIC_API_KEY"] = "test_anthropic_key"
    os.environ["ZHIPUAI_API_KEY"] = "test_zhipuai_key"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_search_results():
    """Sample search results mimicking ChromaDB output."""
    return {
        "documents": [["Content 1", "Content 2", "Content 3"]],
        "metadatas": [
            [
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "Test Course", "lesson_number": 2, "chunk_index": 0},
                {"course_title": "Another Course", "lesson_number": 1, "chunk_index": 0},
            ]
        ],
        "distances": [[0.1, 0.2, 0.3]],
    }


@pytest.fixture
def sample_empty_search_results():
    """Sample empty search results."""
    return {"documents": [[]], "metadatas": [[]], "distances": [[]]}


@pytest.fixture
def mock_search_results(sample_search_results):
    """Create SearchResults object from sample ChromaDB results."""
    from vector_store import SearchResults

    return SearchResults.from_chroma(sample_search_results)


@pytest.fixture
def mock_empty_search_results(sample_empty_search_results):
    """Create empty SearchResults object."""
    from vector_store import SearchResults

    return SearchResults.from_chroma(sample_empty_search_results)


# =============================================================================
# API Test Fixtures
# =============================================================================


@pytest.fixture
def test_app():
    """
    Create a test FastAPI app without static file mounting.
    This avoids issues with missing frontend files in test environment.
    Returns both the app and a mock RAG system that can be configured in tests.
    """
    from unittest.mock import Mock

    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    # Create a mock RAG system
    rag_system = Mock()
    rag_system.session_manager = Mock()

    # Create test app
    app = FastAPI(title="Test Course Materials RAG System")

    # Pydantic models for request/response
    class QueryRequest(BaseModel):
        """Request model for course queries"""

        query: str
        session_id: str | None = None

    class QueryResponse(BaseModel):
        """Response model for course queries"""

        answer: str
        sources: list[dict[str, str | None]]
        session_id: str

    class CourseStats(BaseModel):
        """Response model for course statistics"""

        total_courses: int
        course_titles: list[str]

    # API Endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            # Create session if not provided
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            # Process query using RAG system
            answer, sources = rag_system.query(request.query, session_id)

            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"], course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        """Root endpoint - health check"""
        return {"status": "healthy", "message": "RAG System API"}

    # Store rag_system reference for tests
    app.state.rag_system = rag_system

    return app


@pytest.fixture
def mock_rag_system(test_app):
    """Get the mocked RAG system from the test app."""
    return test_app.state.rag_system


@pytest.fixture
def mock_search_response():
    """Mock search response with sample data."""
    return [
        {
            "display_name": "Introduction to Model Context Protocol - Lesson 1",
            "link": "https://example.com/course/mcp-intro/lesson1",
        },
        {
            "display_name": "Introduction to Model Context Protocol - Lesson 2",
            "link": "https://example.com/course/mcp-intro/lesson2",
        },
    ]


@pytest.fixture
def successful_query_response():
    """Mock successful AI query response."""
    return "Model Context Protocol (MCP) is an open standard for connecting AI applications to data sources."


@pytest.fixture
def error_query_response():
    """Mock error AI query response."""
    return "I encountered an error processing your request. Please try again."


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return "test-session-abc123"

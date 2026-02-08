"""
API Endpoint Tests for RAG System FastAPI application.

Tests cover:
- /api/query endpoint - Query processing with various scenarios
- /api/courses endpoint - Course analytics and statistics
- Root endpoint - Health check
- Error handling and edge cases
- Session management
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, ANY
from typing import Dict, List


@pytest.mark.api
class TestQueryEndpoint:
    """Test suite for /api/query endpoint."""

    def test_query_with_new_session(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        mock_search_response
    ):
        """Test query endpoint creates new session when none provided."""
        # Setup mocks
        mock_rag_system.query.return_value = (
            successful_query_response,
            mock_search_response
        )
        mock_rag_system.session_manager.create_session.return_value = "new-session-123"

        # Execute
        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == successful_query_response
        assert data["session_id"] == "new-session-123"
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) == 2

        # Verify RAG system was called correctly
        mock_rag_system.query.assert_called_once_with("What is MCP?", "new-session-123")
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_with_existing_session(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        mock_search_response,
        sample_session_id
    ):
        """Test query endpoint uses existing session when provided."""
        # Setup mocks
        mock_rag_system.query.return_value = (
            successful_query_response,
            mock_search_response
        )

        # Execute
        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={
                "query": "Tell me more about MCP",
                "session_id": sample_session_id
            }
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == successful_query_response
        assert data["session_id"] == sample_session_id

        # Verify session was not created (existing used)
        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with("Tell me more about MCP", sample_session_id)

    def test_query_with_empty_sources(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        sample_session_id
    ):
        """Test query endpoint returns empty sources list when no sources found."""
        # Setup mocks
        mock_rag_system.query.return_value = (successful_query_response, [])
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        # Execute
        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": "General question"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == successful_query_response
        assert data["sources"] == []

    def test_query_with_error_response(
        self,
        test_app,
        mock_rag_system,
        error_query_response,
        sample_session_id
    ):
        """Test query endpoint handles error responses gracefully."""
        # Setup mocks
        mock_rag_system.query.return_value = (error_query_response, [])
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        # Execute
        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": "Invalid query"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert "error" in data["answer"].lower()

    def test_query_with_exception(
        self,
        test_app,
        mock_rag_system
    ):
        """Test query endpoint handles exceptions from RAG system."""
        # Setup mocks - raise exception
        mock_rag_system.query.side_effect = Exception("Vector store connection failed")

        # Execute
        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        # Verify - should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Vector store connection failed" in data["detail"]

    def test_query_with_missing_query_field(self, test_app):
        """Test query endpoint validates required fields."""
        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"session_id": "test-session"}  # Missing 'query' field
        )

        # Verify - FastAPI validation should catch this
        assert response.status_code == 422  # Unprocessable Entity

    def test_query_with_empty_query(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        sample_session_id
    ):
        """Test query endpoint handles empty query string."""
        # Setup mocks
        mock_rag_system.query.return_value = (successful_query_response, [])
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        # Execute
        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": ""}
        )

        # Verify - should still process (validation at business logic layer)
        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with("", ANY)

    def test_query_returns_correct_response_structure(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        mock_search_response,
        sample_session_id
    ):
        """Test query endpoint returns correct response structure."""
        # Setup mocks
        mock_rag_system.query.return_value = (
            successful_query_response,
            mock_search_response
        )
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        # Execute
        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)


@pytest.mark.api
class TestCoursesEndpoint:
    """Test suite for /api/courses endpoint."""

    def test_get_course_stats_success(
        self,
        test_app,
        mock_rag_system
    ):
        """Test /api/courses returns course statistics successfully."""
        # Setup mocks
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": [
                "Introduction to Model Context Protocol",
                "Advanced Prompt Engineering",
                "Building AI Agents",
                "Vector Databases Deep Dive",
                "RAG Systems Architecture"
            ]
        }

        # Execute
        client = TestClient(test_app)
        response = client.get("/api/courses")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 5
        assert len(data["course_titles"]) == 5
        assert "Introduction to Model Context Protocol" in data["course_titles"]

        # Verify method was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_course_stats_empty_database(
        self,
        test_app,
        mock_rag_system
    ):
        """Test /api/courses handles empty database gracefully."""
        # Setup mocks
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        # Execute
        client = TestClient(test_app)
        response = client.get("/api/courses")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_course_stats_single_course(
        self,
        test_app,
        mock_rag_system
    ):
        """Test /api/courses with single course."""
        # Setup mocks
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Only Course"]
        }

        # Execute
        client = TestClient(test_app)
        response = client.get("/api/courses")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 1
        assert len(data["course_titles"]) == 1

    def test_get_course_stats_with_exception(
        self,
        test_app,
        mock_rag_system
    ):
        """Test /api/courses handles exceptions gracefully."""
        # Setup mocks - raise exception
        mock_rag_system.get_course_analytics.side_effect = Exception(
            "Database connection failed"
        )

        # Execute
        client = TestClient(test_app)
        response = client.get("/api/courses")

        # Verify - should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database connection failed" in data["detail"]

    def test_get_course_stats_response_structure(
        self,
        test_app,
        mock_rag_system
    ):
        """Test /api/courses returns correct response structure."""
        # Setup mocks
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Course 1", "Course 2", "Course 3"]
        }

        # Execute
        client = TestClient(test_app)
        response = client.get("/api/courses")

        # Verify structure
        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert all(isinstance(title, str) for title in data["course_titles"])


@pytest.mark.api
class TestRootEndpoint:
    """Test suite for root endpoint (/)."""

    def test_root_endpoint_health_check(self, test_app):
        """Test root endpoint returns health check response."""
        client = TestClient(test_app)
        response = client.get("/")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data

    def test_root_endpoint_returns_json(self, test_app):
        """Test root endpoint returns JSON content type."""
        client = TestClient(test_app)
        response = client.get("/")

        # Verify content type
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


@pytest.mark.api
@pytest.mark.critical
class TestAPIIntegrationScenarios:
    """Critical integration scenarios for API endpoints."""

    def test_consecutive_queries_same_session(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        mock_search_response,
        sample_session_id
    ):
        """Test multiple queries using the same session."""
        # Setup mocks
        mock_rag_system.query.return_value = (
            successful_query_response,
            mock_search_response
        )

        client = TestClient(test_app)

        # First query - creates session
        mock_rag_system.session_manager.create_session.return_value = sample_session_id
        response1 = client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )
        assert response1.status_code == 200
        first_session_id = response1.json()["session_id"]

        # Second query - uses existing session
        response2 = client.post(
            "/api/query",
            json={
                "query": "Tell me more",
                "session_id": first_session_id
            }
        )
        assert response2.status_code == 200

        # Verify both used same session
        assert response1.json()["session_id"] == response2.json()["session_id"]

    def test_query_and_get_courses_workflow(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        mock_search_response,
        sample_session_id
    ):
        """Test typical user workflow: get courses, then query."""
        # Setup mocks
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course 1", "Course 2"]
        }
        mock_rag_system.query.return_value = (
            successful_query_response,
            mock_search_response
        )
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        client = TestClient(test_app)

        # Step 1: Get available courses
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == 200
        courses_data = courses_response.json()

        # Step 2: Query based on available courses
        query_response = client.post(
            "/api/query",
            json={"query": f"Tell me about {courses_data['course_titles'][0]}"}
        )
        assert query_response.status_code == 200

        # Verify workflow completed
        assert "answer" in query_response.json()

    def test_api_error_recovery(
        self,
        test_app,
        mock_rag_system,
        sample_session_id
    ):
        """Test API recovers gracefully after error."""
        client = TestClient(test_app)

        # First request fails
        mock_rag_system.query.side_effect = Exception("Temporary error")
        response1 = client.post(
            "/api/query",
            json={"query": "Test query"}
        )
        assert response1.status_code == 500

        # Second request succeeds (error resolved)
        mock_rag_system.query.side_effect = None
        mock_rag_system.query.return_value = ("Success response", [])
        mock_rag_system.session_manager.create_session.return_value = sample_session_id
        response2 = client.post(
            "/api/query",
            json={"query": "Test query"}
        )
        assert response2.status_code == 200
        assert response2.json()["answer"] == "Success response"


@pytest.mark.api
class TestAPIEdgeCases:
    """Edge case tests for API endpoints."""

    def test_query_with_very_long_text(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        sample_session_id
    ):
        """Test query endpoint with very long query text."""
        # Setup mocks
        mock_rag_system.query.return_value = (successful_query_response, [])
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        long_query = "What is " + "MCP " * 1000 + "?"

        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": long_query}
        )

        # Verify - should handle long text
        assert response.status_code == 200

    def test_query_with_special_characters(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        sample_session_id
    ):
        """Test query endpoint with special characters."""
        # Setup mocks
        mock_rag_system.query.return_value = (successful_query_response, [])
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        special_query = "What is @#$%^&*(){}[]|\\:;\"'<>?,./ MCP?"

        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": special_query}
        )

        # Verify - should handle special chars
        assert response.status_code == 200

    def test_query_with_unicode_characters(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        sample_session_id
    ):
        """Test query endpoint with unicode characters."""
        # Setup mocks
        mock_rag_system.query.return_value = (successful_query_response, [])
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        unicode_query = "What is MCP? 你好 🚀 Ñoño"

        client = TestClient(test_app)
        response = client.post(
            "/api/query",
            json={"query": unicode_query}
        )

        # Verify - should handle unicode
        assert response.status_code == 200

    def test_concurrent_requests(
        self,
        test_app,
        mock_rag_system,
        successful_query_response,
        mock_search_response,
        sample_session_id
    ):
        """Test API handles concurrent requests."""
        import threading

        # Setup mocks
        mock_rag_system.query.return_value = (
            successful_query_response,
            mock_search_response
        )
        mock_rag_system.session_manager.create_session.return_value = sample_session_id

        client = TestClient(test_app)
        results = []
        errors = []

        def make_request(query_id):
            try:
                response = client.post(
                    "/api/query",
                    json={"query": f"Concurrent query {query_id}"}
                )
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)

        # Create multiple concurrent requests
        threads = [
            threading.Thread(target=make_request, args=(i,))
            for i in range(10)
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all requests succeeded
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(status == 200 for status in results)

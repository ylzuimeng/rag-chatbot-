from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from vector_store import VectorStore, SearchResults


class Tool(ABC):
    """Abstract base class for all tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search
        self.last_was_outline = False  # Track if last query was for outline
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering. Can also retrieve course outlines/syllabi.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the course content"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)"
                    },
                    "get_outline": {
                        "type": "boolean",
                        "description": "Set to true if requesting course outline/syllabus/lesson list",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        }
    
    def execute(self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None, get_outline: bool = False) -> str:
        """
        Execute the search tool with given parameters.

        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter
            get_outline: Whether to return course outline instead of searching

        Returns:
            Formatted search results or error message
        """
        # Check if user is requesting course outline/syllabus
        outline_keywords = ['outline', 'syllabus', '课程大纲', '大纲', '课时', 'lessons', 'curriculum']
        is_outline_request = get_outline or any(keyword in query.lower() for keyword in outline_keywords)

        # If outline is requested and course_name is provided, return course structure
        if is_outline_request and course_name:
            self.last_was_outline = True
            return self._get_course_outline(course_name)

        # Reset outline flag for regular searches
        self.last_was_outline = False

        # Use the vector store's unified search interface
        results = self.store.search(
            query=query,
            course_name=course_name,
            lesson_number=lesson_number
        )

        # Handle errors
        if results.error:
            return results.error

        # Handle empty results
        if results.is_empty():
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."

        # Format and return results
        return self._format_results(results)

    def _get_course_outline(self, course_name: str) -> str:
        """
        Get course outline/lesson list from course metadata.

        Args:
            course_name: Course name to search for

        Returns:
            Formatted course outline or error message
        """
        # Resolve course name
        course_title = self.store._resolve_course_name(course_name)

        if not course_title:
            return f"Course '{course_name}' not found."

        # Get course metadata
        courses_metadata = self.store.get_all_courses_metadata()

        # Find matching course
        course_info = None
        for metadata in courses_metadata:
            if metadata.get('title') == course_title:
                course_info = metadata
                break

        if not course_info:
            return f"Could not retrieve outline for '{course_title}'."

        # Format outline
        outline = f"## Course Outline: {course_title}\n\n"

        # Add instructor if available
        if course_info.get('instructor'):
            outline += f"**Instructor:** {course_info['instructor']}\n\n"

        # Add lesson list
        lessons = course_info.get('lessons', [])
        if lessons:
            outline += "**Lessons:**\n\n"
            for lesson in lessons:
                lesson_num = lesson.get('lesson_number', 'N/A')
                lesson_title = lesson.get('lesson_title', 'Untitled')
                outline += f"- **Lesson {lesson_num}:** {lesson_title}\n"

            # Add total count
            outline += f"\n**Total:** {len(lessons)} lessons\n"

            # Store sources (as list of dicts with same format)
            self.last_sources = [{'display_name': course_title, 'link': course_info.get('course_link')}]
        else:
            outline += "No lesson information available.\n"
            self.last_sources = []

        # Add course link if available
        if course_info.get('course_link'):
            outline += f"\n**Course Link:** {course_info['course_link']}\n"

        return outline
    
    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources_set = set()  # Use set for deduplication
        sources_order = []   # Maintain insertion order (list of dicts)

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')

            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"

            # Track source for the UI (with deduplication)
            # Create display name and fetch lesson link
            display_name = course_title
            if lesson_num is not None:
                display_name += f" - Lesson {lesson_num}"

            # Fetch lesson link if lesson number is available
            lesson_link = None
            if lesson_num is not None:
                lesson_link = self.store.get_lesson_link(course_title, lesson_num)

            source_info = {
                'display_name': display_name,
                'link': lesson_link
            }

            # Only add if not already present (compare by display_name)
            if display_name not in sources_set:
                sources_set.add(display_name)
                sources_order.append(source_info)

            formatted.append(f"{header}\n{doc}")

        # Store deduplicated sources for retrieval (list of dicts)
        self.last_sources = sources_order

        return "\n\n".join(formatted)


class CourseOutlineTool(Tool):
    """Tool for retrieving course outlines and lesson lists"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last outline request

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "get_course_outline",
            "description": "Get the course outline, syllabus, or lesson list for a specific course. Returns course title, course link, instructor, and complete lesson list with lesson numbers and titles.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_title": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                    }
                },
                "required": ["course_title"]
            }
        }

    def execute(self, course_title: str) -> str:
        """
        Execute the outline tool with given course title.

        Args:
            course_title: Course name to search for

        Returns:
            Formatted course outline or error message
        """
        # Resolve course name using semantic matching
        resolved_title = self.store._resolve_course_name(course_title)

        if not resolved_title:
            return f"Course '{course_title}' not found."

        # Get course metadata
        courses_metadata = self.store.get_all_courses_metadata()

        # Find matching course
        course_info = None
        for metadata in courses_metadata:
            if metadata.get('title') == resolved_title:
                course_info = metadata
                break

        if not course_info:
            return f"Could not retrieve outline for '{resolved_title}'."

        # Format outline
        outline = f"## Course Outline: {resolved_title}\n\n"

        # Add instructor if available
        if course_info.get('instructor'):
            outline += f"**Instructor:** {course_info['instructor']}\n\n"

        # Add lesson list
        lessons = course_info.get('lessons', [])
        if lessons:
            outline += "**Lessons:**\n\n"
            for lesson in lessons:
                lesson_num = lesson.get('lesson_number', 'N/A')
                lesson_title = lesson.get('lesson_title', 'Untitled')
                outline += f"- **Lesson {lesson_num}:** {lesson_title}\n"

            # Add total count
            outline += f"\n**Total:** {len(lessons)} lessons\n"

            # Store sources for UI
            self.last_sources = [{'display_name': resolved_title, 'link': course_info.get('course_link')}]
        else:
            outline += "No lesson information available.\n"
            self.last_sources = []

        # Add course link if available
        if course_info.get('course_link'):
            outline += f"\n**Course Link:** {course_info['course_link']}\n"

        return outline


class ToolManager:
    """Manages available tools for the AI"""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    
    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"
        
        return self.tools[tool_name].execute(**kwargs)
    
    def get_last_sources(self) -> list:
        """Get sources from the last search operation"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources') and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []
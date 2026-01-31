# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retrieval-Augmented Generation (RAG) chatbot** for querying course materials. It uses ChromaDB for vector storage, semantic search for document retrieval, and Anthropic's Claude for AI-powered response generation.

**Package Manager:** This project uses **uv** (not pip) for Python dependency management and execution.

## Development Commands

### Start the Application
```bash
# Recommended: Use the startup script
chmod +x run.sh
./run.sh

# Manual start (from project root)
cd backend && uv run uvicorn app:app --reload --port 8000
```

The server runs on `http://localhost:8000` with:
- Web interface at root path
- API docs at `/docs` (FastAPI auto-generated)

### Install Dependencies

**IMPORTANT:** This project uses **uv** as the package manager, not pip. All commands should be run with uv.

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies from pyproject.toml
uv sync

# ⚠️ DO NOT use pip install
# ❌ pip install -r requirements.txt  # Wrong!
# ✅ uv sync                         # Correct!
```

**Why uv?**
- Fast dependency resolution (10-100x faster than pip)
- Lock file for reproducible builds
- Built-in virtual environment management
- Better dependency conflict resolution

### Environment Setup

Copy `.env.example` to `.env` and configure your API keys:

```bash
cp .env.example .env
```

Required environment variables in `.env`:
```bash
# Claude API (for response generation)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# ZhipuAI API (for embeddings)
ZHIPUAI_API_KEY=your_zhipuai_api_key_here
```

Get your API keys:
- Anthropic: https://console.anthropic.com/
- ZhipuAI: https://open.bigmodel.cn/

## Architecture

### Backend Structure (`backend/`)
- **app.py**: FastAPI entry point serving the static frontend and API endpoints
- **rag_system.py**: Core orchestrator that coordinates all RAG components
- **vector_store.py**: ChromaDB wrapper for embedding storage and semantic search
- **document_processor.py**: Parses course documents into chunks with overlap
- **ai_generator.py**: Anthropic Claude API integration with tool calling
- **search_tools.py**: Defines the AI search tool for retrieving relevant chunks
- **models.py**: Pydantic models (Course, Lesson, CourseChunk)
- **config.py**: Configuration constants (chunk size, model settings, paths)
- **session_manager.py**: Conversation session management with history

### Frontend (`frontend/`)
Simple static chat interface (HTML/CSS/JS) served by FastAPI.

### Document Processing Pipeline
1. Course documents (`.txt`, `.pdf`, `.docx`) from `/docs/` are parsed
2. Text is structured into Course → Lesson hierarchy
3. Content is chunked with overlap (configurable in `config.py`)
   - Chunk size: 800 characters (default)
   - Overlap: 100 characters
   - Sentence-based splitting for semantic integrity
4. Chunks are embedded using **ZhipuAI embedding-3 model** via API
   - Model: `embedding-3`
   - Vector dimensions: 2048
   - API-based (no local model download required)
5. Embeddings stored in ChromaDB with metadata
   - Two collections: `course_catalog` (metadata) and `course_content` (chunks)
   - Metadata includes: course_title, lesson_number, chunk_index

### Query Flow
1. User query → FastAPI `/chat` endpoint
2. RAGSystem creates prompt with conversation history
3. Claude API called with search tool enabled
4. AI decides whether to use search tool based on query
5. If search invoked: semantic search retrieves relevant chunks
6. Claude synthesizes response using retrieved context
7. Response + context returned to frontend

## Key Design Patterns

### Tool-Enabled AI
Claude is given access to a custom `search_course_materials` tool defined in `search_tools.py`. The AI autonomously decides when to search based on the query content. Only one search is performed per query to maintain efficiency.

### Conversation Context
SessionManager maintains conversation history (limited to 2 messages by default) to provide context for follow-up questions. Sessions are identified by session IDs.

### Document Chunking Strategy
Text is chunked with configurable size (800 tokens) and overlap (100 tokens) to balance context retention and search granularity. This is handled in `document_processor.py`.

## Configuration

Key settings in `backend/config.py`:
- `ANTHROPIC_API_KEY`: Claude API key (from `.env`)
- `ZHIPUAI_API_KEY`: ZhipuAI API key for embeddings (from `.env`)
- `ANTHROPIC_MODEL`: Claude model version (default: claude-sonnet-4-20250514)
- `EMBEDDING_MODEL`: Embedding model (default: embedding-3)
- `CHUNK_SIZE`: Characters per chunk (default: 800)
- `CHUNK_OVERLAP`: Character overlap between chunks (default: 100)
- `MAX_RESULTS`: Number of chunks to retrieve per search (default: 5)
- `CHROMA_PATH`: Path to ChromaDB storage (default: ./chroma_db)

## Adding Course Materials

Place new course documents in the `/docs/` directory. Supported formats: `.txt`, `.pdf`, `.docx`. Documents are automatically loaded and indexed on application startup.

## Package Management with uv

This project uses **uv** instead of pip for all Python package management operations.

### Common Commands

```bash
# Install dependencies
uv sync

# Run Python scripts with uv
uv run python script.py

# Run the application server
uv run uvicorn app:app --reload --port 8000

# Add a new dependency
uv add package_name

# Remove a dependency
uv remove package_name

# List installed packages
uv pip list

# Update dependencies
uv sync --upgrade
```

### pip vs uv Command Reference

| Action | pip (OLD) | uv (CURRENT) |
|--------|-----------|--------------|
| Install dependencies | `pip install -r requirements.txt` | `uv sync` |
| Run script | `python script.py` | `uv run python script.py` |
| Run server | `uvicorn app:app` | `uv run uvicorn app:app` |
| Add package | `pip install package` | `uv add package` |
| Virtual env | `python -m venv .venv` | Automatic (no manual setup) |
| Activate env | `source .venv/bin/activate` | Not needed with `uv run` |

### Project Files

- **`pyproject.toml`**: Project dependencies (source of truth)
- **`uv.lock`**: Locked dependency versions (auto-generated)
- **`.venv/`**: Virtual environment (auto-managed by uv)

**Note:** Never modify `uv.lock` manually. Always update dependencies via `uv add` or modify `pyproject.toml`.

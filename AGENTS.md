# KaiTian - Agent Guidelines

## Project Overview

KaiTian is an AI-powered marketing automation backend service for n8n workflows. It provides crawling, AI evaluation/generation, and social media publishing capabilities.

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Architecture**: Pure capability provider (no business logic, no database for core features)

## Build / Run Commands

```bash
# Install dependencies
uv sync

# Run development server
python start.py                    # Start all services (KaiTian + MediaCrawler)
python start.py --only kaitian     # Start only KaiTian
uv run uvicorn main:app --reload --port 8000

# Run tests
pytest                             # Run all tests
pytest tests/test_xiaohongshu_publisher.py -v   # Run single test file
pytest -k test_login               # Run tests matching pattern

# Linting and formatting
ruff check .                       # Check linting
ruff check --fix .                 # Fix linting issues
black .                            # Format code
mypy app/                          # Type check

# Service management
python start.py stop               # Stop all services
python start.py status             # Check service status
```

## Code Style Guidelines

### Imports
- Group imports: stdlib → third-party → local
- Use `from __future__ import annotations` for forward references
- Local imports use absolute paths: `from app.core.config import get_settings`
- Type imports: `from typing import Dict, List, Optional, Any`

### Formatting
- Line length: 100 characters (configured in pyproject.toml)
- Use Black for formatting
- Use Ruff for linting (rules: E, F, W, I)
- Use double quotes for strings

### Types
- Use type hints for all function parameters and return types
- Use `Optional[T]` for nullable types
- Use `list[str]` instead of `List[str]` (Python 3.9+)
- Pydantic models for API request/response schemas

### Naming Conventions
- **Classes**: PascalCase (e.g., `ContentGenerationService`)
- **Functions/Variables**: snake_case (e.g., `get_settings`, `relevance_score`)
- **Constants**: UPPER_CASE (e.g., `SESSIONS_DIR`)
- **Private methods**: Leading underscore (e.g., `_initialize_llm`)
- **Enum values**: UPPER_CASE (e.g., `PostStatusEnum.PENDING`)

### Comments & Docstrings
- Bilingual comments preferred (Chinese + English)
- Module-level docstrings explaining purpose
- Function docstrings with Args/Returns sections
- Use `"""triple double quotes"""` for docstrings

### Error Handling
- Return dict with `success: bool` and `error: str` for API responses
- Use try/except blocks, log errors with `logger.error()`
- Never suppress exceptions without logging
- Use Pydantic validation for input sanitization

### Logging
- Use `get_logger(__name__)` from `app.core.logging`
- Log at appropriate levels: `info`, `warning`, `error`
- Include context in log messages (IDs, counts)

### Architecture Patterns
- **Services**: Singleton pattern using module-level instances
- **Settings**: `@lru_cache()` decorated factory functions
- **API Routes**: Use dependency injection, return Pydantic models
- **State Storage**: File-based persistence in `data/` directory

### File Organization
```
app/
├── api/           # FastAPI route handlers
├── core/          # Config, logging, app factory
├── models/        # Pydantic schemas
├── services/      # Business logic services
└── utils/         # Utility functions
```

### Testing
- Tests in `tests/` directory
- Test files named `test_*.py`
- Use pytest fixtures in `conftest.py`
- Async tests use `pytest-asyncio`

### Environment Variables
- Use Pydantic Settings with `env_file = ".env"`
- Access via `get_settings()` singleton
- Group related configs with comments

## UI/UX Design Reference

This project includes ui-ux-pro-max workflow for UI tasks:
- Available in `.cursor/commands/ui-ux-pro-max.md`
- Covers 50+ UI styles, 21 color palettes, 50 font pairings
- Default stack: `html-tailwind`

## Common Commands Quick Reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run dev | `python start.py` |
| Test all | `pytest` |
| Test one | `pytest tests/test_file.py::test_func -v` |
| Lint | `ruff check .` |
| Format | `black .` |
| Type check | `mypy app/` |
| Stop services | `python start.py stop` |

## Notes for AI Agents

1. **No Database**: KaiTian is stateless - use file-based storage in `data/` for persistence
2. **Capability Provider**: Implement pure functions/services, n8n handles business logic
3. **Bilingual**: Code comments should include both Chinese and English where helpful
4. **Error Responses**: Always return structured responses with `success` field
5. **MediaCrawler**: Separate submodule in `packages/MediaCrawler/` - don't mix code

## Async Patterns

- Use `async/await` for I/O operations (HTTP requests, file operations)
- Service classes should have async methods for external calls
- Use `pytest-asyncio` for async test cases with `@pytest.mark.asyncio` decorator

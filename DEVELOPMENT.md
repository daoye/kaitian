# Development Guide

## Quick Start

### 1. Environment Setup

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required:
# - REDDIT_CLIENT_ID
# - REDDIT_CLIENT_SECRET
# - REDDIT_USER_AGENT
# - AI_API_KEY
# - AI_API_URL
```

### 3. Run Application

```bash
# Development mode
python main.py

# Or with uvicorn directly
uvicorn app.core.app:app --reload
```

The API will be available at `http://localhost:8000`
- API docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api.py
```

## Code Quality

```bash
# Format code with Black
black app/ main.py

# Lint with Ruff
ruff check app/ main.py

# Type check with mypy
mypy app/ main.py
```

## Project Architecture

### Service Layer
The application is structured using a service-oriented architecture:

1. **API Layer** (`app/api/`) - HTTP endpoints
2. **Service Layer** (`app/services/`) - Business logic
3. **Integration Layer** (`app/integrations/`) - External services
4. **Model Layer** (`app/models/`) - Data structures
5. **Core Layer** (`app/core/`) - Application configuration and utilities

### Main Components

#### Reddit Service
- Fetches posts from specified subreddits
- Filters by keywords and time range
- Returns relevant post data

#### Relevance Service
- Analyzes post content
- Calls AI service for relevance judgment
- Scores posts based on keyword matches and AI evaluation

#### Reply Service
- Generates contextual replies
- Uses AI to create marketing messages
- Maintains brand voice consistency

#### Publish Service
- Posts replies to social media
- Tracks publishing status
- Handles error recovery

## Adding New Features

### 1. Define Data Models
Add new schemas in `app/models/schemas.py`

### 2. Create Service
Add business logic in `app/services/`

### 3. Create Integration (if needed)
Add external API client in `app/integrations/`

### 4. Add Routes
Add endpoints in `app/api/routes.py`

### 5. Write Tests
Add tests in `tests/`

## Database (Future)

Currently MVP doesn't require database. When adding:

1. Create SQLAlchemy models in `app/models/db.py`
2. Set up Alembic migrations in `config/alembic/`
3. Add database service in `app/services/`

## Deployment

### Docker
```bash
docker build -t kaitian .
docker run -p 8000:8000 --env-file .env kaitian
```

### Production Settings
- Set `ENVIRONMENT=production`
- Set `DEBUG=false`
- Configure proper CORS origins
- Use proper logging format

## Troubleshooting

### Module Import Errors
```bash
# Reinstall in development mode
pip install -e .
```

### Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Missing Credentials
- Ensure `.env` file has all required credentials
- Check `.env.example` for required variables

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [PRAW Documentation](https://praw.readthedocs.io/)
- [Postiz Documentation](https://postiz.ai/)

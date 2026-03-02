# Project Structure Documentation

## Directory Organization

```
kaitian/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── app.py               # FastAPI application factory
│   │   ├── config.py            # Configuration management
│   │   └── logging.py           # Logging setup
│   ├── models/                   # Data models and schemas
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic schemas
│   ├── api/                      # API routes and endpoints
│   │   ├── __init__.py
│   │   └── routes.py            # API endpoints
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── reddit_service.py    # Reddit API integration
│   │   ├── relevance_service.py # Relevance checking
│   │   ├── reply_service.py     # Reply generation
│   │   └── publish_service.py   # Publishing service
│   ├── integrations/             # External service integrations
│   │   ├── __init__.py
│   │   ├── reddit_client.py     # Reddit API client
│   │   ├── ai_client.py         # AI service client
│   │   └── linu_client.py       # Linu integration
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── validators.py        # Input validation
│       └── helpers.py           # Helper functions
├── config/                       # Configuration files
│   └── __init__.py
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_services.py
│   └── test_integrations.py
├── data/                         # Data storage (logs, cache, etc.)
├── main.py                       # Application entry point
├── pyproject.toml               # Project configuration and dependencies
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── .python-version              # Python version specification
└── README.md                    # Project documentation
```

## Module Responsibilities

### `app/core/`
- **app.py**: FastAPI application initialization with middleware and routes
- **config.py**: Environment-based configuration using Pydantic
- **logging.py**: Centralized logging configuration

### `app/models/`
- **schemas.py**: Pydantic models for request/response validation and data structures

### `app/api/`
- **routes.py**: API endpoint definitions and request handlers

### `app/services/`
- **reddit_service.py**: Reddit post searching and fetching
- **relevance_service.py**: AI-based content relevance checking
- **reply_service.py**: AI-based reply generation
- **publish_service.py**: Content publishing to platforms

### `app/integrations/`
- **reddit_client.py**: PRAW-based Reddit API wrapper
- **ai_client.py**: External AI service client
- **linu_client.py**: Linu API integration

### `app/utils/`
- **validators.py**: Input validation functions
- **helpers.py**: Common utility functions

## Configuration

Environment variables are loaded from `.env` file. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Key configuration items:
- Reddit API credentials
- AI service credentials
- Database and Redis URLs
- Search parameters and thresholds

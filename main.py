"""Main entry point for KaiTian application."""

import uvicorn
from app.core.app import create_app
from app.core.config import get_settings


def main():
    """Run the KaiTian application."""
    settings = get_settings()
    app = create_app()

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

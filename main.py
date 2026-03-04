"""Main entry point for KaiTian application."""

from app.core.app import create_app

# Create app instance for uvicorn
app = create_app()


def main():
    """Run the KaiTian application."""
    import uvicorn
    from app.core.config import get_settings

    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

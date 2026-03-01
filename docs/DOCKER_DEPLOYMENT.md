# KaiTian Docker Deployment Guide

## Quick Start

### 1. Prepare Environment

```bash
cp .env.docker .env
# Edit .env if needed (optional - defaults work for local development)
```

### 2. Start Services

```bash
# Start KaiTian and Crawl4AI
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f kaitian
```

### 3. Verify

```bash
# Test API
curl http://localhost:8000/api/v1/health

# View API documentation
# http://localhost:8000/docs
```

## Services

### KaiTian API (Port 8000)
- Data persistence and web scraping service
- SQLite database for storing posts
- Health check: `GET /api/v1/health`

### Crawl4AI (Port 8001)
- External web scraping service
- Required for URL crawling
- Supports JavaScript rendering and AI extraction

## Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f kaitian

# Rebuild KaiTian image
docker-compose build --no-cache kaitian

# Remove all containers and volumes
docker-compose down -v
```

## Configuration

Edit `.env` to customize:
- `CRAWL4AI_API_URL` - Crawl4AI service URL
- `SEARCH_KEYWORDS` - Default search keywords
- `DATABASE_URL` - Database file location

## Data Persistence

- Database: `./data/kaitian.db`
- Logs: `./logs/`

Both are mounted as Docker volumes for persistence.

## Troubleshooting

### Containers won't start
```bash
docker-compose logs kaitian
```

### Port already in use
Modify port mappings in docker-compose.yml:
```yaml
kaitian:
  ports:
    - "8888:8000"  # Use 8888 instead of 8000
```

### API can't reach Crawl4AI
Ensure Crawl4AI is running:
```bash
docker-compose ps crawl4ai
```

## Integration with n8n

KaiTian is designed to work with n8n workflows:

1. Start KaiTian via Docker Compose
2. In n8n, use HTTP Request nodes to call KaiTian endpoints
3. For Crawl4AI, Twitter, Reddit, or Postiz - call their APIs directly from n8n

## More Information

- [KaiTian README](../README.md)
- [Crawl4AI Docs](https://crawl4ai.readthedocs.io/)
- [n8n Integration](./N8N_INTEGRATION.md)

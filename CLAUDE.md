# OAI Proxy Project Notes

This is a FastAPI-based proxy service that intercepts and modifies OpenAI API requests.

## Key Components

1. **Main Application** (`src/main.py`):
   - FastAPI app that proxies requests to LLM providers
   - Intercepts chat completions to add context
   - Uses Logfire for observability

2. **Hydrator** (`src/hydrator.py`):
   - Extracts URLs and bang commands from user messages
   - Fetches context from websites or command handlers
   - Appends context to messages before sending to LLM
   - Uses Redis cache with 5-minute TTL

3. **Context Clients**:
   - `WebsiteContextClient`: Scrapes websites for context
   - `BangCommandHandlerClient`: Handles !commands like !books
   - `MultiClient`: Uses external API for resource creation

4. **Bang Commands**:
   - `!books` or `!book <title>`: Searches book content
   - `!testcmd`: Test command
   - Extensible system for adding new commands

## Environment Variables
- `LLM_BASE_URL`: Target LLM API endpoint
- `LOGFIRE_TOKEN`: Token for Logfire monitoring
- `BOOKS_DIR_PATH`: Directory containing book .txt files (default: ./context/books/)
- `REDIS_URL`: Redis connection URL (default: redis://redis:6379)
- `CONTEXT_KILLER_API_BASE_URL`: Scraping service URL (default: http://127.0.0.1:8000)

## Build and Deploy
```bash
# Build the Docker image
./scripts/docker_build.sh

# Deploy with docker-compose
docker compose up -d

# View logs
docker logs oai-proxy -f

# Restart containers
docker compose restart
```

## Redis Cache Management
```bash
# Check cached keys
docker exec oai-proxy-redis redis-cli keys "*"

# Check TTL on a key
docker exec oai-proxy-redis redis-cli ttl "<key>"

# Flush/clear all cache
docker exec oai-proxy-redis redis-cli FLUSHDB

# View a cached value
docker exec oai-proxy-redis redis-cli get "<key>"
```

## Testing
Run tests with: `pytest`

## Docker
Build: `./scripts/docker_build.sh`
Run: `docker-compose up -d`
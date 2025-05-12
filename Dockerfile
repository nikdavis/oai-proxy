FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# better caching this way
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app

# Set the default command to run the API
CMD ["uv", "run", "python", "-m", "src.main"]

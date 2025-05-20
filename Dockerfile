FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory first
WORKDIR /app

# better caching this way
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

# Copy the project into the image
ADD . .

# Sync the project into a new environment, asserting the lockfile is up to date
# This step might be redundant now if the above sync correctly creates the venv in /app
# We'll keep it for now to ensure correctness, can be removed if confirmed redundant.

# Set the default command to run the API
CMD ["uv", "run", "python", "-m", "src.main"]

# Use a lightweight Python 3.12 base image
FROM python:3.12-slim

# Copy the uv binary directly from the official image for blazing-fast installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory inside the container
WORKDIR /app

# Explicitly define the Python path so module imports resolve correctly globally
ENV PYTHONPATH=/app

# Copy the lockfile and configuration first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies only
RUN uv sync --frozen --no-dev --no-install-project

# Download model files directly into a local folder inside /app
RUN uv run --no-sync python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-small-en-v1.5', local_dir='/app/models/bge-small-en-v1.5')"

# Copy the rest of the application code
COPY ./backend ./backend

# Expose the port FastAPI runs on
EXPOSE 8080

# Start the FastAPI server
CMD ["sh", "-c", "uv run --no-sync python backend/scripts/init_db.py && uv run --no-sync uvicorn backend.app.main:app --host 0.0.0.0 --port 8080"]
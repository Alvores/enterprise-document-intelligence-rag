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

# Install dependencies only (frozen ensures exact lockfile match, no-dev omits testing tools)
# --no-install-project allows building the environment before copying the app source code
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application code
COPY ./backend ./backend

# Expose the port FastAPI runs on
EXPOSE 8000

# Start the FastAPI server using the uv virtual environment environment
CMD ["sh", "-c", "uv run python backend/scripts/init_db.py && uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]

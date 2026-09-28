FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv

WORKDIR /app

# Install locked dependencies first so this layer is cached between code changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN chmod +x start.sh

# Runs the monitor in the background and the API in the foreground
CMD ["./start.sh"]

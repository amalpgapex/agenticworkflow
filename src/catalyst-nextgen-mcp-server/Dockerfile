FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

ENV MCP_PORT=8010
EXPOSE 8010
CMD ["uv", "run", "uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8010"]
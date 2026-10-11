FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY definitions ./definitions
COPY templates ./templates

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
CMD ["wf", "--help"]

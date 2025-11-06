FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY pyproject.toml .
COPY claudebridge/ claudebridge/

RUN python -m claudebridge.scripts.download_deps

RUN pip install --no-cache-dir build
RUN python -m build --wheel

RUN pip install --no-cache-dir dist/*.whl

FROM python:3.11-alpine
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/claudebridge /usr/local/bin/claudebridge
ENV DEBUG=info
CMD ["claudebridge"]

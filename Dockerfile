FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
RUN curl -sL https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.16/tailwindcss-linux-x64 -o /usr/local/bin/tailwindcss && \ 
    chmod +x /usr/local/bin/tailwindcss
WORKDIR /build

COPY pyproject.toml .
COPY claudebridge/ claudebridge/
COPY styles/ styles/
COPY tailwind.config.js .


RUN pip install --no-cache-dir build
RUN python -m claudebridge.scripts.build

RUN pip install --no-cache-dir dist/*.whl

FROM python:3.11-alpine
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/claudeprobridge /usr/local/bin/claudeprobridge
ENV DEBUG=info
CMD ["claudeprobridge"]

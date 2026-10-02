FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server.py /app/server.py

RUN useradd -u 10001 -m renderer && mkdir -p /tmp/tcg-render && chown -R renderer:renderer /tmp/tcg-render /app
USER renderer

ENV PYTHONUNBUFFERED=1 PORT=10000
EXPOSE 10000
CMD ["python", "-u", "/app/server.py"]

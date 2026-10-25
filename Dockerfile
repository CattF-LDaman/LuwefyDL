FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY music_importer/ music_importer/

RUN mkdir -p /data/music /app/temp \
    && chown -R appuser:appuser /app /data/music

ENV DOCKER=1 \
    MUSIC_LIBRARY_PATH=/data/music \
    PORT=8080 \
    SHOW_BROWSER=false

USER appuser

EXPOSE 8080

CMD ["python", "-m", "music_importer.main"]

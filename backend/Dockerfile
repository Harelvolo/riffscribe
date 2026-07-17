FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    fluidsynth \
    ffmpeg \
    libsndfile1 \
    libchromaprint-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY assets ./assets
COPY google_client_id.txt ./google_client_id.txt

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Mount a host volume at /app/storage so uploads/generated audio/the SQLite
# db survive container restarts and redeploys.
VOLUME ["/app/storage"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

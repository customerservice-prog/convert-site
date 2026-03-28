FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    DOWNLOAD_DIR=/data/downloads \
    DATABASE_URL=sqlite:////data/jobs.db

RUN mkdir -p /data/downloads

EXPOSE 8000

# Run with a non-root user only if /data is writable for that uid (see README).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

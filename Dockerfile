FROM node:20-alpine AS frontend-build
WORKDIR /fe
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DATA_DIR=/data \
    DOWNLOAD_DIR=/data/downloads \
    DATABASE_URL=sqlite:////data/jobs.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY main.py cleanup.py requirements.txt pytest.ini ./
COPY legal ./legal
COPY tests ./tests
COPY --from=frontend-build /fe/dist ./frontend/dist

RUN mkdir -p /data/downloads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

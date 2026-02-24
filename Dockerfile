FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

COPY . .

EXPOSE 5000

ENV APP_ROLE=web \
    GUNICORN_BIND=0.0.0.0:5000 \
    GUNICORN_WORKERS=3

CMD ["sh", "-c", "if [ \"$APP_ROLE\" = \"worker\" ]; then python worker.py; else gunicorn --bind \"$GUNICORN_BIND\" --workers \"$GUNICORN_WORKERS\" app:app; fi"]

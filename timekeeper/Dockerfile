FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home timekeeper && mkdir /data && chown timekeeper:timekeeper /data
COPY . .
USER timekeeper
EXPOSE 8000
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "45", "app:create_app()"]

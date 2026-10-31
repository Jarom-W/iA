FROM python:3.13-slim
WORKDIR /app
COPY feedback/requirements.txt .
COPY platform_auth /opt/platform_auth
RUN pip install --no-cache-dir /opt/platform_auth -r requirements.txt && useradd --uid 10001 --create-home feedback && mkdir /data && chown feedback:feedback /data
COPY feedback/ .
USER feedback
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "45", "app:create_app()"]

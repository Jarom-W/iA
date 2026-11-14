FROM python:3.13-slim
WORKDIR /app
COPY survey/requirements.txt .
COPY platform_auth /opt/platform_auth
RUN pip install --no-cache-dir /opt/platform_auth -r requirements.txt && useradd --uid 10001 --create-home survey && mkdir /data && chown survey:survey /data
COPY --chown=survey:survey survey/ .
RUN chmod -R a+rX /app /opt/platform_auth
USER survey
EXPOSE 8000
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "45", "app:create_app()"]

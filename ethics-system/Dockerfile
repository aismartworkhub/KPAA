FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    KPAA_DATA_DIR=/data KPAA_FRONTEND_DIR=/app/frontend
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY frontend /app/frontend
RUN useradd --system --uid 10001 kpaa && mkdir -p /data && chown kpaa /data
USER kpaa
WORKDIR /app/backend
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
